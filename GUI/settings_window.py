from lib import ui_text
from GUI.files import get_file
from GUI.custom_gui_classes import TPTextEdit, FolderSelectBox

from PyQt5.QtWidgets import QWidget, QLabel, QTabWidget, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout, QFormLayout,\
    QSpinBox, QCheckBox, QDialog, QSizePolicy
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QSettings, QSize

TYPE_MAP = {
    'le': QLineEdit,
    'te': TPTextEdit,
    'chb': QCheckBox,
    'spb': QSpinBox,
    'fsb': FolderSelectBox
}
ACTION_MAP = {
    QLineEdit: (lambda x: x.textChanged, lambda x, y: x.setText(y)),
    TPTextEdit: (lambda x: x.plainTextChanged, lambda x, y: x.setText(y)),
    QCheckBox: (lambda x: x.stateChanged, lambda x, y: x.setCheckState(y)),
    QSpinBox: (lambda x: x.valueChanged, lambda x, y: x.setValue(y)),
    FolderSelectBox: (lambda x: x.list_changed, lambda x, y: x.set_list(y))
}
# name: (default value, make label)
CONFIG_NAMES = {
    'le_key_1': (None, True),
    'le_key_2': (None, True),
    'fsb_data_dir': ([], True),
    'fsb_scan_dir': ([], True),
    'fsb_dtor_save_dir': ([], True),
    'chb_save_dtors': (0, False),
    'chb_del_dtors': (0, True),
    'chb_file_check': (2, True),
    'chb_show_tips': (2, True),
    'spb_verbosity': (2, True),
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
    'chb_show_rem_tr2': (0, True),
    'chb_rehost': (0, True),
    'le_whitelist': (ui_text.default_whitelist, True),
    'le_ptpimg_key': (None, True),
}

class SettingsWindow(QDialog):
    def __init__(self, parent, config: QSettings):
        super().__init__(parent)
        self.setWindowTitle(ui_text.settings_window_title)
        self.setWindowIcon(QIcon(get_file('gear.svg')))
        self.config = config
        self.user_input_elements()
        self.ui_elements()
        self.ui_layout()

    def user_input_elements(self):

        def make_lambda(name):
            return lambda x: self.config.setValue(name, x)

        for el_name, (df, mk_lbl) in CONFIG_NAMES.items():
            typ_str, name = el_name.split('_', maxsplit=1)

            # instantiate
            obj_type = TYPE_MAP[typ_str]
            setattr(self, el_name, obj_type())
            obj = getattr(self, el_name)
            obj.setObjectName(el_name)

            # connection to ini
            ACTION_MAP[type(obj)][0](obj).connect(make_lambda(el_name))

            # instantiate Label
            if mk_lbl:
                label_name = 'l_' + name
                setattr(self, label_name, QLabel(getattr(ui_text, label_name)))

    def set_element_properties(self):
        """
        This function must be called after (or by) 'load_config'
        Otherwise spinbox minimum will be set in config.
        """
        for fsb in self.findChildren(FolderSelectBox):
            fsb.setMaxCount(8)
            fsb.folder_button.setIcon(QIcon(get_file('open-folder.svg')))
            fsb.dialog_caption = getattr(ui_text, f'tt_{fsb.objectName()}')
            fsb.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Preferred)

        self.spb_verbosity.setMaximum(3)
        self.spb_verbosity.setMaximumWidth(40)

        self.chb_add_src_descr.setText(ui_text.chb_add_src_descr)

        self.spb_splitter_weight.setMaximum(10)
        self.spb_splitter_weight.setMaximumWidth(40)

        self.spb_row_height.setMinimum(12)
        self.spb_row_height.setMaximum(99)
        self.spb_row_height.setMaximumWidth(40)

    def ui_elements(self):
        self.config_tabs = QTabWidget()
        self.config_tabs.setDocumentMode(True)
        self.main_settings = QWidget()
        self.cust_descr = QWidget()
        self.looks = QWidget()
        self.config_tabs.addTab(self.main_settings, ui_text.main_tab)
        self.config_tabs.addTab(self.cust_descr, ui_text.desc_tab)
        self.config_tabs.addTab(self.looks, ui_text.looks_tab)

        self.pb_cancel = QPushButton(ui_text.pb_cancel)
        self.pb_ok = QPushButton(ui_text.pb_ok)

        # descr tab
        self.l_variables = QLabel(ui_text.l_placeholders)
        self.pb_def_descr = QPushButton()
        self.pb_def_descr.setText(ui_text.pb_def_descr)
        self.l_variables.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # looks tab
        self.l_job_list = QLabel(ui_text.l_job_list)

    def ui_layout(self):
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        bottom_row.addWidget(self.pb_cancel)
        bottom_row.addWidget(self.pb_ok)

        # main
        save_dtor = QHBoxLayout()
        save_dtor.addWidget(self.chb_save_dtors)
        save_dtor.addWidget(self.fsb_dtor_save_dir)

        settings_form = QFormLayout(self.main_settings)
        settings_form.setLabelAlignment(Qt.AlignRight)
        settings_form.setVerticalSpacing(20)
        settings_form.setHorizontalSpacing(20)
        settings_form.addRow(self.l_key_1, self.le_key_1)
        settings_form.addRow(self.l_key_2, self.le_key_2)
        settings_form.addRow(self.l_data_dir, self.fsb_data_dir)
        settings_form.addRow(self.l_scan_dir, self.fsb_scan_dir)
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

        # Total
        total_layout = QVBoxLayout(self)
        total_layout.setContentsMargins(0, 0, 10, 10)
        total_layout.addWidget(self.config_tabs)
        total_layout.addSpacing(20)
        total_layout.addLayout(bottom_row)

    def load_config(self):
        for name, (df, mk_lbl) in CONFIG_NAMES.items():
            obj = getattr(self, name)

            if not self.config.contains(name):
                self.config.setValue(name, df)

            actions = ACTION_MAP[type(obj)]
            value = self.config.value(name)
            actions[1](obj, value)
            actions[0](obj).emit(value)

        self.set_element_properties()
        self.le_key_1.setCursorPosition(0)
        self.le_key_2.setCursorPosition(0)

        self.resize(self.config.value('geometry/config_window_size', defaultValue=QSize(400, 450)))

    def trpl_settings(self):
        user_settings = (
            'chb_save_dtors',
            'chb_del_dtors',
            'chb_file_check',
            'te_rel_descr_templ',
            'chb_add_src_descr',
            'te_src_descr_templ'
        )
        settings_dict = {
            'data_dir': self.fsb_data_dir.currentText(),
            'dtor_save_dir': self.fsb_dtor_save_dir.currentText()
        }
        for x in user_settings:
            _, arg_name = x.split('_', maxsplit=1)
            settings_dict[arg_name] = self.config.value(x)

        if self.config.value('chb_rehost'):
            white_str_nospace = ''.join(self.config.value('le_whitelist').split())
            if white_str_nospace:
                whitelist = white_str_nospace.split(',')
                settings_dict.update(img_rehost=True, whitelist=whitelist,
                                     ptpimg_key=self.config.value('le_ptpimg_key'))

        return settings_dict
