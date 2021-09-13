import html
import re

field_names = {
    'img_url': ('group', 'wikiImage'),
    'grp_id': ('group', 'id'),
    'title': ('group', 'name'),
    'o_year': ('group', 'year'),
    'o_label': ('group', 'recordLabel'),
    'o_cat_nr': ('group', 'catalogueNumber'),
    'rel_type': ('group', 'releaseType'),
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
    'rel_descr': ('torrent', 'description'),
    'files_str': ('torrent', 'fileList'),
    'folder_name': ('torrent', 'filePath'),
    'uploader_id': ('torrent', 'userId'),
    'uploader': ('torrent', 'username')
}
tr_specific = {
    'RED': {
        'alb_descr': ('group', 'bbBody')
    },
    'OPS': {
        'alb_descr': ('group', 'wikiBBcode'),
        'log_ids': ('torrent', 'ripLogIds')
    }
}


class TorrentInfo:
    tr_fields = NotImplemented

    def __init__(self, req_m, **kwargs):
        self.img_url = None
        self.grp_id = None
        self.title = None
        self.o_year = None
        self.o_label = None
        self.o_cat_nr = None
        self.rel_type = None
        self.vanity = None
        self.artist_data = None
        self.tags = None
        self.alb_descr = None

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
        self.log_ids = None
        self.rel_descr = None
        self.files_str = None
        self.folder_name = None
        self.uploader_id = None
        self.uploader = None

        self.file_list = None
        self.unknown = False
        self.unconfirmed = False

        fields = field_names.copy()
        fields.update(self.tr_fields)
        r = req_m('GET', 'torrent', **kwargs)
        self.set_fields(fields, r)
        self.parse_files_str()
        self.unknown_etc()
        self.further_actions(req_m)

    def set_fields(self, fields, api_r):
        for k, v in fields.items():
            sub, name = v
            value = self.value_action(api_r[sub][name])
            setattr(self, k, value)

    def parse_files_str(self):
        files = []
        for s in self.files_str.split("|||"):
            match = re.match(r"(.+){{3}(\d+)}{3}", s)
            files.append({'names': match.group(1).split("/"),
                          'size': match.group(2)})
        self.file_list = files

    def value_action(self, value):
        raise NotImplementedError

    def unknown_etc(self):
        raise NotImplementedError

    def further_actions(self, api):
        raise NotImplementedError

    def __repr__(self):
        return self.folder_name

class REDTorrentInfo(TorrentInfo):
    tr_fields = tr_specific['RED']

    def __init__(self, api_r, **kwargs):
        super().__init__(api_r, **kwargs)

    def value_action(self, value):
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
                self.unconfirmed = True

    def further_actions(self, api):
        pass

class OPSTorrentInfo(TorrentInfo):
    tr_fields = tr_specific['OPS']

    def __init__(self, api_r, **kwargs):
        super().__init__(api_r, **kwargs)

    def value_action(self, value):
        return value

    def unknown_etc(self):
        if self.remastered and not self.rem_year:
            self.unknown = True

    def further_actions(self, req_m):
        # missing wiki info
        if not any((self.alb_descr, self.img_url)):
            group_info = req_m('GET', 'torrentgroup', id=self.grp_id)
            self.img_url = group_info['group']['wikiImage']
            self.alb_descr = group_info['group']['wikiBBcode']

        # tags not a proper list
        if len(self.tags) == 1:
            self.tags = self.tags[0].split(',')
