import os
import re

from PyQt6.QtWidgets import (QFrame, QTextEdit, QComboBox, QFileDialog, QLineEdit, QTabBar, QVBoxLayout, QLabel,
                             QTextBrowser, QSizePolicy, QApplication, QStyleFactory, QToolButton, QPushButton)
from PyQt6.QtGui import QIcon, QAction, QIconEngine
from PyQt6.QtCore import Qt, QObject, QEvent, pyqtSignal, QSettings, QTimer, QAbstractListModel, QModelIndex


class TTfilter(QObject):
    def __init__(self, *args):
        super().__init__(*args)
        self.tt_enabled = False

    def set_tt_enabled(self, enabled: bool):
        self.tt_enabled = enabled

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.ToolTip and not self.tt_enabled:
            return True
        return False


class PButton(QPushButton):
    def animateClick(self):
        if self.isVisible():
            super().animateClick()


class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def mouseReleaseEvent(self, event):
        self.clicked.emit()
        super().mouseReleaseEvent(event)


class Application(QApplication):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scheme = None
        self.scheme_eval()
        self.styleHints().colorSchemeChanged.connect(self.scheme_eval)

    def set_style(self, style):
        super().setStyle(style)
        self.scheme_eval()

    def scheme_eval(self):
        style = self.style().name()
        cur_scheme = self.styleHints().colorScheme()
        if cur_scheme is not Qt.ColorScheme.Dark or style == 'windowsvista':
            scheme = Qt.ColorScheme.Light
        else:
            scheme = Qt.ColorScheme.Dark

        self.scheme = scheme


class ThemeEngine(QIconEngine):
    app = None
    offload = {}

    def __init__(self, file_name, f1, f2):
        super().__init__()
        if not self.app:
            self.__class__.app = QApplication.instance()
        self.file_name = file_name
        if self.file_name not in self.offload:
            self.offload[self.file_name] = {
                Qt.ColorScheme.Light: QIcon(f1),
                Qt.ColorScheme.Dark: QIcon(f2),
            }

    def pixmap(self, size, mode, state):
        return self.offload[self.file_name][self.app.scheme].pixmap(size, mode, state)


class ThemeIcon(QIcon):
    def __init__(self, file_name):
        f1 = f':/light/{file_name}'
        f2 = f':/dark/{file_name}'
        engine = ThemeEngine(file_name, f1, f2)
        super().__init__(engine)


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
    css_changed = pyqtSignal(str)

    texts = ('This is normal text<br>'
             '<span class=warning >This may require your attention</span><br>'
             '<span class=bad >Oops, something went bad</span><br>'
             '<span class=good >That went well</span><br>'
             '<a href="https://example.com">example.com</a>')

    def __init__(self, config: QSettings):
        super().__init__()
        self.current_colors = {i: '_' for i in range(1, 5)}

    @property
    def css(self):
        return (f'.warning {{color: {self.current_colors[1]}}}'
                f'.bad {{color: {self.current_colors[2]}}}'
                f'.good {{color: {self.current_colors[3]}}}'
                f'a {{color: {self.current_colors[4]}}}')

    def update_colors(self, color: str, index):
        color = ''.join(color.split())
        if color == self.current_colors[index]:
            return
        self.current_colors[index] = color
        css = self.css
        self.css_changed.emit(css)
        self.document().setDefaultStyleSheet(css)
        self.setHtml(self.texts)


class StyleSelector(QComboBox):
    def __init__(self):
        super().__init__()
        self.addItems(QStyleFactory.keys())


class ThemeSelector(QComboBox):
    current_data_changed = pyqtSignal(Qt.ColorScheme)

    def __init__(self):
        super().__init__()
        self.setModel(ThemeModel())
        self.currentTextChanged.connect(lambda x: self.current_data_changed.emit(self.currentData()))


class ThemeModel(QAbstractListModel):
    def __init__(self):
        super().__init__()
        self.themes = Qt.ColorScheme
        self.th_names = tuple(t.name.replace('Unknown', 'System') for t in self.themes)

    def rowCount(self, parent=None):
        return len(self.themes)

    def data(self, index: QModelIndex, role: int = 1):
        if role == Qt.ItemDataRole.DisplayRole:
            return self.th_names[index.row()]
        if role == Qt.ItemDataRole.UserRole:
            return self.themes(index.row())


class HistoryBox(QComboBox):
    list_changed = pyqtSignal(list)

    def set_list(self, item_list):
        if item_list:
            self.clear()
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
        self.folder_action = QAction()
        self.folder_action.setIcon(ThemeIcon('open-folder'))
        self.folder_action.triggered.connect(self.select_folder)
        self.lineEdit().addAction(self.folder_action, QLineEdit.ActionPosition.TrailingPosition)
        self.folder_button = self.lineEdit().findChild(QToolButton)
        self.dialog_caption = None

    def select_folder(self):
        selected = QFileDialog.getExistingDirectory(self, self.dialog_caption, self.currentText())
        if not selected:
            return
        selected = os.path.normpath(selected)
        self.add(selected)

    def setToolTip(self, txt):
        self.folder_action.setToolTip(txt)

    def installEventFilter(self, f):
        self.folder_button.installEventFilter(f)


class IniSettings(QSettings):
    int_regex = re.compile(r'#int\((\d+)\)')
    bool_regex = re.compile(r'#bool\((True|False)\)')

    def __init__(self, path):
        super().__init__(path, QSettings.Format.IniFormat)

    def setValue(self, key, value):
        if type(value) is int:
            value = f'#int({value})'
        elif type(value) is bool:
            value = f'#bool({value})'
        elif isinstance(value, list) and not value:
            value = '#empty list'
        super().setValue(key, value)

    def value(self, key, **kwargs):
        value = super().value(key, **kwargs)
        if isinstance(value, str):
            if int_match := self.int_regex.match(value):
                value = int(int_match.group(1))
            elif bool_match := self.bool_regex.match(value):
                value = bool_match.group(1) == 'True'
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
