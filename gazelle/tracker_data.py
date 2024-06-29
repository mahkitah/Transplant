from enum import Enum, Flag, EnumMeta

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
    def __new__(cls, value: dict):
        obj = object.__new__(cls)
        obj._value_ = 2 ** len(cls.__members__)
        for k, v in value.items():
            setattr(obj, k, v)
        return obj


tr = Tr('Tr', tr_data.items())


class RelTypeMeta(EnumMeta):
    def __getitem__(cls, item):
        try:
            item = item.replace(' ', '_')
        except AttributeError:
            pass
        return cls._member_map_[item]


class ReleaseType(Enum, metaclass=RelTypeMeta):
    Album = 1
    Soundtrack = 3
    EP = 5
    Anthology = 6
    Compilation = 7
    Sampler = None, 8
    Single = 9
    Demo = 17, 10
    Live_album = 11
    Split = None, 12
    Remix = 13
    Bootleg = 14
    Interview = 15
    Mixtape = 16
    DJ_Mix = 19, 17
    Concert_recording = 18
    Unknown = 21

    def __new__(cls, *args):
        obj = object.__new__(cls)
        obj._value_ = len(cls.__members__) + 1
        return obj

    def __init__(self, *values):
        if len(values) != len(tr):
            values *= len(tr)
        for t, val in zip(tr, values):
            setattr(self, t.name, val)

    @property
    def name(self):
        return super().name.replace('_', ' ')

    def tracker_value(self, t):
        return getattr(self, t.name)


class ArtistType(Enum):
    Main = 1
    Guest = 2
    Remixer = 3
    Composer = 4
    Conductor = 5
    DJ_Comp = 6
    Producer = 7
    Arranger = 8


class EncMeta(EnumMeta):
    def __new__(cls, *args, **kwargs):
        classdict = args[2]
        cls.alt_names = {v: k for k, v in classdict.items() if k in classdict._member_names}
        return super().__new__(cls, *args, **kwargs)


class Encoding(Flag, metaclass=EncMeta):
    Lossless = 'Lossless'
    Lossless_24 = '24bit Lossless'
    C320 = '320'
    C256 = '256'
    C192 = '192'
    C160 = '160'
    C128 = '128'
    V0 = 'V0 (VBR)'
    V1 = 'V1 (VBR)'
    V2 = 'V2 (VBR)'
    APS = 'APS (VBR)'
    APX = 'APX (VBR)'
    Other = 'Other'

    def __new__(cls, arg):
        obj = object.__new__(cls)
        obj._value_ = 2 ** len(cls.__members__)
        obj.alt_name = arg
        return obj

    @property
    def name(self):
        return self.alt_name

    @classmethod
    def mem_from_enc_str(cls, enc_str: str):
        mem_name: str = cls.alt_names.get(enc_str)
        if mem_name is None:
            mem = cls._member_map_['Other']
            bitr, vbr, _ = enc_str.partition(' (VBR)')
            mem.bitr = int(bitr)
            mem.vbr = bool(vbr)
        else:
            mem = cls._member_map_[mem_name]
        return mem

BAD_RED_ENCODINGS = Encoding.C128 | Encoding.C160
