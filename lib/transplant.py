import os
import html
import base64
import re

from bencoder import bencode, bdecode
from hashlib import sha1, sha256
from requests import HTTPError

from lib.gazelle_api import RequestFailure
from lib.torrent_info import TorrentInfo
from lib import utils, ui_text, constants, ptpimg_uploader

choose_the_other = utils.choose_the_other([ui_text.tracker_1, ui_text.tracker_2])


class Job:
    def __init__(self, src_id=None, tor_id=None, dtor_path=None, data_dir=None, dtor_save_dir=None, save_dtors=False,
                 del_dtors=False, file_check=True, img_rehost=False, whitelist=None, ptpimg_key=None, rel_descr=None,
                 add_src_descr=True, src_descr=None, dest_group=None, new_dtor=False):

        self.src_id = src_id
        self.tor_id = tor_id
        self.dtor_path = dtor_path
        self.data_dir = data_dir
        self.dtor_save_dir = dtor_save_dir
        self.save_dtors = save_dtors
        self.del_dtors = del_dtors
        self.file_check = file_check
        self.img_rehost = img_rehost
        self.whitelist = whitelist
        self.ptpimg_key = ptpimg_key
        self.rel_descr = rel_descr
        self.add_src_descr = add_src_descr
        self.src_descr = src_descr
        self.dest_group = dest_group
        self.new_dtor = new_dtor

        if img_rehost:
            assert type(whitelist) == list
            assert type(ptpimg_key) == str

        self.info_hash = None
        self.display_name = None
        self.dtor_dict = None

        if dtor_path:
            self.parse_dtorrent(dtor_path)
            self.display_name = os.path.splitext(os.path.basename(dtor_path))[0]

        assert self.src_id
        assert self.tor_id or self.info_hash
        assert not (self.tor_id and self.info_hash)

        self.dest_id = choose_the_other(self.src_id)

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
        assert tr_domain in constants.SITE_ID_MAP, "Not a RED or OPS torrent"
        self.src_id = constants.SITE_ID_MAP.get(tr_domain)
        info = self.dtor_dict[b'info']
        self.info_hash = sha1(bencode(info)).hexdigest()

    def __hash__(self):
        return hash((self.src_id, self.tor_id, self.info_hash))

    def __eq__(self, other):
        return (self.src_id, self.tor_id, self.info_hash) == (other.src_id, other.tor_id, other.info_hash)


class Transplanter:
    def __init__(self, job, api_map, report=lambda *x: None):

        self.report = report
        self.job = job

        self.report(f"\n{self.job.src_id} {self.job.display_name or self.job.tor_id}", 2)

        self.src_api = api_map[self.job.src_id]
        self.dest_api = api_map[self.job.dest_id]

        self.report(ui_text.requesting, 2)
        if self.job.tor_id:
            self.tor_info = TorrentInfo(self.src_api, id=self.job.tor_id)
        elif self.job.info_hash:
            self.tor_info = TorrentInfo(self.src_api, hash=job.info_hash)
            self.job.tor_id = self.tor_info.tor_id
        else:
            return

        self.job.display_name = html.unescape(self.tor_info.folder_path)
        self.report(self.job.display_name, 2)

        if self.job.file_check:
            self.check_files()

        self.edit_to_unknown = False
        self.upl_data = None
        self.generate_upload_data()
        self.upl_files = self.getfiles()
        self.new_upl_url = None

    def parse_artists(self):
        artists = []
        importances = []
        for a_type, names in self.tor_info.artist_data.items():
            for n in names:
                imp = constants.ARTIST_MAP.get(a_type)
                if imp:
                    importances.append(imp)
                    artists.append(n['name'])

        self.upl_data["artists[]"] = artists
        self.upl_data["importance[]"] = importances

    def release_type(self):
        source_reltype_num = self.tor_info.rel_type
        for name, num in constants.RELEASE_TYPE_MAP[self.job.src_id].items():
            if num == source_reltype_num:
                self.upl_data["releasetype"] = constants.RELEASE_TYPE_MAP[self.job.dest_id][name]
                break

    def remaster_data(self):

        remaster_year = self.tor_info.rem_year

        # Unknown and unconfirmes releases
        if self.job.src_id == "RED" and remaster_year == 0:
            # unknown
            if self.tor_info.remastered:
                self.upl_data["remaster"] = True
                self.upl_data['unknown'] = True
                # Due to bug, there has to be a rem.year > 1982
                self.upl_data['remaster_year'] = '2000'

            # unconfirmed
            else:
                self.upl_data["remaster"] = True
                self.upl_data["remaster_year"] = self.tor_info.o_year
                self.upl_data["remaster_record_label"] = html.unescape(self.tor_info.rem_label)
                self.upl_data["remaster_catalogue_number"] = self.tor_info.rem_cat_nr

        # unknown can't be uploaded to RED directly
        elif self.job.src_id == "OPS" and self.tor_info.remastered and not remaster_year:
            self.upl_data["remaster"] = True
            self.upl_data['remaster_year'] = '1990'
            self.upl_data["remaster_title"] = 'Unknown release year'
            self.edit_to_unknown = True

        # get rid of original release
        elif self.job.src_id == "OPS" and not self.tor_info.remastered:
            self.upl_data["remaster"] = True
            self.upl_data["remaster_year"] = self.tor_info.o_year
            self.upl_data["remaster_record_label"] = html.unescape(self.tor_info.o_label)
            self.upl_data["remaster_catalogue_number"] = self.tor_info.o_cat_nr

        else:
            self.upl_data["remaster"] = True
            self.upl_data["remaster_year"] = remaster_year
            self.upl_data["remaster_title"] = html.unescape(self.tor_info.rem_title)
            self.upl_data["remaster_record_label"] = html.unescape(self.tor_info.rem_label)
            self.upl_data["remaster_catalogue_number"] = self.tor_info.rem_cat_nr

    def tags(self):
        # There's a 200 character limit for tags
        tag_list = []
        ch_count = 0
        for t in self.tor_info.tags:
            ch_count += len(t)
            if ch_count < 200:
                tag_list.append(t)
            else:
                break
        self.upl_data["tags"] = ",".join(tag_list)

    def release_description(self):
        descr_placeholders = {
            '%src_id%': self.job.src_id,
            '%src_url%': constants.SITE_URLS[self.job.src_id],
            '%ori_upl%': self.tor_info.uploader,
            '%upl_id%': str(self.tor_info.uploader_id),
            '%tor_id%': str(self.tor_info.tor_id),
            '%gr_id%': str(self.tor_info.grp_id)
        }

        rel_descr = utils.multi_replace(self.job.rel_descr, descr_placeholders)

        src_descr = self.tor_info.rel_descr
        if src_descr and self.job.add_src_descr:
            rel_descr += '\n\n' + utils.multi_replace(self.job.src_descr, descr_placeholders, {'%src_descr%': src_descr})

        self.upl_data["release_desc"] = rel_descr

    def rehost_img(self):

        src_img_url = self.tor_info.img_url
        if not src_img_url:
            return ''

        if any(w in src_img_url for w in self.job.whitelist):
            return src_img_url

        # # ptpimg doesn't handle webp well
        # if all(x in src_img_url for x in ('img.discogs.com', 'format(webp)')):
        #     return ptpimg_uploader.ra_rehost(src_img_url, self.job.rapi_key)

        try:
            rehosted_url = ptpimg_uploader.upload(self.job.ptpimg_key, [src_img_url])[0]
            self.report(f"{ui_text.img_rehosted} {rehosted_url}", 2)
            return rehosted_url

        except (ptpimg_uploader.UploadFailed, ValueError):
            self.report(ui_text.rehost_failed, 1)
            return src_img_url

    def bitrate(self):
        encoding = self.tor_info.encoding
        if encoding in ['192', 'APS (VBR)', 'V2 (VBR)', 'V1 (VBR)', '256', 'APX (VBR)',
                        'V0 (VBR)', 'Lossless', '24bit Lossless']:
            self.upl_data["bitrate"] = encoding
        else:
            self.upl_data["bitrate"] = 'Other'
            if encoding.endswith('(VBR)'):
                self.upl_data['vbr'] = True
                encoding = encoding[:-6]

            self.upl_data['other_bitrate'] = encoding

    def generate_upload_data(self):

        self.upl_data = {
            "type": "0",
            "media": self.tor_info.medium,
            "format": self.tor_info.format
        }
        self.remaster_data()
        self.bitrate()
        self.release_description()

        if self.job.dest_group:
            self.upl_data['groupid'] = self.job.dest_group
        else:
            self.upl_data.update({
                "title": html.unescape(self.tor_info.title),
                "year": self.tor_info.o_year,
                "image": self.rehost_img() if self.job.img_rehost else self.tor_info.img_url,
                "vanity_house": self.tor_info.vanity,
                # apparantly 'False' doesn't work for "scene" on OPS. Must be 'None'
                "scene": None if not self.tor_info.scene else True
            })
            self.parse_artists()
            self.release_type()
            self.tags()

            d_url_switched = self.tor_info.alb_descr.replace(self.src_api.url, self.dest_api.url)
            self.upl_data["album_desc"] = html.unescape(d_url_switched)

        # self.upl_data["media"] = 'blabla'

    def create_new_torrent(self):

        from dottorrent import Torrent

        torfolder = os.path.join(self.job.data_dir, self.job.display_name)
        self.report(ui_text.new_tor, 2)
        t = Torrent(torfolder, private=True)
        t.generate()

        # dottorrent creates dict with string keys.
        # Following code will add bytes keys. and key type must be uniform for bencoder to encode.
        def dict_stringkeys_to_bytes(inp_dict):
            output_dict = {}
            for k, v in inp_dict.items():
                try:
                    v = dict_stringkeys_to_bytes(v)
                except AttributeError:
                    pass
                output_dict[k.encode()] = v
            return output_dict

        return dict_stringkeys_to_bytes(t.data)

    def getfiles(self):
        files = []

        # .torrent
        if self.job.new_dtor:
            self.job.dtor_dict = self.create_new_torrent()

        if not self.job.dtor_dict:
            dtor_bytes = self.src_api.request("GET", "download", expect_bytes=True, id=self.job.tor_id)
            self.job.dtor_dict = bdecode(dtor_bytes)

        self.job.dtor_dict[b'announce'] = self.dest_api.announce.encode()
        self.job.dtor_dict[b"info"][b"source"] = self.job.dest_id.encode()
        tor_bytes = bencode(self.job.dtor_dict)
        files.append(("file_input", (f"blabla.torrent", tor_bytes, "application/octet-stream")))

        # riplogs
        if self.tor_info.haslog:

            if self.job.src_id == "OPS":
                log_ids = self.tor_info.log_ids
                for i in log_ids:
                    r = self.src_api.request("GET", "riplog", id=self.job.tor_id, logid=i)
                    log_bytes = base64.b64decode(r["log"])
                    log_checksum = sha256(log_bytes).hexdigest()
                    assert log_checksum == r['log_sha256']
                    file_tuple = ("log.log", log_bytes, "application/octet-stream")
                    files.append(("logfiles[]", file_tuple))

            if self.job.src_id == "RED":
                log_paths = []
                base_path = html.unescape(os.path.join(self.job.data_dir, self.tor_info.folder_path))
                assert os.path.isdir(base_path), f"{ui_text.missing} {base_path}"

                for p in utils.file_list_gen(base_path):
                    fn = os.path.split(p)[1]
                    if fn.endswith(".log") and fn.lower() not in constants.LOGS_TO_IGNORE:
                        log_paths.append(p)
                assert log_paths, ui_text.no_log

                log_paths.sort()
                for lp in log_paths:
                    with open(lp, "rb") as f:
                        log_data = f.read()
                    file_tuple = ("log.log", log_data, "application/octet-stream")
                    files.append(("logfiles[]", file_tuple))

        return files

    def api_filelist_gen(self):
        for s in html.unescape(self.tor_info.file_list).split("|||"):
            yield re.match(r"(.+){{3}\d+}{3}", s).group(1).split("/")

    def check_files(self):
        torfolder = html.unescape(self.tor_info.folder_path)
        for fl in self.api_filelist_gen():
            full_path = os.path.join(self.job.data_dir, torfolder, *fl)
            if not os.path.isfile(full_path):
                raise FileNotFoundError(f"{ui_text.missing} {full_path}")
        self.report(ui_text.f_checked, 2)

    def save_dtorrent(self):
        assert self.job.src_id != self.job.dtor_dict[b"info"][b"source"]
        file_path = os.path.join(self.job.dtor_save_dir, self.job.display_name) + ".torrent"
        with open(file_path, "wb") as f:
            f.write(bencode(self.job.dtor_dict))

    def transplant(self):
        try:
            self.report(f"{ui_text.upl1} {self.job.dest_id}", 2)
            r = self.dest_api.request("POST", "upload", data=self.upl_data, files=self.upl_files)
            self.report(f"{r}", 4)
        except (RequestFailure, HTTPError) as e:
            self.report(f"{ui_text.upl3} {str(e)}", 1)
            return False

        try:
            # RED = lowercase keys. OPS = camelCase keys
            group_id = r.get('groupId', r.get('groupid'))
            torrent_id = r.get('torrentId', r.get('torrentid'))
        except AttributeError as ee:
            self.report(f"{ui_text.upl3} {str(ee)}", 1)
            return False

        self.new_upl_url = self.dest_api.url + f"torrents.php?id={group_id}&torrentid={torrent_id}"
        self.report(f"{ui_text.upl2} {self.new_upl_url}", 2)
        self.job.dtor_dict[b'comment'] = self.new_upl_url.encode()

        if self.edit_to_unknown:
            try:
                self.dest_api.request("POST", "torrentedit", id=torrent_id, data={'unknown': True})
                self.report(ui_text.upl_to_unkn, 2)
            except (RequestFailure, HTTPError) as e:
                self.report(f"{ui_text.edit_fail}{str(e)}", 1)

        if self.job.save_dtors:
            self.save_dtorrent()
            self.report(f"{ui_text.dtor_saved} {self.job.dtor_save_dir}", 2)

        if self.job.del_dtors:
            os.remove(self.job.dtor_path)
            self.report(f"{ui_text.dtor_deleted}", 2)

        return True
