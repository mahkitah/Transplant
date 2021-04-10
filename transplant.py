import os
import html
import base64
import sys
import re

from bencoder import bencode, bdecode
from hashlib import sha256

from gazelle_api import GazelleApi
import config


def make_file_list(path):
    """
    create list of files in dir + subdirs
    :param path: path like object (str or bytes)
    :return: list of files (full path)
    """
    file_list = []
    for root, dirs, files in os.walk(path):
        for x in files:
            file_list.append(os.path.join(root, x))
    return file_list


def parse_input(sys_arg):
    tid = None
    match = re.search(r"torrentid=(\d+)", sys_arg)
    if match:
        tid = int(match.group(1))
    else:
        match2 = re.fullmatch(r"\d+", sys_arg)
        if match2:
            tid = int(match2.group(0))
    return tid


def api_filelist_parser(api_resp):
    api_file_list = api_resp["torrent"]["fileList"]
    split = html.unescape(api_file_list).split("|||")
    split[:] = [re.match(r"(.+){{3}\d+}{3}", s).group(1) for s in split]
    split[:] = [s.split("/") for s in split]
    return split


def api_filelist_checker(api_response, base_path2):
    torfolder = html.unescape(api_response["torrent"]["filePath"])
    for fl in api_filelist_parser(api_response):
        full_path = os.path.join(base_path2, torfolder, *fl)
        if not os.path.isfile(full_path):
            raise FileNotFoundError(f"missing file {full_path}")


src, dst, tid = sys.argv[1:4]

tor_id = parse_input(tid)
assert tor_id, f"no valid input: {tid}"

source = GazelleApi(src)
dest = GazelleApi(dst)

tor_info = source.request("GET", "torrent", id=tor_id)

artist_map = {
    'composers': '4',
    'dj': '6',
    'with': '2',
    'artists': '1',
    'conductor': '5',
    'remixedBy': '3',
    'producer': '7'
}
releasetype_map = {
    "RED": {
        "Album": 1,
        "Soundtrack": 3,
        "EP": 5,
        "Anthology": 6,
        "Compilation": 7,
        "Single": 9,
        "Live album": 11,
        "Remix": 13,
        "Bootleg": 14,
        "Interview": 15,
        "Mixtape": 16,
        "Demo": 17,
        "Concert Recording": 18,
        "DJ Mix": 19,
        "Unknown": 21
    },
    "OPS": {
        "Album": 1,
        "Soundtrack": 3,
        "EP": 5,
        "Anthology": 6,
        "Compilation": 7,
        "Sampler": 8,
        "Single": 9,
        "Demo": 10,
        "Live album": 11,
        "Split": 12,
        "Remix": 13,
        "Bootleg": 14,
        "Interview": 15,
        "Mixtape": 16,
        "DJ Mix": 17,
        "Concert Recording": 18,
        "Unknown": 21
    }
}
# filecheck before we realy start

api_filelist_checker(tor_info, config.torrent_files)

# ----data----

upl_data = {"type": "0"}

artists = []
importance = []
for a_type, names in tor_info['group']['musicInfo'].items():
    for n in names:
        imp = artist_map.get(a_type)
        if imp:
            importance.append(imp)
            artists.append(n['name'])

upl_data["artists[]"] = artists
upl_data["importance[]"] = importance
upl_data["title"] = html.unescape(tor_info['group']['name'])
upl_data["year"] = tor_info['group']['year']

# translate release types
source_reltype_num = tor_info['group']['releaseType']
for name, num in releasetype_map[source.id].items():
    if num == source_reltype_num:
        source_reltype_name = name
        break
# noinspection PyUnboundLocalVariable
upl_data["releasetype"] = releasetype_map[dest.id][source_reltype_name]

upl_data["remaster"] = tor_info['torrent']['remastered']
upl_data["remaster_year"] = tor_info['torrent']['remasterYear']
upl_data["remaster_title"] = html.unescape(tor_info['torrent']['remasterTitle'])
upl_data["remaster_record_label"] = html.unescape(tor_info['torrent']['remasterRecordLabel'])
upl_data["remaster_catalogue_number"] = tor_info['torrent']['remasterCatalogueNumber']
# upl_data["scene"] = tor_info['torrent']['scene']
upl_data["scene"] = "" if not tor_info['torrent']['scene'] else True
upl_data["media"] = tor_info['torrent']['media']
upl_data["format"] = tor_info['torrent']['format']
upl_data["bitrate"] = tor_info['torrent']['encoding']

upl_data["vanity_house"] = tor_info['group']['vanityHouse']
upl_data["tags"] = ",".join(tor_info['group']['tags'])
upl_data["image"] = tor_info['group']['wikiImage']

#  RED uses "bbBody", OPS uses "wikiBBcode"
d = tor_info['group'].get("bbBody", tor_info['group'].get("wikiBBcode"))
upl_data["album_desc"] = html.unescape(d)

rel_descr = f"Transplanted from {source.id}"
descr = tor_info['torrent']['description']
if descr:
    rel_descr += f"\n\n[hide=source description:]{descr}[/hide]"
upl_data["release_desc"] = rel_descr

# get rid of original release
if not upl_data["remaster"]:
    upl_data["remaster_year"] = tor_info['group']['year']
    upl_data["remaster_record_label"] = html.unescape(tor_info['group']['recordLabel'])
    upl_data["remaster_catalogue_number"] = tor_info['group']['catalogueNumber']
    upl_data["remaster"] = True

# ----files----

files = []

# .torrent

tor_bytes = source.request("GET", "download", id=tor_id)
tor_dict = bdecode(tor_bytes)
tor_dict[b'announce'] = dest.announce.encode()
tor_dict[b"info"][b"source"] = dest.id.encode()
tor_upl = bencode(tor_dict)
files.append(("file_input", (f"blabla.torrent", tor_upl, "application/octet-stream")))

if config.torrent_output:
    tor_name = tor_info['torrent']['filePath']
    file_path = f"{os.path.join(config.torrent_output, tor_name)}.torrent"
    with open(file_path, "wb") as f:
        f.write(tor_upl)

# riplogs

if tor_info["torrent"]["hasLog"]:
    if source.id == "OPS":
        log_ids = tor_info["torrent"]["ripLogIds"]
        for i in log_ids:
            r = source.request("GET", "riplog", id=tor_id, logid=i)
            log_bytes = base64.b64decode(r["log"])
            log_checksum = sha256(log_bytes).hexdigest()
            assert log_checksum == r['log_sha256']
            file_tuple = ("log.log", log_bytes, "application/octet-stream")
            files.append(("logfiles[]", file_tuple))
    if source.id == "RED":
        log_paths = []
        base_path = html.unescape(os.path.join(config.torrent_files, tor_info['torrent']['filePath']))
        assert os.path.isdir(base_path), f"Torrent path not found: {base_path}"
        for p in make_file_list(base_path):
            fn = os.path.split(p)[1]
            if fn.endswith(".log") and fn.lower() not in config.logs_to_ignore:
                log_paths.append(p)
        log_paths.sort()
        for lp in log_paths:
            with open(lp, "rb") as f:
                log_data = f.read()
            file_tuple = ("log.log", log_data, "application/octet-stream")
            files.append(("logfiles[]", file_tuple))

# upl_data["media"] = 'blabla'
up = dest.request("POST", "upload", data=upl_data, files=files)
new_upl_url = dest.url + f"torrents.php?id={up['groupId']}&torrentid={up['torrentId']}"
print(new_upl_url)
