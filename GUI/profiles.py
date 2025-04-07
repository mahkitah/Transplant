from pathlib import Path
from enum import IntFlag, auto

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QCheckBox, QButtonGroup, QDialog,
                             QPushButton, QComboBox, QToolButton, QMessageBox)

from GUI import gui_text


class STab(IntFlag):
    main = auto()
    rehost = auto()
    descriptions = auto()
    looks = auto()


class NewProfile(QDialog):
    new_profile = pyqtSignal(str, STab)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle(gui_text.newprof_window)

        self.selected = STab(0)
        self.bg = QButtonGroup()
        self.bg.setExclusive(False)
        self.le_name = QLineEdit()
        self.pb_ok = QPushButton(gui_text.pb_ok)
        self.pb_cancel = QPushButton(gui_text.pb_cancel)

        for s in STab:
            chb = QCheckBox(s.name, self)
            self.bg.addButton(chb, id=s.value)

        self.bg.idToggled.connect(self.update_sel)
        self.bg.idToggled.connect(self.ok_enabled)
        self.pb_ok.clicked.connect(self.okay)
        self.pb_cancel.clicked.connect(self.reject)
        self.le_name.textChanged.connect(self.ok_enabled)

        self.do_layout()

    def update_sel(self, b_id: int, _: bool):
        self.selected ^= b_id

    def ok_enabled(self):
        self.pb_ok.setEnabled(bool(self.selected and self.le_name.text()))

    def open(self):
        for b in self.bg.buttons():
            b.setChecked(True)
        self.le_name.clear()
        self.le_name.setFocus()
        super().open()

    def okay(self):
        self.new_profile.emit(self.le_name.text(), self.selected)
        self.accept()

    def do_layout(self):
        chb_lay = QVBoxLayout()
        chb_lay.setSpacing(0)
        chb_lay.setContentsMargins(0, 0, 0, 0)
        for b in self.bg.buttons():
            chb_lay.addWidget(b)

        bottom_buts = QHBoxLayout()
        bottom_buts.addStretch()
        bottom_buts.addWidget(self.pb_ok)
        bottom_buts.addWidget(self.pb_cancel)

        lay = QVBoxLayout(self)
        lay.setSpacing(lay.spacing() * 2)
        lay.addWidget(QLabel(gui_text.newprof_name_label))
        lay.addWidget(self.le_name)
        lay.addLayout(chb_lay)
        lay.addLayout(bottom_buts)


class Profiles(QWidget):
    new_profile = pyqtSignal(str, STab)
    save_profile = pyqtSignal(str)
    load_profile = pyqtSignal(str)

    def __init__(self, *args):
        super().__init__(*args)
        self.setMaximumHeight(20)
        self.combo = QComboBox()
        self.combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._new_prof_diag = None

        self.buttons = []
        for txt in gui_text.profile_buttons:
            btn = QToolButton()
            btn.setText(txt)
            btn.clicked.connect(getattr(self, txt.lower()))
            self.buttons.append(btn)

        self.new_prof_diag.new_profile.connect(self.new_profile.emit)
        self.combo.currentIndexChanged.connect(self.disable_buttons)
        self.refresh()
        self.disable_buttons(self.combo.currentIndex())

        self.do_layout()

    @property
    def new_prof_diag(self):
        if not self._new_prof_diag:
            self._new_prof_diag = NewProfile(self)
        return self._new_prof_diag

    def load(self):
        self.load_profile.emit(f'{self.combo.currentText()}.tpp')

    def save(self):
        cur_prof = self.combo.currentText()
        if not cur_prof:
            return

        if self.confirm(cur_prof, gui_text.prof_action_save):
            self.save_profile.emit(f'{cur_prof}.tpp')

    def new(self):
        self.new_prof_diag.open()

    def confirm(self, profile: str, action: str):
        buts = QMessageBox.StandardButton
        conf_diag = QMessageBox(self)
        conf_diag.setStandardButtons(buts.Ok | buts.Cancel)
        conf_diag.setIcon(QMessageBox.Icon.Warning)
        conf_diag.setText(gui_text.prof_conf.format(profile=profile, action=action))
        return conf_diag.exec() == buts.Ok

    def refresh(self):
        if self.combo.count():
            self.combo.clear()
        self.combo.addItems(map(lambda p: p.stem, Path.cwd().glob('*.tpp')))

    def delete(self):
        cur_prof = self.combo.currentText()
        if self.confirm(cur_prof, gui_text.prof_action_del):
            file = Path(f'{cur_prof}.tpp')
            if file.is_file():
                file.unlink()
            self.combo.removeItem(self.combo.findText(cur_prof))

    def disable_buttons(self, combo_idx: int):
        for i in (0, 1, 3):
            self.buttons[i].setDisabled(combo_idx == -1)

    def do_layout(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(5, 0, 0, 0)
        lay.setSpacing(3)
        lay.addWidget(QLabel(gui_text.profiles))
        lay.addWidget(self.combo)
        for b in self.buttons:
            lay.addWidget(b)
