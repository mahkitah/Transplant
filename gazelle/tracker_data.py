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
    def __new__(cls, *args, **kwargs):
        classdict = args[2]
        cls.value_tr_map = {t: {} for t in tr}
        for k, v in classdict.items():
            if k not in classdict._member_names:
                continue
            if isinstance(v, int):
                v = (v, v)

            for t, val in zip(tr, v):
                if val is not None:
                    cls.value_tr_map[t].update({val: k})

        return super().__new__(cls, *args, **kwargs)

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

    def tracker_value(self, t: tr):
        return getattr(self, t.name)

    @classmethod
    def mem_from_tr_value(cls, val: int, t: tr):
        mem_name = cls.value_tr_map[t][val]
        return cls._member_map_[mem_name]


class ArtistType(Enum):
    Main = 1, 'artists'
    Guest = 2, 'with'
    Remixer = 3, 'remixedBy'
    Composer = 4, 'composers'
    Conductor = 5, 'conductor'
    DJ_Comp = 6, 'dj'
    Producer = 7, 'producer'
    Arranger = 8, 'arranger'

    def __new__(cls, int_val, str_val):
        obj = object.__new__(cls)
        obj._value_ = str_val
        obj.nr = int_val
        return obj


class EncMeta(EnumMeta):
    alt_names_map = {}

    def __getitem__(cls, item):
        if item in cls.alt_names_map:
            return cls.alt_names_map[item]
        return cls._member_map_['Other']


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
        cls.alt_names_map[arg] = obj
        return obj

    @property
    def name(self):
        return self.alt_name


BAD_RED_ENCODINGS = Encoding.C128 | Encoding.C160
