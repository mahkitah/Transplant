import html
import re

from gazelle.tracker_data import tr, ReleaseType, ArtistType, Encoding


class TorrentInfo:
    def __init__(self):
        self.grp_id: int | None = None
        self.img_url: str | None = None
        self.title: str | None = None
        self.o_year: int | None = None
        self.rel_type: ReleaseType | None = None
        self.vanity: bool = False
        self.artist_data: dict | None = None
        self.tags: list | None = None
        self.alb_descr: str | None = None
    
        self.tor_id: int | None = None
        self.medium: str | None = None
        self.format: str | None = None
        self.encoding: Encoding | None = None
        self.rem_year: int | None = None
        self.rem_title: str | None = None
        self.rem_label: str | None = None
        self.rem_cat_nr: str | None = None
        self.scene: bool = False
        self.haslog: bool = False
        self.log_score: int | None = None
        self.log_ids: list | None = None
        self.rel_descr: str | None = None
        self.folder_name: str | None = None
        self.uploader_id: int | None = None
        self.uploader: str | None = None
    
        self.file_list: list | None = None
        self.unknown: bool = False
        self.src_tr: tr | None = None


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
    ARTIST_MAP = {
        'artists': 1,
        'with': 2,
        'remixedBy': 3,
        'composers': 4,
        'conductor': 5,
        'dj': 6,
        'producer': 7,
        'arranger': 8
    }

    def __init__(self, tr_resp: dict):
        super().__init__()

        for sub_name, sub_dict in self.FIELD_MAP.items():
            for gaz_name, torinfo_name in sub_dict.items():
                value = tr_resp[sub_name][gaz_name]
                if value:
                    setattr(self, torinfo_name, value)

        self.encoding = Encoding.mem_from_enc_str(tr_resp['torrent']['encoding'])

        files = []
        for s in tr_resp['torrent']['fileList'].split("|||"):
            match = re.match(r"(.+){{3}(\d+)}{3}", s)
            files.append({'names': match.group(1).split("/"),
                          'size': match.group(2)})
        self.file_list = files

        artists = {}
        for a_type, artist_list in tr_resp['group']['musicInfo'].items():
            artists[ArtistType(self.ARTIST_MAP[a_type])] = artist_list
        self.artist_data = artists


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

    def unexape(self, thing: str | list | dict | int):
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
