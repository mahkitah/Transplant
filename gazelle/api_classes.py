import re
import time
import base64
import logging
from hashlib import sha256
from collections import deque
from http.cookiejar import LWPCookieJar, LoadError

import requests
from requests.exceptions import JSONDecodeError

from lib import tp_text
from gazelle.torrent_info import TorrentInfo
from gazelle.tracker_data import TR


class RequestFailure(Exception):
    pass

report = logging.getLogger('tr.api')


class BaseApi:
    def __init__(self, tracker: TR, **kwargs):
        assert tracker in TR, 'Unknown Tracker'  # TODO uitext
        self.tr = tracker
        self.url = self.tr.site
        self.session = requests.Session()
        self.last_x_reqs = deque([.0], maxlen=self.tr.req_limit)
        self.authenticate(**kwargs)
        self._account_info = None

    def _rate_limit(self):
        t = time.time() - self.last_x_reqs[0]
        if t <= 10:
            time.sleep(10 - t)

    def authenticate(self, _):
        return NotImplementedError

    @property
    def announce(self):
        return self.tr.tracker.format(**self.account_info)

    @ property
    def account_info(self):
        if not self._account_info:
            self._account_info = self.get_account_info()

        return self._account_info

    def get_account_info(self):
        r = self.request('index')
        return {k: r[k] for k in ('authkey', 'passkey', 'id', 'username')}

    def request(self, url_suffix: str, data=None, files=None, **kwargs):
        url = self.url + url_suffix + '.php'
        report.debug(f'{self.tr.name} {url_suffix} {kwargs}')
        req_method = 'POST' if data or files else 'GET'

        self._rate_limit()
        r = self.session.request(req_method, url, params=kwargs, data=data, files=files)
        self.last_x_reqs.append(time.time())

        try:
            r_dict = r.json()
        except JSONDecodeError:
            if 'application/x-bittorrent' in r.headers['content-type']:
                return r.content
            else:
                raise RequestFailure(f'no json, no torrent. {r.status_code}')
        else:
            status = r_dict.get('status')
            if status == 'success':
                return r_dict['response']
            elif status == 'failure':
                raise RequestFailure(r_dict['error'])

            raise RequestFailure(r_dict)

    def torrent_info(self, **kwargs) -> TorrentInfo:
        r = self.request('torrent', **kwargs)
        return TorrentInfo(r, self.tr)

    def upload(self, upl_data: dict, files: list):
        return self._uploader(upl_data, files)

    def _uploader(self, data: dict, files: list) -> dict:
        r = self.request('upload', data=data, files=files)

        return self.upl_response_handler(r)

    def upl_response_handler(self, r):
        raise NotImplementedError


class KeyApi(BaseApi):

    def authenticate(self, **kwargs):
        key = kwargs['key']
        self.session.headers.update({"Authorization": key})

    def request(self, action: str, data=None, files=None, **kwargs):
        kwargs.update(action=action)
        return super().request('ajax', data=data, files=files, **kwargs)

    def upl_response_handler(self, r):
        raise NotImplementedError

    def get_riplog(self, tor_id: int, log_id: int):
        r: dict = self.request('riplog', id=tor_id, logid=log_id)
        log_bytes = base64.b64decode(r['log'])
        log_checksum = sha256(log_bytes).hexdigest()
        assert log_checksum == r['log_sha256']
        return log_bytes


class CookieApi(BaseApi):

    def authenticate(self, **kwargs):
        self.session.cookies = LWPCookieJar(f'cookie{self.tr.name}.txt')
        if not self._load_cookie():
            self._login(**kwargs)

    def _load_cookie(self) -> bool:
        jar = self.session.cookies
        try:
            jar.load()
            session_cookie = [c for c in jar if c.name == "session"][0]
            assert not session_cookie.is_expired()
        except (FileNotFoundError, LoadError, IndexError, AssertionError):
            return False

        return True

    def _login(self, **kwargs):
        username, password = kwargs['f']()
        data = {'username': username,
                'password': password,
                'keeplogged': '1'}
        self.session.cookies.clear()
        self.request('login', data=data)
        assert [c for c in self.session.cookies if c.name == 'session']
        self.session.cookies.save()

    def request(self, action: str, data=None, files=None, **kwargs):
        if action in ('upload', 'login'):  # TODO download?
            url_addon = action
        else:
            url_addon = 'ajax'
            kwargs.update(action=action)

        return super().request(url_addon, data=data, files=files, **kwargs)

    def _uploader(self, data: dict, files: list):
        data['submit'] = True
        super()._uploader(data, files)

    def upl_response_handler(self, r: requests.Response):
        if 'torrents.php' not in r.url:
            warning = re.search(r'<p style="color: red;text-align:center;">(.+?)</p>', r.text)
            raise RequestFailure(f"{warning.group(1) if warning else r.url}")
        return r.url  # TODO re torrentid from url and return


class HtmlApi(CookieApi):

    def get_account_info(self):
        r = self.session.get(self.url + 'index.php')
        return {
            'authkey': re.search(r"authkey=(.+?)[^a-zA-Z0-9]", r.text).group(1),
            'passkey': re.search(r"passkey=(.+?)[^a-zA-Z0-9]", r.text).group(1),
            'id': int(re.search(r"useri?d?=(.+?)[^0-9]", r.text).group(1))
        }

    def torrent_info(self, **kwargs):
        raise AttributeError(f'{self.tr.name} does not provide torrent info')


class RedApi(KeyApi):
    def __init__(self, key=None):
        super().__init__(TR.RED, key=key)

    def _uploader(self, data: dict, files: list) -> (int, int, str):
        try:
            unknown = data.pop('unknown')
        except KeyError:
            unknown = False

        torrent_id, group_id = super()._uploader(data, files)

        if unknown:
            try:
                self.request('torrentedit', id=torrent_id, data={'unknown': True})
                report.info(tp_text.upl_to_unkn)
            except (RequestFailure, requests.HTTPError) as e:
                report.warning(f'{tp_text.edit_fail}{str(e)}')
        return torrent_id, group_id, self.url + f"torrents.php?id={group_id}&torrentid={torrent_id}"

    def upl_response_handler(self, r: dict) -> (int, int):
        return r.get('torrentid'), r.get('groupid')


class OpsApi(KeyApi):
    def __init__(self, key=None):
        super().__init__(TR.OPS, key=f"token {key}")

    def upl_response_handler(self, r):
        group_id = r.get('groupId')
        torrent_id = r.get('torrentId')

        return torrent_id, group_id, self.url + f"torrents.php?id={group_id}&torrentid={torrent_id}"

def sleeve(trckr: TR, **kwargs) -> RedApi | OpsApi:
    api_map = {
        TR.RED: RedApi,
        TR.OPS: OpsApi
    }
    return api_map[trckr](**kwargs)
