import os
import re
import logging
import base64
import traceback
from collections import defaultdict

from bencoder import bencode, bdecode
from hashlib import sha1, sha256

from gazelle import upload
from gazelle.tracker_data import tr, tr_data

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
            for t, data in tr_data.items():
                if src_dom in data['site']:
                    self.src_tr = t
                    break

        assert self.src_tr
        assert self.tor_id or self.info_hash
        assert not (self.tor_id and self.info_hash)

        if not self.dest_trs:
            self.dest_trs = [choose_the_other(self.src_tr)]

    def update(self, settings_dict):
        for k, v in settings_dict.items():
            if hasattr(self, k):
                setattr(self, k, v)

    def parse_dtorrent(self, path):
        with open(path, "rb") as f:
            torbytes = f.read()
        self.dtor_dict = bdecode(torbytes)
        announce = self.dtor_dict[b'announce'].decode()

        tr_domain = re.search(r"https?://(.+?)/.+", announce).group(1)
        for t, data in tr_data.items():
            if tr_domain in data['tracker']:
                self.src_tr = t
                break

        info = self.dtor_dict[b'info']
        self.info_hash = sha1(bencode(info)).hexdigest()

    def __hash__(self):
        return self.info_hash or hash((self.src_tr, self.tor_id))

    def __eq__(self, other):
        return (self.info_hash or (self.src_tr, self.tor_id)) == (other.info_hash or (other.src_tr, other.tor_id))


class Transplanter:
    def __init__(self, api_map, data_dir=None, dtor_save_dir=None, save_dtors=False, del_dtors=False, file_check=True,
                 rel_descr_templ=None, add_src_descr=True, src_descr_templ=None, img_rehost=False, whitelist=None,
                 ptpimg_key=None):

        self.api_map = api_map
        self.data_dir = data_dir
        self.dtor_save_dir = dtor_save_dir
        self.save_dtors = save_dtors
        self.del_dtors = del_dtors
        self.file_check = file_check
        self.img_rehost = img_rehost
        self.whitelist = whitelist
        self.ptpimg_key = ptpimg_key
        self.rel_descr_templ = rel_descr_templ
        self.add_src_descr = add_src_descr
        self.src_descr_templ = src_descr_templ

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
                                   self.rel_descr_templ, self.add_src_descr, self.src_descr_templ)
        upl_files = upload.Files()
        self.get_dtor(upl_files)
        if self.tor_info.haslog:
            self.get_logs(upl_files)

        saul_goodman = True
        for dest_tr in self.job.dest_trs:

            dest_api = self.api_map[dest_tr]

            report.info(f"{ui_text.upl1} {dest_api.tr.name}")
            try:
                new_url = dest_api.upload(upl_data, upl_files)
                report.info(f"{ui_text.upl2} {new_url}")
            except Exception:
                saul_goodman = False
                report.error(f"{ui_text.upl3}")
                report.error(traceback.format_exc())
                continue

            if self.save_dtors:
                self.save_dtorrent(upl_files, new_url)
                report.info(f"{ui_text.dtor_saved} {self.dtor_save_dir}")

        if saul_goodman and self.del_dtors and self.job.scanned:
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
            try:
                rootpath_list = self.subdir_index[self.tor_info.folder_name]
            except KeyError:
                raise FileNotFoundError(f"{ui_text.missing} {self.tor_info.folder_name}")

            if len(rootpath_list) > 1:
                raise Exception(f'"{self.tor_info.folder_name}" found multiple times')

            self._torrent_folder_path = os.path.join(rootpath_list[0], self.tor_info.folder_name)

        return self._torrent_folder_path

    def get_dtor(self, files):
        if self.job.new_dtor:
            files.add_dtor(self.create_new_torrent(), as_dict=True)

        elif self.job.dtor_dict:
            files.add_dtor(self.job.dtor_dict, as_dict=True)
        else:
            dtor_bytes = self.api_map[self.job.src_tr].request("GET", "download", id=self.tor_info.tor_id).content
            files.add_dtor(dtor_bytes)

    def get_logs(self, files):
        if self.tor_info.log_ids:
            for i in self.tor_info.log_ids:
                r = self.api_map[self.job.src_tr].request("GET", "riplog", id=self.tor_info.tor_id, logid=i)
                log_bytes = base64.b64decode(r["log"])
                log_checksum = sha256(log_bytes).hexdigest()
                assert log_checksum == r['log_sha256']
                files.add_log(log_bytes)
        else:
            for path in utils.file_list_gen(self.torrent_folder_path):
                fn = os.path.basename(path)
                if fn.endswith(".log") and fn.lower() not in upload.LOGS_TO_IGNORE:
                    files.add_log(path, as_path=True)
            assert files.logs, ui_text.no_log

    def create_new_torrent(self):
        from dottorrent import Torrent

        report.info(ui_text.new_tor)
        t = Torrent(self.torrent_folder_path, private=True)
        t.generate()

        # dottorrent creates dict with string keys.
        # Following code will add bytes keys. and key type must be uniform for bencoder to encode.
        utils.dict_stringkeys_to_bytes(t.data)
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
            dtor[b'comment'] = comment.encode()
        file_path = os.path.join(self.dtor_save_dir, self.tor_info.folder_name) + ".torrent"
        with open(file_path, "wb") as f:
            f.write(bencode(dtor))
