from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QGridLayout
from PyQt6.QtGui import QIcon, QKeyEvent
from PyQt6.QtCore import pyqtSignal

from lib import ui_text
from lib.version import __version__
from GUI.widget_bank import wb


class MainWindow(QWidget):
    key_press = pyqtSignal(QKeyEvent)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(ui_text.main_window_title.format(__version__))
        self.setWindowIcon(QIcon(':/switch.svg'))
        self.layout()

    def keyPressEvent(self, event: QKeyEvent):
        self.key_press.emit(event)
        super().keyPressEvent(event)

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

        settings_button = QVBoxLayout()
        settings_button.addWidget(wb.tb_open_config)
        settings_button.addStretch()

        top_layout = QGridLayout(wb.topwidget)
        top_layout.addWidget(wb.te_paste_box, 0, 0, 2, 1)
        top_layout.addLayout(source_buttons, 0, 1)
        top_layout.addLayout(settings_button, 0, 2)
        top_layout.addWidget(wb.pb_add, 1, 1, 1, 2)

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

        wb.go_stop_stack.addWidget(wb.tb_go)
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
        add_n_scan.addWidget(wb.tb_open_config2)

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
