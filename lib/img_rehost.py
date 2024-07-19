from enum import Enum, member
import requests


def ra_rehost(img_link, key):
    url = "https://thesungod.xyz/api/image/rehost_new"
    data = {'api_key': key,
            'link': img_link}
    r = requests.post(url, data=data)
    return r.json()['link']


def ptpimg_rehost(img_link, key):
    url = "https://ptpimg.me/"
    data = {'api_key': key,
            'link-upload': img_link}
    r = requests.post(url + 'upload.php', data=data)
    rj = r.json()[0]
    return f"{url}{rj['code']}.{rj['ext']}"


def imgbb_rehost(img_link, key):
    url = 'https://api.imgbb.com/1/upload'
    data = {'key': key,
            'image': img_link}
    r = requests.post(url, data=data)
    return r.json()['data']['url']


class IH(Enum):
    Ra = member(ra_rehost)
    PTPimg = member(ptpimg_rehost)
    ImgBB = member(imgbb_rehost)

    def __new__(cls, func):
        obj = object.__new__(cls)
        obj._value_ = len(cls.__members__)
        return obj

    def __init__(self, func):
        self.key = ''
        self.enabled = False
        self.prio = self.value
        self.func = func

    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, key: str):
        self._key = key.strip()

    def extra_attrs(self):
        return self.enabled, self.key, self.prio

    def set_extras(self, enabled, key, prio):
        self.enabled = enabled
        self.key = key
        self.prio = prio

    @classmethod
    def set_attrs(cls, attr_dict: dict):
        for name, attrs in attr_dict.items():
            mem = cls[name]
            if mem:
                mem.set_extras(*attrs)

    @classmethod
    def get_attrs(cls) -> dict:
        attr_dict = {}
        for mem in cls:
            attr_dict[mem.name] = mem.extra_attrs()
        return attr_dict

    @classmethod
    def prioritised(cls) -> list:
        return sorted(cls, key=lambda m: m.prio)
