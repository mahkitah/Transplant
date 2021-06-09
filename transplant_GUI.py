import sys
import os
import re
import traceback

from bencoder import BTFailure

from lib.transplant import Transplanter, Job
from lib.gazelle_api import GazelleApi
from lib import constants, ui_text, utils

from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QTabWidget, QTextBrowser, QTextEdit, QLineEdit, QPushButton,\
    QToolButton, QRadioButton, QButtonGroup, QHBoxLayout, QVBoxLayout, QFormLayout, QSpinBox, QCheckBox, \
    QFileDialog, QAction, QSplitter, QListView, QAbstractItemView, QDialog, QMessageBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QSettings, QAbstractListModel, QSize, QThread, pyqtSignal


# noinspection PyBroadException
class TransplantThread(QThread):
    feedback = pyqtSignal(str, int)

    def __init__(self, job_data, key_1, key_2):
        super().__init__()
        self.go_on = True
        self.job_data = job_data
        self.key_1 = key_1
        self.key_2 = key_2
        self.stop_run = False

    def stop(self):
        self.stop_run = True

    def run(self):
        def report_back(msg, msg_verb):
            self.feedback.emit(msg, msg_verb)

        api_map = {'RED': GazelleApi("RED", self.key_1, report=report_back),
                   'OPS': GazelleApi("OPS", f"token {self.key_2}", report=report_back)}

        for job in self.job_data:
            if self.stop_run:
                break

            try:
                operation = Transplanter(job, api_map, report=report_back)
                operation.transplant()
            except Exception:
                self.feedback.emit(traceback.format_exc(), 1)
                continue

            if job.upl_succes:
                try:
                    if job.save_dtors:
                        job.save_dtorrent()
                        self.feedback.emit(f"{ui_text.dtor_saved} {job.dtor_save_dir}", 2)
                except Exception:
                    self.feedback.emit(traceback.format_exc(), 1)
                try:
                    if job.del_dtors:
                        os.remove(job.dtor_path)
                        self.feedback.emit(f"{ui_text.dtor_deleted}", 2)

                except Exception:
                    self.feedback.emit(traceback.format_exc(), 1)


class MainWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle(ui_text.main_window_title)
        self.setWindowIcon(QIcon('gui_files/switch.svg'))
        self.job_data = JobModel()
        self.ui_main_elements()
        self.ui_main_layout()
        self.ui_settings_elements()
        self.ui_settings_layout()
        self.ui_main_connections()
        self.ui_settings_connections()
        self.settings = QSettings("gui_files/gui.ini", QSettings.IniFormat)
        self.load_main_settings()
        self.load_settings_settings()

        self.show()

    def ui_main_elements(self):

        self.topwidget = QWidget()
        self.bottomwidget = QWidget()
        self.splitter = QSplitter(Qt.Vertical)

        self.tb_settings = QToolButton()
        self.tb_settings.setIcon(QIcon('gui_files/gear.svg'))
        self.tb_settings.setAutoRaise(True)

        self.te_paste_box = QTextEdit()
        self.te_paste_box.setAcceptDrops(False)
        self.te_paste_box.setLineWrapMode(QTextEdit.NoWrap)
        self.te_paste_box.setPlaceholderText(ui_text.pb_placeholder)

        self.rb_RED = QRadioButton(ui_text.tracker_1)
        self.rb_OPS = QRadioButton(ui_text.tracker_2)
        self.source_b_group = QButtonGroup()
        self.source_b_group.addButton(self.rb_RED, 0)
        self.source_b_group.addButton(self.rb_OPS, 1)

        self.pb_add = QPushButton(ui_text.pb_add)
        self.pb_add.setEnabled(False)

        self.pb_open_dtors = QPushButton(ui_text.open_dtors)

        self.ac_select_scandir = QAction()
        self.ac_select_scandir.setIcon(QIcon("gui_files/open-folder.svg"))
        self.le_scandir = QLineEdit()
        self.le_scandir.setPlaceholderText(ui_text.tt_select_scandir)
        self.pb_scan = QPushButton(ui_text.pb_scan)
        self.pb_scan.setEnabled(False)

        self.job_view = QListView()
        self.job_view.setContentsMargins(0, 0, 0, 0)
        self.job_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.job_view.setAlternatingRowColors(True)
        self.result_view = QTextBrowser()
        self.result_view.setOpenExternalLinks(True)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self.job_view, ui_text.tab_joblist)

        self.pb_clear = QPushButton(ui_text.pb_clear)
        self.pb_rem_sel = QPushButton(ui_text.pb_rem_sel)
        self.pb_del_sel = QPushButton(ui_text.pb_del_sel)
        self.pb_open_tsavedir = QPushButton(ui_text.pb_open_tsavedir)
        self.pb_go = QPushButton(ui_text.pb_go)
        self.pb_go.setEnabled(False)
        self.pb_stop = QPushButton('stop')
        self.pb_stop.hide()

    def ui_main_layout(self):
        # Top
        source_area = QVBoxLayout()

        sa_topleft = QVBoxLayout()
        sa_topleft.addStretch(3)
        sa_topleft.addWidget(self.rb_RED)
        sa_topleft.addWidget(self.rb_OPS)
        sa_topleft.addStretch(1)

        sa_topright = QVBoxLayout()
        sa_topright.addWidget(self.tb_settings)
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

        top_layout = QVBoxLayout(self.topwidget)
        top_layout.addLayout(paste_row)
        top_layout.addSpacing(10)
        top_layout.addWidget(self.pb_open_dtors)

        # Bottom
        scan_row = QHBoxLayout()
        self.le_scandir.addAction(self.ac_select_scandir, QLineEdit.TrailingPosition)
        scan_row.addWidget(self.le_scandir)
        scan_row.addWidget(self.pb_scan)

        self.control_buttons = QVBoxLayout()
        control_buttons = self.control_buttons
        control_buttons.addSpacing(20)
        control_buttons.addWidget(self.pb_clear)
        control_buttons.addWidget(self.pb_rem_sel)
        control_buttons.addWidget(self.pb_del_sel)
        control_buttons.addStretch(3)
        control_buttons.addWidget(self.pb_open_tsavedir)
        control_buttons.addStretch(1)
        control_buttons.addWidget(self.pb_go)
        control_buttons.addWidget(self.pb_stop)

        view_n_buttons = QHBoxLayout()
        view_n_buttons.addWidget(self.tabs)
        view_n_buttons.addLayout(control_buttons)

        bottom_layout = QVBoxLayout(self.bottomwidget)
        bottom_layout.addLayout(scan_row)
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
        self.job_view.setModel(self.job_data)
        self.te_paste_box.textChanged.connect(lambda: self.enable_button(self.pb_add, bool(self.te_paste_box.toPlainText())))
        self.source_b_group.idClicked.connect(self.set_source)
        self.pb_add.clicked.connect(self.parse_paste_input)
        self.pb_open_dtors.clicked.connect(self.select_dtors)
        self.pb_scan.clicked.connect(self.scan_dtorrents)
        self.pb_clear.clicked.connect(self.clear_button)
        self.pb_rem_sel.clicked.connect(self.remove_selected)
        self.pb_del_sel.clicked.connect(self.delete_selected)
        self.pb_open_tsavedir.clicked.connect(lambda: utils.open_local_folder(self.settings.value('settings/dtor_save_dir')))
        self.le_scandir.textChanged.connect(lambda: self.enable_button(self.pb_scan, bool(self.le_scandir.text())))
        self.ac_select_scandir.triggered.connect(self.select_scan_dir)
        self.job_data.layoutChanged.connect(lambda: self.enable_button(self.pb_go, bool(self.job_data)))
        # self.job_view.selectionChanged()
        self.tb_settings.clicked.connect(self.settings_window.open)
        self.pb_go.clicked.connect(self.gogogo)
        # self.pb_go.clicked.connect(self.slot_blabla)
        self.tabs.currentChanged.connect(self.tabs_clicked)

    def ui_settings_elements(self):
        self.settings_window = QDialog(self)
        self.settings_window.setWindowTitle(ui_text.s_window_title)
        self.settings_window.setWindowIcon(QIcon('gui_files/gear.svg'))

        self.le_key_1 = QLineEdit()
        self.l_key_1 = QLabel(ui_text.l_key_1)
        self.le_key_2 = QLineEdit()
        self.l_key_2 = QLabel(ui_text.l_key_2)
        self.le_data_dir = QLineEdit()
        self.l_data_dir = QLabel(ui_text.l_data_dir)
        self.le_tor_save_dir = QLineEdit()
        self.l_tor_save_dir = QLabel(ui_text.l_tor_save_dir)
        self.chb_save_dtors = QCheckBox()
        self.chb_del_dtors = QCheckBox()
        self.l_del_dtors = QLabel(ui_text.l_del_dtors)
        self.chb_file_check = QCheckBox()
        self.l_file_check = QLabel(ui_text.l_file_check)
        self.chb_show_tips = QCheckBox()
        self.l_show_tips = QLabel(ui_text.l_show_tips)
        self.l_verbosity = QLabel(ui_text.l_verbosity)
        self.spb_verbosity = QSpinBox()
        self.spb_verbosity.setMaximum(5)
        self.spb_verbosity.setMaximumWidth(40)
        self.chb_rehost = QCheckBox()
        self.l_rehost = QLabel(ui_text.l_rehost)
        self.le_whitelist = QLineEdit()
        self.l_whitelist = QLabel(ui_text.l_whitelist)
        self.le_ptpimg_key = QLineEdit()
        self.l_ptpimg_key = QLabel(ui_text.l_ptpimg_key)
        self.pb_cancel = QPushButton(ui_text.pb_cancel)
        self.pb_ok = QPushButton(ui_text.pb_ok)
        self.ac_select_datadir = QAction()
        self.ac_select_datadir.setIcon(QIcon("gui_files/open-folder.svg"))
        self.ac_select_torsave = QAction()
        self.ac_select_torsave.setIcon(QIcon("gui_files/open-folder.svg"))

    def ui_settings_layout(self):
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        bottom_row.addWidget(self.pb_cancel)
        bottom_row.addWidget(self.pb_ok)

        self.le_data_dir.addAction(self.ac_select_datadir, QLineEdit.TrailingPosition)
        self.le_tor_save_dir.addAction(self.ac_select_torsave, QLineEdit.TrailingPosition)

        save_dtor = QHBoxLayout()
        save_dtor.addWidget(self.chb_save_dtors)
        save_dtor.addWidget(self.le_tor_save_dir)

        self.settings_form = QFormLayout()
        settings_form = self.settings_form
        settings_form.setLabelAlignment(Qt.AlignRight)
        settings_form.setVerticalSpacing(20)
        settings_form.setHorizontalSpacing(20)
        settings_form.addRow(self.l_key_1, self.le_key_1)
        settings_form.addRow(self.l_key_2, self.le_key_2)
        settings_form.addRow(self.l_data_dir, self.le_data_dir)
        settings_form.addRow(self.l_tor_save_dir, save_dtor)
        settings_form.addRow(self.l_del_dtors, self.chb_del_dtors)
        settings_form.addRow(self.l_file_check, self.chb_file_check)
        settings_form.addRow(self.l_show_tips, self.chb_show_tips)
        settings_form.addRow(self.l_verbosity, self.spb_verbosity)
        settings_form.addRow(self.l_rehost, self.chb_rehost)
        settings_form.addRow(self.l_whitelist, self.le_whitelist)
        settings_form.addRow(self.l_ptpimg_key, self.le_ptpimg_key)

        total_layout = QVBoxLayout(self.settings_window)
        total_layout.addLayout(settings_form)
        total_layout.addSpacing(20)
        total_layout.addLayout(bottom_row)

    def ui_settings_connections(self):
        self.pb_ok.clicked.connect(self.settings_check)
        self.pb_cancel.clicked.connect(self.settings_window.reject)
        self.settings_window.accepted.connect(self.save_settings)
        self.settings_window.accepted.connect(lambda: self.enable_button(self.pb_open_tsavedir, bool(self.le_tor_save_dir.text())))
        self.settings_window.rejected.connect(self.load_settings_settings)
        self.ac_select_datadir.triggered.connect(self.select_datadir)
        self.ac_select_torsave.triggered.connect(self.select_torsave)

    def tooltips(self, flag):
        tiplist = (
            (self.rb_RED, ui_text.tt_source_buts),
            (self.rb_OPS, ui_text.tt_source_buts),
            (self.pb_add, ui_text.tt_add_but),
            (self.pb_open_dtors, ui_text.tt_add_dtors_but),
            (self.le_scandir, ui_text.tt_scandir),
            (self.ac_select_scandir, ui_text.tt_select_scandir),
            (self.pb_scan, ui_text.tt_scan_but),
            (self.pb_clear, ui_text.tt_clear_but),
            (self.pb_rem_sel, ui_text.tt_rem_sel_but),
            (self.pb_del_sel, ui_text.tt_del_sel_but),
            (self.pb_open_tsavedir, ui_text.tt_open_tsavedir),
            (self.pb_go, ui_text.tt_go_but),

            (self.tb_settings, ui_text.s_window_title),
            (self.l_key_1, ui_text.tt_keys),
            (self.l_key_2, ui_text.tt_keys),
            (self.l_data_dir, ui_text.tt_data_dir),
            (self.ac_select_datadir, ui_text.tt_sel_ddir),
            (self.l_tor_save_dir, ui_text.tt_dtor_save_dir),
            (self.ac_select_torsave, ui_text.tt_sel_dtor_save_dir),
            (self.l_del_dtors, ui_text.tt_del_dtors),
            (self.l_file_check, ui_text.tt_check_files),
            (self.l_show_tips, ui_text.tt_show_tips),
            (self.l_verbosity, ui_text.tt_verbosity),
            (self.l_rehost, ui_text.tt_rehost),
            (self.l_whitelist, ui_text.tt_whitelist)
        )
        for x in tiplist:
            x[0].setToolTip(x[1] if flag else '')

    def slot_blabla(self):
        print('blabla')

    @staticmethod
    def enable_button(button, flag):
        button.setEnabled(flag)

    def select_datadir(self):
        d_dir = QFileDialog.getExistingDirectory(self, ui_text.tt_sel_ddir, self.settings.value('settings/data_dir'))
        if not d_dir:
            return
        d_dir = os.path.normpath(d_dir)
        self.settings.setValue('settings/data_dir', d_dir)
        self.le_data_dir.setText(d_dir)

    def select_torsave(self):
        t_dir = QFileDialog.getExistingDirectory(self, ui_text.tt_sel_dtor_save_dir, self.settings.value('settings/dtor_save_dir'))
        if not t_dir:
            return
        t_dir = os.path.normpath(t_dir)
        self.settings.setValue('settings/dtor_save_dir', t_dir)
        self.le_tor_save_dir.setText(t_dir)

    def settings_check(self):
        data_dir = self.le_data_dir.text()
        tor_save_dir = self.le_tor_save_dir.text()
        save_dtors = self.chb_save_dtors.isChecked()
        rehost = self.chb_rehost.isChecked()
        ptpimg_key = self.le_ptpimg_key.text()

        sum_ting_wong = []
        if not os.path.isdir(data_dir):
            sum_ting_wong.append('Invalid data folder')
        if save_dtors and not os.path.isdir(tor_save_dir):
            sum_ting_wong.append('Invalid torrent save folder')
        if rehost and not ptpimg_key:
            sum_ting_wong.append('No PTPimg API-key')

        if sum_ting_wong:
            warning = QMessageBox()
            warning.setIcon(QMessageBox.Warning)
            warning.setText("- " + "\n- ".join(sum_ting_wong))
            warning.exec()
            return
        else:
            self.settings_window.accept()

    def tabs_clicked(self, index):
        if index == 0:
            self.pb_rem_sel.setEnabled(True)
        else:
            self.pb_rem_sel.setEnabled(False)

    def set_source(self, id):
        self.settings.setValue('state/source', id)

    def parse_paste_input(self):

        paste_blob = self.te_paste_box.toPlainText()
        if not paste_blob:
            return

        self.tabs.setCurrentIndex(0)

        split = re.split("[\n\s]", paste_blob)

        if self.settings.value('state/source') == 0:
            src_id = ui_text.tracker_1
        elif self.settings.value('state/source') == 1:
            src_id = ui_text.tracker_2
        else:
            src_id = None

        for line in split:
            match_id = re.fullmatch(r"\d+", line)
            if match_id:
                self.job_data.append(Job(src_id=src_id, tor_id=line))
                continue
            match_url = re.search(r"https?://(.+?)/.+torrentid=(\d+)", line)
            if match_url:
                domain = match_url.group(1)
                tor_id = match_url.group(2)
                url_id = constants.SITE_ID_MAP[domain]
                self.job_data.append(Job(src_id=url_id, tor_id=tor_id))
        self.te_paste_box.clear()

    def select_dtors(self):

        file_paths = QFileDialog.getOpenFileNames(self, ui_text.sel_dtors_window_title,
                                                  self.settings.value('history/torselect_dir'),
                                                  "torrents (*.torrent);;All Files (*)")[0]
        if not file_paths:
            return

        self.tabs.setCurrentIndex(0)
        if len(file_paths) > 1:
            common_path = os.path.commonpath(file_paths)
        else:
            common_path = os.path.dirname(file_paths[0])

        self.settings.setValue('history/torselect_dir', os.path.normpath(common_path))

        for p in file_paths:
            if os.path.isfile(p) and p.endswith(".torrent"):
                try:
                    self.job_data.append(Job(dtor_path=p))
                except (AssertionError, BTFailure):
                    continue

    def scan_dtorrents(self):

        path = self.le_scandir.text()
        if path and os.path.isdir(path):
            self.tabs.setCurrentIndex(0)

            del_dtors = bool(int(self.settings.value('settings/del_dtors', defaultValue=False)))

            for i in os.scandir(self.le_scandir.text()):
                if i.is_file() and i.name.endswith(".torrent"):
                    try:
                        self.job_data.append(Job(dtor_path=i.path, del_dtors=del_dtors))
                    except (AssertionError, BTFailure):
                        continue
            self.settings.setValue('history/scan_dir', os.path.normpath(path))

    def clear_button(self):
        # job list
        if self.tabs.currentIndex() == 0:
            self.job_data.clear()

        # results
        if self.tabs.currentIndex() == 1:
            self.result_view.clear()

    def remove_selected(self):
        indices = self.job_view.selectedIndexes()
        if indices:
            indices.sort(reverse=True)
            for i in indices:
                self.job_data.remove(i.row())
            self.job_view.clearSelection()

    def delete_selected(self):
        indices = self.job_view.selectedIndexes()
        if indices:
            indices.sort(reverse=True)
            for i in indices:
                job = self.job_data.jobs[i.row()]
                if job.dtor_path and job.dtor_path.startswith(self.le_scandir.text()):
                    os.remove(job.dtor_path)
                    self.job_data.remove(i.row())
                    self.job_view.clearSelection()

    def select_scan_dir(self):
        s_dir = QFileDialog.getExistingDirectory(self, ui_text.tt_select_scandir, self.settings.value('history/scan_dir'))
        if not s_dir:
            return
        s_dir = os.path.normpath(s_dir)
        self.settings.setValue('history/scan_dir', s_dir)
        self.le_scandir.setText(s_dir)

    @staticmethod
    def switch_buttons(but1, but2, flag):
        if flag:
            but1.setVisible(False)
            but2.setVisible(True)
        else:
            but1.setVisible(True)
            but2.setVisible(False)

    def gogogo(self):
        if not self.job_data:
            return

        min_req_config = ("settings/key_1", "settings/key_2", "settings/data_dir")
        if not all(self.settings.value(x) for x in min_req_config):
            self.settings_window.open()
            return

        job_user_settings = self.load_job_user_settings()
        for job in self.job_data:
            job.update(job_user_settings)

        key_1 = self.settings.value('settings/key_1')
        key_2 = self.settings.value('settings/key_2')

        if self.tabs.count() == 1:
            self.tabs.addTab(self.result_view, ui_text.tab_results)
        self.tabs.setCurrentIndex(1)

        self.tr_thread = TransplantThread(self.job_data, key_1, key_2)

        self.pb_stop.clicked.connect(self.tr_thread.stop)
        self.tr_thread.started.connect(lambda: self.show_feedback(ui_text.start, 2))
        self.tr_thread.started.connect(lambda: self.switch_buttons(self.pb_go, self.pb_stop, True))
        self.tr_thread.finished.connect(lambda: self.show_feedback(ui_text.thread_finish, 2))
        self.tr_thread.finished.connect(lambda: self.switch_buttons(self.pb_go, self.pb_stop, False))
        self.tr_thread.finished.connect(self.job_data.remove_finished)
        self.tr_thread.feedback.connect(self.show_feedback)
        self.tr_thread.start()

    def show_feedback(self, msg, msg_verb):
        if msg_verb <= int(self.settings.value('settings/verbosity')):
            repl = re.sub(r'(https?://[^\s\n\r]+)', r'<a href="\1">\1</a> ', msg)

            self.result_view.append(repl)

    def load_main_settings(self):
        self.le_scandir.setText(self.settings.value('history/scan_dir'))
        source_id = int(self.settings.value('state/source', defaultValue=0))
        self.source_b_group.buttons()[source_id].click()
        self.resize(self.settings.value('geometry/size', defaultValue=QSize(450, 500)))
        win_pos = self.settings.value('geometry/position')
        if win_pos:
            self.move(win_pos)
        splittersizes = [int(x) for x in self.settings.value('geometry/splitter_pos', defaultValue=[150, 345])]
        self.splitter.setSizes(splittersizes)

    def save_settings(self):
        data_dir = self.le_data_dir.text()
        tor_save_dir = self.le_tor_save_dir.text()
        tt_state_before = int(self.settings.value('settings/show_tips', defaultValue=1))

        self.settings.setValue('settings/key_1', self.le_key_1.text())
        self.settings.setValue('settings/key_2', self.le_key_2.text())
        self.settings.setValue('settings/data_dir', os.path.normpath(data_dir) if data_dir else data_dir)
        self.settings.setValue('settings/dtor_save_dir', os.path.normpath(tor_save_dir) if tor_save_dir else tor_save_dir)
        self.settings.setValue('settings/save_dtors', int(self.chb_save_dtors.isChecked()))
        self.settings.setValue('settings/del_dtors', int(self.chb_del_dtors.isChecked()))
        self.settings.setValue('settings/file_check', int(self.chb_file_check.isChecked()))
        self.settings.setValue('settings/show_tips', int(self.chb_show_tips.isChecked()))
        self.settings.setValue('settings/verbosity', self.spb_verbosity.value())
        self.settings.setValue('settings/rehost', int(self.chb_rehost.isChecked()))
        self.settings.setValue('settings/whitelist', self.le_whitelist.text())
        self.settings.setValue('settings/ptpimg_key', self.le_ptpimg_key.text())
        self.settings.setValue('settings/window_size', self.settings_window.size())

        tt_state_after = int(self.settings.value('settings/show_tips'))
        if tt_state_before != tt_state_after:
            self.tooltips(bool(tt_state_after))

    def load_settings_settings(self):
        self.le_key_1.setText(self.settings.value('settings/key_1'))
        self.le_key_2.setText(self.settings.value('settings/key_2'))
        self.le_data_dir.setText(self.settings.value('settings/data_dir'))
        self.le_tor_save_dir.setText(self.settings.value('settings/dtor_save_dir'))

        self.chb_save_dtors.setChecked(bool(int(self.settings.value('settings/save_dtors',
                                                                    defaultValue=bool(
                                                                        self.settings.value('settings/dtor_save_dir'))))))
        self.chb_del_dtors.setChecked(bool(int(self.settings.value('settings/del_dtors', defaultValue=0))))
        self.chb_file_check.setChecked(bool(int(self.settings.value('settings/file_check', defaultValue=1))))
        self.chb_show_tips.setChecked(bool(int(self.settings.value('settings/show_tips', defaultValue=1))))
        self.spb_verbosity.setValue(int(self.settings.value('settings/verbosity', defaultValue=2)))
        self.chb_rehost.setChecked(bool(int(self.settings.value('settings/rehost', defaultValue=0))))
        self.le_whitelist.setText(self.settings.value('settings/whitelist', defaultValue=ui_text.default_whitelist))
        self.le_ptpimg_key.setText(self.settings.value('settings/ptpimg_key'))

        if bool(int(self.settings.value('settings/show_tips', defaultValue=1))):
            self.tooltips(True)

        self.le_key_1.setCursorPosition(0)
        self.le_key_2.setCursorPosition(0)
        self.enable_button(self.pb_open_tsavedir, bool(self.le_tor_save_dir.text()))

        winsize = self.settings.value('settings/window_size')
        if winsize:
            self.settings_window.resize(winsize)

    def load_job_user_settings(self):
        user_settings = {
            'data_dir': self.settings.value('settings/data_dir'),
            'dtor_save_dir': self.settings.value('settings/dtor_save_dir', defaultValue=None),
            'save_dtors': bool(int(self.settings.value('settings/save_dtors', defaultValue=False))),
            'file_check': bool(int(self.settings.value('settings/file_check', defaultValue=True))),
        }
        if bool(int(self.settings.value('settings/rehost'))):
            whitelist = []
            white_str_nospace = ''.join(self.settings.value('settings/whitelist').split())
            if white_str_nospace:
                whitelist.extend(white_str_nospace.split(','))

            user_settings.update(img_rehost=True,
                                 whitelist=whitelist,
                                 ptpimg_key=self.settings.value('settings/ptpimg_key'))
        return user_settings

    def save_state(self):
        self.settings.setValue('geometry/size', self.size())
        self.settings.setValue('geometry/position', self.pos())
        self.settings.setValue('geometry/splitter_pos', self.splitter.sizes())


class JobModel(QAbstractListModel):
    def __init__(self):
        """
        Can keep a job.
        """
        super().__init__()
        self.jobs = []

    def data(self, index, role):
        if role == Qt.DisplayRole:
            job = self.jobs[index.row()]
            if job.display_name:
                return f"{job.src_id} {job.display_name}"
            else:
                return f"{job.src_id} {job.tor_id}"

    def rowCount(self, index):
        return len(self.jobs)

    def append(self, stuff):
        if stuff not in self.jobs:
            self.jobs.append(stuff)
            self.layoutChanged.emit()

    def clear(self):
        self.jobs.clear()
        self.layoutChanged.emit()

    def remove(self, index):
        self.jobs.pop(index)
        self.layoutChanged.emit()

    def remove_finished(self):
        self.jobs[:] = (j for j in self.jobs if not j.upl_succes)
        self.layoutChanged.emit()

    def __bool__(self):
        return bool(self.jobs)

    def __iter__(self):
        for j in self.jobs:
            yield j


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    app.aboutToQuit.connect(window.save_state)
    sys.exit(app.exec_())
