from __future__ import annotations

import requests

from base64 import b64encode
from enum import Enum

try:
    from enum import member
except ImportError:
    def member(value):
        return (value,)


def ra_rehost(img_input: str | bytes, key) -> str:
    data = {'api_key': key}
    if isinstance(img_input, str):
        url = "https://thesungod.xyz/api/image/rehost_new"
        data.update(link=img_input)
        r = requests.post(url, data=data)
        return r.json()['link']
    else:
        url = "https://thesungod.xyz/api/image/upload"
        files = [('image', ('blabla', img_input, 'image/bla'))]
        r = requests.post(url, data=data, files=files)
        return r.json()['links'].pop()


def imgbb_rehost(img_input: str | bytes, key):
    url = 'https://api.imgbb.com/1/upload'
    if isinstance(img_input, bytes):
        img_input = b64encode(img_input)
    data = {'key': key,
            'image': img_input}
    r = requests.post(url, data=data)
    return r.json()['data']['url']


def pt_rehost(img_input: str | bytes, key):
    if isinstance(img_input, str):
        h = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        r = requests.get(img_input, headers=h)
        if r.status_code == 200 and r.headers['content-type'].startswith('image'):
            img_input = r.content
        else:
            raise ValueError
    url = 'https://ptscreens.com/api/1/upload'
    r = requests.post(url, headers={'X-API-Key': key}, data={'source': b64encode(img_input)})
    return r.json()['image']['url']


class IH(Enum):
    Ra = member(ra_rehost)
    ImgBB = member(imgbb_rehost)
    PTScreens = member(pt_rehost)

    def __new__(cls, func):
        obj = object.__new__(cls)
        obj._value_ = len(cls.__members__)
        return obj

    def __init__(self, func):
        self.key = ''
        self.enabled = False
        self.value: int
        self.prio: int = self.value
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

    def rehost(self, img_input: str | bytes):
        return self.func(img_input, self.key)

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
    def prioritised(cls) -> list[IH]:
        return sorted(cls, key=lambda m: m.prio)
