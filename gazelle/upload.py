from bcoding import bencode, bdecode
from gazelle.tracker_data import tr, RELEASE_TYPE_MAP

class FormData:
    field_mapping = {
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
            'vbr_bitrate': 'vbr',
            'rel_descr': 'release_desc',
            'request_id': 'requestid',
            'extra_format': 'extra_format[]',
            'extra_encoding': 'extra_bitrate[]',
            'extra_rel_descr': 'extra_release_desc[]'
        },
        'group': {
            'rel_type': 'releasetype',
            'artists': 'artists[]',
            'importances': 'importance[]',
            'title': 'title',
            'o_year': 'year',
            'tags': 'tags',
            'upl_img_url': 'image',
            'vanity': 'vanity_house',
            'alb_descr': 'album_desc'
        }
    }

    def __init__(self):
        self.rel_type_name = None
        self.artists = None
        self.importances = None
        self.title = None
        self.o_year = None
        self.unknown = False
        self.remastered = False
        self.rem_year = None
        self.rem_title = None
        self.rem_label = None
        self.rem_cat_nr = None
        self.scene = False
        self.medium = None
        self.format = None
        self.encoding = None
        self.other_bitrate = None
        self.vbr_bitrate = False
        self.vanity = False
        self.tags = None
        self.upl_img_url = None
        self.alb_descr = None
        self.rel_descr = None
        self.request_id = None
        self.extra_format = None
        self.extra_encoding = None
        self.extra_rel_descr = None

        self.src_tr = None
        self.unknown = False

    def _get_field(self, name, dest):

        if name == 'rel_type':
            return RELEASE_TYPE_MAP[dest][self.rel_type_name]

        if name == 'alb_descr':
            src_url = self.src_tr.site
            dest_url = dest.site
            return self.alb_descr.replace(src_url, dest_url)

        return getattr(self, name)

    def upl_dict(self, dest, dest_group=None):

        field_map = self.field_mapping['edition'].copy()
        upl_data = {'type': 0}

        if dest_group:
            upl_data['groupid'] = dest_group
        else:
            field_map.update(self.field_mapping['group'])

        for k, v in field_map.items():
            value = self._get_field(k, dest)
            if value:
                upl_data[v] = value

        if dest == tr.RED:
            if self.unknown:
                upl_data['remaster_year'] = '1990'
                upl_data['remaster_title'] = 'Unknown release year'

        elif dest == tr.OPS:
            if self.unknown:
                # BUG There has to be a rem.year > 1982
                # https://orpheus.network/forums.php?action=viewthread&threadid=10003
                # https://orpheus.network/forums.php?action=viewthread&threadid=5994
                upl_data['remaster_year'] = '1990'

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

    def files_list(self, announce=None, source=None):
        files = []
        for field_name, dtor, i in zip(self.tor_field_names(), self.dtors, range(len(self.dtors))):
            if announce or source:
                dtor.trackerise(announce, source)
            files.append((field_name, (f'blabla{i}.torrent', dtor.as_bytes, 'application/x-bittorrent')))

        for log in self.logs:
            files.append(('logfiles[]', ('log.log', log, 'application/octet-stream')))

        return files
