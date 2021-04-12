# Remember to double up the backslashes for windows paths

# .torrent is saved here
# Put 'None' (without quotes) if you don't want the .torrent to be saved to disc:
torrent_output = "D:\\Test\\torrents"

# torrent files can be found here:
album_folder = "D:\\Test"

# will be scanned for .torrent files in batchmode
batch_folder = "D:\\Test\\Batch"
# delete the .torrents from batch folder after successful upload. True/False
remove_after_upload = True

# level of feedback.
# 0: silent, 1: only errors, 2: normal, 3: include naptime (see rate limiting in action), 4: debugging
verbosity = 2

# check if torrent content can be found before uploading. True/False
# Be very careful when setting this to False. It will allow you to transplant torrents you can't seed.
file_check = True

api_keys = {"RED": "123456789",
            "OPS": "token 123456789"}


# must be lower case
logs_to_ignore = ["audiochecker.log", "aucdtect.log", "info.log"]

site_urls = {'RED': 'https://redacted.ch/',
             'OPS': 'https://orpheus.network/'}

tracker_urls = {"RED": "https://flacsfor.me/",
                'OPS': "https://home.opsfet.ch/"}

request_limits = {"RED": 10,
                  'OPS': 5}

releasetype_map = {
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
artist_map = {
    'artists': '1',
    'with': '2',
    'remixedBy': '3',
    'composers': '4',
    'conductor': '5',
    'dj': '6',
    'producer': '7'
}
site_id_map = {
    "redacted.ch": "RED",
    "orpheus.network": "OPS",
    "flacsfor.me": "RED",
    "home.opsfet.ch": "OPS"
}
