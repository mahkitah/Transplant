import re
from lib import utils
from bencoder import bencode, bdecode
from gazelle.tracker_data import tr, tr_data, RELEASE_TYPE_MAP

LOGS_TO_IGNORE = ["audiochecker.log", "aucdtect.log", "info.log"]

class FormData:
    field_mapping = {
        'release': {
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

        self.submit = False
        self.src_tr = None
        self.unknown = False

    def _get_field(self, name, dest):

        if name == 'rel_type':
            if dest in RELEASE_TYPE_MAP:
                return RELEASE_TYPE_MAP[dest][self.rel_type_name]

        if name == 'alb_descr':
            src_url = tr_data[self.src_tr]['site']
            dest_url = tr_data[dest]['site']
            return self.alb_descr.replace(src_url, dest_url)

        return getattr(self, name)

    def upl_dict(self, dest, dest_group=None):

        field_map = self.field_mapping['release'].copy()
        if not dest_group:
            field_map.update(self.field_mapping['group'])

        if dest == tr.bB:
            return self.bacon_dict(field_map)

        upl_data = {'type': 0}
        for k, v in field_map.items():
            value = self._get_field(k, dest)
            if value:
                upl_data[v] = value
        if self.submit:
            upl_data['submit'] = True
        if self.unknown:
            if dest == tr.RED:
                upl_data['remaster_year'] = '1990'
                upl_data['remaster_title'] = 'Unknown release year'

            elif dest == tr.OPS:
                # BUG There has to be a rem.year > 1982
                # https://orpheus.network/forums.php?action=viewthread&threadid=10003
                # https://orpheus.network/forums.php?action=viewthread&threadid=5994
                upl_data['remaster_year'] = '1990'
        return upl_data

    def bacon_dict(self, field_map):
        dont_do = ('remastered',
                   'rem_year',
                   'rem_title',
                   'rem_label',
                   'rem_cat_nr',
                   'extra_format',
                   'extra_encoding',
                   'extra_rel_descr',
                   'request_id',
                   'rel_descr',
                   'rel_type',
                   'artists',
                   'importances',
                   'vanity',
                   'medium')

        for x in dont_do:
            del field_map[x]

        upl_data = {'submit': True, 'type': 'Music'}

        for k, v in field_map.items():
            value = getattr(self, k)
            if value:
                upl_data[v] = value

        mains = [name for name, imp in zip(self.artists, self.importances) if imp == 1]
        if len(mains) <= 3:
            artists = utils.joiner(mains)
        else:
            artists = 'Various Artists'

        upl_data.update({
            "artist": artists,
            "media": self.medium.replace('WEB', 'Web'),
        })

        if 'Lossless' in self.encoding:
            upl_data['bitrate'] = 'Lossless'
        if '24bit' in self.encoding:
            upl_data['format'] = '24bit FLAC'

        if self.o_year != self.rem_year:
            upl_data['remaster'] = True
            upl_data['remaster_year'] = self.rem_year
            if self.rem_title:
                upl_data['remaster_title'] = self.rem_title

        rel_descr = ' / '.join((x for x in (str(self.rem_year), self.rem_label, self.rem_cat_nr, self.rem_title) if x))
        rel_descr += '\n\n' + re.sub(r'\[/?hide.*?]', '', self.rel_descr)
        upl_data['release_desc'] = rel_descr

        return upl_data


class Dtor:
    def __init__(self, tbytes=None, tdict=None, path=None):
        assert len([x for x in (tbytes, tdict, path) if x]) == 1
        self._tdict = None

        if tbytes:
            self._tdict = bdecode(tbytes)
        if tdict:
            try:
                utils.dict_stringkeys_to_bytes(tdict)
            except AttributeError:
                raise TypeError("Input doesn't seem to be a dict")  # TODO uitext

            self._tdict = {b'info': tdict[b'info']}
            if b'announce' in tdict:
                self._tdict[b'announce'] = tdict[b'announce']
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
            self._tdict[b'announce'] = announce.encode()
        if source:
            self._tdict[b'info'][b'source'] = source.encode()
        else:
            try:
                del self._tdict[b'info'][b'source']
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
    def tor_field_names(index=0):
        while True:
            if not index:
                name = 'file_input'
            else:
                name = f'extra_file_{index}'
            index += 1
            yield name

    def files_list(self, announce=None, source=None):
        files = []
        for field_name, dtor, i in zip(self.tor_field_names(), self.dtors, range(len(self.dtors))):
            if announce or source:
                dtor.trackerise(announce, source)
            files.append((field_name, (f'blabla{i}.torrent', dtor.as_bytes, 'application/x-bittorrent')))

        for log in self.logs:
            files.append(('logfiles[]', ('log.log', log, 'application/octet-stream')))

        return files
