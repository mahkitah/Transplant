import os
import re
import logging
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from lib import utils, tp_text
from lib.img_rehost import IH
from lib.transplant import Job, Transplanter, JobCreationError
from gazelle.tracker_data import TR
from GUI import gui_text
from GUI.widget_bank import wb
from GUI.main_gui import MainWindow
from GUI.settings_window import SettingsWindow

from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.QtGui import QDesktopServices, QTextCursor, QShortcut
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QThread, QSize, QUrl, QModelIndex


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

    def run(self):
        logger.log(22, gui_text.start)
        key_dict = {
            TR.RED: wb.config.value('le_key_1'),
            TR.OPS: wb.config.value('le_key_2')
        }
        transplanter = Transplanter(key_dict, **self.trpl_settings)

        for job in wb.job_data.jobs.copy():
            if self.isInterruptionRequested():
                break
            try:
                if job not in wb.job_data.jobs:  # It's possible to remove jobs from joblist during transplanting
                    logger.warning(f'{gui_text.removed} {job.display_name}')
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
    set_shortcuts()
    set_tooltips()
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
    wb.pb_rem_tr1.clicked.connect(lambda: wb.job_data.filter_for_attr('src_tr', TR.RED))
    wb.pb_rem_tr2.clicked.connect(lambda: wb.job_data.filter_for_attr('src_tr', TR.OPS))
    wb.pb_open_tsavedir.clicked.connect(
        lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(wb.fsb_dtor_save_dir.currentText())))
    wb.pb_go.clicked.connect(gogogo)
    wb.pb_open_upl_urls.clicked.connect(open_tor_urls)
    wb.job_view.horizontalHeader().sectionDoubleClicked.connect(job_view_header_double_clicked)
    wb.selection.selectionChanged.connect(lambda: wb.pb_rem_sel.setEnabled(wb.selection.hasSelection()))
    wb.selection.selectionChanged.connect(
        lambda: wb.pb_crop.setEnabled(0 < len(wb.selection.selectedRows()) < len(wb.job_data.jobs)))
    wb.selection.selectionChanged.connect(lambda x: wb.pb_del_sel.setEnabled(wb.selection.hasSelection()))
    wb.job_view.doubleClicked.connect(open_torrent_page)
    wb.job_data.layout_changed.connect(lambda: wb.pb_go.setEnabled(bool(wb.job_data)))
    wb.job_data.layout_changed.connect(lambda: wb.pb_clear_j.setEnabled(bool(wb.job_data)))
    wb.job_data.layout_changed.connect(
        lambda: wb.pb_rem_tr1.setEnabled(any(j.src_tr is TR.RED for j in wb.job_data)))
    wb.job_data.layout_changed.connect(
        lambda: wb.pb_rem_tr2.setEnabled(any(j.src_tr is TR.OPS for j in wb.job_data)))
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
    wb.settings_window.accepted.connect(settings_accepted)
    wb.tb_key_test1.clicked.connect(lambda: api_key_test(TR.RED, wb.le_key_1.text()))
    wb.tb_key_test2.clicked.connect(lambda: api_key_test(TR.OPS, wb.le_key_2.text()))
    wb.le_key_1.textChanged.connect(lambda t: wb.tb_key_test1.setEnabled(bool(t)))
    wb.le_key_2.textChanged.connect(lambda t: wb.tb_key_test2.setEnabled(bool(t)))
    wb.fsb_scan_dir.list_changed.connect(
        lambda: wb.pb_scan.setEnabled(bool(wb.fsb_scan_dir.currentText())))
    wb.fsb_dtor_save_dir.list_changed.connect(
        lambda: wb.pb_open_tsavedir.setEnabled(bool(wb.fsb_dtor_save_dir.currentText())))
    wb.chb_deep_search.stateChanged.connect(lambda x: wb.spb_deep_search_level.setEnabled(bool(x)))
    wb.chb_show_tips.stateChanged.connect(wb.tt_filter.set_tt_enabled)
    wb.spb_verbosity.valueChanged.connect(set_verbosity)
    wb.chb_rehost.stateChanged.connect(wb.rh_on_off_container.setEnabled)
    wb.pb_def_descr.clicked.connect(default_descr)
    wb.pb_def_descr.clicked.connect(default_descr)
    wb.sty_style_selector.currentTextChanged.connect(wb.app.set_style)
    if wb.theme_writable:
        wb.sty_style_selector.currentTextChanged.connect(
        lambda t: wb.thm_theme_selector.setEnabled(t.lower() != 'windowsvista'))
        wb.thm_theme_selector.current_data_changed.connect(lambda x: wb.app.styleHints().setColorScheme(x))
    wb.chb_rehost.stateChanged.connect(wb.rh_on_off_container.setEnabled)
    wb.pb_def_descr.clicked.connect(default_descr)
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
    wb.ple_link_color.text_changed.connect(lambda c: wb.l_colors.setText(gui_text.l_colors.format(c)))
    wb.color_examples.css_changed.connect(wb.result_view.document().setDefaultStyleSheet)


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
        IH.set_attrs(hostdata)
    wb.rehost_table.move_to_priority()


def settings_accepted():
    wb.config.setValue('geometry/config_window_size', wb.settings_window.size())
    wb.config.setValue('rehost_data', IH.get_attrs())
    for fsb in wb.fsbs:
        fsb.consolidate()


SC_DATA = (
    (('pb_go',), 'Ctrl+Shift+Return'),
    (('tabs',), 'Ctrl+Tab'),
    (('pb_scan',), 'Ctrl+S'),
    (('pb_rem_sel',), 'Backspace'),
    (('pb_crop',), 'Ctrl+R'),
    (('pb_clear_j', 'pb_clear_r'), 'Ctrl+W'),
    (('pb_open_upl_urls',), 'Ctrl+O'),
    (('pb_rem_tr1',), 'Ctrl+1'),
    (('pb_rem_tr2',), 'Ctrl+2'),
)
widg_sc_map = {}


def set_shortcuts():
    for w_names, default in SC_DATA:
        sc = QShortcut(wb.main_window)
        sc.setKey(default)
        for w_name in w_names:
            widg_sc_map[w_name] = sc
            widg = getattr(wb, w_name)
            if w_name == 'tabs':
                slot = widg.next
            else:
                slot = widg.animateClick
            sc.activated.connect(slot)


LINK_REGEX = re.compile(r'(https?://)([^\s\n\r]+)')
REPL_PATTERN = r'<a href="\1\2"{}>\2</a>'
LEVEL_SETTING_NAME_MAP = {
    40: 'bad',
    30: 'warning',
    25: 'good',
    20: 'normal'
}


def print_logs(record: logging.LogRecord):
    if wb.tabs.count() == 1:
        wb.tabs.addTab(gui_text.tab_results)

    cls_val_q, same_line = divmod(record.levelno, 5)
    cls_name = LEVEL_SETTING_NAME_MAP.get(cls_val_q * 5)
    prefix = '&nbsp;' if same_line else '<br>'
    has_exc = bool(record.exc_info) and None not in record.exc_info
    wb.result_view.moveCursor(QTextCursor.MoveOperation.End)

    if record.msg or not has_exc:
        if record.msg:
            msg = LINK_REGEX.sub(REPL_PATTERN, record.msg)
            msg = msg.replace('\n', '<br>')
            msg = f"<span class={cls_name}>{prefix}{msg}</span>"
        else:
            msg = prefix

        wb.result_view.insertHtml(msg)

    if has_exc:
        cls, ex, tb = record.exc_info
        msg = f'{cls.__name__}: {ex}'

        if logger.level < logging.INFO:
            wb.result_view.insertHtml('<span>&zwnj;</span>')  # to prevent the following text taking previous color
            wb.result_view.insertPlainText('\n' + 'Traceback (most recent call last):')
            wb.result_view.insertPlainText('\n' + '\n'.join(utils.tb_line_gen(tb)))

        wb.result_view.insertHtml(f'<br><span class={cls_name}>{msg}</span>')


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
        'data_dir': Path(wb.fsb_data_dir.currentText()),
        'dtor_save_dir': Path(tsd) if (tsd := wb.fsb_dtor_save_dir.currentText()) else None
    }
    for s in user_settings:
        typ, arg_name = s.split('_', maxsplit=1)
        val = wb.config.value(s)
        if typ == 'chb':
            val = bool(val)
        settings_dict[arg_name] = val

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
        wb.tabs.addTab(gui_text.tab_results)
    wb.tabs.setCurrentIndex(1)

    if not wb.thread:
        wb.thread = TransplantThread()
        wb.thread.started.connect(lambda: wb.go_stop_stack.setCurrentIndex(1))
        wb.thread.started.connect(lambda: wb.pb_stop.clicked.connect(wb.thread.requestInterruption))
        wb.thread.finished.connect(lambda: logger.info(gui_text.thread_finish))
        wb.thread.finished.connect(lambda: wb.go_stop_stack.setCurrentIndex(0))

    wb.thread.trpl_settings = trpl_settings()
    wb.thread.stop_run = False
    wb.thread.start()


class JobCollector:
    def __init__(self):
        self.jobs = []

    def collect(self, name, **kwargs):
        try:
            job = Job(**kwargs)
        except JobCreationError as e:
            logger.debug(name)
            logger.debug(str(e) + '\n')
            return

        if job in self.jobs or job in wb.job_data.jobs:
            logger.debug(name)
            logger.debug(f'{tp_text.skip}{gui_text.dupe_add}\n')
            return

        self.jobs.append(job)
        return True

    def add_jobs_2_joblist(self, empty_msg=None):
        if self.jobs:
            wb.job_data.append_jobs(self.jobs)
        elif empty_msg:
            wb.pop_up.pop_up(empty_msg)
        wb.job_view.setFocus()


def parse_paste_input():
    paste_blob = wb.te_paste_box.toPlainText()
    if not paste_blob:
        return

    wb.tabs.setCurrentIndex(0)
    src_tr = TR(wb.config.value('bg_source'))

    new_jobs = JobCollector()
    for line in paste_blob.split():
        match_id = re.fullmatch(r"\d+", line)
        if match_id:
            new_jobs.collect(line, src_tr=src_tr, tor_id=line)
        else:
            parsed = urlparse(line)
            hostname = parsed.hostname
            id_list = parse_qs(parsed.query).get('torrentid')
            if id_list and hostname:
                new_jobs.collect(line, src_dom=hostname, tor_id=id_list.pop())

    new_jobs.add_jobs_2_joblist(gui_text.pop3)
    wb.te_paste_box.clear()


def select_dtors():
    file_paths = QFileDialog.getOpenFileNames(wb.main_window, gui_text.sel_dtors_window_title,
                                              wb.config.value('torselect_dir'),
                                              "torrents (*.torrent);;All Files (*)")[0]
    if not file_paths:
        return

    wb.tabs.setCurrentIndex(0)
    if len(file_paths) > 1:
        common_path = os.path.commonpath(file_paths)
    else:
        common_path = os.path.dirname(file_paths[0])

    wb.config.setValue('torselect_dir', common_path)

    new_jobs = JobCollector()
    for fp in file_paths:
        p = Path(fp)
        new_jobs.collect(p.name, dtor_path=p)

    new_jobs.add_jobs_2_joblist()


def scan_dtorrents():
    scan_path = Path(wb.fsb_scan_dir.currentText())
    wb.tabs.setCurrentIndex(0)

    torpaths = tuple(scan_path.glob('*.torrent'))
    new_jobs = JobCollector()

    for p in torpaths:
        new_jobs.collect(p.name, dtor_path=p, scanned=True)

    poptxt = gui_text.pop2 if torpaths else gui_text.pop1
    new_jobs.add_jobs_2_joblist(f'{poptxt}\n{scan_path}')


def settings_check():
    data_dir = wb.fsb_data_dir.currentText()
    scan_dir = wb.fsb_scan_dir.currentText()
    dtor_save_dir = wb.fsb_dtor_save_dir.currentText()
    save_dtors = wb.config.value('chb_save_dtors')
    rehost = wb.config.value('chb_rehost')
    add_src_descr = wb.config.value('chb_add_src_descr')

    # Path('') exists and is_dir
    sum_ting_wong = []
    if not data_dir or not Path(data_dir).is_dir():
        sum_ting_wong.append(gui_text.sum_ting_wong_1)
    if scan_dir and not Path(scan_dir).is_dir():
        sum_ting_wong.append(gui_text.sum_ting_wong_2)
    if save_dtors and (not dtor_save_dir or not Path(dtor_save_dir).is_dir()):
        sum_ting_wong.append(gui_text.sum_ting_wong_3)
    if rehost and not any(h.enabled for h in IH):
        sum_ting_wong.append(gui_text.sum_ting_wong_4)
    if add_src_descr and '%src_descr%' not in wb.te_src_descr_templ.toPlainText():
        sum_ting_wong.append(gui_text.sum_ting_wong_5)

    if sum_ting_wong:
        warning = QMessageBox(wb.settings_window)
        warning.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        warning.setIcon(QMessageBox.Icon.Warning)
        warning.setText("- " + "\n- ".join(sum_ting_wong))
        warning.exec()
        return
    else:
        wb.settings_window.accept()


def set_tooltip(name:  str, ttip: str):
    obj = getattr(wb, name)
    obj.installEventFilter(wb.tt_filter)
    obj.setToolTip(ttip)


def set_tooltips():
    wb.splitter_handle = wb.splitter.handle(1)
    for name, ttip in gui_text.tooltips.items():
        set_tooltip(name, ttip)
    for name, ttip in gui_text.tooltips_with_sc.items():
        sc = widg_sc_map.get(name)
        if sc:
            ttip = f'{ttip} ({sc.key().toString()})'
        set_tooltip(name, ttip)


def default_descr():
    wb.te_rel_descr_templ.setText(gui_text.def_rel_descr)
    wb.te_rel_descr_own_templ.setText(gui_text.def_rel_descr_own)
    wb.te_src_descr_templ.setText(gui_text.def_src_descr)


def open_tor_urls():
    for piece in wb.result_view.toPlainText().split():
        if 'torrentid' in piece:
            QDesktopServices.openUrl(QUrl('https://' + piece))


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
            job.dtor_path.unlink()
        else:
            row_list.remove(i)
            non_scanned += 1

    if non_scanned:
        wb.pop_up.pop_up(gui_text.pop4.format(non_scanned, 's' if non_scanned > 1 else ''))

    wb.job_data.del_multi(row_list)


def job_view_header_double_clicked(section: int):
    if section == 2:
        wb.job_data.nt_check_uncheck_all()


def open_torrent_page(index: QModelIndex):
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


def key_precheck(tracker: TR, key: str) -> str:
    if key != key.strip():
        return gui_text.keycheck_spaces

    if tracker is TR.RED:
        m = re.match(r'[0-9a-f]{8}\.[0-9a-f]{32}', key)
        if not m:
            return gui_text.keycheck_red_mismatch

    elif tracker is TR.OPS:
        if len(key) not in (116, 118):
            return gui_text.keycheck_ops_mismatch

    return ''


def api_key_test(tracker: TR, key: str):
    msg_box = QMessageBox(wb.settings_window)
    msg_box.setWindowTitle(gui_text.msg_box_title.format(tracker.name))
    precheck_msg = key_precheck(tracker, key)
    if precheck_msg:
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setText(precheck_msg)
        msg_box.show()
    else:
        from gazelle.api_classes import sleeve, RequestFailure
        api = sleeve(tracker, key=key)
        try:
            account_info = api.account_info
        except RequestFailure as e:
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setText(gui_text.keycheck_bad_key.format(tracker.name, e))
        else:
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setText(gui_text.keycheck_good_key.format(account_info['username']))
        msg_box.show()


def set_verbosity(lvl: int):
    verb_map = {
        0: logging.CRITICAL,
        1: logging.ERROR,
        2: logging.INFO,
        3: logging.DEBUG}
    logger.setLevel(verb_map[lvl])


def save_state():
    wb.config.setValue('rehost_data', IH.get_attrs())
    wb.config.setValue('geometry/size', wb.main_window.size())
    wb.config.setValue('geometry/position', wb.main_window.pos())
    wb.config.setValue('geometry/splitter_pos', wb.splitter.sizes())
    wb.config.setValue('geometry/job_view_header', wb.job_view.horizontalHeader().saveState())
    wb.config.sync()
