from PyQt6.QtWidgets import QWidget, QTextEdit, QPushButton, QToolButton, QRadioButton, QButtonGroup,\
    QSplitter, QSizePolicy, QLabel, QTabWidget, QLineEdit, QSpinBox, QCheckBox, QStackedLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from gazelle.tracker_data import tr
from lib import ui_text
from GUI.misc_classes import TPTextEdit, CyclingTabBar, FolderSelectBox, ResultBrowser, IniSettings, TempPopUp,\
    ColorExample, PatientLineEdit
from GUI.mv_classes import JobModel, JobView, RehostModel, RehostTable

TYPE_MAP = {
    'le': QLineEdit,
    'ple': PatientLineEdit,
    'te': TPTextEdit,
    'chb': QCheckBox,
    'spb': QSpinBox,
    'fsb': FolderSelectBox
}
ACTION_MAP = {
    QLineEdit: (lambda x: x.textChanged, lambda x, y: x.setText(y)),
    PatientLineEdit: (lambda x: x.text_changed, lambda x, y: x.setText(y)),
    TPTextEdit: (lambda x: x.plain_text_changed, lambda x, y: x.setText(y)),
    QCheckBox: (lambda x: x.stateChanged, lambda x, y: x.setCheckState(Qt.CheckState(y))),
    QSpinBox: (lambda x: x.valueChanged, lambda x, y: x.setValue(y)),
    FolderSelectBox: (lambda x: x.list_changed, lambda x, y: x.set_list(y))
}
# name: (default value, make label)
CONFIG_NAMES = {
    'le_key_1': (None, True),
    'le_key_2': (None, True),
    'fsb_data_dir': ([], True),
    'chb_deep_search': (0, False),
    'spb_deep_search_level': (2, False),
    'fsb_scan_dir': ([], True),
    'fsb_dtor_save_dir': ([], True),
    'chb_save_dtors': (0, False),
    'chb_del_dtors': (0, True),
    'chb_file_check': (2, True),
    'chb_post_compare': (0, True),
    'chb_show_tips': (2, True),
    'spb_verbosity': (2, True),
    'te_rel_descr_templ': (ui_text.def_rel_descr, False),
    'te_rel_descr_own_templ': (ui_text.def_rel_descr_own, False),
    'te_src_descr_templ': (ui_text.def_src_descr, False),
    'chb_add_src_descr': (2, False),
    'chb_no_icon': (0, True),
    'chb_alt_row_colour': (2, True),
    'chb_show_grid': (0, True),
    'spb_row_height': (20, True),
    'chb_show_add_dtors': (2, True),
    'chb_show_rem_tr1': (0, True),
    'chb_show_rem_tr2': (0, True),
    'chb_rehost': (0, True),
    'le_whitelist': (ui_text.default_whitelist, True),
    'ple_warning_color': ('orange', True),
    'ple_error_color': ('crimson', True),
    'ple_success_color': ('forestgreen', True),
    'ple_link_color': ('dodgerblue', True),
}


class WidgetBank:
    def __init__(self):
        super().__init__()
        self.config = IniSettings("Transplant.ini")
        self.user_input_elements()
        self.main_window = None
        self.settings_window = None
        self.main_widgets()
        self.settings_window_widgets()

        self._pop_up = None

    @property
    def pop_up(self):
        if not self._pop_up:
            self._pop_up = TempPopUp(self.main_window)

        return self._pop_up

    def main_widgets(self):
        self.topwidget = QWidget()
        self.bottomwidget = QWidget()
        self.splitter = QSplitter(Qt.Orientation.Vertical)

        self.tb_open_config = QToolButton()
        self.tb_open_config.setIcon(QIcon(':/gear.svg'))
        self.tb_open_config.setAutoRaise(True)
        self.tb_open_config2 = QToolButton()
        self.tb_open_config2.setIcon(QIcon(':/gear.svg'))
        self.tb_open_config2.setAutoRaise(True)

        self.te_paste_box = TPTextEdit()
        self.te_paste_box.setAcceptDrops(False)
        self.te_paste_box.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.te_paste_box.setPlaceholderText(ui_text.pb_placeholder)

        self.rb_tracker1 = QRadioButton(tr.RED.name)
        self.rb_tracker2 = QRadioButton(tr.OPS.name)
        self.bg_source = QButtonGroup()
        self.bg_source.addButton(self.rb_tracker1, 1)
        self.bg_source.addButton(self.rb_tracker2, 2)

        self.pb_add = QPushButton(ui_text.pb_add)
        self.pb_add.setEnabled(False)

        self.pb_open_dtors = QPushButton(ui_text.open_dtors)

        self.pb_scan = QPushButton(ui_text.pb_scan)
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
        self.pb_crop = QPushButton(ui_text.pb_crop)
        self.pb_crop.setEnabled(False)
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
        self.tb_go.setIcon(QIcon(':/switch.svg'))
        self.tb_go.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        self.pb_stop = QPushButton(ui_text.pb_stop)
        self.pb_stop.hide()

    def settings_window_widgets(self):
        self.config_tabs = QTabWidget()
        self.config_tabs.setDocumentMode(True)
        self.main_settings = QWidget()
        self.rehost = QWidget()
        self.cust_descr = QWidget()
        self.looks = QWidget()
        self.config_tabs.addTab(self.main_settings, ui_text.main_tab)
        self.config_tabs.addTab(self.rehost, ui_text.rehost_tab)
        self.config_tabs.addTab(self.cust_descr, ui_text.desc_tab)
        self.config_tabs.addTab(self.looks, ui_text.looks_tab)

        self.pb_cancel = QPushButton(ui_text.pb_cancel)
        self.pb_ok = QPushButton(ui_text.pb_ok)

        # rehost tab
        self.rh_on_off_container = QWidget()
        self.rehost_model = RehostModel()
        self.rehost_table = RehostTable(self.rehost_model)
        self.l_rehost_table = QLabel(ui_text.l_rehost_table)

        # descr tab
        self.l_variables = QLabel(ui_text.l_placeholders)
        self.l_own_uploads = QLabel(ui_text.l_own_uploads)
        self.pb_def_descr = QPushButton()
        self.pb_def_descr.setText(ui_text.pb_def_descr)
        self.l_variables.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        # looks tab
        self.l_job_list = QLabel(ui_text.l_job_list)
        self.l_colors = QLabel(ui_text.l_colors)
        self.l_colors.setTextFormat(Qt.TextFormat.RichText)
        self.l_colors.setOpenExternalLinks(True)
        self.color_examples = ColorExample()
        self.color_examples.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.color_examples.setSizeAdjustPolicy(QTextEdit.SizeAdjustPolicy.AdjustToContents)

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

            # set values from config
            if not self.config.contains(el_name):
                self.config.setValue(el_name, df)

            change_sig, set_value = ACTION_MAP[type(obj)]
            value = self.config.value(el_name)
            set_value(obj, value)

            # connection to ini
            change_sig(obj).connect(make_lambda(el_name))

            # make Label
            if mk_lbl:
                label_name = 'l_' + name
                setattr(self, label_name, QLabel(getattr(ui_text, label_name)))

            if obj_type == FolderSelectBox:
                obj.dialog_caption = getattr(ui_text, f'tt_{el_name}')

        self.le_key_1.setCursorPosition(0)
        self.le_key_2.setCursorPosition(0)

        self.chb_deep_search.setText(ui_text.chb_deep_search)
        self.spb_deep_search_level.setMinimum(2)
        self.spb_verbosity.setMaximum(3)
        self.spb_verbosity.setMaximumWidth(40)

        self.chb_add_src_descr.setText(ui_text.chb_add_src_descr)

        self.spb_row_height.setMinimum(12)
        self.spb_row_height.setMaximum(99)
        self.spb_row_height.setMaximumWidth(40)

    def emit_state(self):
        for el_name in CONFIG_NAMES:
            obj = getattr(self, el_name)
            signal_func, _ = ACTION_MAP[type(obj)]
            value = self.config.value(el_name)
            signal_func(obj).emit(value)

    def fsbs(self):
        for el_name in CONFIG_NAMES:
            if el_name.startswith('fsb_'):
                yield getattr(self, el_name)

wb = WidgetBank()
