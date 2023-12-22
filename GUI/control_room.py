import os
import re
import logging
from urllib.parse import urlparse, parse_qs

from lib import utils, ui_text
from lib.img_rehost import ih
from lib.transplant import Job, Transplanter
from gazelle.tracker_data import tr
from GUI.widget_bank import wb
from GUI.main_gui import MainWindow
from GUI.settings_window import SettingsWindow

from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.QtGui import QKeyEvent, QDesktopServices
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QThread, QSize, QUrl


class LogForward(QObject, logging.Handler):
    log_forward = pyqtSignal(logging.LogRecord)

    def emit(self, record):
        self.log_forward.emit(record)

logger = logging.getLogger('tr')
logger.setLevel(logging.INFO)
handler = LogForward()
logger.addHandler(handler)


class TransplantThread(QThread):
    def __init__(self):
        super().__init__()
        self.trpl_settings = None
        self.stop_run = False

    def stop(self):
        self.stop_run = True

    def run(self):
        logger.info(ui_text.start)
        key_dict = {
            tr.RED: wb.config.value('le_key_1'),
            tr.OPS: wb.config.value('le_key_2')
        }
        transplanter = Transplanter(key_dict, **self.trpl_settings)

        for job in wb.job_data.jobs.copy():
            if self.stop_run:
                break
            try:
                if job not in wb.job_data.jobs:  # It's possible to remove jobs from joblist during transplanting
                    logger.warning(f'{ui_text.removed} {job.display_name}')
                    continue
                try:
                    success = transplanter.do_your_job(job)
                except Exception:
                    logger.exception('')
                    continue
                if success:
                    wb.job_data.remove_this_job(job)

            finally:
                logger.info('')


def start_up():
    wb.main_window = MainWindow()
    wb.main_window.keyPressEvent = key_press
    wb.settings_window = SettingsWindow(wb.main_window)
    main_connections()
    config_connections()
    load_config()
    wb.emit_state()
    wb.pb_scan.setFocus()
    wb.main_window.show()


def main_connections():
    handler.log_forward.connect(print_logs)
    wb.te_paste_box.plain_text_changed.connect(lambda x: wb.pb_add.setEnabled(bool(x)))
    wb.bg_source.idClicked.connect(lambda x: wb.config.setValue('bg_source', x))
    wb.pb_add.clicked.connect(parse_paste_input)
    wb.pb_open_dtors.clicked.connect(select_dtors)
    wb.pb_scan.clicked.connect(scan_dtorrents)
    wb.pb_clear_j.clicked.connect(wb.job_data.clear)
    wb.pb_clear_r.clicked.connect(wb.result_view.clear)
    wb.pb_rem_sel.clicked.connect(remove_selected)
    wb.pb_crop.clicked.connect(crop)
    wb.pb_del_sel.clicked.connect(delete_selected)
    wb.pb_rem_tr1.clicked.connect(lambda: wb.job_data.filter_for_attr('src_tr', tr.RED))
    wb.pb_rem_tr2.clicked.connect(lambda: wb.job_data.filter_for_attr('src_tr', tr.OPS))
    wb.pb_open_tsavedir.clicked.connect(
        lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(wb.fsb_dtor_save_dir.currentText())))
    wb.tb_go.clicked.connect(gogogo)
    wb.pb_open_upl_urls.clicked.connect(open_tor_urls)
    wb.job_view.horizontalHeader().sectionDoubleClicked.connect(wb.job_data.header_double_clicked)
    wb.selection.selectionChanged.connect(lambda: wb.pb_rem_sel.setEnabled(wb.selection.hasSelection()))
    wb.selection.selectionChanged.connect(
        lambda: wb.pb_crop.setEnabled(0 < len(wb.selection.selectedRows()) < len(wb.job_data.jobs)))
    wb.selection.selectionChanged.connect(lambda x: wb.pb_del_sel.setEnabled(wb.selection.hasSelection()))
    wb.job_view.doubleClicked.connect(open_torrent_page)
    wb.job_view.key_override_sig.connect(key_press)
    wb.job_data.layout_changed.connect(lambda: wb.tb_go.setEnabled(bool(wb.job_data)))
    wb.job_data.layout_changed.connect(lambda: wb.pb_clear_j.setEnabled(bool(wb.job_data)))
    wb.job_data.layout_changed.connect(
        lambda: wb.pb_rem_tr1.setEnabled(any(j.src_tr == tr.RED for j in wb.job_data)))
    wb.job_data.layout_changed.connect(
        lambda: wb.pb_rem_tr2.setEnabled(any(j.src_tr == tr.OPS for j in wb.job_data)))
    wb.result_view.textChanged.connect(
        lambda: wb.pb_clear_r.setEnabled(bool(wb.result_view.toPlainText())))
    wb.result_view.textChanged.connect(
        lambda: wb.pb_open_upl_urls.setEnabled('torrentid' in wb.result_view.toPlainText()))
    wb.tb_open_config.clicked.connect(wb.settings_window.open)
    wb.tb_open_config2.clicked.connect(wb.tb_open_config.click)
    wb.splitter.splitterMoved.connect(lambda x, y: wb.tb_open_config2.setHidden(bool(x)))
    wb.tabs.currentChanged.connect(wb.view_stack.setCurrentIndex)
    wb.view_stack.currentChanged.connect(wb.tabs.setCurrentIndex)
    wb.view_stack.currentChanged.connect(wb.button_stack.setCurrentIndex)


def config_connections():
    wb.pb_ok.clicked.connect(settings_check)
    wb.pb_cancel.clicked.connect(wb.settings_window.reject)
    wb.settings_window.accepted.connect(settings_accepted)
    wb.fsb_scan_dir.list_changed.connect(
        lambda: wb.pb_scan.setEnabled(bool(wb.fsb_scan_dir.currentText())))
    wb.fsb_dtor_save_dir.list_changed.connect(
        lambda: wb.pb_open_tsavedir.setEnabled(bool(wb.fsb_dtor_save_dir.currentText())))
    wb.chb_deep_search.stateChanged.connect(lambda x: wb.spb_deep_search_level.setEnabled(bool(x)))
    wb.chb_show_tips.stateChanged.connect(tooltips)
    wb.spb_verbosity.valueChanged.connect(set_verbosity)
    wb.sty_style_selecter.currentTextChanged.connect(wb.app.setStyle)
    wb.chb_rehost.stateChanged.connect(wb.rh_on_off_container.setEnabled)
    wb.pb_def_descr.clicked.connect(default_descr)
    wb.sty_style_selecter.currentTextChanged.connect(wb.app.setStyle)
    wb.pb_def_descr.clicked.connect(default_descr)
    wb.sty_style_selecter.currentTextChanged.connect(wb.app.setStyle)
    wb.chb_rehost.stateChanged.connect(wb.rh_on_off_container.setEnabled)
    wb.pb_def_descr.clicked.connect(default_descr)
    wb.sty_style_selecter.currentTextChanged.connect(wb.app.setStyle)
    wb.chb_show_add_dtors.stateChanged.connect(lambda x: wb.pb_open_dtors.setVisible(x)),
    wb.chb_show_rem_tr1.stateChanged.connect(lambda x: wb.pb_rem_tr1.setVisible(x)),
    wb.chb_show_rem_tr2.stateChanged.connect(lambda x: wb.pb_rem_tr2.setVisible(x)),
    wb.chb_no_icon.stateChanged.connect(wb.job_data.layoutChanged.emit)
    wb.chb_show_tor_folder.stateChanged.connect(wb.job_data.layoutChanged.emit)
    wb.chb_alt_row_colour.stateChanged.connect(wb.job_view.setAlternatingRowColors)
    wb.chb_show_grid.stateChanged.connect(wb.job_view.setShowGrid)
    wb.spb_row_height.valueChanged.connect(wb.job_view.verticalHeader().setDefaultSectionSize)
    wb.ple_warning_color.text_changed.connect(lambda t: wb.color_examples.update_colors(t, 1))
    wb.ple_error_color.text_changed.connect(lambda t: wb.color_examples.update_colors(t, 2))
    wb.ple_success_color.text_changed.connect(lambda t: wb.color_examples.update_colors(t, 3))
    wb.ple_link_color.text_changed.connect(lambda t: wb.color_examples.update_colors(t, 4))


def load_config():
    source_id = wb.config.value('bg_source', defaultValue=1)
    wb.bg_source.button(source_id).click()
    wb.main_window.resize(wb.config.value('geometry/size', defaultValue=QSize(730, 440)))

    try:
        wb.main_window.move(wb.config.value('geometry/position'))
    except TypeError:
        pass

    splittersizes = wb.config.value('geometry/splitter_pos', defaultValue=[100, 336], type=int)
    wb.splitter.setSizes(splittersizes)
    wb.splitter.splitterMoved.emit(splittersizes[0], 1)
    wb.job_view.horizontalHeader().restoreState(wb.config.value('geometry/job_view_header'))

    wb.settings_window.resize(wb.config.value('geometry/config_window_size', defaultValue=QSize(400, 450)))

    hostdata = wb.config.value('rehost_data')
    if hostdata:
        ih.set_attrs(hostdata)
    wb.rehost_table.move_to_priority()


def settings_accepted():
    wb.config.setValue('geometry/config_window_size', wb.settings_window.size())
    consolidate_fsbs()
    wb.config.setValue('rehost_data', ih.get_attrs())


def key_press(event: QKeyEvent):
    if not event.modifiers():
        if event.key() == Qt.Key.Key_Backspace:
            remove_selected()
    elif event.modifiers() == Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier:
        if event.key() == Qt.Key.Key_Return:
            wb.tb_go.click()
    elif event.modifiers() == Qt.KeyboardModifier.ControlModifier:
        if event.key() == Qt.Key.Key_S:
            wb.pb_scan.click()
        if event.key() == Qt.Key.Key_Tab:
            wb.tabs.next()
        if event.key() == Qt.Key.Key_R:
            crop()
        if event.key() == Qt.Key.Key_W:
            for clr_button in (wb.pb_clear_j, wb.pb_clear_r):
                if clr_button.isVisible():
                    clr_button.click()
        if event.key() == Qt.Key.Key_O:
            if wb.pb_open_upl_urls.isVisible():
                wb.pb_open_upl_urls.click()
        # number keys:
        if 0x31 <= event.key() <= 0x39:
            nr = event.key() - 0x30
            try:
                pb_rem_tr = getattr(wb, f'pb_rem_tr{nr}')
            except AttributeError:
                return
            if pb_rem_tr.isVisible():
                pb_rem_tr.click()


def splitlines(txt: str):
    if txt in ('', '\n'):
        return [txt]
    if txt.endswith('\n'):
        txt += '\n'
    return txt.splitlines()


LINK_REGEX = re.compile(r'(https?://)([^\s\n\r]+)')
STUPID_3_11_TB = re.compile(r'[\s^~]+')
LINK_STYLE = ' style="color: {}"'
REPL_PATTERN = r'<a href="\1\2"{}>\2</a>'
LEVEL_SETTING_NAME_MAP = {
    40: 'ple_error_color',
    30: 'ple_warning_color',
    25: 'ple_success_color',
}


def print_logs(record: logging.LogRecord):
    if wb.tabs.count() == 1:
        wb.tabs.addTab(ui_text.tab_results)

    color = wb.config.value(LEVEL_SETTING_NAME_MAP.get(record.levelno))
    link_color = wb.config.value('ple_link_color')
    link_style = LINK_STYLE.format(link_color) if link_color else ''
    repl_pattern = REPL_PATTERN.format(link_style)

    if not (not record.msg and record.exc_info):
        for line in splitlines(record.msg):
            print_log_line(line, repl_pattern, color=color)

    if record.exc_info:
        cls, ex, tb = record.exc_info
        for line in utils.tb_line_gen(tb):
            print_log_line(line, repl_pattern)

        print_log_line(f'{cls.__name__}: {ex}', repl_pattern, color=color)


def print_log_line(line: str, repl_pattern: str, color: str = None):
    line = LINK_REGEX.sub(repl_pattern, line)

    if color:
        line = f'<span style="color: {color}">{line}</span>'

    wb.result_view.append(line)


def trpl_settings():
    user_settings = (
        'chb_deep_search',
        'spb_deep_search_level',
        'chb_save_dtors',
        'chb_del_dtors',
        'chb_file_check',
        'chb_post_compare',
        'te_rel_descr_templ',
        'te_rel_descr_own_templ',
        'chb_add_src_descr',
        'te_src_descr_templ'
    )
    settings_dict = {
        'data_dir': wb.fsb_data_dir.currentText(),
        'dtor_save_dir': wb.fsb_dtor_save_dir.currentText()
    }
    for s in user_settings:
        _, arg_name = s.split('_', maxsplit=1)
        settings_dict[arg_name] = wb.config.value(s)

    if wb.config.value('chb_rehost'):
        white_str_nospace = ''.join(wb.config.value('le_whitelist').split())

        whitelist = white_str_nospace.split(',')
        if '' in whitelist:
            whitelist.remove('')
        settings_dict.update(img_rehost=True, whitelist=whitelist)

    return settings_dict


def gogogo():
    if not wb.job_data:
        return

    min_req_config = ("le_key_1", "le_key_2", "fsb_data_dir")
    if not all(wb.config.value(x) for x in min_req_config):
        wb.settings_window.open()
        return

    if wb.tabs.count() == 1:
        wb.tabs.addTab(ui_text.tab_results)
    wb.tabs.setCurrentIndex(1)

    if not wb.thread:
        wb.thread = TransplantThread()
        wb.thread.started.connect(lambda: wb.go_stop_stack.setCurrentIndex(1))
        wb.thread.started.connect(lambda: wb.pb_stop.clicked.connect(wb.thread.stop))
        wb.thread.finished.connect(lambda: logger.info(ui_text.thread_finish))
        wb.thread.finished.connect(lambda: wb.go_stop_stack.setCurrentIndex(0))

    wb.thread.trpl_settings = trpl_settings()
    wb.thread.stop_run = False
    wb.thread.start()


def parse_paste_input():
    paste_blob = wb.te_paste_box.toPlainText()
    if not paste_blob:
        return

    wb.tabs.setCurrentIndex(0)
    src_tr = tr(wb.config.value('bg_source'))

    new_jobs = []
    for line in paste_blob.split():
        match_id = re.fullmatch(r"\d+", line)
        if match_id:
            new_jobs.append(Job(src_tr=src_tr, tor_id=line))
            continue

        parsed = urlparse(line)
        hostname = parsed.hostname
        id_list = parse_qs(parsed.query).get('torrentid')
        if id_list and hostname:
            try:
                new_jobs.append(Job(src_dom=hostname, tor_id=id_list.pop()))
            except AssertionError:
                continue

    if not wb.job_data.append_jobs(new_jobs):
        wb.pop_up.pop_up(f'{ui_text.pop3}')

    wb.te_paste_box.clear()


def add_jobs_from_torpaths(torpaths, **kwargs):
    new_jobs = []
    for path in torpaths:
        try:
            new_jobs.append(Job(dtor_path=path, **kwargs))
        except (AssertionError, TypeError, AttributeError):
            continue

    if wb.job_data.append_jobs(new_jobs):
        wb.job_view.setFocus()
        return True


def select_dtors():
    file_paths = QFileDialog.getOpenFileNames(wb.main_window, ui_text.sel_dtors_window_title,
                                              wb.config.value('torselect_dir'),
                                              "torrents (*.torrent);;All Files (*)")[0]
    if not file_paths:
        return

    wb.tabs.setCurrentIndex(0)
    if len(file_paths) > 1:
        common_path = os.path.commonpath(file_paths)
    else:
        common_path = os.path.dirname(file_paths[0])

    wb.config.setValue('torselect_dir', os.path.normpath(common_path))

    add_jobs_from_torpaths(file_paths)


def scan_dtorrents():
    path = wb.fsb_scan_dir.currentText()
    wb.tabs.setCurrentIndex(0)

    torpaths = [scan.path for scan in os.scandir(path) if scan.is_file() and scan.name.endswith(".torrent")]
    if torpaths:
        if add_jobs_from_torpaths(torpaths, scanned=True) is None:
            wb.pop_up.pop_up(f'{ui_text.pop2}\n{path}')
    else:
        wb.pop_up.pop_up(f'{ui_text.pop1}\n{path}')


def settings_check():
    data_dir = wb.fsb_data_dir.currentText()
    scan_dir = wb.fsb_scan_dir.currentText()
    dtor_save_dir = wb.fsb_dtor_save_dir.currentText()
    save_dtors = wb.config.value('chb_save_dtors')
    rehost = wb.config.value('chb_rehost')
    add_src_descr = wb.config.value('chb_add_src_descr')

    sum_ting_wong = []
    if not os.path.isdir(data_dir):
        sum_ting_wong.append(ui_text.sum_ting_wong_1)
    if scan_dir and not os.path.isdir(scan_dir):
        sum_ting_wong.append(ui_text.sum_ting_wong_2)
    if save_dtors and not os.path.isdir(dtor_save_dir):
        sum_ting_wong.append(ui_text.sum_ting_wong_3)
    if rehost and not any(h.enabled for h in ih):
        sum_ting_wong.append(ui_text.sum_ting_wong_4)
    if add_src_descr and '%src_descr%' not in wb.te_src_descr_templ.toPlainText():
        sum_ting_wong.append(ui_text.sum_ting_wong_5)
    for set_name in ('le_key_1', 'le_key_2'):
        value = wb.config.value(set_name)
        stripped = value.strip()
        if value != stripped:
            show_name = set_name.split('_', maxsplit=1)[1]
            sum_ting_wong.append(ui_text.sum_ting_wong_6.format(show_name))

    if sum_ting_wong:
        warning = QMessageBox()
        warning.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        warning.setIcon(QMessageBox.Icon.Warning)
        warning.setText("- " + "\n- ".join(sum_ting_wong))
        warning.exec()
        return
    else:
        wb.settings_window.accept()


def tooltips(flag):
    for t_name, ttip in vars(ui_text).items():
        if t_name.startswith('tt_'):
            obj_name = t_name.split('_', maxsplit=1)[1]
            obj = getattr(wb, obj_name)
            obj.setToolTip(ttip if flag else '')

    wb.splitter.handle(1).setToolTip(ui_text.ttm_splitter if flag else '')


def consolidate_fsbs():
    for fsb in wb.fsbs():
        fsb.consolidate()


def default_descr():
    wb.te_rel_descr_templ.setText(ui_text.def_rel_descr)
    wb.te_rel_descr_own_templ.setText(ui_text.def_rel_descr_own)
    wb.te_src_descr_templ.setText(ui_text.def_src_descr)


def open_tor_urls():
    for piece in wb.result_view.toPlainText().split():
        if 'torrentid' in piece:
            QDesktopServices.openUrl(QUrl(piece))


def remove_selected():
    row_list = wb.selection.selectedRows()
    if not row_list:
        return

    wb.job_data.del_multi(row_list)


def crop():
    row_list = wb.selection.selectedRows()
    if not row_list:
        return

    reversed_selection = [x for x in range(len(wb.job_data.jobs)) if x not in row_list]
    wb.job_data.del_multi(reversed_selection)
    wb.selection.clearSelection()


def delete_selected():
    row_list = wb.selection.selectedRows()
    if not row_list:
        return

    non_scanned = 0
    for i in row_list.copy():
        job = wb.job_data.jobs[i]
        if job.scanned:
            os.remove(job.dtor_path)
        else:
            row_list.remove(i)
            non_scanned += 1

    if non_scanned:
        wb.pop_up.pop_up(ui_text.pop4.format(non_scanned, 's' if non_scanned > 1 else ''))

    wb.job_data.del_multi(row_list)


def open_torrent_page(index):
    if index.column() > 0:
        return
    job = wb.job_data.jobs[index.row()]
    domain = job.src_tr.site
    if job.info_hash:
        url = domain + 'torrents.php?searchstr=' + job.info_hash
    elif job.tor_id:
        url = domain + 'torrents.php?torrentid=' + job.tor_id
    else:
        return
    QDesktopServices.openUrl(QUrl(url))


def set_verbosity(lvl):
    verb_map = {
        0: logging.CRITICAL,
        1: logging.ERROR,
        2: logging.INFO,
        3: logging.DEBUG}
    logger.setLevel(verb_map[lvl])


def save_state():
    wb.config.setValue('rehost_data', ih.get_attrs())
    wb.config.setValue('geometry/size', wb.main_window.size())
    wb.config.setValue('geometry/position', wb.main_window.pos())
    wb.config.setValue('geometry/splitter_pos', wb.splitter.sizes())
    wb.config.setValue('geometry/job_view_header', wb.job_view.horizontalHeader().saveState())
    wb.config.sync()
