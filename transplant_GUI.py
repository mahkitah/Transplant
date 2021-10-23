import sys
import os
import re
import logging

import traceback
import webbrowser

from bencoder import BTFailure

from lib.transplant import Transplanter, Job
from gazelle.tracker_data import tr
from gazelle.api_classes import KeyApi, RedApi
from lib import ui_text, utils
from GUI.settings_window import SettingsWindow
from GUI.custom_gui_classes import MyTextEdit, MyHeaderView, MyTableView, JobModel, IniSettings

from PyQt5.QtWidgets import QApplication, QWidget, QTabBar, QTextBrowser, QTextEdit, QPushButton, QToolButton,\
    QRadioButton, QButtonGroup, QHBoxLayout, QVBoxLayout, QGridLayout, QFileDialog, QSplitter, QTableView, QMessageBox,\
    QHeaderView, QSizePolicy,QStackedLayout
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QObject, QSize, QThread, pyqtSignal

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

class MainWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle(ui_text.main_window_title)
        self.setWindowIcon(QIcon('gui_files/switch.svg'))

        try:
            with open('gui_files/stylesheet.qsst', 'r') as f:
                stylesheet = f.read()
            self.setStyleSheet(stylesheet)
        except FileNotFoundError:
            pass
        self.config = IniSettings("gui_files/gui_config.ini")
        self.set_window = SettingsWindow(self, self.config)
        self.job_data = JobModel(self.config)
        self.ui_elements()
        self.ui_main_layout()
        self.ui_main_connections()
        self.ui_config_connections()
        self.set_logging()
        self.load_config()
        self.set_window.load_config()
        self.show()

    def set_logging(self):
        self.report = logging.getLogger()
        self.handler = Report()
        self.report.addHandler(self.handler)
        self.handler.logging_sig.connect(self.result_view.append)

    def ui_elements(self):

        self.topwidget = QWidget()
        self.bottomwidget = QWidget()
        self.splitter = QSplitter(Qt.Vertical)
        self.section_add_dtor_btn = QWidget()

        self.tb_open_config = QToolButton()
        self.tb_open_config.setIcon(QIcon('gui_files/gear.svg'))
        self.tb_open_config.setAutoRaise(True)
        self.tb_open_config2 = QToolButton()
        self.tb_open_config2.setIcon(QIcon('gui_files/gear.svg'))
        self.tb_open_config2.setAutoRaise(True)

        self.te_paste_box = MyTextEdit()
        self.te_paste_box.setAcceptDrops(False)
        self.te_paste_box.setLineWrapMode(QTextEdit.NoWrap)
        self.te_paste_box.setPlaceholderText(ui_text.pb_placeholder)

        self.rb_tracker1 = QRadioButton(tr.RED.name)
        self.rb_tracker2 = QRadioButton(tr.OPS.name)
        self.bg_source = QButtonGroup()
        self.bg_source.addButton(self.rb_tracker1, 0)
        self.bg_source.addButton(self.rb_tracker2, 1)

        self.pb_add = QPushButton(ui_text.pb_add)
        self.pb_add.setEnabled(False)

        self.pb_open_dtors = QPushButton(ui_text.open_dtors)

        self.pb_scan = QPushButton(ui_text.pb_scan)
        self.pb_scan.setEnabled(False)

        self.job_view = MyTableView()
        self.job_view.setHorizontalHeader(MyHeaderView(Qt.Horizontal, self.job_data.headers))
        self.job_view.setEditTriggers(QTableView.SelectedClicked | QTableView.DoubleClicked | QTableView.AnyKeyPressed)
        self.job_view.setModel(self.job_data)
        self.job_view.setSelectionBehavior(QTableView.SelectRows)
        self.job_view.verticalHeader().hide()
        self.job_view.verticalHeader().setMinimumSectionSize(12)
        self.job_view.horizontalHeader().setSectionsMovable(True)
        self.job_view.horizontalHeader().setMinimumSectionSize(18)
        self.job_view.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.job_view.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.job_view.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.job_view.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)

        self.result_view = QTextBrowser()
        self.result_view.setOpenExternalLinks(True)

        self.tabs = QTabBar()
        self.tabs.setDrawBase(False)
        self.tabs.setExpanding(False)
        self.tabs.addTab(ui_text.tab_joblist)

        self.job_buttons = QWidget()
        self.result_buttons = QWidget()
        self.result_buttons.hide()
        self.pb_clear_j = QPushButton(ui_text.pb_clear)
        self.pb_clear_j.setEnabled(False)
        self.pb_clear_r = QPushButton(ui_text.pb_clear)
        self.pb_clear_r.setEnabled(False)
        self.pb_rem_sel = QPushButton(ui_text.pb_rem_sel)
        self.pb_rem_sel.setEnabled(False)
        self.pb_del_sel = QPushButton(ui_text.pb_del_sel)
        self.pb_del_sel.setEnabled(False)
        self.pb_rem_tr1 = QPushButton(ui_text.pb_del_tr1)
        self.pb_rem_tr1.setEnabled(False)
        self.pb_rem_tr2 = QPushButton(ui_text.pb_del_tr2)
        self.pb_rem_tr2.setEnabled(False)
        self.pb_open_tsavedir = QPushButton(ui_text.pb_open_tsavedir)
        self.pb_open_upl_urls = QPushButton(ui_text.pb_open_upl_urls)
        self.pb_open_upl_urls.setEnabled(False)
        self.tb_go = QToolButton()
        self.tb_go.setEnabled(False)
        self.tb_go.setIcon(QIcon('gui_files/switch.svg'))
        self.tb_go.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        self.pb_stop = QPushButton(ui_text.pb_stop)
        self.pb_stop.hide()

    def ui_main_layout(self):
        # Top
        source_area = QVBoxLayout()

        sa_topleft = QVBoxLayout()
        sa_topleft.addStretch(3)
        sa_topleft.addWidget(self.rb_tracker1)
        sa_topleft.addWidget(self.rb_tracker2)
        sa_topleft.addStretch(1)

        sa_topright = QVBoxLayout()
        sa_topright.addWidget(self.tb_open_config)
        sa_topright.addStretch()

        sa_top = QHBoxLayout()
        sa_top.addLayout(sa_topleft)
        sa_top.addLayout(sa_topright)

        source_area.addLayout(sa_top)
        source_area.addWidget(self.pb_add)

        pastebox = QVBoxLayout()
        pastebox.addSpacing(10)
        pastebox.addWidget(self.te_paste_box)

        paste_row = QHBoxLayout()
        paste_row.addLayout(pastebox)
        paste_row.addLayout(source_area)

        add_dtors = QVBoxLayout(self.section_add_dtor_btn)
        add_dtors.setContentsMargins(0, 0, 0, 0)
        add_dtors.addSpacing(10)
        add_dtors.addWidget(self.pb_open_dtors)

        top_layout = QVBoxLayout(self.topwidget)
        top_layout.addLayout(paste_row)
        top_layout.addWidget(self.section_add_dtor_btn)

        # Bottom
        scan_row = QHBoxLayout()
        scan_row.addStretch()
        scan_row.addWidget(self.pb_scan)
        scan_row.addWidget(self.tb_open_config2)

        buttons_job = QVBoxLayout(self.job_buttons)
        buttons_job.setContentsMargins(0, 0, 0, 0)
        buttons_job.addWidget(self.pb_scan)
        buttons_job.addWidget(self.pb_clear_j)
        buttons_job.addWidget(self.pb_rem_sel)
        buttons_job.addWidget(self.pb_del_sel)
        buttons_job.addWidget(self.pb_rem_tr1)
        buttons_job.addWidget(self.pb_rem_tr2)
        buttons_result = QVBoxLayout(self.result_buttons)
        buttons_result.setContentsMargins(0, 0, 0, 0)
        buttons_result.addWidget(self.pb_clear_r)
        buttons_result.addWidget(self.pb_open_upl_urls)
        buttons_result.addStretch()

        self.tab_button_stack = QStackedLayout()
        self.tab_button_stack.addWidget(self.job_buttons)
        self.tab_button_stack.addWidget(self.result_buttons)

        self.go_stop_stack = QStackedLayout()
        self.go_stop_stack.addWidget(self.tb_go)
        self.go_stop_stack.addWidget(self.pb_stop)

        control_buttons = QVBoxLayout()
        control_buttons.addLayout(self.tab_button_stack)
        control_buttons.addStretch(3)
        control_buttons.addWidget(self.pb_open_tsavedir)
        control_buttons.addStretch(1)
        control_buttons.addLayout(self.go_stop_stack)

        self.view_stack = QStackedLayout()
        self.view_stack.addWidget(self.job_view)
        self.view_stack.addWidget(self.result_view)

        open_config2 = QHBoxLayout()
        open_config2.addStretch()
        open_config2.addWidget(self.tb_open_config2)

        view_n_buttons = QGridLayout()
        view_n_buttons.setVerticalSpacing(0)
        view_n_buttons.addLayout(open_config2, 0, 1)
        view_n_buttons.addWidget(self.tabs, 0, 0)
        view_n_buttons.addLayout(self.view_stack, 1, 0)
        view_n_buttons.addLayout(control_buttons, 1, 1)
        view_n_buttons.setColumnStretch(0, 1)
        view_n_buttons.setColumnStretch(1, 0)

        bottom_layout = QVBoxLayout(self.bottomwidget)
        bottom_layout.addLayout(view_n_buttons)

        splitter = self.splitter
        splitter.addWidget(self.topwidget)
        splitter.addWidget(self.bottomwidget)
        splitter.setCollapsible(1, False)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        total_layout = QHBoxLayout(self)
        total_layout.setContentsMargins(0, 0, 0, 0)
        total_layout.addWidget(splitter)

    def ui_main_connections(self):
        self.te_paste_box.plainTextChanged.connect(lambda x: self.pb_add.setEnabled(bool(x)))
        self.bg_source.idClicked.connect(lambda x: self.config.setValue('bg_source', x))
        self.pb_add.clicked.connect(self.parse_paste_input)
        self.pb_open_dtors.clicked.connect(self.select_dtors)
        self.pb_scan.clicked.connect(self.scan_dtorrents)
        self.pb_clear_j.clicked.connect(self.job_data.clear)
        self.pb_clear_r.clicked.connect(self.result_view.clear)
        self.pb_rem_sel.clicked.connect(self.remove_selected)
        self.pb_del_sel.clicked.connect(self.delete_selected)
        self.pb_rem_tr1.clicked.connect(lambda: self.job_data.filter_for_attr('src_tr', tr.RED))
        self.pb_rem_tr2.clicked.connect(lambda: self.job_data.filter_for_attr('src_tr', tr.OPS))
        self.pb_open_tsavedir.clicked.connect(lambda: utils.open_local_folder(self.config.value('le_dtor_save_dir')))
        # self.tb_go.clicked.connect(self.gogogo)
        self.tb_go.clicked.connect(self.blabla)
        self.pb_open_upl_urls.clicked.connect(self.open_tor_urls)
        self.job_view.horizontalHeader().sectionDoubleClicked.connect(self.job_data.header_double_clicked)
        self.job_view.selectionChange.connect(lambda x: self.pb_rem_sel.setEnabled(bool(x)))
        self.job_view.selectionChange.connect(lambda x: self.pb_del_sel.setEnabled(bool(x)))
        self.job_data.layoutChanged.connect(self.job_view.clearSelection)
        self.job_data.layoutChanged.connect(lambda: self.tb_go.setEnabled(bool(self.job_data)))
        self.job_data.layoutChanged.connect(lambda: self.pb_clear_j.setEnabled(bool(self.job_data)))
        self.job_data.layoutChanged.connect(
            lambda: self.pb_rem_tr1.setEnabled(any(j.src_tr == tr.RED for j in self.job_data)))
        self.job_data.layoutChanged.connect(
            lambda: self.pb_rem_tr2.setEnabled(any(j.src_tr == tr.OPS for j in self.job_data)))
        self.result_view.textChanged.connect(lambda: self.pb_clear_r.setEnabled(bool(self.result_view.toPlainText())))
        self.result_view.textChanged.connect(
            lambda: self.pb_open_upl_urls.setEnabled('torrentid' in self.result_view.toPlainText()))
        self.tb_open_config.clicked.connect(self.set_window.open)
        self.tb_open_config2.clicked.connect(self.tb_open_config.click)
        self.splitter.splitterMoved.connect(lambda x, y: self.tb_open_config2.setHidden(bool(x)))
        self.tabs.currentChanged.connect(self.view_stack.setCurrentIndex)
        self.view_stack.currentChanged.connect(self.tabs.setCurrentIndex)
        self.view_stack.currentChanged.connect(self.tab_button_stack.setCurrentIndex)

    def ui_config_connections(self):
        self.set_window.pb_def_descr.clicked.connect(self.default_descr)
        self.set_window.pb_ok.clicked.connect(self.settings_check)
        self.set_window.pb_cancel.clicked.connect(self.set_window.reject)
        self.set_window.accepted.connect(
            lambda: self.config.setValue('geometry/config_window_size', self.set_window.size()))
        self.set_window.ac_select_datadir.triggered.connect(self.select_datadir)
        self.set_window.ac_select_scandir.triggered.connect(self.select_scan_dir)
        self.set_window.ac_select_torsave.triggered.connect(self.select_torsave)
        self.set_window.le_scan_dir.textChanged.connect(lambda: self.pb_scan.setEnabled(bool(self.set_window.le_scan_dir.text())))
        self.set_window.le_dtor_save_dir.textChanged.connect(lambda x: self.pb_open_tsavedir.setEnabled(bool(x)))
        self.set_window.chb_show_tips.stateChanged.connect(self.tooltips)
        self.set_window.spb_verbosity.valueChanged.connect(self.set_verbosity)
        self.set_window.chb_show_add_dtors.stateChanged.connect(lambda x: self.section_add_dtor_btn.setVisible(x)),
        self.set_window.chb_show_rem_tr1.stateChanged.connect(lambda x: self.pb_rem_tr1.setVisible(x)),
        self.set_window.chb_show_rem_tr2.stateChanged.connect(lambda x: self.pb_rem_tr2.setVisible(x)),
        self.set_window.chb_no_icon.stateChanged.connect(self.job_data.layoutChanged.emit)
        self.set_window.spb_splitter_weight.valueChanged.connect(self.splitter.setHandleWidth)
        self.set_window.chb_alt_row_colour.stateChanged.connect(self.job_view.setAlternatingRowColors)
        self.set_window.chb_show_grid.stateChanged.connect(self.job_view.setShowGrid)
        self.set_window.chb_show_grid.stateChanged.connect(self.job_data.layoutChanged.emit)
        self.set_window.spb_row_height.valueChanged.connect(self.job_view.verticalHeader().setDefaultSectionSize)

    def load_config(self):
        source_id = int(self.config.value('bg_source', defaultValue=0))
        self.bg_source.buttons()[source_id].click()
        self.resize(self.config.value('geometry/size', defaultValue=QSize(550, 500)))

        try:
            self.move(self.config.value('geometry/position'))
        except TypeError:
            pass

        splittersizes = [int(x) for x in self.config.value('geometry/splitter_pos', defaultValue=[150, 345])]
        self.splitter.setSizes(splittersizes)
        self.splitter.splitterMoved.emit(splittersizes[0], 1)
        try:
            self.job_view.horizontalHeader().restoreState(self.config.value('geometry/header'))
        except TypeError:
            self.job_view.horizontalHeader().set_all_sections_visible()

    def tooltips(self, flag):

        for t_name, ttip in vars(ui_text).items():
            if t_name.startswith('tt_'):
                obj_name = t_name.split('_', maxsplit=1)[1]
                try:
                    obj = getattr(self, obj_name)
                except AttributeError:
                    obj = getattr(self.set_window, obj_name)
                obj.setToolTip(ttip if flag else '')

        self.splitter.handle(1).setToolTip(ui_text.ttm_splitter if flag else '')

    def blabla(self, *args):
        self.report.info('blabla\n')
        from testzooi.testrun import testrun
        testrun(self)
        pass

    def gogogo(self):
        if not self.job_data:
            return

        min_req_config = ("le_key_1", "le_key_2", "le_data_dir")
        if not all(self.config.value(x) for x in min_req_config):
            self.set_window.open()
            return

        key_1 = self.config.value('le_key_1')
        key_2 = self.config.value('le_key_2')

        settings = self.trpl_settings()

        if self.tabs.count() == 1:
            self.tabs.addTab(ui_text.tab_results)
        self.tabs.setCurrentIndex(1)

        self.tr_thread = TransplantThread(self.job_data.jobs.copy(), key_1, key_2, settings)

        self.pb_stop.clicked.connect(self.tr_thread.stop)
        self.tr_thread.started.connect(lambda: self.report.info(ui_text.start))
        self.tr_thread.started.connect(lambda: self.go_stop_stack.setCurrentIndex(1))
        self.tr_thread.finished.connect(lambda: self.report.info(ui_text.thread_finish))
        self.tr_thread.finished.connect(lambda: self.go_stop_stack.setCurrentIndex(0))
        self.tr_thread.upl_succes.connect(self.job_data.remove)
        self.tr_thread.start()

    def select_datadir(self):
        d_dir = QFileDialog.getExistingDirectory(self, ui_text.tt_ac_select_datadir, self.config.value('le_data_dir'))
        if not d_dir:
            return
        d_dir = os.path.normpath(d_dir)
        self.set_window.le_data_dir.setText(d_dir)

    def select_torsave(self):
        t_dir = QFileDialog.getExistingDirectory(self, ui_text.tt_ac_select_torsave,
                                                 self.config.value('le_dtor_save_dir'))
        if not t_dir:
            return
        t_dir = os.path.normpath(t_dir)
        self.set_window.le_dtor_save_dir.setText(t_dir)

    def select_dtors(self):

        file_paths = QFileDialog.getOpenFileNames(self, ui_text.sel_dtors_window_title,
                                                  self.config.value('torselect_dir'),
                                                  "torrents (*.torrent);;All Files (*)")[0]
        if not file_paths:
            return

        self.tabs.setCurrentIndex(0)
        if len(file_paths) > 1:
            common_path = os.path.commonpath(file_paths)
        else:
            common_path = os.path.dirname(file_paths[0])

        self.config.setValue('torselect_dir', os.path.normpath(common_path))

        for p in file_paths:
            if os.path.isfile(p) and p.endswith(".torrent"):
                try:
                    self.job_data.append(Job(dtor_path=p))
                except (AssertionError, BTFailure):
                    continue

    def scan_dtorrents(self):
        path = self.config.value('le_scan_dir')
        if path and os.path.isdir(path):
            self.tabs.setCurrentIndex(0)

            for scan in os.scandir(path):
                if scan.is_file() and scan.name.endswith(".torrent"):
                    try:
                        self.job_data.append(Job(dtor_path=scan.path, scanned=True))
                    except (AssertionError, BTFailure):
                        continue

    def settings_check(self):
        data_dir = self.config.value('le_data_dir')
        dtor_save_dir = self.config.value('le_dtor_save_dir')
        save_dtors = self.config.value('chb_save_dtors')
        rehost = self.config.value('chb_rehost')
        ptpimg_key = self.config.value('le_ptpimg_key')
        add_src_descr = self.config.value('chb_add_src_descr')

        sum_ting_wong = []
        if not os.path.isdir(data_dir):
            sum_ting_wong.append(ui_text.sum_ting_wong_1)
        if save_dtors and not os.path.isdir(dtor_save_dir):
            sum_ting_wong.append(ui_text.sum_ting_wong_2)
        if rehost and not ptpimg_key:
            sum_ting_wong.append(ui_text.sum_ting_wong_3)
        if add_src_descr and '%src_descr%' not in self.set_window.te_src_descr_templ.toPlainText():
            sum_ting_wong.append(ui_text.sum_ting_wong_4)

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

        paste_blob = self.te_paste_box.toPlainText()
        if not paste_blob:
            return

        self.tabs.setCurrentIndex(0)
        tr_map = {0: tr.RED, 1: tr.OPS}
        src_tr = tr_map.get(self.config.value('bg_source'))

        for line in paste_blob.split():
            match_id = re.fullmatch(r"\d+", line)
            if match_id:
                self.job_data.append(Job(src_tr=src_tr, tor_id=line))
                continue
            match_url = re.search(r"https?://(.+?)/.+torrentid=(\d+)", line)
            if match_url:
                self.job_data.append(Job(src_dom=match_url.group(1), tor_id=match_url.group(2)))

        self.te_paste_box.clear()

    def open_tor_urls(self):
        for word in self.result_view.toPlainText().split():
            if 'torrentid' in word:
                webbrowser.open(word)

    def remove_selected(self):
        selected_rows = list(set((x.row() for x in self.job_view.selectedIndexes())))
        if not selected_rows:
            return

        self.job_data.del_multi(selected_rows)

    def delete_selected(self):
        selected_rows = list(set((x.row() for x in self.job_view.selectedIndexes())))
        if not selected_rows:
            return

        for i in selected_rows:
            job = self.job_data.jobs[i]
            if job.scanned:
                os.remove(job.dtor_path)

        self.job_data.del_multi(selected_rows)

    def select_scan_dir(self):
        s_dir = QFileDialog.getExistingDirectory(self, ui_text.tt_ac_select_scandir, self.config.value('le_scan_dir'))
        if not s_dir:
            return
        s_dir = os.path.normpath(s_dir)
        self.set_window.le_scan_dir.setText(s_dir)

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
        self.config.setValue('geometry/splitter_pos', self.splitter.sizes())
        self.config.setValue('geometry/header', self.job_view.horizontalHeader().saveState())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    app.aboutToQuit.connect(window.save_state)
    sys.exit(app.exec_())
