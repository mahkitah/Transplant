# Remember to double up the backslashes for windows paths

# Music files can be found here:
data_dir = "D:\\Test"

# .torrent is saved here
# Put 'None' (without quotes) if you don't want the .torrent to be saved to disc:
torrent_save_dir = "D:\\Test\\Torrents"

# will be scanned for .torrent files in batchmode
scan_dir = "D:\\Test\\Torrents\\tBatch"

# delete the .torrents from batch folder after successful upload. True/False
del_dtors = False

# check if torrent content can be found before uploading. True/False
# Be very careful when setting this to False. It will allow you to transplant torrents you can't seed.
file_check = True

# level of feedback.
# 0: silent, 1: only errors, 2: normal, 3: include naptime, 4: debugging, 5: include upload data
verbosity = 2

# rehost non-whitelisted images to ptpimg
img_rehost = False
whitelist = ["ptpimg.me", "thesungod.xyz"]
ptpimg_key = '123456'

# "Set a custom release description.

# You can use these variables:\n"
# %src_id% :   Source id (OPS/RED)
# "%src_url% :  Source url (eg https://redacted.ch/)
# "%ori_upl% :  Name of uploader
# "%upl_id% :   id of uploader
# "%tor_id% :   Source torrent id
# "%gr_id% :    Source torrent group id

rel_descr = "Transplanted from %src_id%, thanks to the original uploader."

# Add release description from source if present
add_src_descr = True

# Must contain %src_descr%
src_descr = '[hide=source description:]%src_descr%[/hide]'
