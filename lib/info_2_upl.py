import re
import logging
from collections import defaultdict

from gazelle.upload import UploadData
from gazelle.tracker_data import ArtistType, ReleaseType, Encoding
from lib import utils, tp_text, img_rehost

report = logging.getLogger('tr.upl')


class TorInfo2UplData(UploadData):
    one_on_one = ('medium', 'format', 'rem_year', 'rem_title', 'rem_label', 'rem_cat_nr', 'src_tr', 'unknown',
                  'rel_type', 'encoding', 'title', 'o_year', 'vanity', 'scene', 'alb_descr')

    def __init__(self, tor_info, img_rehost, whitelist, rel_descr_templ, rel_descr_own_templ, add_src_descr,
                 src_descr_templ, user_id, dest_group):
        super().__init__()
        self.tor_info = tor_info

        self.img_rehost = img_rehost
        self.whitelist = whitelist
        self.rel_descr_templ = rel_descr_templ
        self.rel_descr_own_templ = rel_descr_own_templ
        self.add_src_descr = add_src_descr
        self.src_descr_templ = src_descr_templ
        self.user_id = user_id
        self.dest_group = dest_group

        self.parse_input()
        # self.medium = 'blabla'

    def parse_input(self):
        self.release_description()
        if not self.dest_group:
            self.parse_artists()
            self.tags_to_string()
            self.do_img()

        for name in self.one_on_one:
            if not hasattr(self, name):
                raise AttributeError(f'no {name}')
            setattr(self, name, getattr(self.tor_info, name))

        if self.encoding == Encoding.Other:
            self.other_bitrate = self.encoding.bitr
            self.vbr = self.encoding.vbr

    def parse_artists(self):
        artists = defaultdict(list)
        a_type: ArtistType
        for a_type, artist_list in self.tor_info.artist_data.items():
            # a_dict: {'id': int, 'name': str}
            for a_dict in artist_list:
                artists[a_dict['name']].append(a_type)

        self.artists = dict(artists)

    decade_rex = re.compile(r'((19|20)\d)0s')

    def tag_gen(self):
        skip_decade = self.tor_info.rel_type in (ReleaseType.Album, ReleaseType.EP, ReleaseType.Single)
        for tag in self.tor_info.tags:
            if skip_decade and (m := self.decade_rex.fullmatch(tag)):
                if m.group(1) == str(self.tor_info.o_year)[:3]:
                    continue
            yield tag

    def tags_to_string(self):
        tag_list = list(self.tag_gen()) or self.tor_info.tags

        # There's a 200-character limit for tags (including commas)
        tag_string = ",".join(tag_list)

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
            rel_descr += '\n\n' + utils.multi_replace(self.src_descr_templ, descr_placeholders,
                                                      {'%src_descr%': src_descr})

        self.rel_descr = rel_descr

    def do_img(self):
        src_img_url = self.tor_info.img_url

        if not self.img_rehost or not src_img_url or any(w in src_img_url for w in self.whitelist):
            self.upl_img_url = src_img_url
            return

        rehosted = img_rehost.rehost(src_img_url)
        if rehosted:
            self.upl_img_url = rehosted
            report.info(f"{tp_text.img_rehosted} {self.upl_img_url}")
        else:
            report.info(tp_text.rehost_failed)
            self.upl_img_url = src_img_url
