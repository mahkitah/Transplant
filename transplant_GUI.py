import sys
import os
import re
import logging

import traceback
import webbrowser

from bencoder import BTFailure

from lib.transplant import Transplanter, Job
from gazelle.tracker_data import tr, tr_data
from gazelle.api_classes import KeyApi, RedApi

from lib import ui_text, utils
from lib.custom_gui_classes import MyTextEdit, MyHeaderView, MyTableView, JobModel

from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QTabWidget, QTabBar, QTextBrowser, QTextEdit, QLineEdit, \
    QPushButton, QToolButton, QRadioButton, QButtonGroup, QHBoxLayout, QVBoxLayout, QFormLayout, QGridLayout, QSpinBox,\
    QCheckBox, QFileDialog, QAction, QSplitter, QTableView, QDialog, QMessageBox, QHeaderView, QSizePolicy,\
    QStackedLayout
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QObject, QSettings, QSize, QThread, pyqtSignal

logging.getLogger('urllib3').setLevel(logging.WARNING)

class Report(logging.Handler):
    class Emit(QObject):
        sig = pyqtSignal(str)

    def __init__(self):
        self.emit_log = self.Emit()
        super().__init__()

    def emit(self, record):
        repl = re.sub(r'(https?://[^\s\n\r]+)', r'<a href="\1">\1</a> ', record.msg)
        self.emit_log.sig.emit(repl)

# noinspection PyBroadException
class TransplantThread(QThread):
    remove_job = pyqtSignal(Job)

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
                self.remove_job.emit(job)

TYPE_MAP = {
    'le': QLineEdit,
    'te': MyTextEdit,
    'chb': QCheckBox,
    'spb': QSpinBox
}
ACTION_MAP = {
    QLineEdit: (lambda x: x.textChanged, lambda x, y: x.setText(y), lambda x: x),
    MyTextEdit: (lambda x: x.plainTextChanged, lambda x, y: x.setText(y), lambda x: x),
    QCheckBox: (lambda x: x.stateChanged, lambda x, y: x.setChecked(y), lambda x: bool(int(x))),
    QSpinBox: (lambda x: x.valueChanged, lambda x, y: x.setValue(y), lambda x: int(x))
}
# name: (default value, make label)
CONFIG_NAMES = {
    'le_scandir': ('', False),
    'le_key_1': (None, True),
    'le_key_2': (None, True),
    'le_data_dir': ('', True),
    'le_dtor_save_dir': ('', True),
    'chb_save_dtors': (0, False),
    'chb_del_dtors': (0, True),
    'chb_file_check': (2, True),
    'chb_show_tips': (2, True),
    'spb_verbosity': (2, True),
    'chb_rehost': (0, True),
    'le_whitelist': (ui_text.default_whitelist, True),
    'le_ptpimg_key': (None, True),
    'te_rel_descr_templ': (ui_text.def_rel_descr, False),
    'te_src_descr_templ': (ui_text.def_src_descr, False),
    'chb_add_src_descr': (1, False),
    'spb_splitter_weight': (0, True),
    'chb_no_icon': (0, True),
    'chb_alt_row_colour': (1, True),
    'chb_show_grid': (0, True),
    'spb_row_height': (20, True),
    'chb_show_add_dtors': (2, True),
    'chb_show_rem_tr1': (0, True),
    'chb_show_rem_tr2': (0, True)
}

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
        self.config = QSettings("gui_files/gui_config.ini", QSettings.IniFormat)
        self.job_data = JobModel(self.config)
        self.user_input_elements()
        self.ui_elements()
        self.ui_main_layout()
        self.ui_config_layout()
        self.ui_main_connections()
        self.ui_config_connections()
        self.set_logging()
        self.load_config()
        self.set_element_properties()
        self.show()

    def set_logging(self):
        self.report = logging.getLogger()
        self.handler = Report()
        self.report.addHandler(self.handler)
        self.handler.emit_log.sig.connect(self.result_view.append)

    def user_input_elements(self):

        for el_name, (df, mk_lbl) in CONFIG_NAMES.items():
            typ, name = el_name.split('_', maxsplit=1)

            # instantiate
            setattr(self, el_name, TYPE_MAP[typ]())

            # connection to ini
            def make_lambda(name):
                return lambda x: self.config.setValue(name, x)

            obj = getattr(self, el_name)
            ACTION_MAP[type(obj)][0](obj).connect(make_lambda(el_name))

            # instantiate Label
            if mk_lbl:
                label_name = 'l_' + name
                setattr(self, label_name, QLabel(getattr(ui_text, label_name)))

    def set_element_properties(self):

        self.le_scandir.setPlaceholderText(ui_text.tt_ac_select_scandir)

        self.spb_verbosity.setMaximum(3)
        self.spb_verbosity.setMaximumWidth(40)

        self.chb_add_src_descr.setText(ui_text.chb_add_src_descr)

        self.spb_splitter_weight.setMaximum(10)
        self.spb_splitter_weight.setMaximumWidth(40)

        self.spb_row_height.setMinimum(12)
        self.spb_row_height.setMaximum(99)
        self.spb_row_height.setMaximumWidth(40)

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

        self.ac_select_scandir = QAction()
        self.ac_select_scandir.setIcon(QIcon("gui_files/open-folder.svg"))
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

        self.config_tabs = QTabWidget()
        self.config_tabs.setDocumentMode(True)
        self.main_settings = QWidget()
        self.cust_descr = QWidget()
        self.looks = QWidget()
        self.config_tabs.addTab(self.main_settings, ui_text.main_tab)
        self.config_tabs.addTab(self.cust_descr, ui_text.desc_tab)
        self.config_tabs.addTab(self.looks, ui_text.looks_tab)

        # Config
        self.config_window = QDialog(self)
        self.config_window.setWindowTitle(ui_text.config_window_title)
        self.config_window.setWindowIcon(QIcon('gui_files/gear.svg'))
        self.pb_cancel = QPushButton(ui_text.pb_cancel)
        self.pb_ok = QPushButton(ui_text.pb_ok)

        # main
        self.ac_select_datadir = QAction()
        self.ac_select_datadir.setIcon(QIcon("gui_files/open-folder.svg"))
        self.ac_select_torsave = QAction()
        self.ac_select_torsave.setIcon(QIcon("gui_files/open-folder.svg"))

        # descr tab
        self.l_variables = QLabel(ui_text.l_placeholders)
        self.pb_def_descr = QPushButton()
        self.pb_def_descr.setText(ui_text.pb_def_descr)
        self.l_variables.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # looks tab
        self.l_job_list = QLabel(ui_text.l_job_list)

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
        self.le_scandir.addAction(self.ac_select_scandir, QLineEdit.TrailingPosition)
        scan_row.addWidget(self.le_scandir)
        scan_row.addWidget(self.pb_scan)
        scan_row.addWidget(self.tb_open_config2)

        buttons_job = QVBoxLayout(self.job_buttons)
        buttons_job.setContentsMargins(0, 0, 0, 0)
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

        view_n_buttons = QGridLayout()
        view_n_buttons.setVerticalSpacing(0)
        view_n_buttons.addWidget(self.tabs, 0, 0)
        view_n_buttons.addLayout(self.view_stack, 1, 0)
        view_n_buttons.addLayout(control_buttons, 1, 1)
        view_n_buttons.setColumnStretch(0, 1)
        view_n_buttons.setColumnStretch(1, 0)

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

    def ui_config_layout(self):
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        bottom_row.addWidget(self.pb_cancel)
        bottom_row.addWidget(self.pb_ok)

        # main
        self.le_data_dir.addAction(self.ac_select_datadir, QLineEdit.TrailingPosition)
        self.le_dtor_save_dir.addAction(self.ac_select_torsave, QLineEdit.TrailingPosition)

        save_dtor = QHBoxLayout()
        save_dtor.addWidget(self.chb_save_dtors)
        save_dtor.addWidget(self.le_dtor_save_dir)

        settings_form = QFormLayout(self.main_settings)
        settings_form.setLabelAlignment(Qt.AlignRight)
        settings_form.setVerticalSpacing(20)
        settings_form.setHorizontalSpacing(20)
        settings_form.addRow(self.l_key_1, self.le_key_1)
        settings_form.addRow(self.l_key_2, self.le_key_2)
        settings_form.addRow(self.l_data_dir, self.le_data_dir)
        settings_form.addRow(self.l_dtor_save_dir, save_dtor)
        settings_form.addRow(self.l_del_dtors, self.chb_del_dtors)
        settings_form.addRow(self.l_file_check, self.chb_file_check)
        settings_form.addRow(self.l_show_tips, self.chb_show_tips)
        settings_form.addRow(self.l_verbosity, self.spb_verbosity)
        settings_form.addRow(self.l_rehost, self.chb_rehost)
        settings_form.addRow(self.l_whitelist, self.le_whitelist)
        settings_form.addRow(self.l_ptpimg_key, self.le_ptpimg_key)

        # descr
        top_left_descr = QVBoxLayout()
        top_left_descr.addStretch()
        top_left_descr.addWidget(self.pb_def_descr)

        top_row_descr = QHBoxLayout()
        top_row_descr.addWidget(self.l_variables)
        top_row_descr.addStretch()
        top_row_descr.addLayout(top_left_descr)

        desc_layout = QVBoxLayout(self.cust_descr)
        desc_layout.addLayout(top_row_descr)
        desc_layout.addWidget(self.te_rel_descr_templ)
        desc_layout.addWidget(self.chb_add_src_descr)
        desc_layout.addWidget(self.te_src_descr_templ)

        # Looks
        main = QFormLayout()
        job_list = QFormLayout()
        main.addRow(self.l_show_add_dtors, self.chb_show_add_dtors)
        main.addRow(self.l_splitter_weight, self.spb_splitter_weight)
        main.addRow(self.l_show_rem_tr1, self.chb_show_rem_tr1)
        main.addRow(self.l_show_rem_tr2, self.chb_show_rem_tr2)
        job_list.addRow(self.l_no_icon, self.chb_no_icon)
        job_list.addRow(self.l_alt_row_colour, self.chb_alt_row_colour)
        job_list.addRow(self.l_show_grid, self.chb_show_grid)
        job_list.addRow(self.l_row_height, self.spb_row_height)

        looks = QVBoxLayout(self.looks)
        looks.addLayout(main)
        looks.addSpacing(16)
        looks.addWidget(self.l_job_list)
        looks.addLayout(job_list)
        looks.addStretch()

        total_layout = QVBoxLayout(self.config_window)
        total_layout.setContentsMargins(0, 0, 10, 10)
        total_layout.addWidget(self.config_tabs)
        total_layout.addSpacing(20)
        total_layout.addLayout(bottom_row)

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
        self.tb_go.clicked.connect(self.gogogo)
        # self.tb_go.clicked.connect(self.blabla)
        self.pb_open_upl_urls.clicked.connect(self.open_tor_urls)
        self.le_scandir.textChanged.connect(lambda: self.pb_scan.setEnabled(bool(self.le_scandir.text())))
        self.ac_select_scandir.triggered.connect(self.select_scan_dir)
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
        self.tb_open_config.clicked.connect(self.config_window.open)
        self.tb_open_config2.clicked.connect(self.config_window.open)
        self.splitter.splitterMoved.connect(lambda x, y: self.tb_open_config2.setHidden(bool(x)))
        self.tabs.currentChanged.connect(self.view_stack.setCurrentIndex)
        self.view_stack.currentChanged.connect(self.tabs.setCurrentIndex)
        self.view_stack.currentChanged.connect(self.tab_button_stack.setCurrentIndex)

    def ui_config_connections(self):
        self.pb_def_descr.clicked.connect(self.default_descr)
        self.pb_ok.clicked.connect(self.settings_check)
        self.pb_cancel.clicked.connect(self.config_window.reject)
        self.config_window.accepted.connect(
            lambda: self.config.setValue('geometry/config_window_size', self.config_window.size()))
        self.ac_select_datadir.triggered.connect(self.select_datadir)
        self.ac_select_torsave.triggered.connect(self.select_torsave)
        self.le_dtor_save_dir.textChanged.connect(lambda x: self.pb_open_tsavedir.setEnabled(bool(x)))
        self.chb_show_tips.stateChanged.connect(self.tooltips)
        self.spb_verbosity.valueChanged.connect(self.set_verbosity)
        self.chb_show_add_dtors.stateChanged.connect(lambda x: self.section_add_dtor_btn.setVisible(x)),
        self.chb_show_rem_tr1.stateChanged.connect(lambda x: self.pb_rem_tr1.setVisible(x)),
        self.chb_show_rem_tr2.stateChanged.connect(lambda x: self.pb_rem_tr2.setVisible(x)),
        self.chb_no_icon.stateChanged.connect(self.job_data.layoutChanged.emit)
        self.spb_splitter_weight.valueChanged.connect(self.splitter.setHandleWidth)
        self.chb_alt_row_colour.stateChanged.connect(self.job_view.setAlternatingRowColors)
        self.chb_show_grid.stateChanged.connect(self.job_view.setShowGrid)
        self.chb_show_grid.stateChanged.connect(self.job_data.layoutChanged.emit)
        self.spb_row_height.valueChanged.connect(self.job_view.verticalHeader().setDefaultSectionSize)

    def load_config(self):
        for name, (df, mk_lbl) in CONFIG_NAMES.items():
            obj = getattr(self, name)

            if not self.config.contains(name):
                self.config.setValue(name, df)

            renamed = {'te_rel_descr': 'te_rel_descr_templ', 'te_src_descr': 'te_src_descr_templ'}

            actions = ACTION_MAP[type(obj)]
            value = actions[2](self.config.value(name))
            actions[1](obj, value)
            actions[0](obj).emit(value)

        for d in (('te_rel_descr', 'te_rel_descr_templ'), ('te_src_descr', 'te_src_descr_templ')):
            if self.config.contains(d[0]):
                if self.config.value(d[0]) != self.config.value(d[1]):
                    obj = getattr(self, d[1])
                    actions = ACTION_MAP[type(obj)]
                    value = actions[2](self.config.value(d[0]))
                    actions[1](obj, value)
                    actions[0](obj).emit(value)

        self.le_key_1.setCursorPosition(0)
        self.le_key_2.setCursorPosition(0)

        source_id = int(self.config.value('bg_source', defaultValue=0))
        self.bg_source.buttons()[source_id].click()
        self.resize(self.config.value('geometry/size', defaultValue=QSize(550, 500)))
        self.config_window.resize(self.config.value('geometry/config_window_size', defaultValue=QSize(400, 450)))

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
                obj = getattr(self, obj_name)
                obj.setToolTip(ttip if flag else '')

        self.splitter.handle(1).setToolTip(ui_text.ttm_splitter if flag else '')

    def blabla(self, *args):
        # self.report.info('blabla\n')
        # from testzooi.testrun import testrun
        # testrun(self)
        pass

    def gogogo(self):
        if not self.job_data:
            return

        min_req_config = ("le_key_1", "le_key_2", "le_data_dir")
        if not all(self.config.value(x) for x in min_req_config):
            self.config_window.open()
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
        self.tr_thread.remove_job.connect(self.job_data.remove)
        self.tr_thread.start()

    def select_datadir(self):
        d_dir = QFileDialog.getExistingDirectory(self, ui_text.tt_ac_select_datadir, self.config.value('le_data_dir'))
        if not d_dir:
            return
        d_dir = os.path.normpath(d_dir)
        self.le_data_dir.setText(d_dir)

    def select_torsave(self):
        t_dir = QFileDialog.getExistingDirectory(self, ui_text.tt_ac_select_torsave,
                                                 self.config.value('le_dtor_save_dir'))
        if not t_dir:
            return
        t_dir = os.path.normpath(t_dir)
        self.le_dtor_save_dir.setText(t_dir)

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
        path = self.le_scandir.text()
        if path and os.path.isdir(path):
            self.tabs.setCurrentIndex(0)

            del_dtors = bool(int(self.config.value('chb_del_dtors')))

            for scan in os.scandir(self.le_scandir.text()):
                if scan.is_file() and scan.name.endswith(".torrent"):
                    try:
                        self.job_data.append(Job(dtor_path=scan.path, scanned=True))
                    except (AssertionError, BTFailure):
                        continue

    def settings_check(self):
        data_dir = self.config.value('le_data_dir')
        dtor_save_dir = self.config.value('le_dtor_save_dir')
        save_dtors = self.chb_save_dtors.isChecked()
        rehost = self.chb_rehost.isChecked()
        ptpimg_key = self.config.value('le_ptpimg_key')
        add_src_descr = self.chb_add_src_descr.isChecked()

        sum_ting_wong = []
        if not os.path.isdir(data_dir):
            sum_ting_wong.append(ui_text.sum_ting_wong_1)
        if save_dtors and not os.path.isdir(dtor_save_dir):
            sum_ting_wong.append(ui_text.sum_ting_wong_2)
        if rehost and not ptpimg_key:
            sum_ting_wong.append(ui_text.sum_ting_wong_3)
        if add_src_descr and '%src_descr%' not in self.te_src_descr_templ.toPlainText():
            sum_ting_wong.append(ui_text.sum_ting_wong_4)

        if sum_ting_wong:
            warning = QMessageBox()
            warning.setIcon(QMessageBox.Warning)
            warning.setText("- " + "\n- ".join(sum_ting_wong))
            warning.exec()
            return
        else:
            self.config_window.accept()

    def default_descr(self):
        self.te_rel_descr_templ.setText(ui_text.def_rel_descr)
        self.te_src_descr_templ.setText(ui_text.def_src_descr)

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
            if job.dtor_path and job.dtor_path.startswith(self.le_scandir.text()):
                os.remove(job.dtor_path)

        self.job_data.del_multi(selected_rows)

    def select_scan_dir(self):
        s_dir = QFileDialog.getExistingDirectory(self, ui_text.tt_ac_select_scandir, self.config.value('le_scandir'))
        if not s_dir:
            return
        s_dir = os.path.normpath(s_dir)
        self.le_scandir.setText(s_dir)

    def set_verbosity(self, lvl):
        verb_map = {
            0: logging.CRITICAL,
            1: logging.ERROR,
            2: logging.INFO,
            3: logging.DEBUG}
        self.report.setLevel(verb_map[lvl])

    def show_feedback(self, msg):
        # if msg_verb <= int(self.config.value('spb_verbosity')):
        #     repl = re.sub(r'(https?://[^\s\n\r]+)', r'<a href="\1">\1</a> ', msg)
        #
        #     self.result_view.append(repl)
        # repl = re.sub(r'(https?://[^\s\n\r]+)', r'<a href="\1">\1</a> ', msg)

        self.result_view.append(msg)

    def trpl_settings(self):
        user_settings = (
            'le_data_dir',
            'le_dtor_save_dir',
            'chb_save_dtors',
            'chb_del_dtors'
            'chb_file_check',
            'te_rel_descr_templ',
            'chb_add_src_descr',
            'te_src_descr_templ'
        )
        settings_dict = {}
        for x in user_settings:
            typ_str, arg_name = x.split('_', maxsplit=1)
            typ = TYPE_MAP[typ_str]
            settings_dict[arg_name] = ACTION_MAP[typ][2](self.config.value(x))

        if bool(int(self.config.value('chb_rehost'))):
            white_str_nospace = ''.join(self.config.value('le_whitelist').split())
            if white_str_nospace:
                whitelist = white_str_nospace.split(',')
                settings_dict.update(img_rehost=True, whitelist=whitelist,
                                     ptpimg_key=self.config.value('le_ptpimg_key'))

        return settings_dict

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
