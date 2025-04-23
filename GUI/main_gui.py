from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QMainWindow
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QSize

from lib.tp_text import tp_version
from GUI import gui_text
from GUI.widget_bank import wb


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(gui_text.main_window_title.format('.'.join(map(str, tp_version))))
        self.setWindowIcon(QIcon(':/switch.svg'))
        self.setCentralWidget(CentralWidget())
        self.addToolBar(wb.toolbar)
        wb.toolbar.addWidget(wb.profiles)
        wb.toolbar.addWidget(wb.tb_spacer)
        wb.toolbar.addWidget(wb.tb_open_config)
        wb.toolbar.setIconSize(QSize(16, 16))


class CentralWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout()

    def layout(self):
        wb.splitter.addWidget(wb.topwidget)
        wb.splitter.addWidget(wb.bottomwidget)
        wb.splitter.setCollapsible(1, False)
        wb.splitter.setStretchFactor(0, 0)
        wb.splitter.setStretchFactor(1, 1)

        total_layout = QHBoxLayout(self)
        total_layout.setContentsMargins(0, 0, 0, 0)
        total_layout.addWidget(wb.splitter)

        # Top
        source_buttons = QVBoxLayout()
        source_buttons.setSpacing(0)
        source_buttons.addStretch(3)
        source_buttons.addWidget(wb.rb_tracker1)
        source_buttons.addWidget(wb.rb_tracker2)
        source_buttons.addStretch(1)
        source_buttons.addWidget(wb.pb_add)

        top_layout = QHBoxLayout(wb.topwidget)
        top_layout.addWidget(wb.te_paste_box)
        top_layout.addLayout(source_buttons, stretch=0)

        # Bottom
        buttons_job = QVBoxLayout(wb.job_buttons)
        buttons_job.setContentsMargins(0, 0, 0, 0)
        buttons_job.addWidget(wb.pb_clear_j)
        buttons_job.addWidget(wb.pb_rem_sel)
        buttons_job.addWidget(wb.pb_crop)
        buttons_job.addWidget(wb.pb_del_sel)
        buttons_job.addWidget(wb.pb_rem_tr1)
        buttons_job.addWidget(wb.pb_rem_tr2)
        buttons_result = QVBoxLayout(wb.result_buttons)
        buttons_result.setContentsMargins(0, 0, 0, 0)
        buttons_result.addWidget(wb.pb_clear_r)
        buttons_result.addWidget(wb.pb_open_upl_urls)
        buttons_result.addStretch()

        wb.button_stack.addWidget(wb.job_buttons)
        wb.button_stack.addWidget(wb.result_buttons)

        wb.go_stop_stack.addWidget(wb.pb_go)
        wb.go_stop_stack.addWidget(wb.pb_stop)

        control_buttons = QVBoxLayout()
        control_buttons.setSpacing(total_layout.spacing())
        control_buttons.addLayout(wb.button_stack)
        control_buttons.addStretch(1)
        control_buttons.addWidget(wb.pb_open_tsavedir)
        control_buttons.addStretch(3)
        control_buttons.addLayout(wb.go_stop_stack)

        wb.view_stack.addWidget(wb.job_view)
        wb.view_stack.addWidget(wb.result_view)

        add_n_scan = QHBoxLayout()
        add_n_scan.setSpacing(total_layout.spacing())
        add_n_scan.addStretch()
        add_n_scan.addWidget(wb.pb_open_dtors)
        add_n_scan.addWidget(wb.pb_scan)

        right_side = QVBoxLayout()
        right_side.addLayout(add_n_scan)
        right_side.addSpacing(total_layout.spacing())

        view_n_buttons = QGridLayout()
        view_n_buttons.setVerticalSpacing(0)
        view_n_buttons.addLayout(right_side, 0, 1, 1, 2)
        view_n_buttons.addWidget(wb.tabs, 0, 0)
        view_n_buttons.addLayout(wb.view_stack, 1, 0, 1, 2)
        view_n_buttons.addLayout(control_buttons, 1, 2)
        view_n_buttons.setColumnStretch(0, 5)
        view_n_buttons.setColumnStretch(1, 1)
        view_n_buttons.setColumnStretch(2, 0)

        bottom_layout = QVBoxLayout(wb.bottomwidget)
        bottom_layout.addLayout(view_n_buttons)
