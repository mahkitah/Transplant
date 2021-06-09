main_window_title = "Transplant 2.0"
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
pb_rem_dupl = "Rem dupl"
pb_open_tsavedir = "Save dir"
pb_go = "Go"

s_window_title = "Settings"
pb_cancel = "Cancel"
pb_ok = "OK"
l_key_1 = f"API-key {tracker_1}"
l_key_2 = f"API-key {tracker_2}"
l_data_dir = 'Data folder'
l_tor_save_dir = 'Save new .torrrents'
l_del_dtors = 'Delete scanned .torrents'
l_file_check = 'Check files'
l_show_tips = "Show tooltips"
l_verbosity = 'Verbosity'
invalid_path_warning = 'Invalid path'
plural = 's'
more_warning = 'Please set existing paths'

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
rel_descr = "Transplanted from {}, thanks to the original uploader."

upl1 = 'Uploading to'
upl2 = 'Upload successful:'
upl3 = 'Upload failed:'
upl_to_unkn = "Upload edited to 'Unknown Release'"
edit_fail = "Failed to edit to 'Unknown Release"

# tooltips
tt_keys = "Get your API-key from the site's user settings\n" \
          "Please note that these keys are stored in plain text"
tt_data_dir = "This should be the top level folder where the album folders can be found."
tt_dtor_save_dir = "Newly created .torrents from the destination tracker can be saved here.\n" \
                   "A torrent client's watch folder would be a logical choice to select here."
tt_sel_ddir = "Select data folder"
tt_sel_dtor_save_dir = "Select save folder"
tt_del_dtors = "If checked, .torrents from the scan folder will be deleted after successful upload.\n" \
            "This setting does not apply to .torrents that were added with the 'Add .torrent files' button.\n" \
            "These will not be deleted."
tt_check_files = "if checked, Transplant will verify that the torrent content (~music files) can be found.\n" \
                 "This will prevent transplanting torrents that you can't seed."
tt_show_tips = "Locally reverse gravity."
tt_verbosity = "Level of feedback.\n" \
               "0: silent\n" \
               "1: only errors\n" \
               "2: normal\n" \
               "3: include naptime (see rate limiting in action)\n" \
               "4: debugging\n"\
               "5: include upload data"
tt_source_buts = "Select source tracker for torrent id's entered in the paste box.\n" \
                    "This setting does not apply to url's and .torrents"
tt_add_but = "Add content of the paste box to the job list.\n" \
                "Only valid entries will be added"
tt_add_dtors_but = "Select .torrents to add to the job list"
tt_scandir = "This folder will be scanned for .torrents when the 'Scan' button is pressed.\n" \
                    "You can download the .torrents from the source tracker here."
tt_select_scandir = "Select scan folder"
tt_scan_but = "Scan the 'scan folder' for .torrents and add them to the job list.\n" \
                 "Subfolders will not be scanned."
tt_clear_but = "Empty the job list or results pane."
tt_rem_sel_but = "Remove selected jobs (torrents) from the job list."
tt_rem_dupl_but = "Remove duplicate jobs (torrents) from the job list."
tt_open_tsavedir = "Open torrent save location"
tt_go_but = "Start Transplanting.\n" \
            "Or order some food. One of the two"
