import html
import re

from gazelle.tracker_data import tr, RELEASE_TYPE_MAP

class TorrentInfo:
    field_mapping = {
        'wikiBody': ('group', 'wikiBody'),
        'img_url': ('group', 'wikiImage'),
        'grp_id': ('group', 'id'),
        'rel_type': ('group', 'releaseType'),
        'title': ('group', 'name'),
        'o_year': ('group', 'year'),
        'o_label': ('group', 'recordLabel'),
        'o_cat_nr': ('group', 'catalogueNumber'),
        'vanity': ('group', 'vanityHouse'),
        'artist_data': ('group', 'musicInfo'),
        'tags': ('group', 'tags'),
        'tor_id': ('torrent', 'id'),
        'medium': ('torrent', 'media'),
        'format': ('torrent', 'format'),
        'encoding': ('torrent', 'encoding'),
        'remastered': ('torrent', 'remastered'),
        'rem_year': ('torrent', 'remasterYear'),
        'rem_title': ('torrent', 'remasterTitle'),
        'rem_label': ('torrent', 'remasterRecordLabel'),
        'rem_cat_nr': ('torrent', 'remasterCatalogueNumber'),
        'scene': ('torrent', 'scene'),
        'haslog': ('torrent', 'hasLog'),
        'log_score': ('torrent', 'logScore'),
        'rel_descr': ('torrent', 'description'),
        'files_str': ('torrent', 'fileList'),
        'folder_name': ('torrent', 'filePath'),
        'uploader_id': ('torrent', 'userId'),
        'uploader': ('torrent', 'username')
    }
    tr_specific = {
        tr.RED: {
            'alb_descr': ('group', 'bbBody')
        },
        tr.OPS: {
            'alb_descr': ('group', 'wikiBBcode'),
            'log_ids': ('torrent', 'ripLogIds')
        }
    }

    def __init__(self, src_tr, tr_resp, **kwargs):
        self.grp_id = None
        self.img_url = None
        self.title = None
        self.o_year = None
        self.o_label = None
        self.o_cat_nr = None
        self.rel_type = None
        self.vanity = None
        self.artist_data = None
        self.tags = None
        self.alb_descr = None
        self.wikibody = None

        self.tor_id = None
        self.medium = None
        self.format = None
        self.encoding = None
        self.remastered = None
        self.rem_year = None
        self.rem_title = None
        self.rem_label = None
        self.rem_cat_nr = None
        self.scene = None
        self.haslog = None
        self.log_score = None
        self.log_ids = None
        self.rel_descr = None
        self.files_str = None
        self.folder_name = None
        self.uploader_id = None
        self.uploader = None

        self.src_tr = src_tr
        self.rel_type_name = None
        self.file_list = None
        self.unknown = False

        fields = self.field_mapping.copy()
        if self.src_tr in self.tr_specific:
            fields.update(self.tr_specific[self.src_tr])
        self.set_fields(fields, tr_resp)
        self.set_rel_type_name()
        self.parse_files_str()
        self.unknown_etc()
        self.further_actions(**kwargs)

    def set_fields(self, fields, api_r):
        for k, (sub, name) in fields.items():
            value = self.value_action(api_r[sub][name], k)
            setattr(self, k, value)

    def set_rel_type_name(self):
        for name, num in RELEASE_TYPE_MAP[self.src_tr].items():
            if num == self.rel_type:
                self.rel_type_name = name
                break

    def parse_files_str(self):
        files = []
        for s in self.files_str.split("|||"):
            match = re.match(r"(.+){{3}(\d+)}{3}", s)
            files.append({'names': match.group(1).split("/"),
                          'size': match.group(2)})
        self.file_list = files

    def value_action(self, value, key):
        return value

    def unknown_etc(self):
        pass

    def further_actions(self, **kwargs):
        pass

    def __repr__(self):
        return self.folder_name


class TradTorrentInfo(TorrentInfo):

    def further_actions(self, **kwargs):
        if not self.alb_descr:
            req_m = kwargs['req_m']
            data = {'html': self.wikibody}
            r = req_m('POST', 'upload', data=data, action='parse_html')
            self.alb_descr = r.text


class REDTorrentInfo(TorrentInfo):

    def value_action(self, value, _):
        try:
            value = html.unescape(value)
        except TypeError:
            pass
        return value

    def unknown_etc(self):
        if self.rem_year == 0:
            if self.remastered:
                self.unknown = True
            else:
                # unconfirmed
                self.remastered = True
                self.rem_year = self.o_year
                self.rem_label = self.o_label
                self.rem_cat_nr = self.o_cat_nr

class OPSTorrentInfo(TorrentInfo):
    artist_strip_regex = re.compile(r'(.+)\s\(\d+\)$')

    def strip_artists(self):
        for a_type, artists in self.artist_data.items():
            for a in artists:
                if match := self.artist_strip_regex.match(a['name']):
                    stripped = match.group(1)
                    a['name'] = stripped

    def unknown_etc(self):
        if self.remastered and not self.rem_year:
            self.unknown = True

    def further_actions(self, **kwargs):
        self.strip_artists()

        # get rid of original release
        if not self.remastered:
            self.rem_year = self.o_year
            self.rem_label = self.o_label
            self.rem_cat_nr = self.o_cat_nr

        if self.medium == 'BD':
            self.medium = 'Blu-Ray'

        if self.rel_type_name == 'Sampler':
            self.rel_type_name = 'Compilation'


tr_map = {
    tr.RED: REDTorrentInfo,
    tr.OPS: OPSTorrentInfo
}
