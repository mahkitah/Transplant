from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QFormLayout, QDialog
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

from lib import ui_text
from GUI.files import get_file
from GUI.widget_bank import wb


class SettingsWindow(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(ui_text.settings_window_title)
        self.setWindowIcon(QIcon(get_file('gear.svg')))
        self.layout()

    def layout(self):
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        bottom_row.addWidget(wb.pb_cancel)
        bottom_row.addWidget(wb.pb_ok)

        # main
        data_dir = QVBoxLayout()
        data_dir.addWidget(wb.fsb_data_dir)
        data_dir.addWidget(wb.chb_deep_search)
        data_dir.setSpacing(5)

        save_dtor = QHBoxLayout()
        save_dtor.addWidget(wb.chb_save_dtors)
        save_dtor.addWidget(wb.fsb_dtor_save_dir)

        settings_form = QFormLayout(wb.main_settings)
        settings_form.setLabelAlignment(Qt.AlignRight)
        settings_form.setVerticalSpacing(20)
        settings_form.setHorizontalSpacing(20)
        settings_form.addRow(wb.l_key_1, wb.le_key_1)
        settings_form.addRow(wb.l_key_2, wb.le_key_2)
        settings_form.addRow(wb.l_data_dir, data_dir)
        settings_form.addRow(wb.l_scan_dir, wb.fsb_scan_dir)
        settings_form.addRow(wb.l_dtor_save_dir, save_dtor)
        settings_form.addRow(wb.l_del_dtors, wb.chb_del_dtors)
        settings_form.addRow(wb.l_file_check, wb.chb_file_check)
        settings_form.addRow(wb.l_post_compare, wb.chb_post_compare)
        settings_form.addRow(wb.l_show_tips, wb.chb_show_tips)
        settings_form.addRow(wb.l_verbosity, wb.spb_verbosity)
        settings_form.addRow(wb.l_rehost, wb.chb_rehost)
        settings_form.addRow(wb.l_whitelist, wb.le_whitelist)
        settings_form.addRow(wb.l_ptpimg_key, wb.le_ptpimg_key)

        # descr
        top_left_descr = QVBoxLayout()
        top_left_descr.addStretch()
        top_left_descr.addWidget(wb.pb_def_descr)

        top_row_descr = QHBoxLayout()
        top_row_descr.addWidget(wb.l_variables)
        top_row_descr.addStretch()
        top_row_descr.addLayout(top_left_descr)

        desc_layout = QVBoxLayout(wb.cust_descr)
        desc_layout.addLayout(top_row_descr)
        desc_layout.addWidget(wb.te_rel_descr_templ)
        desc_layout.addWidget(wb.l_own_uploads)
        desc_layout.addWidget(wb.te_rel_descr_own_templ)
        desc_layout.addWidget(wb.chb_add_src_descr)
        desc_layout.addWidget(wb.te_src_descr_templ)

        # Looks
        main = QFormLayout()
        job_list = QFormLayout()
        main.addRow(wb.l_show_add_dtors, wb.chb_show_add_dtors)
        main.addRow(wb.l_splitter_weight, wb.spb_splitter_weight)
        main.addRow(wb.l_show_rem_tr1, wb.chb_show_rem_tr1)
        main.addRow(wb.l_show_rem_tr2, wb.chb_show_rem_tr2)
        job_list.addRow(wb.l_no_icon, wb.chb_no_icon)
        job_list.addRow(wb.l_alt_row_colour, wb.chb_alt_row_colour)
        job_list.addRow(wb.l_show_grid, wb.chb_show_grid)
        job_list.addRow(wb.l_row_height, wb.spb_row_height)

        looks = QVBoxLayout(wb.looks)
        looks.addLayout(main)
        looks.addSpacing(16)
        looks.addWidget(wb.l_job_list)
        looks.addLayout(job_list)
        looks.addStretch()

        # Total
        total_layout = QVBoxLayout(self)
        total_layout.setContentsMargins(0, 0, 10, 10)
        total_layout.addWidget(wb.config_tabs)
        total_layout.addSpacing(20)
        total_layout.addLayout(bottom_row)



