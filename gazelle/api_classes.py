import time
import re
import logging
from collections import deque
from http.cookiejar import LWPCookieJar, LoadError

import requests

try:
    from simplejson import JSONDecodeError
except ImportError:
    from json.decoder import JSONDecodeError

from lib import ui_text
from gazelle import torrent_info
from gazelle.tracker_data import tr, tr_data


class RequestFailure(Exception):
    pass

report = logging.getLogger(__name__)

# noinspection PyTypeChecker
class BaseApi:
    def __init__(self, tracker, **kwargs):
        assert tracker in tr, 'Unknown Tracker'  # TODO uitext
        self.tr = tracker
        self.url = tr_data[self.tr]['site']
        self.session = requests.Session()
        self.last_x_reqs = deque([0], maxlen=tr_data[self.tr]['req_limit'])
        self.authenticate(kwargs)
        self._account_info = None

    def _rate_limit(self):
        t = time.time() - self.last_x_reqs[0]
        if t <= 10:
            time.sleep(10 - t)

    def authenticate(self, _):
        return NotImplementedError

    @property
    def announce(self):
        announce = tr_data[self.tr]['tracker'].format(**self.account_info)
        if self.account_info['username'] == 'bumblyboo':
            announce = announce.replace('https://', 'http://')
        return announce

    @ property
    def account_info(self):
        if not self._account_info:
            self._account_info = self.get_account_info()

        return self._account_info

    def get_account_info(self):
        r = self.request('GET', 'index')
        return {k: v for k, v in r.copy().items() if k in ('authkey', 'passkey', 'id', 'username')}

    def request(self, req_method, url_suffix, data=None, files=None, **kwargs):
        assert req_method in ('GET', 'POST')
        url = self.url + url_suffix + '.php'
        report.debug(f'{url_suffix} {kwargs}')

        self._rate_limit()
        r = self.session.request(req_method, url, params=kwargs, data=data, files=files)
        self.last_x_reqs.append(time.time())
        r.raise_for_status()

        try:
            r_dict = r.json()
            logging.debug(r_dict)
            if r_dict["status"] == "success":
                return r_dict["response"]
            elif r_dict["status"] == "failure":
                raise RequestFailure(r_dict["error"])
        except JSONDecodeError:
            return r

    def torrent_info(self, **kwargs):
        r = self.request('GET', 'torrent', **kwargs)

        return torrent_info.tr_map[self.tr](self.tr, r, req_m=self.request)

    def upload(self, data, files, dest_group=None):
        data_dict = data.upl_dict(self.tr, dest_group)
        upl_files = files.files_list(self.announce, self.tr.name)
        return self._uploader(data_dict, upl_files, dest_group)

    def _uploader(self, data, files, dest_group):
        raise NotImplementedError

class KeyApi(BaseApi):

    def authenticate(self, kwargs):
        key = kwargs['key']
        self.session.headers.update({"Authorization": key})

    def request(self, req_method, action, data=None, files=None, **kwargs):
        kwargs.update(action=action)
        return super().request(req_method, 'ajax', data=data, files=files, **kwargs)

    def _uploader(self, data, files, dest_group):
        if dest_group:
            data['groupid'] = dest_group

        r = self.request('POST', 'upload', data=data, files=files)

        return self.upl_response_handler(r)

    def upl_response_handler(self, r):
        # RED = lowercase keys. OPS = camelCase keys
        group_id = r.get('groupId', r.get('groupid'))
        torrent_id = r.get('torrentId', r.get('torrentid'))

        return self.url + f"torrents.php?id={group_id}&torrentid={torrent_id}"

class CookieApi(BaseApi):

    def authenticate(self, kwargs):
        self.session.cookies = LWPCookieJar(f'cookie{self.tr.name}.txt')
        if not self._load_cookie():
            self._login(kwargs)

    def _load_cookie(self):
        jar = self.session.cookies
        try:
            jar.load()
            session_cookie = [c for c in jar if c.name == "session"][0]
            assert not session_cookie.is_expired()
        except(FileNotFoundError, LoadError, IndexError, AssertionError):
            return False

        return True

    def _login(self, kwargs):
        username, password = kwargs['f']()
        data = {'username': username,
                'password': password,
                'keeplogged': '1'}
        self.session.cookies.clear()
        r = self.request('POST', 'login', data=data)
        assert [c for c in self.session.cookies if c.name == 'session']
        self.session.cookies.save()

    def request(self, req_method, action, data=None, files=None, **kwargs):
        if action in ('upload', 'login'):  # TODO download?
            url_addon = action
        else:
            url_addon = 'ajax'
            kwargs.update(action=action)

        return super().request(req_method, url_addon, data=data, files=files, **kwargs)

    def _uploader(self, data, files, dest_group=None):
        data['submit'] = True
        r = self.request('POST', 'upload', data=data, files=files, groupid=dest_group)

        if 'torrents.php' not in r.url:  # TODO better warning regex. Soup?
            with open('ooops.html', 'wb') as f:
                f.write(r.content)
            import webbrowser
            webbrowser.open('ooops.html')
            warning = re.search(r'<p style="color: red;text-align:center;">(.+?)</p>', r.text)
            raise RequestFailure(f"{warning.group(1) if warning else r.url}")
        return r.url

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

    def _uploader(self, data, files, dest_group):
        unknown = False
        if data.get('unknown'):
            del data['unknown']
            unknown = True
        group_id, torrent_id = super()._uploader(data, files, dest_group)
        if unknown:
            try:
                self.request("POST", "torrentedit", id=torrent_id, data={'unknown': True})
                report.info(ui_text.upl_to_unkn)
            except (RequestFailure, requests.HTTPError) as e:
                report.error(f'{ui_text.edit_fail}{str(e)}')
        return self.url + f"torrents.php?id={group_id}&torrentid={torrent_id}"

    def upl_response_handler(self, r):
        return r.get('groupid'), r.get('torrentid')
