from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QStackedLayout

from GUI.widget_bank import wb


class Central(QWidget):
    def __init__(self):
        super().__init__()
        self.layout()

    def layout(self):
        # Top
        source_area = QVBoxLayout()

        sa_topleft = QVBoxLayout()
        sa_topleft.addStretch(3)
        sa_topleft.addWidget(wb.rb_tracker1)
        sa_topleft.addWidget(wb.rb_tracker2)
        sa_topleft.addStretch(1)

        sa_topright = QVBoxLayout()
        sa_topright.addWidget(wb.tb_open_config)
        sa_topright.addStretch()

        sa_top = QHBoxLayout()
        sa_top.addLayout(sa_topleft)
        sa_top.addLayout(sa_topright)

        source_area.addLayout(sa_top)
        source_area.addWidget(wb.pb_add)

        pastebox = QVBoxLayout()
        pastebox.addSpacing(10)
        pastebox.addWidget(wb.te_paste_box)

        paste_row = QHBoxLayout()
        paste_row.addLayout(pastebox)
        paste_row.addLayout(source_area)

        add_dtors = QVBoxLayout(wb.section_add_dtor_btn)
        add_dtors.setContentsMargins(0, 0, 0, 0)
        add_dtors.addSpacing(10)
        add_dtors.addWidget(wb.pb_open_dtors)

        top_layout = QVBoxLayout(wb.topwidget)
        top_layout.addLayout(paste_row)
        top_layout.addWidget(wb.section_add_dtor_btn)

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

        wb.tab_button_stack = QStackedLayout()
        wb.tab_button_stack.addWidget(wb.job_buttons)
        wb.tab_button_stack.addWidget(wb.result_buttons)

        wb.go_stop_stack = QStackedLayout()
        wb.go_stop_stack.addWidget(wb.tb_go)
        wb.go_stop_stack.addWidget(wb.pb_stop)

        control_buttons = QVBoxLayout()
        control_buttons.addLayout(wb.tab_button_stack)
        control_buttons.addStretch(3)
        control_buttons.addWidget(wb.pb_open_tsavedir)
        control_buttons.addStretch(1)
        control_buttons.addLayout(wb.go_stop_stack)

        wb.view_stack = QStackedLayout()
        wb.view_stack.addWidget(wb.job_view)
        wb.view_stack.addWidget(wb.result_view)

        open_config2 = QHBoxLayout()
        right_top = QHBoxLayout()
        right_top.addWidget(wb.pb_scan)
        right_top.addWidget(wb.tb_open_config2)
        right_side = QVBoxLayout()
        right_side.addLayout(right_top)
        right_side.addSpacing(5)
        open_config2.addStretch()
        open_config2.addLayout(right_side)

        view_n_buttons = QGridLayout()
        view_n_buttons.setVerticalSpacing(0)
        view_n_buttons.addLayout(open_config2, 0, 1, 2, 2)
        view_n_buttons.addWidget(wb.tabs, 1, 0, 1, 2)
        view_n_buttons.addLayout(wb.view_stack, 2, 0, 1, 2)
        view_n_buttons.addLayout(control_buttons, 2, 2)
        view_n_buttons.setColumnStretch(0, 1)
        view_n_buttons.setColumnStretch(1, 1)
        view_n_buttons.setColumnStretch(2, 0)

        bottom_layout = QVBoxLayout(wb.bottomwidget)
        bottom_layout.addLayout(view_n_buttons)

        splitter = wb.splitter
        splitter.addWidget(wb.topwidget)
        splitter.addWidget(wb.bottomwidget)
        splitter.setCollapsible(1, False)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        total_layout = QHBoxLayout(self)
        total_layout.setContentsMargins(0, 0, 0, 0)
        total_layout.addWidget(splitter)
