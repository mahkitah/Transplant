from gazelle.tracker_data import tr

# thread
start = 'Starting\n'
removed = 'No longer on job list:'
thread_finish = 'Finished\n'

# main
main_window_title = "Transplant {}"
sel_dtors_window_title = "Select .torrent files"
pb_placeholder = ("Paste/type torrent ids and/or urls here.\n"
                  "Space or newline separated.\n"
                  "The source buttons only apply to ids.")
tab_results = "Results"
tab_joblist = "Job list"

header_restore = 'Restore all'
header0 = 'torrent'
header1 = ' dest. group '
header2 = ' nt '

pb_add = "Add"
open_dtors = "Add .torrent files"
pb_scan = "Scan"
pb_clear = "Clear"
pb_rem_sel = "Rem sel"
pb_crop = "Crop"
pb_del_sel = "Del sel"
pb_del_tr1 = f"Rem {tr.RED.name}"
pb_del_tr2 = f"Rem {tr.OPS.name}"
pb_open_tsavedir = "Save dir"
pb_open_upl_urls = "Open urls"
pb_stop = 'Stop'

sum_ting_wong_1 = 'Invalid data folder'
sum_ting_wong_2 = 'Invalid scan folder'
sum_ting_wong_3 = 'Invalid torrent save folder'
sum_ting_wong_4 = 'No image hosts enabled'
sum_ting_wong_5 = 'Source description text must contain %src_descr%'
sum_ting_wong_6 = 'Leading and/or trailing space in {}'

# Pop-ups
pop1 = 'Nothing to add in'
pop2 = 'Nothing new found in'
pop3 = 'Nothing useful in pastebox'
pop4 = ('{} torrent{} not deleted.\n'
        'Only scanned torrents can be deleted')

# settings
settings_window_title = "Settings"
pb_cancel = "Cancel"
pb_ok = "OK"
main_tab = 'Main'
rehost_tab = 'Rehost'
desc_tab = 'Rel Descr'
looks_tab = 'Looks'

chb_deep_search = 'Deep search to level:'

default_whitelist = "ptpimg.me, thesungod.xyz"
l_rehost_table = ('Enable image hosts with the checkbox.\n'
                  'Change priority by dragging rows up or down. (drag row header)\n'
                  'Enabled host will be tried from the top down.\n'
                  'If the first one fails the next will be tried and so forth.')
rehost_columns = ('Host', 'API key')

l_placeholders = ("Set a custom release description.\n\n"
                  "You can use these placeholders:\n"
                  "%src_id% :   Source id (OPS/RED)\n"
                  "%src_url% :  Source url (eg https://redacted.ch/)\n"
                  "%ori_upl% :  Name of uploader\n"
                  "%upl_id% :   id of uploader\n"
                  "%tor_id% :   Source torrent id\n"
                  "%gr_id% :    Source torrent group id\n")

pb_def_descr = 'Restore Defaults'
l_own_uploads = "Description for own uploads."

def_rel_descr = ("Transplanted from [url=%src_url%torrents.php?torrentid=%tor_id%]%src_id%[/url],\n"
                 "thanks to the original uploader.")
def_rel_descr_own = "Transplant of my own upload on [url=%src_url%torrents.php?torrentid=%tor_id%]%src_id%[/url]."
chb_add_src_descr = "Add release description from source if present. (Must contain %src_descr%)"
def_src_descr = "[quote=source description:]%src_descr%[/quote]"

l_job_list = 'Job list:'
l_colors = ('Set colours for text in the results pane.<br>'
            'Use colour names, hex values: #xxxxxx, or rgb values: rgb(xx,xx,xx)<br>'
            'See <a href="https://en.wikipedia.org/wiki/Web_colors">wikipedia.org/wiki/Web_colors</a>,<br>'
            'or one of the thousand online html colour pickers<br>'
            'Leave empty for default text colour.')

# user input element labels
l_key_1 = f"API-key {tr.RED.name}"
l_key_2 = f"API-key {tr.OPS.name}"
l_data_dir = 'Data folder'
l_scan_dir = 'Scan folder'
l_save_dtors = 'Save new .torrrents'
l_del_dtors = 'Delete scanned .torrents'
l_file_check = 'Check files'
l_post_compare = 'Post upload checks'
l_show_tips = "Show tooltips"
l_verbosity = 'Verbosity'
l_rehost = 'Rehost cover art'
l_whitelist = 'Image host whitelist'
l_style_selector = 'GUI Style'
l_show_add_dtors = "Show 'Add torrent files' button"
l_show_rem_tr1 = f"Show '{pb_del_tr1}' button"
l_show_rem_tr2 = f"Show '{pb_del_tr2}' button"
l_no_icon = 'Text instead of icon'
l_show_tor_folder = 'Torrent folder instead of file name'
l_alt_row_colour = 'Alternating row colours'
l_show_grid = 'Show grid'
l_row_height = 'Row height'
l_warning_color = 'Warning'
l_error_color = 'Error'
l_success_color = 'Sucess'
l_link_color = 'link'

# tooltips
tt_l_key_1 = ("Get your API-key from the site's user settings\n"
              "Please note that these keys are stored in plain text")
tt_l_key_2 = tt_l_key_1
tt_l_data_dir = "This should be the top level folder where the album folders can be found"
tt_chb_deep_search = ("When checked, the data folder will be searched for torrent folders up til 'level' deep,\n"
                      "level 1 is direct subfolder of data dir. Subfolder of that is level 2 etc.")
tt_l_scan_dir = ("This folder will be scanned for .torrents when the 'Scan' button is pressed\n"
                 "You can download the .torrents from the source tracker here")
tt_l_save_dtors = ("Newly created .torrents from the destination tracker can be saved here\n"
                   "A torrent client's watch folder would be a logical choice to select here")
tt_fsb_data_dir = "Select data folder"
tt_fsb_scan_dir = "Select scan folder"
tt_fsb_dtor_save_dir = "Select save folder"
tt_l_del_dtors = ("If checked, .torrents from the scan folder will be deleted after successful upload\n"
                  "This setting does not apply to .torrents that were added with the 'Add .torrent files' button\n"
                  "These will not be deleted")
tt_l_file_check = ("if checked, Transplant will verify that the torrent content (~music files) can be found\n"
                   "This will prevent transplanting torrents that you can't seed")
tt_l_post_compare = "Check if the upload was merged into an existing group or if the log scores are different"
tt_l_show_tips = "Tip the tools"
tt_l_verbosity = ("Level of feedback.\n"
                  "0: silent\n"
                  "1: only errors\n"
                  "2: normal\n"
                  "3: debugging")
tt_l_rehost = 'Rehost non-whitelisted cover images'
tt_l_whitelist = ("Images hosted on these sites will not be rehosted\n"
                  "Comma separated")
tt_pb_def_descr = 'Restore default descriptions'
tt_rb_tracker1 = ("Select source tracker for torrent id's entered in the paste box\n"
                  "This setting does not apply to url's and .torrents")
tt_rb_tracker2 = tt_rb_tracker1
tt_tb_open_config = settings_window_title
tt_tb_open_config2 = tt_tb_open_config
tt_pb_add = ("Add content of the paste box to the job list\n"
             "Only valid entries will be added")
tt_pb_open_dtors = "Select .torrents to add to the job list"
tt_pb_scan = ("Scan the 'scan folder' for .torrents and add them to the job list\n"
              "Subfolders will not be scanned (ctrl-S)")
tt_pb_clear_j = "Empty the job list (ctrl-W)"
tt_pb_clear_r = "Empty the results pane (ctrl-W)"
tt_pb_rem_sel = "Remove selected jobs (torrents) from the job list (Backspace)"
tt_pb_crop = "Keep selection (ctrl-R)"
tt_pb_del_sel = "Delete selected .torrent files from scan dir"
tt_pb_rem_tr1 = f"Remove all {tr.RED.name} jobs from job list (ctrl-1)"
tt_pb_rem_tr2 = f"Remove all {tr.OPS.name} jobs from job list (ctrl-2)"
tt_pb_open_tsavedir = "Open torrent save location"
tt_pb_open_upl_urls = "Open all uploads in browser (ctrl-O)"
tt_tb_go = "Start Transplanting\n (ctrl-shift-Enter)"
ttm_header1 = "Upload to a specific group"
ttm_header2 = ('Create new .torrent file\n'
               'Instead of modifying source torrent')
ttm_splitter = 'Drag all the way up to hide top section'
