import logging

from gazelle.upload import FormData
from gazelle.tracker_data import ARTIST_MAP
from lib import utils, ui_text, ptpimg_uploader

report = logging.getLogger(__name__)

class TorInfo2UplData(FormData):
    one_on_one = ('medium', 'format', 'rem_year', 'rem_title', 'rem_label', 'rem_cat_nr', 'src_tr', 'unknown',
                  'rel_type_name', 'title', 'o_year', 'vanity', 'scene', 'remastered', 'alb_descr')

    def __init__(self, tor_info, img_rehost, whitelist, ptpimg_key, rel_descr_templ, rel_descr_own_templ, add_src_descr,
                 src_descr_templ, user_id):
        super().__init__()
        self.tor_info = tor_info

        self.img_rehost = img_rehost
        self.whitelist = whitelist
        self.ptpimg_key = ptpimg_key
        self.rel_descr_templ = rel_descr_templ
        self.rel_descr_own_templ = rel_descr_own_templ
        self.add_src_descr = add_src_descr
        self.src_descr_templ = src_descr_templ
        self.user_id = user_id

        self.parse_input()
        # self.medium = 'blabla'

    def parse_input(self):
        self.parse_artists()
        self.bitrate()
        self.tags_to_string()
        self.release_description()
        self.do_img()
        for name in self.one_on_one:
            if not hasattr(self, name):
                raise AttributeError
            setattr(self, name, getattr(self.tor_info, name))

    def parse_artists(self):
        artists = []
        importances = []
        for a_type, names in self.tor_info.artist_data.items():
            imp = ARTIST_MAP.get(a_type)
            if imp:
                for n in names:
                    importances.append(imp)
                    artists.append(n['name'])

        self.artists = artists
        self.importances = importances

    def bitrate(self):
        inp_encoding = self.tor_info.encoding
        if inp_encoding in ['192', 'APS (VBR)', 'V2 (VBR)', 'V1 (VBR)', '256', 'APX (VBR)',
                            'V0 (VBR)', 'Lossless', '24bit Lossless']:
            self.encoding = inp_encoding
        else:
            self.encoding = 'Other'
            if inp_encoding.endswith('(VBR)'):
                self.vbr_bitrate = True
                inp_encoding = inp_encoding[:-6]

            self.other_bitrate = inp_encoding

    def tags_to_string(self):
        # There's a 200 character limit for tags (including commas)
        tag_string = ",".join(self.tor_info.tags)

        if len(tag_string) > 200:
            tag_string = tag_string[:tag_string.rfind(',', 0, 201)]

        self.tags = tag_string

    def release_description(self):
        descr_placeholders = {
            '%src_id%': self.tor_info.src_tr.name,
            '%src_url%': self.tor_info.src_tr.site,
            '%ori_upl%': self.tor_info.uploader,
            '%upl_id%': str(self.tor_info.uploader_id),
            '%tor_id%': str(self.tor_info.tor_id),
            '%gr_id%': str(self.tor_info.grp_id)
        }
        if self.user_id == self.tor_info.uploader_id:
            templ = self.rel_descr_own_templ
        else:
            templ = self.rel_descr_templ

        rel_descr = utils.multi_replace(templ, descr_placeholders)

        src_descr = self.tor_info.rel_descr
        if src_descr and self.add_src_descr:
            rel_descr += '\n\n' + utils.multi_replace(self.src_descr_templ, descr_placeholders, {'%src_descr%': src_descr})

        self.rel_descr = rel_descr

    def do_img(self):
        src_img_url = self.tor_info.img_url

        if not self.img_rehost or not src_img_url or any(w in src_img_url for w in self.whitelist):
            self.upl_img_url = src_img_url

        else:
            try:
                self.upl_img_url = ptpimg_uploader.upload(self.ptpimg_key, [src_img_url])[0]
                report.info(f"{ui_text.img_rehosted} {self.upl_img_url}")

            except (ptpimg_uploader.UploadFailed, ValueError):
                report.info(ui_text.rehost_failed)
                self.upl_img_url = src_img_url
