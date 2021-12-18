import os
import re
import random

from PyQt5.QtWidgets import QTextEdit, QHeaderView, QAction, QTableView, QComboBox, QFileDialog, QLineEdit
from PyQt5.QtGui import QIcon, QKeyEvent
from PyQt5.QtCore import Qt, pyqtSignal, QAbstractTableModel, QSettings
from lib import ui_text
from gazelle.tracker_data import tr_data


class HistoryBox(QComboBox):
    list_changed = pyqtSignal(list)

    def set_list(self, item_list):
        if item_list:
            self.addItems(item_list)
            self.list_changed.emit(item_list)

    def contains(self, txt):
        if self.findText(txt) < 0:
            return False
        else:
            return True

    def items(self):
        for i in range(self.count()):
            yield self.itemText(i)

    def top_insert(self, txt):
        if not self.contains(txt):
            self.insertItem(0, txt)
            self.setCurrentIndex(0)
            self.list_changed.emit(list(self.items()))

    def consolidate(self):
        if not self.contains(self.currentText()):
            self.top_insert(self.currentText())
        if self.currentIndex() > 0:
            txt = self.currentText()
            self.removeItem(self.currentIndex())
            self.top_insert(txt)


class FolderSelectBox(HistoryBox):
    def __init__(self):
        super().__init__()
        self.setEditable(True)
        self.folder_button = QAction()
        self.lineEdit().addAction(self.folder_button, QLineEdit.TrailingPosition)
        self.folder_button.triggered.connect(self.select_folder)
        self.dialog_caption = None

    def select_folder(self):
        selected = QFileDialog.getExistingDirectory(self, self.dialog_caption, self.currentText())
        if not selected:
            return
        selected = os.path.normpath(selected)
        self.top_insert(selected)

    def setToolTip(self, txt):
        self.folder_button.setToolTip(txt)


class IniSettings(QSettings):
    def __init__(self, path):
        super().__init__(path, QSettings.IniFormat)

    def setValue(self, key, value):
        if type(value) == int:
            value = f'#int({value})'
        elif type(value) == bool:
            value = f'#bool({value})'

        super().setValue(key, value)

    def value(self, key, defaultValue=None):
        value = super().value(key, defaultValue=defaultValue)
        if isinstance(value, str):
            if value.startswith('#int('):
                as_str = re.match(r'#int\((\d+)\)', value).group(1)
                value = int(as_str)
            elif value.startswith('#bool('):
                as_str = re.match(r'#bool\((True|False)\)', value).group(1)
                value = as_str == 'True'

        return value


class TPTextEdit(QTextEdit):
    plainTextChanged = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.textChanged.connect(lambda: self.plainTextChanged.emit(self.toPlainText()))


class TPTableView(QTableView):
    selectionChange = pyqtSignal(list)
    key_with_mod_sig = pyqtSignal(QKeyEvent)

    def selectionChanged(self, selected, deselected):
        super().selectionChanged(selected, deselected)
        self.selectionChange.emit(self.selectedIndexes())

    def selected_rows(self):
        return list(set((x.row() for x in self.selectedIndexes())))

    def keyPressEvent(self, event: QKeyEvent):
        if event.modifiers() == Qt.ControlModifier:
            self.key_with_mod_sig.emit(event)
        super().keyPressEvent(event)


class TPHeaderView(QHeaderView):
    sectionVisibilityChanged = pyqtSignal(int, bool)

    def __init__(self, orientation, headers):
        super().__init__(orientation)
        self.headers = headers
        self.context_actions()
        self.sectionVisibilityChanged.connect(self.set_action_icons)
        self.sectionVisibilityChanged.connect(self.disable_actions)
        self.setContextMenuPolicy(Qt.ActionsContextMenu)

    def hideSection(self, index):
        super().hideSection(index)
        self.sectionVisibilityChanged.emit(index, True)

    def showSection(self, index):
        super().showSection(index)
        self.sectionVisibilityChanged.emit(index, False)

    def setSectionHidden(self, index, hide):
        super().setSectionHidden(index, hide)
        self.sectionVisibilityChanged.emit(index, hide)

    def restoreState(self, state):
        super().restoreState(state)
        for x in range(self.count()):
            self.sectionVisibilityChanged.emit(x, self.isSectionHidden(x))

    def context_actions(self):
        self.ac_restore_all = QAction(ui_text.header_restore)
        self.addAction(self.ac_restore_all)
        self.ac_restore_all.triggered.connect(self.set_all_sections_visible)

        for n, h in enumerate(self.headers):
            action_name = f'ac_header{n}'
            setattr(self, action_name, QAction())
            action = getattr(self, action_name)
            action.setText(h)
            self.addAction(action)

            def make_lambda(index):
                return lambda: self.setSectionHidden(index, not self.isSectionHidden(index))

            action.triggered.connect(make_lambda(n))

    def set_all_sections_visible(self):
        for x in range(self.count()):
            self.showSection(x)

    def disable_actions(self):
        if not self.hiddenSectionCount():
            self.ac_restore_all.setEnabled(False)

        elif self.hiddenSectionCount() == self.count() - 1:
            section = 0
            while self.isSectionHidden(section):
                section += 1

            self.actions()[section + 1].setEnabled(False)

        else:
            for action in self.actions():
                action.setEnabled(True)

    def set_action_icons(self, index, hidden):
        if hidden:
            self.actions()[index + 1].setIcon(QIcon('gui_files/blank-check-box.svg'))
        else:
            self.actions()[index + 1].setIcon(QIcon('gui_files/check-box.svg'))


class JobModel(QAbstractTableModel):
    def __init__(self, parentconfig):
        """
        Can keep a job.
        """
        super().__init__()
        self.jobs = []
        self.config = parentconfig
        self._headers = None

    @property
    def headers(self):
        if self._headers:
            return self._headers
        else:
            headers = []
            index = 0
            while True:
                try:
                    headers.append(getattr(ui_text, f'header{index}'))
                except AttributeError:
                    self._headers = headers
                    return headers
                index += 1

    def data(self, index, role):
        column = index.column()
        job = self.jobs[index.row()]
        no_icon = bool(int(self.config.value('chb_no_icon')))

        if role == Qt.DisplayRole or role == Qt.EditRole:
            if column == 0 and no_icon:
                return job.src_tr.name
            if column == 1:
                return job.display_name or job.tor_id
            if column == 2:
                return job.dest_group

        if role == Qt.CheckStateRole and column == 3:
            return Qt.Checked if job.new_dtor else Qt.Unchecked

        if role == Qt.DecorationRole and column == 0 and not no_icon:
            return QIcon(tr_data[job.src_tr]['favicon'])

    def rowCount(self, index):
        return len(self.jobs)

    def columnCount(self, index):
        return len(self.headers)

    # noinspection PyTypeChecker
    def flags(self, index):
        if index.column() == 2:
            return super().flags(index) | Qt.ItemIsEditable
        if index.column() == 3:
            return super().flags(index) | Qt.ItemIsUserCheckable
        else:
            return super().flags(index)

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.headers[section]

        if role == Qt.ToolTipRole and orientation == Qt.Horizontal and section == 3:
            if bool(int(self.config.value('chb_show_tips'))):
                return ui_text.ttm_header3
        else:
            return super().headerData(section, orientation, role)

    def setData(self, index, value, role):
        job = self.jobs[index.row()]
        column = index.column()

        if column == 2:
            if value:
                try:
                    value = str(int(value))
                except ValueError:
                    return False
            job.dest_group = value or None

        if column == 3 and role == Qt.CheckStateRole:
            job.new_dtor = True if value == Qt.Checked else False

        return True

    def header_double_clicked(self, column: int):
        if column == 3:
            allchecked = all(j.new_dtor for j in self.jobs)

            for i, job in enumerate(self.jobs):
                index = self.index(i, column)
                if not allchecked:
                    if not job.new_dtor:
                        job.new_dtor = True
                        self.dataChanged.emit(index, index, [])
                else:
                    job.new_dtor = False
                    self.dataChanged.emit(index, index, [])

    def append(self, item):
        if item not in self.jobs:
            self.jobs.append(item)
            self.layoutChanged.emit()

    def clear(self):
        self.jobs.clear()
        self.layoutChanged.emit()

    def remove(self, item):
        self.jobs.remove(item)
        self.layoutChanged.emit()

    def del_multi(self, indices):
        indices.sort(reverse=True)
        for i in indices:
            del self.jobs[i]
        self.layoutChanged.emit()

    def filter_for_attr(self, attr, value):
        self.jobs[:] = (j for j in self.jobs if not getattr(j, attr) == value)
        self.layoutChanged.emit()

    def __bool__(self):
        return bool(self.jobs)

    def __iter__(self):
        for j in self.jobs:
            yield j
