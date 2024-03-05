from enum import Enum, EnumMeta
from itertools import islice
import requests


def ra(img_link, key):
    url = "https://thesungod.xyz/api/image/rehost_new"
    data = {'api_key': key,
            'link': img_link}
    r = requests.post(url, data=data)
    return r.json()['link']


def ptpimg(img_link, key):
    url = "https://ptpimg.me/"
    data = {'api_key': key,
            'link-upload': img_link}
    r = requests.post(url + 'upload.php', data=data)
    rj = r.json()[0]
    return f"{url}{rj['code']}.{rj['ext']}"


def imgbb(img_link, key):
    url = 'https://api.imgbb.com/1/upload'
    data = {'key': key,
            'image': img_link}
    r = requests.post(url, data=data)
    return r.json()['data']['url']


class IHMeta(EnumMeta):
    extra = ('enabled', 'key', 'prio')

    # make it sliceable
    def __getitem__(cls, index):
        if isinstance(index, slice):
            return [cls._member_map_[i] for i in islice(cls._member_map_, index.start, index.stop, index.step)]
        if isinstance(index, int):
            return cls._member_map_[next(islice(cls._member_map_, index, index + 1))]
        return cls._member_map_[index]

    def set_attrs(cls, attr_dict: dict):
        for name, attrs in attr_dict.items():
            member = cls._member_map_.get(name)
            if member:
                for k, v in zip(cls.extra, attrs):
                    setattr(member, k, v)

    def get_attrs(cls) -> dict:
        attr_dict = {}
        for m in cls:
            attrs = tuple(getattr(m, name) for name in cls.extra)
            attr_dict[m.name] = attrs
        return attr_dict

    def prioritised(cls) -> list:
        return sorted(cls, key=lambda m: m.prio)


class ih(Enum, metaclass=IHMeta):
    Ra = 0
    PTPimg = 1
    ImgBB = 2

    def __init__(self, value):
        self.key = ''
        self.enabled = False
        self.prio = value
        self.func = globals()[self.name.lower()]

    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, key: str):
        self._key = key.strip()


def rehost(img_link: str) -> str:
    for host in ih.prioritised():
        if host.enabled:
            args = [img_link]
            if host.key:
                args.append(host.key)
            try:
                return host.func(*args)
            except Exception:
                continue
