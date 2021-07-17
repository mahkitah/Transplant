main_window_title = "Transplant 2.2.3"
pb_placeholder = "Paste/type torrent ids and/or urls here.\n" \
                 "Space or newline separated.\n" \
                 "The source buttons only apply to ids."
tracker_1 = "RED"
tracker_2 = "OPS"
pb_add = "Add"
open_dtors = "Add .torrent files"
sel_dtors_window_title = "Select .torrent files"
pb_scan = "Scan"
tab_joblist = "Job list"
tab_results = "Results"
pb_clear = "Clear"
pb_rem_sel = "Rem sel"
pb_del_sel = "Del sel"
pb_open_tsavedir = "Save dir"
pb_open_upl_urls = "Open urls"
pb_go = "Go"
pb_stop = 'Stop'
header_restore = 'Restore all'
header0 = 'src'
header1 = 'torrent'
header2 = 'dest. group'
header3 = 'nt'

config_window_title = "Settings"
main_tab = 'Main'
desc_tab = 'Rel Descr'
looks_tab = 'Looks'
pb_cancel = "Cancel"
pb_ok = "OK"
l_key_1 = f"API-key {tracker_1}"
l_key_2 = f"API-key {tracker_2}"
l_data_dir = 'Data folder'
l_dtor_save_dir = 'Save new .torrrents'
l_del_dtors = 'Delete scanned .torrents'
l_file_check = 'Check files'
l_show_tips = "Show tooltips"
l_verbosity = 'Verbosity'
l_rehost = 'Rehost img to ptpimg'
l_whitelist = 'Image host whitelist'
l_ptpimg_key = 'PTPimg API-key'
l_placeholders = "Set a custom release description.\n\n" \
              "You can use these placeholders:\n" \
              "%src_id% :   Source id (OPS/RED)\n" \
              "%src_url% :  Source url (eg https://redacted.ch/)\n" \
              "%ori_upl% :  Name of uploader\n" \
              "%upl_id% :   id of uploader\n" \
              "%tor_id% :   Source torrent id\n" \
              "%gr_id% :    Source torrent group id\n"
pb_def_descr = 'Defaults'
chb_add_src_descr = "Add release description from source if present. (Must contain %src_descr%)"
def_rel_descr = "Transplanted from %src_id%, thanks to the original uploader."
def_src_descr = "[hide=source description:]%src_descr%[/hide]"

l_job_list = 'Job list:'
l_show_add_dtors = "Show 'Add torrent files' button"
l_splitter_weight = 'Splitter weight'
l_no_icon = 'Text instead of icon'
l_alt_row_colour = 'Alternating row colours'
l_show_grid = 'Show grid'
l_row_height = 'Row height'


default_whitelist = "ptpimg.me, thesungod.xyz"
sum_ting_wong_1 = 'Invalid data folder'
sum_ting_wong_2 = 'Invalid torrent save folder'
sum_ting_wong_3 = 'No PTPimg API-key'
sum_ting_wong_4 = 'Source description text must contain %src_descr%'

start = 'Starting'
thread_finish = '\nFinished'
dtor_saved = 'New .torrent saved to:'
dtor_deleted = '.torrent deleted from scan dir'

# Job
bad_tor = f'Not a {tracker_1} or {tracker_2} .torrent'

# Transplanter
missing = "Can't locate:"
no_log = "No logs found"
f_checked = 'Files checked'

requesting = "Requesting torrent info"
new_tor = 'Generating new torrent'
upl1 = 'Uploading to'
upl2 = 'Upload successful:'
upl3 = 'Upload failed:'
upl_to_unkn = "Upload edited to 'Unknown Release'"
edit_fail = "Failed to edit to 'Unknown Release' because of: "
img_rehosted = "Image rehosted:"
rehost_failed = "Image rehost failed. Using source url"

# tooltips
tt_l_key_1 = "Get your API-key from the site's user settings\n" \
          "Please note that these keys are stored in plain text"
tt_l_key_2 = tt_l_key_1
tt_l_data_dir = "This should be the top level folder where the album folders can be found"
tt_l_dtor_save_dir = "Newly created .torrents from the destination tracker can be saved here\n" \
                   "A torrent client's watch folder would be a logical choice to select here"
tt_ac_select_datadir = "Select data folder"
tt_ac_select_torsave = "Select save folder"
tt_l_del_dtors = "If checked, .torrents from the scan folder will be deleted after successful upload\n" \
            "This setting does not apply to .torrents that were added with the 'Add .torrent files' button\n" \
            "These will not be deleted"
tt_l_file_check = "if checked, Transplant will verify that the torrent content (~music files) can be found\n" \
                 "This will prevent transplanting torrents that you can't seed"
tt_l_show_tips = "Reverse gravity locally"
tt_l_verbosity = "Level of feedback.\n" \
               "0: silent\n" \
               "1: only errors\n" \
               "2: normal\n" \
               "3: include naptime (see rate limiting in action)\n" \
               "4: debugging\n"\
               "5: include upload data"
tt_l_rehost = 'Rehost non-whitelisted cover images to ptpimg'
tt_l_whitelist = "Images hosted on these sites will not be rehosted\n" \
               "Comma separated"
tt_pb_def_descr = 'Restore default descriptions'
tt_splitter = 'Drag all the way up to collapse top section'
tt_rb_tracker1 = "Select source tracker for torrent id's entered in the paste box\n" \
                    "This setting does not apply to url's and .torrents"
tt_rb_tracker2 = tt_rb_tracker1
tt_tb_open_config = config_window_title
tt_tb_open_config2 = tt_tb_open_config
tt_pb_add = "Add content of the paste box to the job list\n" \
                "Only valid entries will be added"
tt_pb_open_dtors = "Select .torrents to add to the job list"
tt_le_scandir = "This folder will be scanned for .torrents when the 'Scan' button is pressed\n" \
                    "You can download the .torrents from the source tracker here"
tt_ac_select_scandir = "Select scan folder"
tt_pb_scan = "Scan the 'scan folder' for .torrents and add them to the job list\n" \
                 "Subfolders will not be scanned"
tt_header3 = 'Create new .torrent file\n' \
             'Instead of modifying source torrent'
tt_pb_clear_j = "Empty the job list"
tt_pb_clear_r = "Empty the results pane"
tt_pb_rem_sel = "Remove selected jobs (torrents) from the job list"
tt_pb_del_sel = "Delete selected .torrent files from scan dir"
tt_pb_open_tsavedir = "Open torrent save location"
tt_pb_open_upl_urls = "Open all uploads in browser"
tt_tb_go = "Start Transplanting\n" \
            "Or order some food. One of the two"
