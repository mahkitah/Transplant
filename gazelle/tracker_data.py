from enum import Enum, Flag, EnumMeta


class TR(Flag):
    RED = {
        'site': 'https://redacted.sh/',
        'tracker': 'https://flacsfor.me/{passkey}/announce',
        'favicon': 'pth.ico',
        'req_limit': 10
    }
    OPS = {
        'site': 'https://orpheus.network/',
        'tracker': 'https://home.opsfet.ch/{passkey}/announce',
        'favicon': 'ops.ico',
        'req_limit': 5,
    }

    def __new__(cls, value: dict):
        obj = object.__new__(cls)
        obj._value_ = 2 ** len(cls.__members__)
        for k, v in value.items():
            setattr(obj, k, v)
        return obj


class RelTypeMeta(EnumMeta):
    tr_val_mem_map = {t: {} for t in TR}

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
        if len(args) != len(TR):
            args *= len(TR)
        obj._tracker_values = {}
        for t, val in zip(TR, args):
            obj._tracker_values[t] = val
            cls.tr_val_mem_map[t][val] = obj
        return obj

    @property
    def name(self):
        return self._name_.replace('_', ' ')

    def tracker_value(self, t: TR):
        return self._tracker_values[t]

    @classmethod
    def mem_from_tr_value(cls, val: int, t: TR):
        return cls.tr_val_mem_map[t][val]


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
        return cls.alt_names_map.get(item) or cls._member_map_['Other']


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
