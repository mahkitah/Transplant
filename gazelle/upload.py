import logging
from pathlib import Path
from bcoding import bencode, bdecode
from gazelle.tracker_data import tr, ReleaseType, Encoding, BAD_RED_ENCODINGS
from lib import tp_text

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
        self.rel_type = None
        self.artists = None
        self.title = None
        self.o_year = None
        self.unknown: bool = False
        self.remastered: bool = True
        self.rem_year = None
        self.rem_title = None
        self.rem_label = None
        self.rem_cat_nr = None
        self.scene: bool = False
        self.medium = None
        self.format = None
        self.encoding = None
        self.other_bitrate = None
        self.vbr: bool = False
        self.vanity: bool = False
        self.tags = None
        self.upl_img_url = None
        self.alb_descr = None
        self.rel_descr = None
        self.request_id = None
        self.extra_format = None
        self.extra_encoding = None
        self.extra_rel_descr = None
        self.src_tr = None

    def _get_field(self, name: str, dest: tr):

        if name == 'rel_type':
            return self.rel_type.tracker_value(dest)
        if name == 'encoding':
            return self.encoding.name
        if name == 'alb_descr':
            src_url = self.src_tr.site
            dest_url = dest.site
            return self.alb_descr.replace(src_url, dest_url)

        return getattr(self, name)

    def upl_dict(self, dest: tr, dest_group=None):

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

        if dest == tr.RED:
            if (self.encoding in BAD_RED_ENCODINGS or
                    (self.encoding == Encoding.Other and self.other_bitrate < 192)):
                raise ValueError(tp_text.bad_bitr)
            if self.rel_type == ReleaseType.Sampler:
                upl_data['releasetype'] = 7
            if self.rel_type == ReleaseType.Split:
                upl_data['releasetype'] = 21
                report.warning(tp_text.split_warn)
            if self.unknown:
                upl_data['remaster_year'] = '1990'
                upl_data['remaster_title'] = 'Unknown release year'

        elif dest == tr.OPS:
            upl_data['workaround_broken_html_entities'] = 0
            if self.medium == 'Blu-Ray':
                upl_data['media'] = 'BD'

        return upl_data


class Dtor:
    def __init__(self, tor):

        if isinstance(tor, bytes):
            self._tdict = bdecode(tor)
        elif isinstance(tor, dict):
            self._tdict = {'info': tor['info']}
            if 'announce' in tor:
                self._tdict['announce'] = tor['announce']
        elif isinstance(tor, Path):
            self._tdict = bdecode(tor.read_bytes())
        else:
            raise TypeError

    @property
    def as_bytes(self):
        return bencode(self._tdict)

    @property
    def as_dict(self):
        return self._tdict.copy()

    def trackerise(self, announce=None, source=None):
        if announce:
            self._tdict['announce'] = announce
        if source:
            self._tdict['info']['source'] = source
        else:
            try:
                del self._tdict['info']['source']
            except KeyError:
                pass


class Files:
    def __init__(self):
        self.dtors = []
        self.logs = []

    def add_log(self, log):
        if isinstance(log, Path):
            self.logs.append(log.read_bytes())
        elif isinstance(log, bytes):
            self.logs.append(log)
        else:
            raise TypeError

    def add_dtor(self, dtor):
        self.dtors.append(Dtor(dtor))

    @staticmethod
    def tor_field_names():
        index = 0
        while True:
            if not index:
                yield 'file_input'
            else:
                yield f'extra_file_{index}'
            index += 1

    def files_list(self, announce=None, source=None) -> list:
        files = []
        for field_name, dtor, i in zip(self.tor_field_names(), self.dtors, range(len(self.dtors))):
            if announce or source:
                dtor.trackerise(announce, source)
            files.append((field_name, (f'blabla{i}.torrent', dtor.as_bytes, 'application/x-bittorrent')))

        for log in self.logs:
            files.append(('logfiles[]', ('log.log', log, 'application/octet-stream')))

        return files
