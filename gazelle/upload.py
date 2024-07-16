import logging
from pathlib import Path
from bcoding import bencode, bdecode
from gazelle.tracker_data import TR, ReleaseType, ArtistType, Encoding
from lib import tp_text
from lib .utils import uni_t_table

report = logging.getLogger('tr.upl')


FIELD_MAPPING = {
    'edition': {
        'unknown': 'unknown',
        'remastered': 'remaster',
        'rem_year': 'remaster_year',
        'rem_title': 'remaster_title',
        'rem_label': 'remaster_record_label',
        'rem_cat_nr': 'remaster_catalogue_number',
        'scene': 'scene',
        'medium': 'media',
        'format': 'format',
        'encoding': 'bitrate',
        'other_bitrate': 'other_bitrate',
        'vbr': 'vbr',
        'rel_descr': 'release_desc',
        'request_id': 'requestid',
        'extra_format': 'extra_format[]',
        'extra_encoding': 'extra_bitrate[]',
        'extra_rel_descr': 'extra_release_desc[]'
    },
    'group': {
        'rel_type': 'releasetype',
        'title': 'title',
        'o_year': 'year',
        'tags': 'tags',
        'upl_img_url': 'image',
        'vanity': 'vanity_house',
        'alb_descr': 'album_desc'
    }
}


class UploadData:
    def __init__(self):
        self.rel_type: ReleaseType | None = None
        self.artists: dict[str, list[ArtistType]] | None = None
        self.title: str | None = None
        self.o_year: int | None = None
        self.unknown: bool = False
        self.remastered: bool = True
        self.rem_year: int | None = None
        self.rem_title: str | None = None
        self.rem_label: str | None = None
        self.rem_cat_nr: str | None = None
        self.scene: bool = False
        self.medium: str | None = None
        self.format: str | None = None
        self.encoding: Encoding | None = None
        self.other_bitrate: int | None = None
        self.vbr: bool = False
        self.vanity: bool = False
        self.tags: str | None = None
        self.upl_img_url: str | None = None
        self.alb_descr: str | None = None
        self.rel_descr: str | None = None
        self.request_id: int | None = None
        self.extra_format: str | None = None
        self.extra_encoding: str | None = None
        self.extra_rel_descr: str | None = None
        self.src_tr: TR | None = None

    def _get_field(self, name: str, dest: TR):

        if name == 'rel_type':
            return self.rel_type.tracker_value(dest)
        if name == 'encoding':
            return self.encoding.name
        if name == 'alb_descr':
            return self.alb_descr.replace(self.src_tr.site, dest.site)

        return getattr(self, name)

    def upl_dict(self, dest: TR, dest_group=None):

        field_map = FIELD_MAPPING['edition'].copy()
        upl_data = {'type': 0}

        if dest_group:
            upl_data['groupid'] = dest_group
        else:
            field_map.update(FIELD_MAPPING['group'])

            artists = []
            importances = []
            for artist_name, a_types in self.artists.items():
                for a_type in a_types:
                    artists.append(artist_name)
                    importances.append(a_type.nr)
            upl_data['artists[]'] = artists
            upl_data['importance[]'] = importances

        for k, v in field_map.items():
            value = self._get_field(k, dest)
            if value:
                upl_data[v] = value

        if dest == TR.RED:
            if self.rel_type == ReleaseType.Sampler:
                upl_data['releasetype'] = 7
            if self.rel_type == ReleaseType.Split:
                upl_data['releasetype'] = 21
                report.warning(tp_text.split_warn)
            if self.unknown:
                upl_data['remaster_year'] = '1990'
                upl_data['remaster_title'] = 'Unknown release year'

        elif dest == TR.OPS:
            upl_data['workaround_broken_html_entities'] = 0
            if self.medium == 'Blu-Ray':
                upl_data['media'] = 'BD'

        return upl_data


class Dtor:
    def __init__(self, tor: bytes | dict | Path):
        self.announce = None
        self.source = None

        if isinstance(tor, bytes):
            self.t_info = bdecode(tor)['info']
        elif isinstance(tor, dict):
            self.t_info = tor['info']
        elif isinstance(tor, Path):
            self.t_info = bdecode(tor.read_bytes())['info']
        else:
            raise TypeError

        if 'source' in self.t_info:
            del self.t_info['source']

        self.lrm = False

        self.stripped_info = self.t_info.copy()
        self.stripped_info['name'] = self.t_info['name'].translate(uni_t_table)
        for fd in self.stripped_info['files']:
            p_elements: list = fd['path']
            fd['path'] = [e.translate(uni_t_table) for e in p_elements]
        if self.stripped_info != self.t_info:
            self.lrm = True

    def as_bytes(self, u_strip=False):
        return bencode(self.as_dict(u_strip))

    def as_dict(self, u_strip=False):
        tordict = {}
        if self.announce:
            tordict['announce'] = self.announce
        if not self.lrm or not u_strip:
            info = self.t_info
        else:
            info = self.stripped_info
        if self.source:
            info['source'] = self.source

        tordict['info'] = info
        return tordict

    def trackerise(self, announce=None, source=None):
        self.announce = announce
        self.source = source


class Files:
    def __init__(self):
        self.dtors: list[Dtor] = []
        self.logs: list[bytes] = []

    def add_log(self, log: Path | bytes):
        if isinstance(log, Path):
            log = log.read_bytes()
        elif isinstance(log, bytes):
            pass
        else:
            raise TypeError
        if log not in self.logs:
            self.logs.append(log)

    def add_dtor(self, dtor):
        self.dtors.append(Dtor(dtor))

    @staticmethod
    def tor_field_names():
        index = 0
        while True:
            if not index:
                yield 'file_input', index
            else:
                yield f'extra_file_{index}', index
            index += 1

    def files_list(self, announce=None, source=None, u_strip=False) -> list:
        files = []
        for (field_name, i), dtor in zip(self.tor_field_names(), self.dtors):
            dtor.trackerise(announce, source)
            files.append((field_name, (f'blabla{i}.torrent', dtor.as_bytes(u_strip), 'application/x-bittorrent')))

        for log in self.logs:
            files.append(('logfiles[]', ('log.log', log, 'application/octet-stream')))

        return files
