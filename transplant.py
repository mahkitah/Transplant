import os
import html
import base64
import sys
import re
import traceback
from bencoder import bencode, bdecode
from hashlib import sha1, sha256

from gazelle_api import GazelleApi, RequestFailure
import config
import utils


class Transplanter:
    def __init__(self, src_id, tor_id, api_map, tor_info=None, dtorbytes=None, report=lambda *x: None):
        self.src_id = src_id
        self.dest_id = choose_the_other(src_id)
        self.src_api = api_map[src_id]
        self.dest_api = api_map[self.dest_id]
        self.tor_id = tor_id
        self.dtor_bytes = dtorbytes
        self.tor_info = self.src_api.request("GET", "torrent", id=tor_id) if not tor_info else tor_info
        if config.file_check:
            self.check_files()
        self.upl_data = self.generate_upload_data()
        self.upl_files = self.getfiles()
        self.report = report

    def generate_upload_data(self):
        upl_data = {"type": "0"}
        artists = []
        importance = []
        for a_type, names in self.tor_info['group']['musicInfo'].items():
            for n in names:
                imp = config.artist_map.get(a_type)
                if imp:
                    importance.append(imp)
                    artists.append(n['name'])

        upl_data["artists[]"] = artists
        upl_data["importance[]"] = importance
        upl_data["title"] = html.unescape(self.tor_info['group']['name'])
        upl_data["year"] = self.tor_info['group']['year']

        # translate release types
        source_reltype_num = self.tor_info['group']['releaseType']
        for name, num in config.releasetype_map[self.src_id].items():
            if num == source_reltype_num:
                upl_data["releasetype"] = config.releasetype_map[self.dest_id][name]
                break

        upl_data["remaster"] = self.tor_info['torrent']['remastered']
        upl_data["remaster_year"] = self.tor_info['torrent']['remasterYear']
        upl_data["remaster_title"] = html.unescape(self.tor_info['torrent']['remasterTitle'])
        upl_data["remaster_record_label"] = html.unescape(self.tor_info['torrent']['remasterRecordLabel'])
        upl_data["remaster_catalogue_number"] = self.tor_info['torrent']['remasterCatalogueNumber']
        # apparantly 'False' doesn't work for "scene". Must be ampty string (or 'None')
        upl_data["scene"] = "" if not self.tor_info['torrent']['scene'] else True
        upl_data["media"] = self.tor_info['torrent']['media']
        upl_data["format"] = self.tor_info['torrent']['format']
        upl_data["bitrate"] = self.tor_info['torrent']['encoding']

        upl_data["vanity_house"] = self.tor_info['group']['vanityHouse']
        upl_data["tags"] = ",".join(self.tor_info['group']['tags'])
        upl_data["image"] = self.tor_info['group']['wikiImage']

        #  RED uses "bbBody", OPS uses "wikiBBcode"
        d = self.tor_info['group'].get("bbBody", self.tor_info['group'].get("wikiBBcode"))
        upl_data["album_desc"] = html.unescape(d)

        rel_descr = f"Transplanted from {self.src_id}"
        descr = self.tor_info['torrent']['description']
        if descr:
            rel_descr += f"\n\n[hide=source description:]{descr}[/hide]"
        upl_data["release_desc"] = rel_descr

        # get rid of original release
        if not upl_data["remaster"]:
            upl_data["remaster_year"] = self.tor_info['group']['year']
            upl_data["remaster_record_label"] = html.unescape(self.tor_info['group']['recordLabel'])
            upl_data["remaster_catalogue_number"] = self.tor_info['group']['catalogueNumber']
            upl_data["remaster"] = True

        # upl_data["media"] = 'blabla'
        return upl_data

    def getfiles(self):
        files = []

        # .torrent

        if not self.dtor_bytes:
            self.dtor_bytes = self.src_api.request("GET", "download", id=self.tor_id)
        tor_dict = bdecode(self.dtor_bytes)
        tor_dict[b'announce'] = self.dest_api.announce.encode()
        tor_dict[b"info"][b"source"] = self.dest_id.encode()
        tor_upl = bencode(tor_dict)
        files.append(("file_input", (f"blabla.torrent", tor_upl, "application/octet-stream")))

        if config.torrent_output:
            tor_name = self.tor_info['torrent']['filePath']
            file_path = f"{os.path.join(config.torrent_output, tor_name)}.torrent"
            with open(file_path, "wb") as f:
                f.write(tor_upl)

        # riplogs

        if self.tor_info["torrent"]["hasLog"]:
            if self.src_id == "OPS":
                log_ids = self.tor_info["torrent"]["ripLogIds"]
                for i in log_ids:
                    r = self.src_api.request("GET", "riplog", id=self.tor_id, logid=i)
                    log_bytes = base64.b64decode(r["log"])
                    log_checksum = sha256(log_bytes).hexdigest()
                    assert log_checksum == r['log_sha256']
                    file_tuple = ("log.log", log_bytes, "application/octet-stream")
                    files.append(("logfiles[]", file_tuple))
            if self.src_id == "RED":
                log_paths = []
                base_path = html.unescape(os.path.join(config.album_folder, self.tor_info['torrent']['filePath']))
                assert os.path.isdir(base_path), f"Torrent path not found {base_path}"
                for p in utils.file_list_gen(base_path):
                    fn = os.path.split(p)[1]
                    if fn.endswith(".log") and fn.lower() not in config.logs_to_ignore:
                        log_paths.append(p)
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
            full_path = os.path.join(config.album_folder, torfolder, *fl)
            if not os.path.isfile(full_path):
                raise FileNotFoundError(f"missing file {full_path}")

    def transplant(self):
        self.report(f"Uploading to {self.dest_id}", 2)
        try:
            r = self.dest_api.request("POST", "upload", data=self.upl_data, files=self.upl_files)
            new_upl_url = self.dest_api.url + f"torrents.php?id={r['groupId']}&torrentid={r['torrentId']}"
            self.report(f"Upload successful: {new_upl_url}", 2)
            return True
        except RequestFailure as e:
            self.report(f"Upload failed: {str(e)}", 1)
            return False


choose_the_other = utils.choose_the_other(["RED", "OPS"])


def get_infohash(torbytes):
    tordict = bdecode(torbytes)
    info = tordict[b'info']
    return sha1(bencode(info)).hexdigest().upper()


def parse_torrentfile(path, api_map):
    with open(path, "rb") as f:
        torbytes = f.read()
    tor_dict = bdecode(torbytes)
    announce = tor_dict[b'announce'].decode()
    tr_domain = re.search(r"https?://(.+?)/.+", announce).group(1)
    src_id = config.site_id_map[tr_domain]
    src_api = api_map[src_id]
    i_hash = get_infohash(torbytes)
    tor_info = src_api.request("GET", "torrent", hash=i_hash)
    return src_id, str(tor_info['torrent']['id']), tor_info, torbytes


def main():
    def report_back(msg, msg_verb):
        if msg_verb <= config.verbosity:
            print(msg)

    def operate(src_id, tor_id, tor_info=None, dtorbytes=None):
        try:
            operation = Transplanter(src_id, tor_id, api_map, tor_info=tor_info, dtorbytes=dtorbytes, report=report_back)
        except Exception:
            traceback.print_exc()
            return False
        try:
            if operation.transplant():
                return True
        except Exception:
            traceback.print_exc()
        return False

    api_map = {'RED': GazelleApi("RED", report=report_back),
               'OPS': GazelleApi("OPS", report=report_back)}

    report_back("Starting", 2)

    args = sys.argv[1:]
    batchmode = False

    for arg in args:
        report_back('', 2)
        if arg.lower() == "batch":
            batchmode = True

        match_url = re.search(r"https://(.+?)/.+torrentid=(\d+)", arg)
        if match_url:
            report_back(f"{arg}", 2)
            src_name = match_url.group(1)
            tor_id = match_url.group(2)
            src_id = config.site_id_map[src_name]
            operate(src_id, tor_id)

        match_id = re.fullmatch(r"(RED|OPS)(\d+)", arg)
        if match_id:
            report_back(f"{arg}", 2)
            src_id = match_id.group(1)
            tor_id = match_id.group(2)
            operate(src_id, tor_id)

    if batchmode:
        for dir_entry in os.scandir(config.batch_folder):
            if dir_entry.is_file() and dir_entry.name.endswith(".torrent"):
                report_back(f"\n{dir_entry.name}", 2)
                src_id, tor_id, tor_info, torbytes = parse_torrentfile(dir_entry.path, api_map)
                success = operate(src_id, tor_id, tor_info=tor_info, dtorbytes=torbytes)
                if success and config.remove_after_upload:
                    os.remove(dir_entry.path)


if __name__ == "__main__":
    main()
