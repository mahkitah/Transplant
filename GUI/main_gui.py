from gazelle.tracker_data import tr
from lib import ui_text
from GUI.custom_gui_classes import TPTextEdit, TPHeaderView, TPTableView, JobModel

from PyQt5.QtWidgets import QWidget, QTabBar, QTextBrowser, QTextEdit, QPushButton, QToolButton, QRadioButton,\
    QButtonGroup, QHBoxLayout, QVBoxLayout, QGridLayout, QSplitter, QTableView, QHeaderView, QSizePolicy, QStackedLayout
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

class MainGui(QWidget):
    def __init__(self, config):
        super().__init__()
        self.job_data = JobModel(config)
        self.ui_elements()
        self.ui_main_layout()

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

        self.te_paste_box = TPTextEdit()
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

        self.job_view = TPTableView()
        self.job_view.setHorizontalHeader(TPHeaderView(Qt.Horizontal, self.job_data.headers))
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
        self.pb_open_tsavedir.setEnabled(False)
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
