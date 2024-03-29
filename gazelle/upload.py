from bcoding import bencode, bdecode
from gazelle.tracker_data import tr, ReleaseType, ArtistType


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
        self.encoding: str | None = None
        self.other_bitrate: str | None = None
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
        self.src_tr: tr | None = None

    def _get_field(self, name, dest: tr):

        if name == 'rel_type':
            return self.rel_type.tracker_value(dest)

        if name == 'alb_descr':
            src_url = self.src_tr.site
            dest_url = dest.site
            return self.alb_descr.replace(src_url, dest_url)

        return getattr(self, name)

    def upl_dict(self, dest, dest_group=None):

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
                    importances.append(a_type.value)
            upl_data['artists[]'] = artists
            upl_data['importance[]'] = importances

        for k, v in field_map.items():
            value = self._get_field(k, dest)
            if value:
                upl_data[v] = value

        if dest == tr.RED:
            if self.unknown:
                upl_data['remaster_year'] = '1990'
                upl_data['remaster_title'] = 'Unknown release year'

            if self.rel_type == ReleaseType.Sampler:
                self.rel_type = ReleaseType.Compilation

        elif dest == tr.OPS:
            upl_data['workaround_broken_html_entities'] = 0
            if self.medium == 'Blu-Ray':
                upl_data['media'] = 'BD'

        return upl_data


class Dtor:
    def __init__(self, tbytes=None, tdict=None, path=None):

        assert len([x for x in (tbytes, tdict, path) if x]) == 1
        self._tdict = None

        if tbytes:
            self._tdict = bdecode(tbytes)
        if tdict:
            self._tdict = {'info': tdict['info']}
            if 'announce' in tdict:
                self._tdict['announce'] = tdict['announce']
        if path:
            with open(path, 'rb') as f:
                self._tdict = bdecode(f.read())

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

    def add_log(self, log, as_path=False):
        if as_path:
            with open(log, 'rb') as f:
                self.logs.append(f.read())
        else:
            assert isinstance(log, bytes)
            self.logs.append(log)

    def add_dtor(self, dtor, as_dict=False, as_path=False):
        if as_path:
            self.dtors.append(Dtor(path=dtor))
        elif as_dict:
            self.dtors.append(Dtor(tdict=dtor))
        else:
            assert isinstance(dtor, bytes)
            self.dtors.append(Dtor(tbytes=dtor))

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
