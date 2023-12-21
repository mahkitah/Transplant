import os
import logging
from hashlib import sha1

from urllib.parse import urlparse

from bcoding import bencode, bdecode

from gazelle import upload
from gazelle.tracker_data import tr
from gazelle.api_classes import sleeve

from lib import utils, ui_text
from lib.info_2_upl import TorInfo2UplData
from lib.lean_torrent import Torrent

report = logging.getLogger('tr.core')

class Job:
    def __init__(self, src_tr=None, tor_id=None, src_dom=None, dtor_path=None, scanned=False, dest_group=None,
                 new_dtor=False, dest_trs=None):

        self.src_tr = src_tr
        self.tor_id = tor_id
        self.scanned = scanned
        self.dtor_path = dtor_path
        self.dest_group = dest_group
        self.new_dtor = new_dtor
        self.dest_trs = dest_trs

        self.info_hash = None
        self.display_name = None
        self.dtor_dict = None

        if dtor_path:
            self.parse_dtorrent(dtor_path)
            self.display_name = os.path.splitext(os.path.basename(dtor_path))[0]

        if src_dom:
            for t in tr:
                if src_dom in t.site:
                    self.src_tr = t
                    break

        assert self.src_tr
        assert (self.tor_id is None) != (self.info_hash is None)

        if not self.dest_trs:
            self.dest_trs = [~self.src_tr]

    def parse_dtorrent(self, path):
        with open(path, "rb") as f:
            torbytes = f.read()
        self.dtor_dict = bdecode(torbytes)

        announce = self.dtor_dict.get('announce')
        info = self.dtor_dict['info']
        source = info.get('source', '').replace('PTH', 'RED')
        self.info_hash = sha1(bencode(info)).hexdigest()

        if source:
            try:
                self.src_tr = tr[source]
                return
            except KeyError:
                pass

        if not announce:
            return
        parsed = urlparse(announce)
        if parsed.hostname:
            for t in tr:
                if parsed.hostname in t.tracker.lower():
                    self.src_tr = t
                    break

    def __hash__(self):
        return int(self.info_hash or f'{hash((self.src_tr, self.tor_id)):x}', 16)

    def __eq__(self, other):
        return (self.info_hash or (self.src_tr, self.tor_id)) == (other.info_hash or (other.src_tr, other.tor_id))


class Transplanter:
    def __init__(self, key_dict, data_dir=None, deep_search=False, deep_search_level=None, dtor_save_dir=None, save_dtors=False, del_dtors=False,
                 file_check=True, rel_descr_templ=None, rel_descr_own_templ=None, add_src_descr=True, src_descr_templ=None,
                 img_rehost=False, whitelist=None, post_compare=False):

        self.api_map = {trckr: sleeve(trckr, key=key_dict[trckr]) for trckr in tr}
        self.data_dir = data_dir
        self.deep_search = deep_search
        self.deep_search_level = deep_search_level
        self.dtor_save_dir = dtor_save_dir
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

        self.job = None
        self.tor_info = None

        if self.deep_search:
            self.subdir_store = {}
            self.subdir_gen = utils.subdirs_gen(self.data_dir, maxlevel=self.deep_search_level)

    def do_your_job(self, job):
        self.tor_info = None
        self._torrent_folder_path = None
        self.job = job
        report.info(f"{self.job.src_tr.name} {self.job.display_name or self.job.tor_id}")

        src_api = self.api_map[self.job.src_tr]

        report.info(ui_text.requesting)
        if self.job.tor_id:
            self.tor_info = src_api.torrent_info(id=self.job.tor_id)
        elif self.job.info_hash:
            self.tor_info = src_api.torrent_info(hash=self.job.info_hash)
        else:
            return False

        if not self.job.display_name:
            self.job.display_name = self.tor_info.folder_name
            report.info(self.job.display_name)

        if (self.file_check or self.job.new_dtor) and not self.check_files():
            return False

        upl_data = TorInfo2UplData(self.tor_info, self.img_rehost, self.whitelist,
                                   self.rel_descr_templ, self.rel_descr_own_templ, self.add_src_descr,
                                   self.src_descr_templ, src_api.account_info['id'])
        upl_files = upload.Files()

        self.get_dtor(upl_files, src_api)

        if (self.tor_info.haslog or self.job.new_dtor) and not self.get_logs(upl_files, src_api):
            return False

        saul_goodman = True
        for dest_tr in self.job.dest_trs:

            dest_api = self.api_map[dest_tr]

            report.info(f"{ui_text.upl1} {dest_api.tr.name}")
            try:
                new_id, new_group, new_url = dest_api.upload(upl_data, upl_files, dest_group=self.job.dest_group)
                report.log(25, f"{ui_text.upl2} {new_url}")
            except Exception:
                saul_goodman = False
                report.exception(f"{ui_text.upl3}")
                continue

            if self.post_compare:
                self.compare_upl_info(src_api, dest_api, new_id)

            if self.save_dtors:
                self.save_dtorrent(upl_files, new_url)
                report.info(f"{ui_text.dtor_saved} {self.dtor_save_dir}")

        if not saul_goodman:
            return False
        elif self.del_dtors and self.job.scanned:
            os.remove(self.job.dtor_path)
            report.info(ui_text.dtor_deleted)

        return True

    @property
    def torrent_folder_path(self):
        if not self._torrent_folder_path:
            tor_folder_name = self.tor_info.folder_name
            if self.deep_search:
                if tor_folder_name in self.subdir_store:
                    self._torrent_folder_path = os.path.join(self.subdir_store[tor_folder_name], tor_folder_name)
                else:
                    for root, subdir in self.subdir_gen:
                        if subdir == tor_folder_name:
                            self._torrent_folder_path = os.path.join(root, subdir)
                            break
                        else:
                            self.subdir_store[subdir] = root
            else:
                self._torrent_folder_path = os.path.join(self.data_dir, tor_folder_name)

        return self._torrent_folder_path

    def compare_upl_info(self, src_api, dest_api, new_id):
        new_tor_info = dest_api.torrent_info(id=new_id)

        if self.tor_info.haslog:
            score_1 = self.tor_info.log_score
            score_2 = new_tor_info.log_score
            if not score_1 == score_2:
                report.warning(ui_text.log_score_dif.format(score_1, score_2))

        src_descr = self.tor_info.alb_descr.replace(src_api.url, '')
        dest_descr = new_tor_info.alb_descr.replace(dest_api.url, '')

        if src_descr != dest_descr or self.tor_info.title != new_tor_info.title:
            report.warning(ui_text.merged)

    def get_dtor(self, files, src_api):
        if self.job.new_dtor:
            files.add_dtor(self.create_new_torrent(), as_dict=True)

        elif self.job.dtor_dict:
            files.add_dtor(self.job.dtor_dict, as_dict=True)
        else:
            dtor_bytes = src_api.request('download', id=self.tor_info.tor_id)
            files.add_dtor(dtor_bytes)

    def get_logs(self, files: upload.Files, src_api) -> bool:

        def is_riplog(fn):
            if fn.endswith('.log') and not any(x in fn.lower() for x in ("audiochecker", "aucdtect", "accurip")):
                return True

        if self.job.new_dtor:
            for scan in utils.scantree(self.torrent_folder_path):
                if is_riplog(scan.name):
                    files.add_log(scan.path, as_path=True)

            return True  # new torrent may have no log while original had one

        elif not self.file_check and self.tor_info.log_ids:
            for i in self.tor_info.log_ids:
                files.add_log(src_api.get_riplog(self.tor_info.tor_id, i))
        else:
            for fl in self.tor_info.file_list:
                fn = fl['names'][-1]

                if is_riplog(fn):
                    full_path = os.path.join(self.torrent_folder_path, *fl['names'])

                    if not os.path.exists(full_path):
                        report.error(f"{ui_text.missing} {full_path}")
                        return False

                    files.add_log(full_path, as_path=True)

        if not files.logs:
            report.error(ui_text.no_log)
            return False

        return True

    def create_new_torrent(self):
        report.info(ui_text.new_tor)
        t = Torrent(self.torrent_folder_path)

        return t.data

    def check_files(self):
        if self.job.new_dtor:
            if not os.path.exists(self.torrent_folder_path):
                report.error(f"{ui_text.missing} {self.torrent_folder_path}")
                return False
        else:
            for fl in self.tor_info.file_list:
                file_path = os.path.join(self.torrent_folder_path, *fl['names'])

                if not os.path.exists(file_path):
                    report.error(f"{ui_text.missing} {file_path}")
                    return False

        report.info(ui_text.f_checked)
        return True

    def save_dtorrent(self, files, comment=None):
        dtor = files.dtors[0].as_dict
        if comment:
            dtor['comment'] = comment
        file_path = os.path.join(self.dtor_save_dir, self.tor_info.folder_name) + ".torrent"
        with open(file_path, "wb") as f:
            f.write(bencode(dtor))
