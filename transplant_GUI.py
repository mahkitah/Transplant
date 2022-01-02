import sys
import os
import re
import logging
import traceback
import webbrowser

from bencoder import BTFailure

from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox
from PyQt5.QtGui import QIcon, QKeyEvent
from PyQt5.QtCore import Qt, QObject, QSize, QThread, pyqtSignal

from lib import ui_text, utils
from lib.transplant import Transplanter, Job
from lib.version import __version__
from gazelle.tracker_data import tr, tr_data
from gazelle.api_classes import KeyApi, RedApi
from GUI.files import get_file
from GUI.settings_window import SettingsWindow
from GUI.main_gui import MainGui
from GUI.custom_gui_classes import IniSettings, FolderSelectBox

logging.getLogger('urllib3').setLevel(logging.WARNING)

class Report(QObject, logging.Handler):
    logging_sig = pyqtSignal(str)

    def emit(self, record):
        repl = re.sub(r'(https?://[^\s\n\r]+)', r'<a href="\1">\1</a> ', str(record.msg))
        self.logging_sig.emit(repl)

# noinspection PyBroadException
class TransplantThread(QThread):
    upl_succes = pyqtSignal(Job)

    def __init__(self, job_list, key_1, key_2, trpl_settings):
        super().__init__()
        self.job_list = job_list
        self.key_1 = key_1
        self.key_2 = key_2
        self.trpl_settings = trpl_settings
        self.stop_run = False

    def stop(self):
        self.stop_run = True

    # noinspection PyUnresolvedReferences
    def run(self):

        api_map = {tr.RED: RedApi(tr.RED, key=self.key_1),
                   tr.OPS: KeyApi(tr.OPS, key=f"token {self.key_2}")}

        transplanter = Transplanter(api_map, **self.trpl_settings)

        for job in self.job_list:
            if self.stop_run:
                break
            try:
                success = transplanter.do_your_job(job)
            except Exception:
                logging.error(traceback.format_exc())
                continue

            if success:
                self.upl_succes.emit(job)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(ui_text.main_window_title.format(__version__))
        self.setWindowIcon(QIcon(get_file('switch.svg')))
        self.set_stylesheet()
        self.set_config()
        self.setCentralWidget(MainGui(self.config))
        self.main = self.centralWidget()
        self.set_window = SettingsWindow(self, self.config)
        self.main_connections()
        self.config_connections()
        self.set_logging()
        self.load_config()
        self.set_window.load_config()
        self.main.pb_scan.setFocus()
        self.show()

    def set_stylesheet(self):
        try:
            with open(get_file('stylesheet.qsst'), 'r') as f:
                stylesheet = f.read()
        except FileNotFoundError:
            pass

        stylesheet = stylesheet.replace('##dots##', get_file('dotsdots.png').replace('\\', '/'))
        self.setStyleSheet(stylesheet)

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

    def set_logging(self):
        self.report = logging.getLogger()
        self.handler = Report()
        self.report.addHandler(self.handler)
        self.handler.logging_sig.connect(self.main.result_view.append)

    def main_connections(self):
        self.main.te_paste_box.plainTextChanged.connect(lambda x: self.main.pb_add.setEnabled(bool(x)))
        self.main.bg_source.idClicked.connect(lambda x: self.config.setValue('bg_source', x))
        self.main.pb_add.clicked.connect(self.parse_paste_input)
        self.main.pb_open_dtors.clicked.connect(self.select_dtors)
        self.main.pb_scan.clicked.connect(self.scan_dtorrents)
        self.main.pb_clear_j.clicked.connect(self.main.job_data.clear)
        self.main.pb_clear_r.clicked.connect(self.main.result_view.clear)
        self.main.pb_rem_sel.clicked.connect(self.remove_selected)
        self.main.pb_del_sel.clicked.connect(self.delete_selected)
        self.main.pb_rem_tr1.clicked.connect(lambda: self.main.job_data.filter_for_attr('src_tr', tr.RED))
        self.main.pb_rem_tr2.clicked.connect(lambda: self.main.job_data.filter_for_attr('src_tr', tr.OPS))
        self.main.pb_open_tsavedir.clicked.connect(
            lambda: utils.open_local_folder(self.set_window.fsb_dtor_save_dir.currentText()))
        self.main.tb_go.clicked.connect(self.gogogo)
        # self.main.tb_go.clicked.connect(self.blabla)
        self.main.pb_open_upl_urls.clicked.connect(self.open_tor_urls)
        self.main.job_view.horizontalHeader().sectionDoubleClicked.connect(self.main.job_data.header_double_clicked)
        self.main.job_view.selectionChange.connect(lambda x: self.main.pb_rem_sel.setEnabled(bool(x)))
        self.main.job_view.selectionChange.connect(lambda x: self.main.pb_del_sel.setEnabled(bool(x)))
        self.main.job_view.doubleClicked.connect(self.open_torrent_page)
        self.main.job_view.key_override_sig.connect(self.keyPressEvent)
        self.main.job_data.layoutChanged.connect(self.main.job_view.clearSelection)
        self.main.job_data.layoutChanged.connect(lambda: self.main.tb_go.setEnabled(bool(self.main.job_data)))
        self.main.job_data.layoutChanged.connect(lambda: self.main.pb_clear_j.setEnabled(bool(self.main.job_data)))
        self.main.job_data.layoutChanged.connect(
            lambda: self.main.pb_rem_tr1.setEnabled(any(j.src_tr == tr.RED for j in self.main.job_data)))
        self.main.job_data.layoutChanged.connect(
            lambda: self.main.pb_rem_tr2.setEnabled(any(j.src_tr == tr.OPS for j in self.main.job_data)))
        self.main.result_view.textChanged.connect(
            lambda: self.main.pb_clear_r.setEnabled(bool(self.main.result_view.toPlainText())))
        self.main.result_view.textChanged.connect(
            lambda: self.main.pb_open_upl_urls.setEnabled('torrentid' in self.main.result_view.toPlainText()))
        self.main.tb_open_config.clicked.connect(self.set_window.open)
        self.main.tb_open_config2.clicked.connect(self.main.tb_open_config.click)
        self.main.splitter.splitterMoved.connect(lambda x, y: self.main.tb_open_config2.setHidden(bool(x)))
        self.main.tabs.currentChanged.connect(self.main.view_stack.setCurrentIndex)
        self.main.view_stack.currentChanged.connect(self.main.tabs.setCurrentIndex)
        self.main.view_stack.currentChanged.connect(self.main.tab_button_stack.setCurrentIndex)

    def config_connections(self):
        self.set_window.pb_def_descr.clicked.connect(self.default_descr)
        self.set_window.pb_ok.clicked.connect(self.settings_check)
        self.set_window.pb_cancel.clicked.connect(self.set_window.reject)
        self.set_window.accepted.connect(
            lambda: self.config.setValue('geometry/config_window_size', self.set_window.size()))
        self.set_window.accepted.connect(self.consolidate_fsbs)
        self.set_window.fsb_scan_dir.list_changed.connect(
            lambda: self.main.pb_scan.setEnabled(bool(self.set_window.fsb_scan_dir.currentText())))
        self.set_window.fsb_dtor_save_dir.list_changed.connect(
            lambda: self.main.pb_open_tsavedir.setEnabled(bool(self.set_window.fsb_dtor_save_dir.currentText())))
        self.set_window.chb_show_tips.stateChanged.connect(self.tooltips)
        self.set_window.spb_verbosity.valueChanged.connect(self.set_verbosity)
        self.set_window.chb_show_add_dtors.stateChanged.connect(lambda x: self.main.section_add_dtor_btn.setVisible(x)),
        self.set_window.chb_show_rem_tr1.stateChanged.connect(lambda x: self.main.pb_rem_tr1.setVisible(x)),
        self.set_window.chb_show_rem_tr2.stateChanged.connect(lambda x: self.main.pb_rem_tr2.setVisible(x)),
        self.set_window.chb_no_icon.stateChanged.connect(self.main.job_data.layoutChanged.emit)
        self.set_window.spb_splitter_weight.valueChanged.connect(self.main.splitter.setHandleWidth)
        self.set_window.chb_alt_row_colour.stateChanged.connect(self.main.job_view.setAlternatingRowColors)
        self.set_window.chb_show_grid.stateChanged.connect(self.main.job_view.setShowGrid)
        self.set_window.chb_show_grid.stateChanged.connect(self.main.job_data.layoutChanged.emit)
        self.set_window.spb_row_height.valueChanged.connect(self.main.job_view.verticalHeader().setDefaultSectionSize)

    def load_config(self):
        source_id = int(self.config.value('bg_source', defaultValue=0))
        self.main.bg_source.buttons()[source_id].click()
        self.resize(self.config.value('geometry/size', defaultValue=QSize(550, 500)))

        try:
            self.move(self.config.value('geometry/position'))
        except TypeError:
            pass

        splittersizes = [int(x) for x in self.config.value('geometry/splitter_pos', defaultValue=[150, 345])]
        self.main.splitter.setSizes(splittersizes)
        self.main.splitter.splitterMoved.emit(splittersizes[0], 1)
        try:
            self.main.job_view.horizontalHeader().restoreState(self.config.value('geometry/job_view_header'))
        except TypeError:
            self.main.job_view.horizontalHeader().set_all_sections_visible()

    def consolidate_fsbs(self):
        for fsb in self.set_window.findChildren(FolderSelectBox):
            fsb.consolidate()

    def keyPressEvent(self, event: QKeyEvent):
        if not event.modifiers():
            if event.key() == Qt.Key_Backspace:
                self.remove_selected()
        elif event.modifiers() == Qt.ControlModifier | Qt.ShiftModifier:
            if event.key() == Qt.Key_Return:
                self.main.tb_go.click()
        elif event.modifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_S:
                self.main.pb_scan.click()
            if event.key() == Qt.Key_Tab:
                self.main.tabs.next()
            if event.key() == Qt.Key_W:
                for clr_button in (self.main.pb_clear_j, self.main.pb_clear_r):
                    if clr_button.isVisible():
                        clr_button.click()
            if event.key() == Qt.Key_O:
                if self.main.pb_open_upl_urls.isVisible():
                    self.main.pb_open_upl_urls.click()
            # number keys:
            if 0x31 <= event.key() <= 0x39:
                nr = event.key() - 0x30
                try:
                    pb_rem_tr = getattr(self.main, f'pb_rem_tr{nr}')
                except AttributeError:
                    return
                if pb_rem_tr.isVisible():
                    pb_rem_tr.click()
        else:
            super().keyPressEvent(event)

    def tooltips(self, flag):
        for t_name, ttip in vars(ui_text).items():
            if t_name.startswith('tt_'):
                obj_name = t_name.split('_', maxsplit=1)[1]
                try:
                    obj = getattr(self.main, obj_name)
                except AttributeError:
                    obj = getattr(self.set_window, obj_name)
                obj.setToolTip(ttip if flag else '')

        self.main.splitter.handle(1).setToolTip(ui_text.ttm_splitter if flag else '')

    def blabla(self, *args):
        self.report.info('blabla\n')
        from testzooi.testrun import testrun
        testrun(self)
        pass

    def gogogo(self):
        if not self.main.job_data:
            return

        min_req_config = ("le_key_1", "le_key_2", "fsb_data_dir")
        if not all(self.config.value(x) for x in min_req_config):
            self.set_window.open()
            return

        key_1 = self.config.value('le_key_1')
        key_2 = self.config.value('le_key_2')

        settings = self.set_window.trpl_settings()

        if self.main.tabs.count() == 1:
            self.main.tabs.addTab(ui_text.tab_results)
        self.main.tabs.setCurrentIndex(1)

        self.tr_thread = TransplantThread(self.main.job_data.jobs.copy(), key_1, key_2, settings)

        self.main.pb_stop.clicked.connect(self.tr_thread.stop)
        self.tr_thread.started.connect(lambda: self.report.info(ui_text.start))
        self.tr_thread.started.connect(lambda: self.main.go_stop_stack.setCurrentIndex(1))
        self.tr_thread.finished.connect(lambda: self.report.info(ui_text.thread_finish))
        self.tr_thread.finished.connect(lambda: self.main.go_stop_stack.setCurrentIndex(0))
        self.tr_thread.upl_succes.connect(self.main.job_data.remove)
        self.tr_thread.start()

    def select_dtors(self):
        file_paths = QFileDialog.getOpenFileNames(self, ui_text.sel_dtors_window_title,
                                                  self.config.value('torselect_dir'),
                                                  "torrents (*.torrent);;All Files (*)")[0]
        if not file_paths:
            return

        self.main.tabs.setCurrentIndex(0)
        if len(file_paths) > 1:
            common_path = os.path.commonpath(file_paths)
        else:
            common_path = os.path.dirname(file_paths[0])

        self.config.setValue('torselect_dir', os.path.normpath(common_path))

        for p in file_paths:
            if os.path.isfile(p) and p.endswith(".torrent"):
                try:
                    self.main.job_data.append(Job(dtor_path=p))
                except (AssertionError, BTFailure):
                    continue

    def scan_dtorrents(self):
        path = self.set_window.fsb_scan_dir.currentText()
        self.main.tabs.setCurrentIndex(0)

        for scan in os.scandir(path):
            if scan.is_file() and scan.name.endswith(".torrent"):
                try:
                    self.main.job_data.append(Job(dtor_path=scan.path, scanned=True))
                except (AssertionError, BTFailure):
                    continue
        self.main.job_view.setFocus()

    def settings_check(self):
        data_dir = self.set_window.fsb_data_dir.currentText()
        scan_dir = self.set_window.fsb_scan_dir.currentText()
        dtor_save_dir = self.set_window.fsb_dtor_save_dir.currentText()
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
        if add_src_descr and '%src_descr%' not in self.set_window.te_src_descr_templ.toPlainText():
            sum_ting_wong.append(ui_text.sum_ting_wong_5)

        if sum_ting_wong:
            warning = QMessageBox()
            warning.setIcon(QMessageBox.Warning)
            warning.setText("- " + "\n- ".join(sum_ting_wong))
            warning.exec()
            return
        else:
            self.set_window.accept()

    def default_descr(self):
        self.set_window.te_rel_descr_templ.setText(ui_text.def_rel_descr)
        self.set_window.te_src_descr_templ.setText(ui_text.def_src_descr)

    def parse_paste_input(self):

        paste_blob = self.main.te_paste_box.toPlainText()
        if not paste_blob:
            return

        self.main.tabs.setCurrentIndex(0)
        tr_map = {0: tr.RED, 1: tr.OPS}
        src_tr = tr_map.get(self.config.value('bg_source'))

        for line in paste_blob.split():
            match_id = re.fullmatch(r"\d+", line)
            if match_id:
                self.main.job_data.append(Job(src_tr=src_tr, tor_id=line))
                continue
            match_url = re.search(r"https?://(.+?)/.+torrentid=(\d+)", line)
            if match_url:
                self.main.job_data.append(Job(src_dom=match_url.group(1), tor_id=match_url.group(2)))

        self.main.te_paste_box.clear()

    def open_tor_urls(self):
        for piece in self.main.result_view.toPlainText().split():
            if 'torrentid' in piece:
                webbrowser.open(piece)

    def remove_selected(self):
        selection = self.main.job_view.selected_rows()
        if not selection:
            return

        self.main.job_data.del_multi(selection)

    def delete_selected(self):
        selection = self.main.job_view.selected_rows()
        if not selection:
            return

        for i in selection:
            job = self.main.job_data.jobs[i]
            if job.scanned:
                os.remove(job.dtor_path)

        self.main.job_data.del_multi(selection)

    def open_torrent_page(self, index):
        if index.column() > 1:
            return
        job = self.main.job_data.jobs[index.row()]
        domain = tr_data[job.src_tr]['site']
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
        self.config.setValue('geometry/splitter_pos', self.main.splitter.sizes())
        self.config.setValue('geometry/job_view_header', self.main.job_view.horizontalHeader().saveState())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    app.aboutToQuit.connect(window.save_state)
    sys.exit(app.exec_())
