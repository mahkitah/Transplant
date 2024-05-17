from functools import partial

from PyQt6.QtWidgets import (QApplication, QWidget, QTextEdit, QPushButton, QToolButton, QRadioButton, QButtonGroup,
                             QSplitter, QSizePolicy, QLabel, QTabWidget, QLineEdit, QSpinBox, QCheckBox, QStackedLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from gazelle.tracker_data import tr
from GUI import gui_text
from lib.version import version
from lib.img_rehost import ih
from GUI.misc_classes import (TPTextEdit, CyclingTabBar, FolderSelectBox, ResultBrowser, IniSettings, TempPopUp,
                              ColorExample, PatientLineEdit, ThemeIcon, StyleSelecter, ClickableLabel)
from GUI.mv_classes import JobModel, JobView, RehostModel, RehostTable

TYPE_MAP = {
    'le': QLineEdit,
    'ple': PatientLineEdit,
    'te': TPTextEdit,
    'chb': QCheckBox,
    'spb': QSpinBox,
    'fsb': FolderSelectBox,
    'sty': StyleSelecter
}
ACTION_MAP = {
    QLineEdit: (lambda x: x.textChanged, lambda x, y: x.setText(y)),
    PatientLineEdit: (lambda x: x.text_changed, lambda x, y: x.setText(y)),
    TPTextEdit: (lambda x: x.plain_text_changed, lambda x, y: x.setText(y)),
    QCheckBox: (lambda x: x.stateChanged, lambda x, y: x.setCheckState(Qt.CheckState(y))),
    QSpinBox: (lambda x: x.valueChanged, lambda x, y: x.setValue(y)),
    FolderSelectBox: (lambda x: x.list_changed, lambda x, y: x.set_list(y)),
    StyleSelecter: (lambda x: x.currentTextChanged, lambda x, y: x.setCurrentText(y)),
}
# name: (default value, make label)
CONFIG_NAMES = {
    'le_key_1': (None, True),
    'le_key_2': (None, True),
    'fsb_data_dir': ([], True),
    'chb_deep_search': (0, False),
    'spb_deep_search_level': (2, False),
    'fsb_scan_dir': ([], True),
    'fsb_dtor_save_dir': ([], False),
    'chb_save_dtors': (0, True),
    'chb_del_dtors': (0, True),
    'chb_file_check': (2, True),
    'chb_post_compare': (0, True),
    'chb_show_tips': (2, True),
    'spb_verbosity': (2, True),
    'chb_rehost': (0, True),
    'le_whitelist': (gui_text.default_whitelist, True),
    'te_rel_descr_templ': (gui_text.def_rel_descr, False),
    'te_rel_descr_own_templ': (gui_text.def_rel_descr_own, False),
    'te_src_descr_templ': (gui_text.def_src_descr, False),
    'chb_add_src_descr': (2, False),
    'sty_style_selector': ('Fusion', True),
    'chb_show_add_dtors': (2, True),
    'chb_show_rem_tr1': (0, True),
    'chb_show_rem_tr2': (0, True),
    'chb_no_icon': (0, True),
    'chb_show_tor_folder': (0, True),
    'chb_alt_row_colour': (2, True),
    'chb_show_grid': (0, True),
    'spb_row_height': (20, True),
    'ple_warning_color': ('orange', True),
    'ple_error_color': ('crimson', True),
    'ple_success_color': ('forestgreen', True),
    'ple_link_color': ('dodgerblue', True),
}


class WidgetBank:
    def __init__(self):
        super().__init__()
        self.app = QApplication.instance()
        self.config = IniSettings("Transplant.ini")
        self.config_update()
        self.fsbs = []
        self.user_input_elements()
        self.main_window = None
        self.settings_window = None
        self.main_widgets()
        self.settings_window_widgets()

        self._pop_up = None
        self.thread = None

    @property
    def pop_up(self):
        if not self._pop_up:
            self._pop_up = TempPopUp(self.main_window)

        return self._pop_up

    def config_update(self):
        config_version = self.config.value('config_version')
        if isinstance(config_version, str):
            config_version = tuple(map(int, config_version.split('.')))
            self.config.setValue('config_version', config_version)
        if config_version == version:
            return
        if config_version is None:
            self.config.setValue('config_version', version)
            return

        changes = (
            ('te_rel_descr', 'te_rel_descr_templ', None),
            ('te_src_descr', 'te_src_descr_templ', None),
            ('le_scandir', 'le_scan_dir', None),
            ('geometry/header', 'geometry/job_view_header', None),
            ('le_data_dir', 'fsb_data_dir', lambda x: [x]),
            ('le_scan_dir', 'fsb_scan_dir', lambda x: [x]),
            ('le_dtor_save_dir', 'fsb_dtor_save_dir', lambda x: [x]),
            ('sty_style_selecter', 'sty_style_selector', None)
        )
        for old, new, conversion in changes:
            if self.config.contains(old):
                value = self.config.value(old)
                if conversion:
                    value = conversion(value)
                self.config.setValue(new, value)
                self.config.remove(old)

        for key in self.config.allKeys():
            if key.startswith('chb_'):
                value = self.config.value(key)
                if value not in (0, 1, 2):
                    value = 2 if bool(int(value)) else 0
                    self.config.setValue(key, value)
            elif key.startswith('spb_'):
                value = self.config.value(key)
                if not type(value) == int:
                    self.config.setValue(key, int(value))
            if key == 'spb_splitter_weight':
                self.config.remove(key)
            if key == 'bg_source' and self.config.value(key) == 0:
                self.config.setValue(key, 1)
            if key == 'le_ptpimg_key':
                value = self.config.value(key)
                if value:
                    ih.PTPimg.key = value
                    if self.config.value('chb_rehost'):
                        ih.PTPimg.enabled = True
                self.config.remove(key)
            if key.startswith('te_rel_descr'):
                value = self.config.value(key).replace('[url=%src_url%torrents.php?id=%tor_id%]',
                                                       '[url=%src_url%torrents.php?torrentid=%tor_id%]')
                self.config.setValue(key, value)

        if config_version < (2, 5, 2) <= version:
            self.config.remove('geometry/job_view_header')

        self.config.setValue('config_version', version)

    def main_widgets(self):
        self.topwidget = QWidget()
        self.bottomwidget = QWidget()
        self.splitter = QSplitter(Qt.Orientation.Vertical)

        self.tb_open_config = QToolButton()
        self.tb_open_config.setIcon(ThemeIcon('gear.svg'))
        self.tb_open_config.setAutoRaise(True)
        self.tb_open_config2 = QToolButton()
        self.tb_open_config2.setIcon(ThemeIcon('gear.svg'))
        self.tb_open_config2.setAutoRaise(True)

        self.te_paste_box = TPTextEdit()
        self.te_paste_box.setAcceptDrops(False)
        self.te_paste_box.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.te_paste_box.setPlaceholderText(gui_text.pb_placeholder)

        self.rb_tracker1 = QRadioButton(tr.RED.name)
        self.rb_tracker2 = QRadioButton(tr.OPS.name)
        self.bg_source = QButtonGroup()
        self.bg_source.addButton(self.rb_tracker1, 1)
        self.bg_source.addButton(self.rb_tracker2, 2)

        self.pb_add = QPushButton(gui_text.pb_add)
        self.pb_add.setEnabled(False)

        self.pb_open_dtors = QPushButton(gui_text.open_dtors)

        self.pb_scan = QPushButton(gui_text.pb_scan)
        self.pb_scan.setEnabled(False)

        self.job_data = JobModel(self.config)
        self.job_view = JobView(self.job_data)
        self.selection = self.job_view.selectionModel()
        self.result_view = ResultBrowser()

        self.button_stack = QStackedLayout()
        self.go_stop_stack = QStackedLayout()
        self.view_stack = QStackedLayout()

        self.tabs = CyclingTabBar()
        self.tabs.setDrawBase(False)
        self.tabs.setExpanding(False)
        self.tabs.addTab(gui_text.tab_joblist)

        self.job_buttons = QWidget()
        self.result_buttons = QWidget()
        self.result_buttons.hide()
        self.pb_clear_j = QPushButton(gui_text.pb_clear)
        self.pb_clear_j.setEnabled(False)
        self.pb_clear_r = QPushButton(gui_text.pb_clear)
        self.pb_clear_r.setEnabled(False)
        self.pb_rem_sel = QPushButton(gui_text.pb_rem_sel)
        self.pb_rem_sel.setEnabled(False)
        self.pb_crop = QPushButton(gui_text.pb_crop)
        self.pb_crop.setEnabled(False)
        self.pb_del_sel = QPushButton(gui_text.pb_del_sel)
        self.pb_del_sel.setEnabled(False)
        self.pb_rem_tr1 = QPushButton(gui_text.pb_del_tr1)
        self.pb_rem_tr1.setEnabled(False)
        self.pb_rem_tr2 = QPushButton(gui_text.pb_del_tr2)
        self.pb_rem_tr2.setEnabled(False)
        self.pb_open_tsavedir = QPushButton(gui_text.pb_open_tsavedir)
        self.pb_open_tsavedir.setEnabled(False)
        self.pb_open_upl_urls = QPushButton(gui_text.pb_open_upl_urls)
        self.pb_open_upl_urls.setEnabled(False)
        self.tb_go = QToolButton()
        self.tb_go.setEnabled(False)
        self.tb_go.setIcon(QIcon(':/switch.svg'))
        self.tb_go.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        self.pb_stop = QPushButton(gui_text.pb_stop)
        self.pb_stop.hide()

    def settings_window_widgets(self):
        self.config_tabs = QTabWidget()
        self.config_tabs.setDocumentMode(True)
        self.main_settings = QWidget()
        self.rehost = QWidget()
        self.cust_descr = QWidget()
        self.looks = QWidget()
        self.config_tabs.addTab(self.main_settings, gui_text.main_tab)
        self.config_tabs.addTab(self.rehost, gui_text.rehost_tab)
        self.config_tabs.addTab(self.cust_descr, gui_text.desc_tab)
        self.config_tabs.addTab(self.looks, gui_text.looks_tab)

        self.pb_cancel = QPushButton(gui_text.pb_cancel)
        self.pb_ok = QPushButton(gui_text.pb_ok)

        # rehost tab
        self.rh_on_off_container = QWidget()
        self.rehost_model = RehostModel()
        self.rehost_table = RehostTable(self.rehost_model)
        self.l_rehost_table = QLabel(gui_text.l_rehost_table)

        # descr tab
        self.l_variables = QLabel(gui_text.l_placeholders)
        self.l_own_uploads = QLabel(gui_text.l_own_uploads)
        self.pb_def_descr = QPushButton()
        self.pb_def_descr.setText(gui_text.pb_def_descr)
        self.l_variables.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        # looks tab
        self.l_job_list = QLabel(gui_text.l_job_list)
        self.l_colors = QLabel(gui_text.l_colors)
        self.l_colors.setTextFormat(Qt.TextFormat.RichText)
        self.l_colors.setOpenExternalLinks(True)
        self.color_examples = ColorExample()
        self.color_examples.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.color_examples.setSizeAdjustPolicy(QTextEdit.SizeAdjustPolicy.AdjustToContents)

    def user_input_elements(self):

        for el_name, (df, mk_lbl) in CONFIG_NAMES.items():
            typ_str, name = el_name.split('_', maxsplit=1)

            # instantiate
            obj_type = TYPE_MAP[typ_str]
            obj = obj_type()
            setattr(self, el_name, obj)

            # set values from config
            if not self.config.contains(el_name):
                self.config.setValue(el_name, df)

            change_sig, set_value_func = ACTION_MAP[obj_type]
            set_value_func(obj, self.config.value(el_name))

            # connection to ini
            change_sig(obj).connect(partial(self.config.setValue, el_name))

            # make Label
            if mk_lbl:
                label_name = 'l_' + name
                if obj_type == QCheckBox:
                    lbl = ClickableLabel()
                    lbl.clicked.connect(obj.click)
                else:
                    lbl = QLabel()
                lbl.setText(getattr(gui_text, label_name))
                setattr(self, label_name, lbl)

            if obj_type == FolderSelectBox:
                obj.dialog_caption = getattr(gui_text, f'tt_{el_name}')
                self.fsbs.append(obj)

        self.le_key_1.setCursorPosition(0)
        self.le_key_2.setCursorPosition(0)

        self.chb_deep_search.setText(gui_text.chb_deep_search)
        self.spb_deep_search_level.setMinimum(2)
        self.spb_verbosity.setMaximum(3)
        self.spb_verbosity.setMaximumWidth(40)

        self.chb_add_src_descr.setText(gui_text.chb_add_src_descr)

        self.spb_row_height.setMinimum(12)
        self.spb_row_height.setMaximum(99)
        self.spb_row_height.setMaximumWidth(40)

    def emit_state(self):
        for el_name in CONFIG_NAMES:
            obj = getattr(self, el_name)
            signal_func, _ = ACTION_MAP[type(obj)]
            value = self.config.value(el_name)
            signal_func(obj).emit(value)

wb = WidgetBank()
