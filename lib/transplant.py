import os
import re
import logging
import base64
import traceback
from collections import defaultdict

from bcoding import bencode, bdecode
from hashlib import sha1, sha256

from gazelle import upload
from gazelle.tracker_data import tr
from gazelle.api_classes import sleeve

from lib import utils, ui_text
from lib.info_2_upl import TorInfo2UplData

choose_the_other = utils.choose_the_other([tr.RED, tr.OPS])
report = logging.getLogger(__name__)

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
            self.dest_trs = [choose_the_other(self.src_tr)]

    def parse_dtorrent(self, path):
        with open(path, "rb") as f:
            torbytes = f.read()
        self.dtor_dict = bdecode(torbytes)
        announce = self.dtor_dict['announce']

        tr_domain = re.search(r"https?://(.+?)/.+", announce).group(1)
        for t in tr:
            if tr_domain in t.tracker:
                self.src_tr = t
                break

        info = self.dtor_dict['info']
        self.info_hash = sha1(bencode(info)).hexdigest()

    def __hash__(self):
        return int(self.info_hash or f'{hash((self.src_tr, self.tor_id)):x}', 16)

    def __eq__(self, other):
        return (self.info_hash or (self.src_tr, self.tor_id)) == (other.info_hash or (other.src_tr, other.tor_id))


class Transplanter:
    def __init__(self, key_dict, data_dir=None, deep_search=False, dtor_save_dir=None, save_dtors=False, del_dtors=False,
                 file_check=True, rel_descr_templ=None, rel_descr_own_templ=None, add_src_descr=True, src_descr_templ=None,
                 img_rehost=False, whitelist=None, ptpimg_key=None, post_compare=False):

        self.api_map = {trckr: sleeve(trckr, key=key_dict[trckr]) for trckr in tr}
        self.data_dir = data_dir
        self.deep_search = deep_search
        self.dtor_save_dir = dtor_save_dir
        self.save_dtors = save_dtors
        self.del_dtors = del_dtors
        self.file_check = file_check
        self.img_rehost = img_rehost
        self.whitelist = whitelist
        self.ptpimg_key = ptpimg_key
        self.rel_descr_templ = rel_descr_templ
        self.rel_descr_own_templ = rel_descr_own_templ
        self.add_src_descr = add_src_descr
        self.src_descr_templ = src_descr_templ
        self.post_compare = post_compare

        if img_rehost:
            assert isinstance(whitelist, list)
            assert isinstance(ptpimg_key, str)

        self.job = None
        self.tor_info = None
        self._subdir_index = None
        self._torrent_folder_path = None

    def do_your_job(self, job):
        self.tor_info = None
        self._torrent_folder_path = None
        self.job = job
        report.info(f"\n{self.job.src_tr.name} {self.job.display_name or self.job.tor_id}")

        src_api = self.api_map[self.job.src_tr]

        report.info(ui_text.requesting)
        if self.job.tor_id:
            self.tor_info = src_api.torrent_info(id=self.job.tor_id)
        elif self.job.info_hash:
            self.tor_info = src_api.torrent_info(hash=self.job.info_hash)
        else:
            return False

        self.job.display_name = self.job.display_name or self.tor_info.folder_name
        report.info(self.job.display_name)

        if self.file_check:
            self.check_files()

        upl_data = TorInfo2UplData(self.tor_info, self.img_rehost, self.whitelist, self.ptpimg_key,
                                   self.rel_descr_templ, self.rel_descr_own_templ, self.add_src_descr,
                                   self.src_descr_templ, src_api.account_info['id'])
        upl_files = upload.Files()
        self.get_dtor(upl_files)
        if self.tor_info.haslog:
            self.get_logs(upl_files)

        saul_goodman = True
        for dest_tr in self.job.dest_trs:

            dest_api = self.api_map[dest_tr]

            report.info(f"{ui_text.upl1} {dest_api.tr.name}")
            try:
                new_id, new_group, new_url = dest_api.upload(upl_data, upl_files, dest_group=self.job.dest_group)
                report.info(f"{ui_text.upl2} {new_url}")
            except Exception:
                saul_goodman = False
                report.error(f"{ui_text.upl3}")
                report.error(traceback.format_exc(chain=False))
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
    def subdir_index(self):
        if not self._subdir_index:
            subdirs = defaultdict(list)
            for root, dirs, files in os.walk(self.data_dir):
                for d in dirs:
                    subdirs[d].append(root)
            self._subdir_index = dict(subdirs)

        return self._subdir_index

    @property
    def torrent_folder_path(self):
        if not self._torrent_folder_path:
            if self.deep_search:
                try:
                    rootpath_list = self.subdir_index[self.tor_info.folder_name]
                except KeyError:
                    raise FileNotFoundError(f"{ui_text.missing} {self.tor_info.folder_name}")

                if len(rootpath_list) > 1:
                    raise Exception(f'"{self.tor_info.folder_name}" {ui_text.multiple}')

                self._torrent_folder_path = os.path.join(rootpath_list[0], self.tor_info.folder_name)
            else:
                self._torrent_folder_path = os.path.join(self.data_dir, self.tor_info.folder_name)

        return self._torrent_folder_path

    def compare_upl_info(self, src_api, dest_api, new_id):
        new_tor_info = dest_api.torrent_info(id=new_id)

        if self.tor_info.haslog:
            score_1 = self.tor_info.log_score
            score_2 = new_tor_info.log_score
            if not score_1 == score_2:
                report.info(ui_text.log_score_dif.format(score_1, score_2))

        src_descr = self.tor_info.alb_descr.replace(src_api.url, '')
        dest_descr = new_tor_info.alb_descr.replace(dest_api.url, '')

        if src_descr != dest_descr or self.tor_info.title != new_tor_info.title:
            report.info(ui_text.merged)

    def get_dtor(self, files):
        if self.job.new_dtor:
            files.add_dtor(self.create_new_torrent(), as_dict=True)

        elif self.job.dtor_dict:
            files.add_dtor(self.job.dtor_dict, as_dict=True)
        else:
            dtor_bytes = self.api_map[self.job.src_tr].request("GET", "download", id=self.tor_info.tor_id)
            files.add_dtor(dtor_bytes)

    def get_logs(self, files):

        def is_riplog(fn):
            if fn.endswith('.log') and not any(x in fn.lower() for x in ("audiochecker", "aucdtect", "accurip")):
                return True

        if self.job.new_dtor:
            for path in utils.file_list_gen(self.torrent_folder_path):
                fn = os.path.basename(path)
                if is_riplog(fn):
                    files.add_log(path, as_path=True)
        elif not self.file_check and self.tor_info.log_ids:
            for i in self.tor_info.log_ids:
                r = self.api_map[self.job.src_tr].request("GET", "riplog", id=self.tor_info.tor_id, logid=i)
                log_bytes = base64.b64decode(r["log"])
                log_checksum = sha256(log_bytes).hexdigest()
                assert log_checksum == r['log_sha256']
                files.add_log(log_bytes)
        else:
            for fl in self.tor_info.file_list:
                fn = fl['names'][-1]
                if is_riplog(fn):
                    files.add_log(os.path.join(self.torrent_folder_path, *fl['names']), as_path=True)

            assert files.logs, ui_text.no_log

    def create_new_torrent(self):
        from dottorrent import Torrent

        report.info(ui_text.new_tor)
        t = Torrent(self.torrent_folder_path, private=True)
        t.generate()

        return t.data

    def check_files(self):
        for fl in self.tor_info.file_list:
            file_path = os.path.join(self.torrent_folder_path, *fl['names'])
            if not os.path.isfile(file_path):
                raise FileNotFoundError(f"{ui_text.missing} {file_path}")
        report.info(ui_text.f_checked)

    def save_dtorrent(self, files, comment=None):
        dtor = files.dtors[0].as_dict
        if comment:
            dtor['comment'] = comment
        file_path = os.path.join(self.dtor_save_dir, self.tor_info.folder_name) + ".torrent"
        with open(file_path, "wb") as f:
            f.write(bencode(dtor))
