from pathlib import Path
import logging
from hashlib import sha1
from urllib.parse import urlparse

from bcoding import bencode, bdecode

from gazelle import upload
from gazelle.tracker_data import TR
from gazelle.api_classes import sleeve, BaseApi, OpsApi, RedApi
from gazelle.torrent_info import TorrentInfo
from lib import utils, tp_text
from lib.info_2_upl import TorInfo2UplData
from lib.lean_torrent import Torrent

report = logging.getLogger('tr.core')


class JobCreationError(Exception):
    pass


class Job:
    def __init__(self, src_tr=None, tor_id=None, src_dom=None, dtor_path=None, scanned=False, dest_group=None,
                 new_dtor=False, dest_trs=None):

        self.src_tr = src_tr
        self.tor_id = tor_id
        self.scanned = scanned
        self.dtor_path: Path = dtor_path
        self.dest_group = dest_group
        self.new_dtor = new_dtor
        self.dest_trs = dest_trs

        self.info_hash = None
        self.display_name = None
        self.dtor_dict = None

        if self.dtor_path:
            self.parse_dtorrent(self.dtor_path)
            self.display_name = self.dtor_path.stem

        if src_dom:
            for t in TR:
                if src_dom in t.site:
                    self.src_tr = t
                    break

        if not self.src_tr:
            raise JobCreationError(tp_text.no_src_tr)

        if (self.tor_id is None) == (self.info_hash is None):
            raise JobCreationError(tp_text.id_and_hash)

        if not self.dest_trs:
            self.dest_trs = ~self.src_tr

    def parse_dtorrent(self, path: Path):
        torbytes = path.read_bytes()
        try:
            self.dtor_dict = bdecode(torbytes)
            info = self.dtor_dict['info']
        except (KeyError, TypeError):
            raise JobCreationError(tp_text.not_dtor)

        source = info.get('source', '').replace('PTH', 'RED')
        self.info_hash = sha1(bencode(info)).hexdigest()

        if source:
            try:
                self.src_tr = TR[source]
                return
            except KeyError:
                pass

        announce = self.dtor_dict.get('announce')
        if not announce:
            return
        parsed = urlparse(announce)
        if parsed.hostname:
            for t in TR:
                if parsed.hostname in t.tracker.lower():
                    self.src_tr = t
                    break

    def __hash__(self):
        return int(self.info_hash or f'{hash((self.src_tr, self.tor_id)):x}', 16)

    def __eq__(self, other):
        return (self.info_hash or (self.src_tr, self.tor_id)) == (other.info_hash or (other.src_tr, other.tor_id))


class Transplanter:
    def __init__(self, key_dict, data_dir=None, deep_search=False, deep_search_level=None, dtor_save_dir=None,
                 save_dtors=False, del_dtors=False, file_check=True, rel_descr_templ=None, rel_descr_own_templ=None,
                 add_src_descr=True, src_descr_templ=None, img_rehost=False, whitelist=None, post_compare=False):

        self.api_map = {trckr: sleeve(trckr, key=key_dict[trckr]) for trckr in TR}
        self.data_dir: Path = data_dir
        self.deep_search = deep_search
        self.deep_search_level = deep_search_level
        self.dtor_save_dir: Path | None = dtor_save_dir
        self.save_dtors = save_dtors
        self.del_dtors = del_dtors
        self.file_check = file_check
        self.img_rehost = img_rehost
        self.whitelist = whitelist
        self.rel_descr_templ = rel_descr_templ
        self.rel_descr_own_templ = rel_descr_own_templ
        self.add_src_descr = add_src_descr
        self.src_descr_templ = src_descr_templ
        self.post_compare = post_compare

        if img_rehost:
            assert isinstance(whitelist, list)

        if self.deep_search:
            self.subdir_store = {}
            self.subdir_gen = utils.subdirs_gen(self.data_dir, maxlevel=self.deep_search_level)

        self.job = None
        self.tor_info = None
        self._torrent_folder_path = None
        self.lrm = False
        self.local_is_stripped = False

    def do_your_job(self, job: Job) -> bool:
        self.job = job
        self.tor_info = None
        self._torrent_folder_path = None
        self.lrm = False
        self.local_is_stripped = False

        report.info(f"{self.job.src_tr.name} {self.job.display_name or self.job.tor_id}")

        src_api = self.api_map[self.job.src_tr]

        report.info(tp_text.requesting)
        if self.job.tor_id:
            info_kwarg = {'id': self.job.tor_id}
        elif self.job.info_hash:
            info_kwarg = {'hash': self.job.info_hash}
        else:
            return False
        self.tor_info: TorrentInfo = src_api.torrent_info(**info_kwarg)

        if not self.tor_info.folder_name:
            report.error(tp_text.no_torfolder)
            return False

        if not self.job.display_name:
            self.job.display_name = self.tor_info.folder_name
            report.info(self.job.display_name)

        if self.tor_folder_is_needed_but_is_missing():
            report.error(f"{tp_text.missing} {self.tor_info.folder_name}")
            return False

        if self.file_check and not self.check_files():
            return False

        upl_files = upload.Files()

        if (self.tor_info.haslog or self.job.new_dtor) and not self.get_logs(upl_files, src_api):
            return False

        upl_data = TorInfo2UplData(self.tor_info, self.img_rehost, self.whitelist,
                                   self.rel_descr_templ, self.rel_descr_own_templ, self.add_src_descr,
                                   self.src_descr_templ, src_api.account_info['id'], self.job.dest_group)

        saul_goodman = True
        for dest_tr in self.job.dest_trs:

            dest_api = self.api_map[dest_tr]
            try:
                data_dict = upl_data.upl_dict(dest_tr, self.job.dest_group)
            except ValueError as e:
                saul_goodman = False
                report.error(str(e))
                continue

            if not upl_files.dtors:
                self.get_dtor(upl_files, src_api)
            files_list = upl_files.files_list(dest_api.announce, dest_tr.name, u_strip=self.strip_tor)

            report.info(f"{tp_text.upl1} {dest_tr.name}")
            try:
                new_id, new_group, new_url = dest_api.upload(data_dict, files_list)
                report.log(25, f"{tp_text.upl2} {new_url}")
            except Exception:
                saul_goodman = False
                report.exception(f"{tp_text.upl3}")
                continue

            if self.post_compare:
                self.compare_upl_info(src_api, dest_api, new_id)

            if self.save_dtors:
                self.save_dtorrent(upl_files, new_url)
                report.info(f"{tp_text.dtor_saved} {self.dtor_save_dir}")

        if not saul_goodman:
            return False
        elif self.del_dtors and self.job.scanned:
            self.job.dtor_path.unlink()
            report.info(tp_text.dtor_deleted)

        return True

    @property
    def strip_tor(self) -> bool:
        return self.lrm == self.local_is_stripped is True

    def tor_folder_is_needed_but_is_missing(self):
        if self.file_check or self.job.new_dtor or (self.tor_info.haslog and not self.tor_info.log_ids):
            return self.torrent_folder_path is None
        else:
            return False

    @property
    def torrent_folder_path(self) -> Path:
        if not self._torrent_folder_path:
            tor_folder_name: str = self.tor_info.folder_name
            stripped_folder = tor_folder_name.translate(utils.uni_t_table)
            if stripped_folder != tor_folder_name:
                self.lrm = True

            if (p := self.data_dir / tor_folder_name).exists():
                self._torrent_folder_path = p
            elif self.lrm and (p := self.data_dir / stripped_folder).exists():
                self._torrent_folder_path = p
                self.local_is_stripped = True

            elif self.deep_search:
                self.search_deep(tor_folder_name, stripped_folder)

        return self._torrent_folder_path

    def search_deep(self, tor_folder_name: str, stripped_folder: str):
        if tor_folder_name in self.subdir_store:
            self._torrent_folder_path = self.subdir_store[tor_folder_name]
            return
        if self.lrm and stripped_folder in self.subdir_store:
            self._torrent_folder_path = self.subdir_store[stripped_folder]
            self.local_is_stripped = True
            return

        for p in self.subdir_gen:
            if p.name == tor_folder_name:
                self._torrent_folder_path = p
                break
            elif self.lrm and p.name == stripped_folder:
                self._torrent_folder_path = p
                self.local_is_stripped = True
                break
            else:
                self.subdir_store[p.name] = p

    def compare_upl_info(self, src_api: BaseApi, dest_api: BaseApi, new_id: int):
        new_tor_info = dest_api.torrent_info(id=new_id)

        if self.tor_info.haslog:
            score_1 = self.tor_info.log_score
            score_2 = new_tor_info.log_score
            if not score_1 == score_2:
                report.warning(tp_text.log_score_dif.format(score_1, score_2))

        src_descr = self.tor_info.alb_descr.replace(src_api.url, '')
        dest_descr = new_tor_info.alb_descr.replace(dest_api.url, '')

        if src_descr != dest_descr or self.tor_info.title != new_tor_info.title:
            report.warning(tp_text.merged)

    def get_dtor(self, files: upload.Files, src_api: BaseApi):
        if self.job.new_dtor:
            files.add_dtor(self.create_new_torrent())

        elif self.job.dtor_dict:
            files.add_dtor(self.job.dtor_dict)
        else:
            dtor_bytes = src_api.request('download', id=self.tor_info.tor_id)
            report.info(tp_text.tor_downed.format(self.job.src_tr.name))
            dtor_dict = bdecode(dtor_bytes)
            self.job.dtor_dict = dtor_dict
            files.add_dtor(dtor_dict)

    NOT_RIPLOG = ('audiochecker', 'aucdtect', 'accurip')

    def is_riplog(self, fn: str) -> bool:
        return not any(x in fn.lower() for x in self.NOT_RIPLOG)

    def get_logs(self, files: upload.Files, src_api: BaseApi | OpsApi | RedApi) -> bool:
        if self.job.new_dtor:
            for p in self.torrent_folder_path.rglob('*.log'):
                if self.is_riplog(p.name):
                    files.add_log(p)

            return True  # new torrent may have no log while original had one

        elif not self.file_check and self.tor_info.log_ids:
            for i in self.tor_info.log_ids:
                files.add_log(src_api.get_riplog(self.tor_info.tor_id, i))
        else:
            for p in self.tor_info.glob('*.log'):
                if not self.is_riplog(p.name):
                    continue
                found = self.check_path(p)
                if found is None:
                    report.error(f"{tp_text.missing} {p}")
                    return False

                files.add_log(found)

        if self.tor_info.log_ids:
            tor_log_count = len(self.tor_info.log_ids)
            found = len(files.logs)
            if tor_log_count != found:
                report.warning(tp_text.log_count_wrong.format(tor_log_count, found))

        elif not files.logs:
            report.error(tp_text.no_log)
            return False

        return True

    def create_new_torrent(self) -> dict:
        report.info(tp_text.new_tor)
        t = Torrent(self.torrent_folder_path)

        return t.data

    def check_path(self, rel_path: Path) -> Path | None:
        stripped = Path(str(rel_path).translate(utils.uni_t_table))

        has_lrm = rel_path != stripped
        if has_lrm:
            self.lrm = True

        full_p = self.torrent_folder_path / rel_path
        if full_p.exists():
            return full_p
        elif has_lrm:
            fp_stripped = self.torrent_folder_path / stripped
            if fp_stripped.exists():
                self.local_is_stripped = True
                return fp_stripped

    def check_files(self) -> bool:
        if self.job.new_dtor:
            return True

        for info_path in self.tor_info.file_paths():
            if self.check_path(info_path) is None:
                report.error(f"{tp_text.missing} {info_path}")
                return False

        report.info(tp_text.f_checked)
        return True

    def save_dtorrent(self, files: upload.Files, comment: str = None):
        dtor = files.dtors[0].as_dict(u_strip=self.strip_tor)
        if comment:
            dtor['comment'] = comment
        file_path = (self.dtor_save_dir / self.tor_info.folder_name).with_suffix('.torrent')
        file_path.write_bytes(bencode(dtor))
