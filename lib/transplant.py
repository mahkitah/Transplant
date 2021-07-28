import os
import html
import base64
import re

from bencoder import bencode, bdecode
from hashlib import sha1, sha256

from lib.gazelle_api import RequestFailure
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
        self.upl_succes = False

        if dtor_path:
            self.parse_dtorrent(dtor_path)
            self.display_name = os.path.splitext(os.path.basename(dtor_path))[0]

        assert self.src_id
        assert self.tor_id or self.info_hash
        assert not (self.tor_id and self.info_hash)

        self.dest_id = choose_the_other(self.src_id)

    def update(self, settings_dict):
        for k, v in settings_dict.items():
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
            self.tor_info = self.src_api.request("GET", "torrent", id=self.job.tor_id)
        elif self.job.info_hash:
            self.tor_info = self.src_api.request("GET", "torrent", hash=job.info_hash)
            self.job.tor_id = self.tor_info['torrent']['id']
        else:
            return
        # bug/change on OPS returns None instead of ''
        if self.job.src_id == 'OPS':
            utils.dict_replace_values(self.tor_info, None, '')

        self.job.display_name = html.unescape(self.tor_info["torrent"]["filePath"])
        self.report(self.job.display_name, 2)

        if self.job.file_check:
            self.check_files()

        self.edit_to_unknown = False
        self.upl_data = self.generate_upload_data(self.tor_info)
        self.upl_files = self.getfiles()
        self.new_upl_url = None

    @staticmethod
    def parse_artists(music_info):
        artists = []
        importances = []
        for a_type, names in music_info.items():
            for n in names:
                imp = constants.ARTIST_MAP.get(a_type)
                if imp:
                    importances.append(imp)
                    artists.append(n['name'])

        return artists, importances

    def release_type(self, source_reltype_num):

        for name, num in constants.RELEASE_TYPE_MAP[self.job.src_id].items():
            if num == source_reltype_num:
                return constants.RELEASE_TYPE_MAP[self.job.dest_id][name]

    def remaster_data(self, tor_info):

        remaster_year = tor_info['torrent']['remasterYear']
        remaster_data = {}

        # Unknown and unconfirmes releases
        if self.job.src_id == "RED" and remaster_year == 0:
            # unknown
            if tor_info['torrent']['remastered']:
                remaster_data["remaster"] = True
                remaster_data['unknown'] = True
                # Due to bug, there has to be a rem.year > 1982
                remaster_data['remaster_year'] = '2000'

            # unconfirmed
            else:
                remaster_data["remaster"] = True
                remaster_data["remaster_year"] = tor_info['group']['year']
                remaster_data["remaster_record_label"] = html.unescape(tor_info['group']['recordLabel'] or "")
                remaster_data["remaster_catalogue_number"] = tor_info['group']['catalogueNumber']

        # unknown can't be uploaded to RED directly
        elif self.job.src_id == "OPS" and tor_info['torrent']['remastered'] and not remaster_year:
            remaster_data["remaster"] = True
            remaster_data['remaster_year'] = 1990
            remaster_data["remaster_title"] = 'Unknown release year'
            self.edit_to_unknown = True

        # get rid of original release
        elif self.job.src_id == "OPS" and not tor_info['torrent']['remastered']:
            remaster_data["remaster"] = True
            remaster_data["remaster_year"] = tor_info['group']['year']
            remaster_data["remaster_record_label"] = html.unescape(tor_info['group']['recordLabel'] or "")
            remaster_data["remaster_catalogue_number"] = tor_info['group']['catalogueNumber']

        else:
            remaster_data["remaster"] = True
            remaster_data["remaster_year"] = remaster_year
            remaster_data["remaster_title"] = html.unescape(tor_info['torrent']['remasterTitle'])
            remaster_data["remaster_record_label"] = html.unescape(tor_info['torrent']['remasterRecordLabel'])
            remaster_data["remaster_catalogue_number"] = tor_info['torrent']['remasterCatalogueNumber']

        return remaster_data

    @staticmethod
    def tags(tags):
        # There's a 200 character limit for tags
        tag_list = []
        ch_count = 0
        for t in tags:
            ch_count += len(t)
            if ch_count < 200:
                tag_list.append(t)
            else:
                break
        return ",".join(tag_list)

    def release_description(self, tor_info):
        descr_placeholders = {
            '%src_id%': self.job.src_id,
            '%src_url%': constants.SITE_URLS[self.job.src_id],
            '%ori_upl%': tor_info['torrent']['username'],
            '%upl_id%': str(tor_info['torrent']['userId']),
            '%tor_id%': str(tor_info['torrent']['id']),
            '%gr_id%': str(tor_info['group']['id'])
        }

        rel_descr = utils.multi_replace(self.job.rel_descr, descr_placeholders)

        src_descr = tor_info['torrent']['description']
        if src_descr and self.job.add_src_descr:
            rel_descr += '\n\n' + utils.multi_replace(self.job.src_descr, descr_placeholders, {'%src_descr%': src_descr})

        return rel_descr

    def rehost_img(self):

        src_img_url = self.tor_info['group']['wikiImage']
        if not src_img_url:
            return ''

        whitelist = self.job.whitelist
        ptpimg_key = self.job.ptpimg_key

        if any(w in src_img_url for w in whitelist):
            return src_img_url
        else:
            try:
                rehosted_url = ptpimg_uploader.upload(ptpimg_key, [src_img_url])[0]
                self.report(f"{ui_text.img_rehosted} {rehosted_url}", 2)
                return rehosted_url

            except (ptpimg_uploader.UploadFailed, ValueError):
                self.report(ui_text.rehost_failed, 1)
                return src_img_url

    @staticmethod
    def bitrate(encoding):

        bitrate_data = {}
        if encoding in ['192', 'APS (VBR)', 'V2 (VBR)', 'V1 (VBR)', '256', 'APX (VBR)',
                        'V0 (VBR)', 'Lossless', '24bit Lossless']:
            bitrate_data["bitrate"] = encoding
        else:
            bitrate_data["bitrate"] = 'Other'
            if encoding.endswith('(VBR)'):
                bitrate_data['vbr'] = True
                encoding = encoding[:-6]

            bitrate_data['other_bitrate'] = encoding

        return bitrate_data

    def generate_upload_data(self, tor_info):

        artists, importances = self.parse_artists(tor_info['group']['musicInfo'])
        
        upl_data = {"type": "0"}

        if self.job.dest_group:
            upl_data['groupid'] = self.job.dest_group
        else:
            upl_data["releasetype"] = self.release_type(tor_info['group']['releaseType'])
            upl_data["title"] = html.unescape(tor_info['group']['name'])
            upl_data["year"] = tor_info['group']['year']
            upl_data["artists[]"] = artists
            upl_data["importance[]"] = importances
            upl_data["image"] = self.rehost_img() if self.job.img_rehost else tor_info['group']['wikiImage']
            upl_data["vanity_house"] = tor_info['group']['vanityHouse']
            # apparantly 'False' doesn't work for "scene" on OPS. Must be 'None'
            upl_data["scene"] = None if not tor_info['torrent']['scene'] else True
            upl_data["tags"] = self.tags(tor_info['group']['tags'])
            #  RED uses "bbBody", OPS uses "wikiBBcode"
            d = tor_info['group'].get("bbBody", tor_info['group'].get("wikiBBcode"))
            d_url_switched = d.replace(self.src_api.url, self.dest_api.url)
            upl_data["album_desc"] = html.unescape(d_url_switched)

        upl_data.update(self.remaster_data(tor_info))
        upl_data["media"] = tor_info['torrent']['media']
        upl_data["format"] = tor_info['torrent']['format']
        upl_data.update(self.bitrate(tor_info['torrent']['encoding']))
        upl_data["release_desc"] = self.release_description(tor_info)
        # upl_data["media"] = 'blabla'

        return upl_data

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
            dtor_bytes = self.src_api.request("GET", "download", id=self.job.tor_id)
            self.job.dtor_dict = bdecode(dtor_bytes)

        self.job.dtor_dict[b'announce'] = self.dest_api.announce.encode()
        self.job.dtor_dict[b"info"][b"source"] = self.job.dest_id.encode()
        tor_bytes = bencode(self.job.dtor_dict)
        files.append(("file_input", (f"blabla.torrent", tor_bytes, "application/octet-stream")))

        # riplogs
        if self.tor_info["torrent"]["hasLog"]:

            if self.job.src_id == "OPS":
                log_ids = self.tor_info["torrent"]["ripLogIds"]
                for i in log_ids:
                    r = self.src_api.request("GET", "riplog", id=self.job.tor_id, logid=i)
                    log_bytes = base64.b64decode(r["log"])
                    log_checksum = sha256(log_bytes).hexdigest()
                    assert log_checksum == r['log_sha256']
                    file_tuple = ("log.log", log_bytes, "application/octet-stream")
                    files.append(("logfiles[]", file_tuple))

            if self.job.src_id == "RED":
                log_paths = []
                base_path = html.unescape(os.path.join(self.job.data_dir, self.tor_info['torrent']['filePath']))
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
        for s in html.unescape(self.tor_info["torrent"]["fileList"]).split("|||"):
            yield re.match(r"(.+){{3}\d+}{3}", s).group(1).split("/")

    def check_files(self):
        torfolder = html.unescape(self.tor_info["torrent"]["filePath"])
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
        except RequestFailure as e:
            self.report(f"{ui_text.upl3} {str(e)}", 1)
            return

        self.job.upl_succes = True

        # RED = lowercase keys. OPS = camelCase keys
        group_id = r.get('groupId', r.get('groupid'))
        torrent_id = r.get('torrentId', r.get('torrentid'))

        self.new_upl_url = self.dest_api.url + f"torrents.php?id={group_id}&torrentid={torrent_id}"
        self.report(f"{ui_text.upl2} {self.new_upl_url}", 2)
        self.job.dtor_dict[b'comment'] = self.new_upl_url.encode()

        if self.edit_to_unknown:
            try:
                self.dest_api.request("POST", "torrentedit", id=torrent_id, data={'unknown': True})
                self.report(ui_text.upl_to_unkn, 2)
            except RequestFailure as e:
                self.report(f"{ui_text.edit_fail}{str(e)}", 1)

        if self.job.save_dtors:
            self.save_dtorrent()
            self.report(f"{ui_text.dtor_saved} {self.job.dtor_save_dir}", 2)

        if self.job.del_dtors:
            os.remove(self.job.dtor_path)
            self.report(f"{ui_text.dtor_deleted}", 2)
