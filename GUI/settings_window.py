from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QFormLayout, QDialog, QGridLayout
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

from lib import ui_text
from GUI.widget_bank import wb


class SettingsWindow(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(ui_text.settings_window_title)
        self.setWindowIcon(QIcon(':/gear.svg'))
        self.layout()

    def layout(self):
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        bottom_row.addWidget(wb.pb_cancel)
        bottom_row.addWidget(wb.pb_ok)

        # main
        data_dir = QVBoxLayout()
        data_dir.addWidget(wb.fsb_data_dir)
        deep_search = QHBoxLayout()
        deep_search.setSpacing(0)
        deep_search.addWidget(wb.chb_deep_search)
        deep_search.addWidget(wb.spb_deep_search_level)
        deep_search.addStretch()
        data_dir.addLayout(deep_search)
        data_dir.setSpacing(5)

        save_dtor = QHBoxLayout()
        save_dtor.addWidget(wb.chb_save_dtors)
        save_dtor.addWidget(wb.fsb_dtor_save_dir)

        settings_form = QFormLayout(wb.main_settings)
        settings_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        settings_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        settings_form.setVerticalSpacing(15)
        settings_form.setHorizontalSpacing(15)
        settings_form.addRow(wb.l_key_1, wb.le_key_1)
        settings_form.addRow(wb.l_key_2, wb.le_key_2)
        settings_form.addRow(wb.l_data_dir, data_dir)
        settings_form.addRow(wb.l_scan_dir, wb.fsb_scan_dir)
        settings_form.addRow(wb.l_save_dtors, save_dtor)
        settings_form.addRow(wb.l_del_dtors, wb.chb_del_dtors)
        settings_form.addRow(wb.l_file_check, wb.chb_file_check)
        settings_form.addRow(wb.l_post_compare, wb.chb_post_compare)
        settings_form.addRow(wb.l_show_tips, wb.chb_show_tips)
        settings_form.addRow(wb.l_verbosity, wb.spb_verbosity)

        # rehost
        toprow = QFormLayout()
        toprow.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        toprow.addRow(wb.l_rehost, wb.chb_rehost)

        white_l_row = QFormLayout()
        white_l_row.addRow(wb.l_whitelist, wb.le_whitelist)

        on_off = QVBoxLayout(wb.rh_on_off_container)
        on_off.setContentsMargins(0, 0, 0, 0)
        on_off.addLayout(white_l_row)
        on_off.addSpacing(15 - on_off.spacing())
        on_off.addWidget(wb.l_rehost_table)
        on_off.addWidget(wb.rehost_table)

        rh_layout = QVBoxLayout(wb.rehost)
        rh_layout.setSpacing(15)
        rh_layout.addLayout(toprow)
        rh_layout.addWidget(wb.rh_on_off_container)
        rh_layout.addStretch()

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
        main.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)
        main.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        job_list = QFormLayout()
        job_list.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        main.addRow(wb.l_style_selector, wb.sty_style_selector)
        main.addRow(wb.l_show_add_dtors, wb.chb_show_add_dtors)
        main.addRow(wb.l_show_rem_tr1, wb.chb_show_rem_tr1)
        main.addRow(wb.l_show_rem_tr2, wb.chb_show_rem_tr2)

        job_list.addRow(wb.l_no_icon, wb.chb_no_icon)
        job_list.addRow(wb.l_show_tor_folder, wb.chb_show_tor_folder)
        job_list.addRow(wb.l_alt_row_colour, wb.chb_alt_row_colour)
        job_list.addRow(wb.l_show_grid, wb.chb_show_grid)
        job_list.addRow(wb.l_row_height, wb.spb_row_height)

        color_form = QFormLayout()
        color_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        color_form.addRow(wb.l_warning_color, wb.ple_warning_color)
        color_form.addRow(wb.l_error_color, wb.ple_error_color)
        color_form.addRow(wb.l_success_color, wb.ple_success_color)
        color_form.addRow(wb.l_link_color, wb.ple_link_color)

        colors = QHBoxLayout()
        colors.addLayout(color_form, stretch=0)
        colors.addWidget(wb.color_examples, stretch=2)

        looks = QVBoxLayout(wb.looks)
        looks.addLayout(main)
        looks.addSpacing(looks.spacing() * 3)
        looks.addWidget(wb.l_job_list)
        looks.addLayout(job_list)
        looks.addSpacing(looks.spacing() * 3)
        looks.addWidget(wb.l_colors)
        looks.addSpacing(looks.spacing())
        looks.addLayout(colors)
        looks.addStretch()

        # Total
        total_layout = QVBoxLayout(self)
        total_layout.setContentsMargins(0, 0, 10, 10)
        total_layout.addWidget(wb.config_tabs)
        total_layout.addSpacing(20)
        total_layout.addLayout(bottom_row)
