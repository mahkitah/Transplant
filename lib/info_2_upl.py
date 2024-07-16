import re
import logging
from typing import Iterable
from collections import defaultdict

from lib.img_rehost import IH
from lib import utils, tp_text
from gazelle.upload import UploadData
from gazelle.tracker_data import ReleaseType
from gazelle.torrent_info import TorrentInfo

report = logging.getLogger('tr.inf2upl')


class TorInfo2UplData:
    group = ('rel_type', 'title', 'o_year', 'vanity', 'alb_descr')
    torrent = ('medium', 'format', 'rem_year', 'rem_title', 'rem_label',
               'rem_cat_nr', 'unknown', 'encoding', 'other_bitrate', 'vbr', 'scene', 'src_tr')

    def __init__(self,
                 rehost_img: bool,
                 whitelist: Iterable,
                 rel_descr_templ: str,
                 rel_descr_own_templ: str,
                 add_src_descr: bool,
                 src_descr_templ: str,
                 ):
        self.rehost_img = rehost_img
        self.whitelist = whitelist
        self.rel_descr_templ = rel_descr_templ
        self.rel_descr_own_templ = rel_descr_own_templ
        self.add_src_descr = add_src_descr
        self.src_descr_templ = src_descr_templ

    def field_gen(self, dest_grp):
        if not dest_grp:
            yield from self.group

        yield from self.torrent

    def translate(self, tor_info: TorrentInfo, user_id: int, dest_group: int) -> UploadData:
        u_data = UploadData()

        for name in self.field_gen(dest_group):
            setattr(u_data, name, getattr(tor_info, name))

        self.release_description(tor_info, u_data, user_id)
        if not dest_group:
            self.parse_artists(tor_info, u_data)
            self.tags_to_string(tor_info, u_data)
            if self.rehost_img:
                self.do_img(tor_info, u_data)

        return u_data

    def release_description(self, tor_info, u_data, user_id):
        descr_placeholders = {
            '%src_id%': tor_info.src_tr.name,
            '%src_url%': tor_info.src_tr.site,
            '%ori_upl%': tor_info.uploader,
            '%upl_id%': str(tor_info.uploader_id),
            '%tor_id%': str(tor_info.tor_id),
            '%gr_id%': str(tor_info.grp_id)
        }
        if user_id == tor_info.uploader_id:
            templ = self.rel_descr_own_templ
        else:
            templ = self.rel_descr_templ

        rel_descr = utils.multi_replace(templ, descr_placeholders)

        src_descr = tor_info.rel_descr
        if src_descr and self.add_src_descr:
            rel_descr += '\n\n' + utils.multi_replace(self.src_descr_templ, descr_placeholders,
                                                      {'%src_descr%': src_descr})
        u_data.rel_descr = rel_descr

    @staticmethod
    def parse_artists(tor_info, u_data):
        artists = defaultdict(list)
        for a_type, artist_list in tor_info.artist_data.items():
            # a_dict: {'id': int, 'name': str}
            for a_dict in artist_list:
                artists[a_dict['name']].append(a_type)

        u_data.artists = dict(artists)

    DECADE_REX = re.compile(r'((19|20)\d)0s')

    def tag_gen(self, tor_info):
        skip_decade = tor_info.rel_type in (ReleaseType.Album, ReleaseType.EP, ReleaseType.Single)
        for tag in tor_info.tags:
            if skip_decade and (m := self.DECADE_REX.fullmatch(tag)):
                if m.group(1) == str(tor_info.o_year)[:3]:
                    continue
            yield tag

    def tags_to_string(self, tor_info, u_data):
        tag_list = list(self.tag_gen(tor_info)) or tor_info.tags
        tag_string = ",".join(tag_list)

        if len(tag_string) > 200:
            tag_string = tag_string[:tag_string.rfind(',', 0, 201)]

        u_data.tags = tag_string

    def do_img(self, tor_info, u_data):
        src_img_url = tor_info.img_url

        if not src_img_url or any(w in src_img_url for w in self.whitelist):
            u_data.upl_img_url = src_img_url
            return

        rehosted = IH.rehost(src_img_url)
        u_data.upl_img_url = rehosted or src_img_url
        if rehosted:
            report.info(f"{tp_text.img_rehosted} {rehosted}")
        else:
            report.info(tp_text.rehost_failed)
