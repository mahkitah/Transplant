from enum import Flag

tr_data = {
    'RED': {
        'site': 'https://redacted.ch/',
        'tracker': 'https://flacsfor.me/{passkey}/announce',
        'favicon': 'pth.ico',
        'api': True,
        'key': True,
        'source_flag': True,
        'req_limit': 10
    },
    'OPS': {
        'site': 'https://orpheus.network/',
        'tracker': 'https://home.opsfet.ch/{passkey}/announce',
        'favicon': 'ops.ico',
        'api': True,
        'key': True,
        'source_flag': True,
        'req_limit': 5,
    },
}

class Tr(Flag):
    def __new__(cls, *args):
        obj = object.__new__(cls)
        obj._value_ = 2 ** len(cls.__members__)
        return obj

    def __init__(self, attr: dict):
        for k, v in attr.items():
            setattr(self, k, v)

tr = Tr('Tr', tr_data.items())

RELEASE_TYPE_MAP = {
    tr.RED: {
        "Album": 1,
        "Soundtrack": 3,
        "EP": 5,
        "Anthology": 6,
        "Compilation": 7,
        "Single": 9,
        "Live album": 11,
        "Remix": 13,
        "Bootleg": 14,
        "Interview": 15,
        "Mixtape": 16,
        "Demo": 17,
        "Concert Recording": 18,
        "DJ Mix": 19,
        "Unknown": 21
    },
    tr.OPS: {
        "Album": 1,
        "Soundtrack": 3,
        "EP": 5,
        "Anthology": 6,
        "Compilation": 7,
        "Sampler": 8,
        "Single": 9,
        "Demo": 10,
        "Live album": 11,
        "Split": 12,
        "Remix": 13,
        "Bootleg": 14,
        "Interview": 15,
        "Mixtape": 16,
        "DJ Mix": 17,
        "Concert Recording": 18,
        "Unknown": 21
    }
}
ARTIST_MAP = {
    'artists': 1,
    'with': 2,
    'remixedBy': 3,
    'composers': 4,
    'conductor': 5,
    'dj': 6,
    'producer': 7
}
