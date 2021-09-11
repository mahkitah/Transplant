import html
from lib import utils

class TorrentInfo:
    field_names = {
        'img_url': 'group/wikiImage',
        'grp_id': 'group/id',
        'title': 'group/name',
        'o_year': 'group/year',
        'o_label': 'group/recordLabel',
        'o_cat_nr': 'group/catalogueNumber',
        'rel_type': 'group/releaseType',
        'vanity': 'group/vanityHouse',
        'artist_data': 'group/musicInfo',
        'tags': 'group/tags',
        'tor_id': 'torrent/id',
        'medium': 'torrent/media',
        'format': 'torrent/format',
        'encoding': 'torrent/encoding',
        'remastered': 'torrent/remastered',
        'rem_year': 'torrent/remasterYear',
        'rem_title': 'torrent/remasterTitle',
        'rem_label': 'torrent/remasterRecordLabel',
        'rem_cat_nr': 'torrent/remasterCatalogueNumber',
        'scene': 'torrent/scene',
        'haslog': 'torrent/hasLog',
        'rel_descr': 'torrent/description',
        'file_list': 'torrent/fileList',
        'folder_name': 'torrent/filePath',
        'uploader_id': 'torrent/userId',
        'uploader': 'torrent/username'
    }
    tr_specific = {
        'OPS': {
            'alb_descr': 'group/wikiBBcode',
            'log_ids': 'torrent/ripLogIds'
        },
        'RED': {
            'alb_descr': 'group/bbBody'
        }
    }

    def __init__(self, api, **kwargs):
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
        self.file_list = None
        self.folder_name = None
        self.uploader_id = None
        self.uploader = None

        self.id = api.id
        fields = self.field_names.copy()
        fields.update(self.tr_specific[self.id])

        api_r = api.request('GET', 'torrent', **kwargs)

        for k, v in fields.items():
            sub, name = v.split('/')
            value = api_r[sub][name]
            if self.id == 'RED':
                try:
                    value = html.unescape(value)
                except TypeError:
                    pass
            setattr(self, k, value)

        if self.id == 'OPS':
            self.ops_bugs(api)

    def ops_bugs(self, api):
        # missing wiki info
        if not any((self.alb_descr, self.img_url)):
            group_info = api.request('GET', 'torrentgroup', id=self.grp_id)
            self.img_url = group_info['group']['wikiImage']
            self.alb_descr = group_info['group']['wikiBBcode']

        # tags not a proper list
        if len(self.tags) == 1:
            self.tags = self.tags[0].split(',')
