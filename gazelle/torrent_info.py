import html
import re
from pathlib import Path
from typing import Iterator

from gazelle.tracker_data import tr, ReleaseType, ArtistType, Encoding


class TorrentInfo:
    def __init__(self):
        self.grp_id = None
        self.img_url = None
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
        self.src_tr = None


class SharedInfo(TorrentInfo):
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
            'description': 'rel_descr',
            'filePath': 'folder_name',
            'userId': 'uploader_id',
            'username': 'uploader',
        }
    }

    def __init__(self, tr_resp: dict):
        super().__init__()

        for sub_name, sub_dict in self.FIELD_MAP.items():
            for gaz_name, torinfo_name in sub_dict.items():
                value = tr_resp[sub_name][gaz_name]
                if value:
                    setattr(self, torinfo_name, value)

        enc_str = tr_resp['torrent']['encoding']
        self.encoding = Encoding[enc_str]
        if self.encoding == Encoding.Other:
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

    def file_paths(self) -> Iterator[Path]:
        for fd in self.file_list:
            yield fd['path']

    def glob(self, pattern: str) -> Iterator[Path]:
        # todo 3.12: pattern = Path(pattern)
        for p in self.file_paths():
            if p.match(pattern):
                yield p


class REDTorrentInfo(SharedInfo):
    def __init__(self, tr_resp: dict):
        self.unexape(tr_resp)
        super().__init__(tr_resp)

        self.src_tr = tr.RED
        self.alb_descr = tr_resp['group']['bbBody']

        rel_type: int = tr_resp['group']['releaseType']
        self.rel_type = ReleaseType.mem_from_tr_value(rel_type, tr.RED)

        if not self.rem_year:
            if tr_resp['torrent']['remastered']:
                self.unknown = True
            else:
                # unconfirmed
                self.rem_year = self.o_year
                self.rem_label = tr_resp['group']['recordLabel']
                self.rem_cat_nr = tr_resp['group']['catalogueNumber']

    def unexape(self, thing):
        if isinstance(thing, list):
            for i, x in enumerate(thing):
                thing[i] = self.unexape(x)
        if isinstance(thing, dict):
            for k, v in thing.items():
                thing[k] = self.unexape(v)
        try:
            return html.unescape(thing)
        except TypeError:
            return thing


class OPSTorrentInfo(SharedInfo):
    artist_strip_regex = re.compile(r'(.+)\s\(\d+\)$')

    def __init__(self, tr_resp: dict):
        super().__init__(tr_resp)

        self.src_tr = tr.OPS
        self.rel_type = ReleaseType[tr_resp['group']['releaseTypeName']]
        self.alb_descr = tr_resp['group']['wikiBBcode']

        log_ids = tr_resp['torrent']['ripLogIds']
        if log_ids:
            self.log_ids = log_ids

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
                if match := self.artist_strip_regex.match(a['name']):
                    stripped = match.group(1)
                    a['name'] = stripped


tr_map = {
    tr.RED: REDTorrentInfo,
    tr.OPS: OPSTorrentInfo
}
