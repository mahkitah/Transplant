import os
import re

from PyQt6.QtWidgets import QFrame, QTextEdit, QComboBox, QFileDialog, QLineEdit, QTabBar, QVBoxLayout, QLabel,\
    QTextBrowser, QSizePolicy
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt, pyqtSignal, QSettings, QTimer


class TempPopUp(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setFrameShape(QFrame.Shape.Box)
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.close)
        self.message = QLabel()
        lay = QVBoxLayout(self)
        lay.addWidget(self.message)

    def pop_up(self, message, time: int = 2000):
        self.message.setText(message)
        self.show()
        self.timer.start(time)


class PatientLineEdit(QLineEdit):
    text_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.last_text = None
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(1500)
        self.textChanged.connect(self.timer.start)
        self.timer.timeout.connect(self.emit_change)

    def emit_change(self):
        if self.text() == self.last_text:
            return
        self.last_text = self.text()
        self.text_changed.emit(self.text())


class ColorExample(QTextBrowser):
    texts = (
        'This is normal text',
        'This may require your attention',
        'Oops, something went bad',
        'That went well',
        'http://example.com/'
    )

    def __init__(self):
        super().__init__()
        self.lines = list(self.texts)
        link = self.lines[4]
        self.lines[4] = f'<a href="{link}">{link}</a>'
        self.current_colors = {i: '_' for i in range(1, 5)}

    def update_colors(self, color: str, index):
        color = ''.join(color.split())
        if color == self.current_colors[index]:
            return
        self.current_colors[index] = color

        style = f' style="color: {color}"' # if color else ''

        line = self.texts[index]
        if index == 4:
            line = f'<a href="{line}"{style}>{line}</a>'
        else:
            line = f'<span{style}>{line}</span>'
        self.lines[index] = line
        self.clear()
        self.append('<br>'.join(self.lines))


class ResultBrowser(QTextBrowser):
    def __init__(self):
        super().__init__()
        self.setOpenExternalLinks(True)
        self.def_format = self.currentCharFormat()

    def append(self, text: str) -> None:
        self.setCurrentCharFormat(self.def_format)
        super().append(text)


class HistoryBox(QComboBox):
    list_changed = pyqtSignal(list)

    def set_list(self, item_list):
        if item_list:
            self.addItems(item_list)
            self.list_changed.emit(item_list)

    @property
    def list(self):
        return [self.itemText(i) for i in range(self.count())]

    def add(self, txt):
        if (index := self.findText(txt)) > 0:
            self.setCurrentIndex(index)
        elif index < 0:
            self.insertItem(0, txt)
            self.setCurrentIndex(0)
            self.list_changed.emit(self.list)

    def consolidate(self):
        self.add(self.currentText())
        if self.currentIndex() > 0:
            txt = self.currentText()
            self.removeItem(self.currentIndex())
            self.add(txt)


class FolderSelectBox(HistoryBox):
    def __init__(self):
        super().__init__()
        self.setEditable(True)
        self.setMaxCount(8)
        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Preferred)
        self.setSizeAdjustPolicy(self.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.folder_button = QAction()
        self.folder_button.setIcon(QIcon(':/open-folder'))
        self.folder_button.triggered.connect(self.select_folder)
        self.lineEdit().addAction(self.folder_button, QLineEdit.ActionPosition.TrailingPosition)
        self.dialog_caption = None

    def select_folder(self):
        selected = QFileDialog.getExistingDirectory(self, self.dialog_caption, self.currentText())
        if not selected:
            return
        selected = os.path.normpath(selected)
        self.add(selected)

    def setToolTip(self, txt):
        self.folder_button.setToolTip(txt)


class IniSettings(QSettings):
    int_regex = re.compile(r'#int\((\d+)\)')
    # bool_regex = re.compile(r'#bool\((True|False)\)')

    def __init__(self, path):
        super().__init__(path, QSettings.Format.IniFormat)

    def setValue(self, key, value):
        if type(value) == int:
            value = f'#int({value})'
        # elif type(value) == bool:
        #     value = f'#bool({value})'
        elif value == []:
            value = '#empty list'

        super().setValue(key, value)

    def value(self, key, **kwargs):
        value = super().value(key, **kwargs)
        if isinstance(value, str):
            if int_match := self.int_regex.match(value):
                value = int(int_match.group(1))
            # elif bool_match := self.bool_regex.match(value):
            #     value = bool_match.group(1) == 'True'
            elif value == '#empty list':
                value = []

        return value


class TPTextEdit(QTextEdit):
    plain_text_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.textChanged.connect(lambda: self.plain_text_changed.emit(self.toPlainText()))


class CyclingTabBar(QTabBar):
    def next(self):
        total = self.count()
        if total > 1:
            current = self.currentIndex()

            if current < total - 1:
                self.setCurrentIndex(current + 1)
            else:
                self.setCurrentIndex(0)