import time
import requests

from collections import deque
try:
    from simplejson import JSONDecodeError
except ImportError:
    from json.decoder import JSONDecodeError

from lib import constants


class RequestFailure(Exception):
    pass


# noinspection PyTypeChecker
class GazelleApi:
    def __init__(self, site_id, key, report=lambda *x: None):
        assert site_id in constants.SITE_URLS, f"{site_id} is not a valid id"
        self.id = site_id
        self.session = requests.Session()
        self.session.headers.update({"Authorization": key})
        self.last_x_reqs = deque([0], maxlen=constants.REQUEST_LIMITS[site_id])
        self.url = constants.SITE_URLS[site_id]
        self._announce = None
        self.report = report

    @property
    def announce(self):
        if self._announce:
            return self._announce
        else:
            accountinfo = self.request("GET", "index")
            passkey = accountinfo["passkey"]
            url = constants.TRACKER_URLS[self.id] + passkey + '/announce'
            self._announce = url
            return url

    def _rate_limit(self):
        t = time.time() - self.last_x_reqs[0]
        if t <= 10:
            self.report(f"sleeping {10-t}", 3)
            time.sleep(10 - t)

    def request(self, req_method, action, data=None, files=None, **kwargs):
        assert req_method in ['GET', 'POST'], f"Invalid request method: {req_method}"

        self.report(f"{self.id} {action}, {kwargs}", 4)
        self.report(f"{data}", 5)

        ajaxpage = self.url + 'ajax.php'
        params = {'action': action}
        params.update(kwargs)

        self._rate_limit()
        r = self.session.request(req_method, ajaxpage, params=params, data=data, files=files)
        self.last_x_reqs.append(time.time())
        r.raise_for_status()

        try:
            r_dict = r.json()
            self.report(f"{r_dict}", 4)
            if r_dict["status"] == "success":
                return r_dict["response"]
            elif r_dict["status"] == "failure":
                raise RequestFailure(r_dict["error"])
        except JSONDecodeError:
            return r.content
