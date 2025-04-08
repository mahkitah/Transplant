import html
import re
from pathlib import Path
from typing import Iterator, Any

from gazelle.tracker_data import TR, ReleaseType, ArtistType, Encoding

FIELD_MAP = {
    'group': {
        'id': 'grp_id',
        'wikiImage': 'img_url',
        'name': 'title',
        'year': 'o_year',
        'vanityHouse': 'vanity',
        'tags': 'tags',
    },
    'torrent': {
        'id': 'tor_id',
        'media': 'medium',
        'format': 'format',
        'remasterYear': 'rem_year',
        'remasterTitle': 'rem_title',
        'remasterRecordLabel': 'rem_label',
        'remasterCatalogueNumber': 'rem_cat_nr',
        'scene': 'scene',
        'hasLog': 'haslog',
        'logScore': 'log_score',
        'ripLogIds': 'log_ids',
        'description': 'rel_descr',
        'filePath': 'folder_name',
        'userId': 'uploader_id',
        'username': 'uploader',
    }
}

ARTTIST_STRIP_REGEX = re.compile(r'(.+)\s\(\d+\)$')


def unexape(thing: Any) -> Any:
    if isinstance(thing, list):
        for i, x in enumerate(thing):
            thing[i] = unexape(x)
    elif isinstance(thing, dict):
        for k, v in thing.items():
            thing[k] = unexape(v)
    try:
        return html.unescape(thing)
    except TypeError:
        return thing


class TorrentInfo:
    def __init__(self, tr_resp: dict, src_tr: TR):
        self.grp_id = None
        self.img_url = None
        self.proxy_img = None
        self.title = None
        self.o_year = None
        self.rel_type = None
        self.vanity: bool = False
        self.artist_data = None
        self.tags = None
        self.alb_descr = None

        self.tor_id = None
        self.medium = None
        self.format = None
        self.encoding = None
        self.other_bitrate = None
        self.vbr: bool = False
        self.rem_year = None
        self.rem_title = None
        self.rem_label = None
        self.rem_cat_nr = None
        self.scene: bool = False
        self.haslog: bool = False
        self.log_score = None
        self.log_ids = None
        self.rel_descr = None
        self.folder_name = None
        self.uploader_id = None
        self.uploader = None

        self.file_list = None
        self.unknown: bool = False
        self.src_tr: TR | None = src_tr

        if src_tr is TR.RED:
            self.set_red_info(tr_resp)
        elif src_tr is TR.OPS:
            self.set_ops_info(tr_resp)

    def set_common_gazelle(self, tr_resp: dict):
        for sub_name, sub_dict in FIELD_MAP.items():
            for gaz_name, torinfo_name in sub_dict.items():
                value = tr_resp[sub_name][gaz_name]
                if value:
                    setattr(self, torinfo_name, value)

        enc_str = tr_resp['torrent']['encoding']
        self.encoding = Encoding[enc_str]
        if self.encoding is Encoding.Other:
            bitr, vbr, _ = enc_str.partition(' (VBR)')
            self.other_bitrate = int(bitr)
            self.vbr = bool(vbr)

        files = []
        for s in tr_resp['torrent']['fileList'].split("|||"):
            path, size = s.removesuffix('}}}').split('{{{')
            files.append({'path': Path(path),
                          'size': int(size)})
        self.file_list = files

        artists = {}
        for a_type, artist_list in tr_resp['group']['musicInfo'].items():
            artists[ArtistType(a_type)] = artist_list
        self.artist_data = artists

    def set_red_info(self, tr_resp: dict):
        tr_resp: dict = unexape(tr_resp)
        self.set_common_gazelle(tr_resp)

        self.alb_descr = tr_resp['group']['bbBody']

        rel_type: int = tr_resp['group']['releaseType']
        self.rel_type = ReleaseType.mem_from_tr_value(rel_type, TR.RED)

        if not self.rem_year:
            if tr_resp['torrent']['remastered']:
                self.unknown = True
            else:
                # unconfirmed
                self.rem_year = self.o_year
                self.rem_label = tr_resp['group']['recordLabel']
                self.rem_cat_nr = tr_resp['group']['catalogueNumber']

    def set_ops_info(self, tr_resp: dict):
        self.set_common_gazelle(tr_resp)
        self.rel_type = ReleaseType[tr_resp['group']['releaseTypeName']]
        self.alb_descr = tr_resp['group']['wikiBBcode']
        self.proxy_img = tr_resp['group']['proxyImage']

        # strip disambiguation nr from artists
        self.strip_artists()

        if tr_resp['torrent']['remastered']:
            if not self.rem_year:
                self.unknown = True
        else:
            # get rid of original release
            self.rem_year = self.o_year
            self.rem_label = tr_resp['group']['recordLabel']
            self.rem_cat_nr = tr_resp['group']['catalogueNumber']

        if self.medium == 'BD':
            self.medium = 'Blu-Ray'

    def strip_artists(self):
        for a_type, artists in self.artist_data.items():
            for a in artists:
                if match := ARTTIST_STRIP_REGEX.match(a['name']):
                    stripped = match.group(1)
                    a['name'] = stripped

    def file_paths(self) -> Iterator[Path]:
        for fd in self.file_list:
            yield fd['path']

    def glob(self, pattern: str) -> Iterator[Path]:
        # todo 3.12: pattern = Path(pattern)
        for p in self.file_paths():
            if p.match(pattern):
                yield p
