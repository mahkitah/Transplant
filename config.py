# Remember to double up the backslashes for windows paths

# .torrent is saved here.
# Must be an existing dir
# Put 'None' (without quotes) if you don't want the .torrent to be saved to disc:
torrent_output = "D:\\Test\\torrents"

# torrent files can be found here:
torrent_files = "D:\\Test"

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
