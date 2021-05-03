# transplant
ARTIST_MAP = {
    'artists': '1',
    'with': '2',
    'remixedBy': '3',
    'composers': '4',
    'conductor': '5',
    'dj': '6',
    'producer': '7'
}
RELEASE_TYPE_MAP = {
    "RED": {
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
    "OPS": {
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
SITE_ID_MAP = {
    "redacted.ch": "RED",
    "orpheus.network": "OPS",
    "flacsfor.me": "RED",
    "home.opsfet.ch": "OPS"
}
LOGS_TO_IGNORE = ["audiochecker.log", "aucdtect.log", "info.log"]

# gazelle_api
SITE_URLS = {
    'RED': 'https://redacted.ch/',
    'OPS': 'https://orpheus.network/'
}
TRACKER_URLS = {
    "RED": "https://flacsfor.me/",
    'OPS': "https://home.opsfet.ch/"
}
REQUEST_LIMITS = {
    "RED": 10,
    'OPS': 5
}
