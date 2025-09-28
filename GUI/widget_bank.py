from functools import partial

from PyQt6.QtWidgets import (QApplication, QWidget, QTextEdit, QPushButton, QToolButton, QRadioButton, QButtonGroup,
                             QSplitter, QLabel, QTabWidget, QLineEdit, QSpinBox, QCheckBox, QStackedLayout,
                             QTextBrowser, QSizePolicy, QToolBar)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from gazelle.tracker_data import TR
from core.tp_text import tp_version
from core.img_rehost import IH
from GUI import gui_text
from GUI.misc_classes import (TPTextEdit, CyclingTabBar, FolderSelectBox, IniSettings, TempPopUp, TTfilter,
                              ColorExample, PatientLineEdit, ThemeIcon, StyleSelector, ThemeSelector, ClickableLabel,
                              PButton)
from GUI.mv_classes import JobModel, JobView, RehostTable
from GUI.profiles import Profiles, STab

TYPE_MAP = {
    'le': QLineEdit,
    'ple': PatientLineEdit,
    'te': TPTextEdit,
    'chb': QCheckBox,
    'spb': QSpinBox,
    'fsb': FolderSelectBox,
    'sty': StyleSelector,
    'thm': ThemeSelector,
    'rht': RehostTable,
}
ACTION_MAP = {
    QLineEdit: (lambda x: x.textChanged, lambda x, y: x.setText(y)),
    PatientLineEdit: (lambda x: x.text_changed, lambda x, y: x.setText(y)),
    TPTextEdit: (lambda x: x.plain_text_changed, lambda x, y: x.setText(y)),
    QCheckBox: (lambda x: x.toggled, lambda x, y: x.setChecked(y)),
    QSpinBox: (lambda x: x.valueChanged, lambda x, y: x.setValue(y)),
    FolderSelectBox: (lambda x: x.list_changed, lambda x, y: x.set_list(y)),
    StyleSelector: (lambda x: x.currentTextChanged, lambda x, y: x.setCurrentText(y)),
    ThemeSelector: (lambda x: x.currentTextChanged, lambda x, y: x.setCurrentText(y)),
    RehostTable: (lambda x: x.rh_data_changed, lambda x, y: x.set_rh_data(y))
}
# name: (default value, make label)
CONFIG_NAMES = {
    STab.main: {
        'le_key_1': (None, True),
        'le_key_2': (None, True),
        'fsb_data_dir': ([], True),
        'chb_deep_search': (False, False),
        'spb_deep_search_level': (2, False),
        'fsb_scan_dir': ([], True),
        'fsb_dtor_save_dir': ([], False),
        'chb_save_dtors': (False, True),
        'chb_del_dtors': (False, True),
        'chb_file_check': (True, True),
        'chb_post_compare': (False, True),
        'chb_show_tips': (True, True),
        'spb_verbosity': (2, True),
    },
    STab.rehost: {
        'chb_rehost': (False, True),
        'le_whitelist': (gui_text.default_whitelist, True),
        'rht_rehost_table': ({}, True),
    },
    STab.descriptions: {
        'te_rel_descr_templ': (gui_text.def_rel_descr, False),
        'te_rel_descr_own_templ': (gui_text.def_rel_descr_own, False),
        'te_src_descr_templ': (gui_text.def_src_descr, False),
        'chb_add_src_descr': (True, False),
    },
    STab.looks: {
        'sty_style_selector': ('Fusion', True),
        'thm_theme_selector': ('System', True),
        'chb_toolbar_loc': (False, True),
        'chb_show_add_dtors': (True, True),
        'chb_show_rem_tr1': (False, True),
        'chb_show_rem_tr2': (False, True),
        'chb_no_icon': (False, True),
        'chb_show_tor_folder': (False, True),
        'chb_alt_row_colour': (True, True),
        'chb_show_grid': (False, True),
        'spb_row_height': (20, True),
        'ple_warning_color': ('orange', True),
        'ple_error_color': ('crimson', True),
        'ple_success_color': ('forestgreen', True),
        'ple_link_color': ('dodgerblue', True),
    },
}


class WidgetBank:
    def __init__(self):
        super().__init__()
        self.app = QApplication.instance()
        self.config = IniSettings("Transplant.ini")
        self.config_update()
        self.fsbs = []
        self.theme_writable = hasattr(self.app.styleHints(), 'setColorScheme')
        self.user_input_elements()
        self.main_window = None
        self.settings_window = None
        self.tt_filter = TTfilter()
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
        if config_version == tp_version:
            return
        if config_version is None:
            self.config.setValue('config_version', tp_version)
            return
        if isinstance(config_version, str):
            config_version = tuple(map(int, config_version.split('.')))

        changes = (
            ('te_rel_descr', 'te_rel_descr_templ', None),
            ('te_src_descr', 'te_src_descr_templ', None),
            ('le_scandir', 'le_scan_dir', None),
            ('geometry/header', 'geometry/job_view_header', None),
            ('le_data_dir', 'fsb_data_dir', lambda x: [x]),
            ('le_scan_dir', 'fsb_scan_dir', lambda x: [x]),
            ('le_dtor_save_dir', 'fsb_dtor_save_dir', lambda x: [x]),
            ('sty_style_selecter', 'sty_style_selector', None),
            ('rehost_data', 'rht_rehost_table', None),
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
                if value in (0, 1, 2):
                    value = bool(value)
                    self.config.setValue(key, value)
            elif key.startswith('spb_'):
                value = self.config.value(key)
                if not type(value) is int:
                    self.config.setValue(key, int(value))
            if key == 'spb_splitter_weight':
                self.config.remove(key)
            if key == 'bg_source' and self.config.value(key) == 0:
                self.config.setValue(key, 1)
            if key == 'le_ptpimg_key':
                value = self.config.value(key)
                if value:
                    IH.PTPimg.key = value
                    if self.config.value('chb_rehost') is True:
                        IH.PTPimg.enabled = True
                self.config.remove(key)
            if key.startswith('te_rel_descr'):
                value = self.config.value(key).replace('[url=%src_url%torrents.php?id=%tor_id%]',
                                                       '[url=%src_url%torrents.php?torrentid=%tor_id%]')
                self.config.setValue(key, value)

        if (g := {'main', 'rehost', 'looks'}) & set(self.config.childGroups()) != g:
            for tab, sd in CONFIG_NAMES.items():
                for el_name in sd:
                    if not self.config.contains(el_name):
                        print('not in config', el_name)
                        continue
                    value = self.config.value(el_name)
                    self.config.setValue(f'{tab.name}/{el_name}', value)
                    self.config.remove(el_name)
                    if self.config.contains(el_name):
                        print('not removed', el_name)

        if config_version < (2, 5, 2) <= tp_version:
            self.config.remove('geometry/job_view_header')

        self.config.setValue('config_version', tp_version)

    def main_widgets(self):
        self.topwidget = QWidget()
        self.bottomwidget = QWidget()
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter_handle = None

        self.toolbar = QToolBar()
        self.toolbar.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        self.toolbar.setMovable(False)
        self.profiles = Profiles()
        self.tb_spacer = QWidget()
        self.tb_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.tb_open_config = QToolButton()
        self.tb_open_config.setIcon(ThemeIcon('gear.svg'))

        self.te_paste_box = TPTextEdit()
        self.te_paste_box.setAcceptDrops(False)
        self.te_paste_box.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.te_paste_box.setPlaceholderText(gui_text.pb_placeholder)

        self.rb_tracker1 = QRadioButton(TR.RED.name)
        self.rb_tracker2 = QRadioButton(TR.OPS.name)
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
        self.result_view = QTextBrowser()
        self.result_view.setOpenExternalLinks(True)

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
        self.pb_clear_j = PButton(gui_text.pb_clear)
        self.pb_clear_j.setEnabled(False)
        self.pb_clear_r = PButton(gui_text.pb_clear)
        self.pb_clear_r.setEnabled(False)
        self.pb_rem_sel = PButton(gui_text.pb_rem_sel)
        self.pb_rem_sel.setEnabled(False)
        self.pb_crop = PButton(gui_text.pb_crop)
        self.pb_crop.setEnabled(False)
        self.pb_del_sel = PButton(gui_text.pb_del_sel)
        self.pb_del_sel.setEnabled(False)
        self.pb_rem_tr1 = PButton(gui_text.pb_rem_tr1)
        self.pb_rem_tr1.setEnabled(False)
        self.pb_rem_tr2 = PButton(gui_text.pb_rem_tr2)
        self.pb_rem_tr2.setEnabled(False)
        self.pb_open_tsavedir = PButton(gui_text.pb_open_tsavedir)
        self.pb_open_tsavedir.setEnabled(False)
        self.pb_open_upl_urls = PButton(gui_text.pb_open_upl_urls)
        self.pb_open_upl_urls.setEnabled(False)
        self.pb_go = QPushButton()
        self.pb_go.setEnabled(False)
        self.pb_go.setIcon(QIcon(':/switch.svg'))

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

        self.pb_ok = QPushButton(gui_text.pb_ok)

        # main tab
        self.tb_key_test1 = QToolButton()
        self.tb_key_test1.setText(gui_text.tb_test)
        self.tb_key_test1.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        self.tb_key_test2 = QToolButton()
        self.tb_key_test2.setText(gui_text.tb_test)
        self.tb_key_test2.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)

        # rehost tab
        self.rh_on_off_container = QWidget()

        # descr tab
        self.l_variables = QLabel(gui_text.l_placeholders)
        self.l_own_uploads = QLabel(gui_text.l_own_uploads)
        self.pb_def_descr = QPushButton()
        self.pb_def_descr.setText(gui_text.pb_def_descr)
        self.l_variables.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        # looks tab
        self.l_job_list = QLabel(gui_text.l_job_list)
        self.l_colors = QLabel(gui_text.l_colors)
        self.l_colors.setOpenExternalLinks(True)
        self.color_examples = ColorExample(self.config)
        self.color_examples.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.color_examples.setSizeAdjustPolicy(QTextEdit.SizeAdjustPolicy.AdjustToContents)

    def user_input_elements(self):
        for tab, sd in CONFIG_NAMES.items():
            self.config.beginGroup(tab.name)
            for el_name, (df, mk_lbl) in sd.items():
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
                    obj.dialog_caption = gui_text.tooltips[el_name]
                    self.fsbs.append(obj)

            self.config.endGroup()

        if not self.theme_writable:
            self.thm_theme_selector.setEnabled(False)

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
        for tab, sd in CONFIG_NAMES.items():
            self.config.beginGroup(tab.name)
            for el_name in sd:
                obj = getattr(self, el_name)
                signal_func, _ = ACTION_MAP[type(obj)]
                value = self.config.value(el_name)
                signal_func(obj).emit(value)
                signal_func(obj).connect(partial(self.config.setValue, f'{tab.name}/{el_name}'))

            self.config.endGroup()


wb = WidgetBank()
