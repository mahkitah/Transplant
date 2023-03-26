import os
import re
import logging
import traceback
import webbrowser

from PyQt6.QtWidgets import QMainWindow, QFileDialog, QMessageBox
from PyQt6.QtGui import QIcon, QKeyEvent
from PyQt6.QtCore import Qt, QObject, QSize, QThread, pyqtSignal

from lib import ui_text, utils
from lib.transplant import Transplanter, Job
from lib.version import __version__
from gazelle.tracker_data import tr
from GUI.settings_window import SettingsWindow
from GUI.central_gui import Central
from GUI.custom_gui_classes import IniSettings, TempPopUp
from GUI.widget_bank import wb
from GUI import resources

logging.getLogger('urllib3').setLevel(logging.WARNING)

class Report(QObject, logging.Handler):
    logging_sig = pyqtSignal(str)

    def emit(self, record):
        self.logging_sig.emit(record.msg)

# noinspection PyBroadException
class TransplantThread(QThread):
    upl_succes = pyqtSignal(int)

    def __init__(self, job_list, key_dict, trpl_settings):
        super().__init__()
        self.job_list = job_list
        self.key_dict = key_dict
        self.trpl_settings = trpl_settings
        self.stop_run = False

    def stop(self):
        self.stop_run = True

    # noinspection PyUnresolvedReferences
    def run(self):
        transplanter = Transplanter(self.key_dict, **self.trpl_settings)
        failed_job_count = 0
        for job in self.job_list:
            if self.stop_run:
                break
            try:
                success = transplanter.do_your_job(job)
            except Exception:
                failed_job_count += 1
                logging.error(traceback.format_exc(chain=False))
                continue
            if success:
                self.upl_succes.emit(failed_job_count)
            else:
                failed_job_count += 1

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(ui_text.main_window_title.format(__version__))
        self.setWindowIcon(QIcon(':/switch.svg'))
        self.set_config()
        wb.add_config(self.config)
        self.setCentralWidget(Central())
        self.set_window = SettingsWindow(self)
        self.main_connections()
        self.config_connections()
        self.set_logging()
        self.load_config()

        self._pop_up = None

        wb.emit_state()
        wb.pb_scan.setFocus()
        self.show()

    def set_config(self):
        self.config = IniSettings("Transplant.ini")
        config_version = self.config.value('config_version')
        if config_version != __version__:
            self.config_update()
            self.config.setValue('config_version', __version__)

    def config_update(self):
        changes = (
            ('te_rel_descr', 'te_rel_descr_templ', None),
            ('te_src_descr', 'te_src_descr_templ', None),
            ('le_scandir', 'le_scan_dir', None),
            ('geometry/header', 'geometry/job_view_header', None),
            ('le_data_dir', 'fsb_data_dir', lambda x: [x]),
            ('le_scan_dir', 'fsb_scan_dir', lambda x: [x]),
            ('le_dtor_save_dir', 'fsb_dtor_save_dir', lambda x: [x]),
        )
        for old, new, conversion in changes:
            if self.config.contains(old):
                value = self.config.value(old)
                if conversion:
                    value = conversion(value)
                self.config.setValue(new, value)
                self.config.remove(old)

        for key in self.config.allKeys():
            if key.startswith('chb_'):
                value = self.config.value(key)
                if value not in (0, 1, 2):
                    value = 2 if bool(int(value)) else 0
                    self.config.setValue(key, value)
            elif key.startswith('spb_'):
                value = self.config.value(key)
                if not type(value) == int:
                    self.config.setValue(key, int(value))
            if key == 'spb_splitter_weight':
                self.config.remove(key)

    def set_logging(self):
        self.report = logging.getLogger()
        self.handler = Report()
        self.report.addHandler(self.handler)
        self.handler.logging_sig.connect(wb.result_view.add)

    def main_connections(self):
        wb.te_paste_box.plain_text_changed.connect(lambda x: wb.pb_add.setEnabled(bool(x)))
        wb.bg_source.idClicked.connect(lambda x: self.config.setValue('bg_source', x))
        wb.pb_add.clicked.connect(self.parse_paste_input)
        wb.pb_open_dtors.clicked.connect(self.select_dtors)
        wb.pb_scan.clicked.connect(self.scan_dtorrents)
        wb.pb_clear_j.clicked.connect(wb.job_data.clear)
        wb.pb_clear_r.clicked.connect(wb.result_view.clear)
        wb.pb_rem_sel.clicked.connect(self.remove_selected)
        wb.pb_crop.clicked.connect(self.crop)
        wb.pb_del_sel.clicked.connect(self.delete_selected)
        wb.pb_rem_tr1.clicked.connect(lambda: wb.job_data.filter_for_attr('src_tr', tr.RED))
        wb.pb_rem_tr2.clicked.connect(lambda: wb.job_data.filter_for_attr('src_tr', tr.OPS))
        wb.pb_open_tsavedir.clicked.connect(
            lambda: utils.open_local_folder(wb.fsb_dtor_save_dir.currentText()))
        wb.tb_go.clicked.connect(self.gogogo)
        wb.pb_open_upl_urls.clicked.connect(self.open_tor_urls)
        wb.job_view.horizontalHeader().sectionDoubleClicked.connect(wb.job_data.header_double_clicked)
        wb.selection.selectionChanged.connect(lambda: wb.pb_rem_sel.setEnabled(wb.selection.hasSelection()))
        wb.selection.selectionChanged.connect(
            lambda: wb.pb_crop.setEnabled(0 < len(wb.selection.selectedRows()) < len(wb.job_data.jobs)))
        wb.selection.selectionChanged.connect(lambda x: wb.pb_del_sel.setEnabled(wb.selection.hasSelection()))
        wb.job_view.doubleClicked.connect(self.open_torrent_page)
        wb.job_view.key_override_sig.connect(self.keyPressEvent)
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
        wb.tb_open_config.clicked.connect(self.set_window.open)
        wb.tb_open_config2.clicked.connect(wb.tb_open_config.click)
        wb.splitter.splitterMoved.connect(lambda x, y: wb.tb_open_config2.setHidden(bool(x)))
        wb.tabs.currentChanged.connect(wb.view_stack.setCurrentIndex)
        wb.view_stack.currentChanged.connect(wb.tabs.setCurrentIndex)
        wb.view_stack.currentChanged.connect(wb.button_stack.setCurrentIndex)

    def config_connections(self):
        wb.pb_def_descr.clicked.connect(self.default_descr)
        wb.pb_ok.clicked.connect(self.settings_check)
        wb.pb_cancel.clicked.connect(self.set_window.reject)
        self.set_window.accepted.connect(
            lambda: self.config.setValue('geometry/config_window_size', self.set_window.size()))
        self.set_window.accepted.connect(self.consolidate_fsbs)
        wb.fsb_scan_dir.list_changed.connect(
            lambda: wb.pb_scan.setEnabled(bool(wb.fsb_scan_dir.currentText())))
        wb.fsb_dtor_save_dir.list_changed.connect(
            lambda: wb.pb_open_tsavedir.setEnabled(bool(wb.fsb_dtor_save_dir.currentText())))
        wb.chb_show_tips.stateChanged.connect(self.tooltips)
        wb.spb_verbosity.valueChanged.connect(self.set_verbosity)
        wb.chb_show_add_dtors.stateChanged.connect(lambda x: wb.pb_open_dtors.setVisible(x)),
        wb.chb_show_rem_tr1.stateChanged.connect(lambda x: wb.pb_rem_tr1.setVisible(x)),
        wb.chb_show_rem_tr2.stateChanged.connect(lambda x: wb.pb_rem_tr2.setVisible(x)),
        wb.chb_no_icon.stateChanged.connect(wb.job_data.layoutChanged.emit)
        wb.chb_alt_row_colour.stateChanged.connect(wb.job_view.setAlternatingRowColors)
        wb.chb_show_grid.stateChanged.connect(wb.job_view.setShowGrid)
        wb.chb_show_grid.stateChanged.connect(wb.job_data.layoutChanged.emit)
        wb.spb_row_height.valueChanged.connect(wb.job_view.verticalHeader().setDefaultSectionSize)

    def keyPressEvent(self, event: QKeyEvent):
        if not event.modifiers():
            if event.key() == Qt.Key.Key_Backspace:
                self.remove_selected()
        elif event.modifiers() == Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier:
            if event.key() == Qt.Key.Key_Return:
                wb.tb_go.click()
        elif event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_S:
                wb.pb_scan.click()
            if event.key() == Qt.Key.Key_Tab:
                wb.tabs.next()
            if event.key() == Qt.Key.Key_R:
                self.crop()
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
        else:
            super().keyPressEvent(event)

    def load_config(self):
        source_id = int(self.config.value('bg_source', defaultValue=0))
        wb.bg_source.buttons()[source_id].click()
        self.resize(self.config.value('geometry/size', defaultValue=QSize(550, 500)))

        try:
            self.move(self.config.value('geometry/position'))
        except TypeError:
            pass

        splittersizes = [int(x) for x in self.config.value('geometry/splitter_pos', defaultValue=[150, 345])]
        wb.splitter.setSizes(splittersizes)
        wb.splitter.splitterMoved.emit(splittersizes[0], 1)
        try:
            wb.job_view.horizontalHeader().restoreState(self.config.value('geometry/job_view_header'))
        except TypeError:
            wb.job_view.horizontalHeader().set_all_sections_visible()

        self.set_window.resize(self.config.value('geometry/config_window_size', defaultValue=QSize(400, 450)))

    @property
    def pop_up(self):
        if not self._pop_up:
            self._pop_up = TempPopUp(self)

        return self._pop_up

    def trpl_settings(self):
        user_settings = (
            'chb_deep_search',
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
            settings_dict[arg_name] = self.config.value(s)

        if self.config.value('chb_rehost'):
            white_str_nospace = ''.join(self.config.value('le_whitelist').split())
            if white_str_nospace:
                whitelist = white_str_nospace.split(',')
                settings_dict.update(img_rehost=True, whitelist=whitelist,
                                     ptpimg_key=self.config.value('le_ptpimg_key'))

        return settings_dict

    def gogogo(self):
        if not wb.job_data:
            return

        min_req_config = ("le_key_1", "le_key_2", "fsb_data_dir")
        if not all(self.config.value(x) for x in min_req_config):
            self.set_window.open()
            return

        key_dict = {
            tr.RED: self.config.value('le_key_1'),
            tr.OPS: self.config.value('le_key_2')
        }

        settings = self.trpl_settings()

        if wb.tabs.count() == 1:
            wb.tabs.addTab(ui_text.tab_results)
        wb.tabs.setCurrentIndex(1)

        self.tr_thread = TransplantThread(wb.job_data.jobs.copy(), key_dict, settings)

        wb.pb_stop.clicked.connect(self.tr_thread.stop)
        self.tr_thread.started.connect(lambda: self.report.info(ui_text.start))
        self.tr_thread.started.connect(lambda: wb.go_stop_stack.setCurrentIndex(1))
        self.tr_thread.finished.connect(lambda: self.report.info(ui_text.thread_finish))
        self.tr_thread.finished.connect(lambda: wb.go_stop_stack.setCurrentIndex(0))
        self.tr_thread.upl_succes.connect(lambda x: wb.job_data.remove_jobs(x, x))
        self.tr_thread.start()

    def select_dtors(self):
        file_paths = QFileDialog.getOpenFileNames(self, ui_text.sel_dtors_window_title,
                                                  self.config.value('torselect_dir'),
                                                  "torrents (*.torrent);;All Files (*)")[0]
        if not file_paths:
            return

        wb.tabs.setCurrentIndex(0)
        if len(file_paths) > 1:
            common_path = os.path.commonpath(file_paths)
        else:
            common_path = os.path.dirname(file_paths[0])

        self.config.setValue('torselect_dir', os.path.normpath(common_path))

        new_jobs = []
        for p in file_paths:
            if os.path.isfile(p) and p.endswith(".torrent"):
                try:
                    new_jobs.append(Job(dtor_path=p))
                except (AssertionError, TypeError, AttributeError):
                    continue
        wb.job_data.append_jobs(new_jobs)

    def parse_paste_input(self):

        paste_blob = wb.te_paste_box.toPlainText()
        if not paste_blob:
            return

        wb.tabs.setCurrentIndex(0)
        tr_map = {0: tr.RED, 1: tr.OPS}
        src_tr = tr_map.get(self.config.value('bg_source'))

        new_jobs = []
        for line in paste_blob.split():
            match_id = re.fullmatch(r"\d+", line)
            if match_id:
                new_jobs.append(Job(src_tr=src_tr, tor_id=line))
                continue
            match_url = re.search(r"https?://(.+?)/.+torrentid=(\d+)", line)
            if match_url:
                try:
                    new_jobs.append(Job(src_dom=match_url.group(1), tor_id=match_url.group(2)))
                except AssertionError:
                    continue

        if not wb.job_data.append_jobs(new_jobs):
            self.pop_up.pop_up(f'{ui_text.pop3}')

        wb.te_paste_box.clear()

    def scan_dtorrents(self):
        path = wb.fsb_scan_dir.currentText()
        wb.tabs.setCurrentIndex(0)

        new_jobs = []
        for scan in os.scandir(path):
            if scan.is_file() and scan.name.endswith(".torrent"):
                try:
                    new_jobs.append(Job(dtor_path=scan.path, scanned=True))
                except (AssertionError, TypeError, AttributeError):
                    continue

        if new_jobs:
            wb.job_view.setFocus()
            if not wb.job_data.append_jobs(new_jobs):
                self.pop_up.pop_up(f'{ui_text.pop2}\n{path}')
        else:
            self.pop_up.pop_up(f'{ui_text.pop1}\n{path}')

    def settings_check(self):
        data_dir = wb.fsb_data_dir.currentText()
        scan_dir = wb.fsb_scan_dir.currentText()
        dtor_save_dir = wb.fsb_dtor_save_dir.currentText()
        save_dtors = self.config.value('chb_save_dtors')
        rehost = self.config.value('chb_rehost')
        ptpimg_key = self.config.value('le_ptpimg_key')
        add_src_descr = self.config.value('chb_add_src_descr')

        sum_ting_wong = []
        if not os.path.isdir(data_dir):
            sum_ting_wong.append(ui_text.sum_ting_wong_1)
        if scan_dir and not os.path.isdir(scan_dir):
            sum_ting_wong.append(ui_text.sum_ting_wong_2)
        if save_dtors and not os.path.isdir(dtor_save_dir):
            sum_ting_wong.append(ui_text.sum_ting_wong_3)
        if rehost and not ptpimg_key:
            sum_ting_wong.append(ui_text.sum_ting_wong_4)
        if add_src_descr and '%src_descr%' not in wb.te_src_descr_templ.toPlainText():
            sum_ting_wong.append(ui_text.sum_ting_wong_5)
        for set_name in ('le_key_1', 'le_key_2', 'le_ptpimg_key'):
            value = self.config.value(set_name)
            stripped = value.strip()
            if value != stripped:
                show_name = set_name.split('_', maxsplit=1)[1]
                sum_ting_wong.append(ui_text.sum_ting_wong_6.format(show_name))

        if sum_ting_wong:
            warning = QMessageBox()
            warning.setIcon(QMessageBox.Icon.Warning)
            warning.setText("- " + "\n- ".join(sum_ting_wong))
            warning.exec()
            return
        else:
            self.set_window.accept()

    @staticmethod
    def tooltips(flag):
        for t_name, ttip in vars(ui_text).items():
            if t_name.startswith('tt_'):
                obj_name = t_name.split('_', maxsplit=1)[1]
                obj = getattr(wb, obj_name)
                obj.setToolTip(ttip if flag else '')

        wb.splitter.handle(1).setToolTip(ui_text.ttm_splitter if flag else '')

    @staticmethod
    def consolidate_fsbs():
        for fsb in wb.fsbs():
            fsb.consolidate()

    @staticmethod
    def default_descr():
        wb.te_rel_descr_templ.setText(ui_text.def_rel_descr)
        wb.te_rel_descr_own_templ.setText(ui_text.def_rel_descr_own)
        wb.te_src_descr_templ.setText(ui_text.def_src_descr)

    @staticmethod
    def open_tor_urls():
        for piece in wb.result_view.toPlainText().split():
            if 'torrentid' in piece:
                webbrowser.open(piece)

    @staticmethod
    def remove_selected():
        row_list = wb.selection.selectedRows()
        if not row_list:
            return

        wb.job_data.del_multi(row_list)

    @staticmethod
    def crop():
        row_list = wb.selection.selectedRows()
        if not row_list:
            return

        reversed_selection = [x for x in range(len(wb.job_data.jobs)) if x not in row_list]
        wb.job_data.del_multi(reversed_selection)
        wb.selection.clearSelection()

    @staticmethod
    def delete_selected():
        row_list = wb.selection.selectedRows()
        if not row_list:
            return

        for i in row_list.copy():
            job = wb.job_data.jobs[i]
            if job.scanned:
                os.remove(job.dtor_path)
            else:
                row_list.remove(i)

        wb.job_data.del_multi(row_list)

    @staticmethod
    def open_torrent_page(index):
        if index.column() > 1:
            return
        job = wb.job_data.jobs[index.row()]
        domain = job.src_tr.site
        if job.info_hash:
            url = domain + 'torrents.php?searchstr=' + job.info_hash
        elif job.tor_id:
            url = domain + 'torrents.php?torrentid=' + job.tor_id
        else:
            return
        webbrowser.open(url)

    def set_verbosity(self, lvl):
        verb_map = {
            0: logging.CRITICAL,
            1: logging.ERROR,
            2: logging.INFO,
            3: logging.DEBUG}
        self.report.setLevel(verb_map[lvl])

    def save_state(self):
        self.config.setValue('geometry/size', self.size())
        self.config.setValue('geometry/position', self.pos())
        self.config.setValue('geometry/splitter_pos', wb.splitter.sizes())
        self.config.setValue('geometry/job_view_header', wb.job_view.horizontalHeader().saveState())
