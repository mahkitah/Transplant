import os
import re

from GUI.files import get_file

from PyQt6.QtWidgets import QTextEdit, QHeaderView, QTableView, QComboBox, QFileDialog, QLineEdit, QTabBar
from PyQt6.QtGui import QIcon, QKeyEvent, QAction
from PyQt6.QtCore import Qt, pyqtSignal, QAbstractTableModel, QSettings, QModelIndex
from lib import ui_text


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
            self.list_changed.emit(list(self.list))

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
        self.setSizeAdjustPolicy(self.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.folder_button = QAction()
        self.lineEdit().addAction(self.folder_button, QLineEdit.ActionPosition.TrailingPosition)
        self.folder_button.triggered.connect(self.select_folder)
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
    def __init__(self, path):
        super().__init__(path, QSettings.Format.IniFormat)

    def setValue(self, key, value):
        if type(value) == int:
            value = f'#int({value})'
        elif type(value) == bool:
            value = f'#bool({value})'
        elif value == []:
            value = '#empty list'

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


class JobView(QTableView):
    selection_changed = pyqtSignal(list)
    key_override_sig = pyqtSignal(QKeyEvent)

    def __init__(self, model):
        super().__init__()
        self.setModel(model)
        self.setEditTriggers(QTableView.EditTrigger.SelectedClicked | QTableView.EditTrigger.DoubleClicked |
                             QTableView.EditTrigger.AnyKeyPressed)
        self.setHorizontalHeader(ContextHeaderView(Qt.Orientation.Horizontal, self))
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.verticalHeader().hide()
        self.verticalHeader().setMinimumSectionSize(12)
        self.horizontalHeader().setSectionsMovable(True)
        self.horizontalHeader().setMinimumSectionSize(18)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

    def selectionChanged(self, selected, deselected):
        super().selectionChanged(selected, deselected)
        self.selection_changed.emit(self.selected_rows())

    def selected_rows(self):
        return list(set((x.row() for x in self.selectedIndexes())))

    def keyPressEvent(self, event: QKeyEvent):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_Tab:
            self.key_override_sig.emit(event)
        else:
            super().keyPressEvent(event)


class ContextHeaderView(QHeaderView):
    a_model_has_been_set = pyqtSignal()
    section_visibility_changed = pyqtSignal(int, bool)

    def __init__(self, orientation, parent):
        super().__init__(orientation, parent)
        self.section_visibility_changed.connect(self.set_action_icon)
        self.section_visibility_changed.connect(self.disable_actions)
        self.a_model_has_been_set.connect(self.context_actions)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)

    def setModel(self, model):
        super().setModel(model)
        self.a_model_has_been_set.emit()

    def text(self, section):
        return self.model().headerData(section, self.orientation(), Qt.ItemDataRole.DisplayRole)

    def hideSection(self, index):
        super().hideSection(index)
        self.section_visibility_changed.emit(index, True)

    def showSection(self, index):
        super().showSection(index)
        self.section_visibility_changed.emit(index, False)

    def setSectionHidden(self, index, hide):
        super().setSectionHidden(index, hide)
        self.section_visibility_changed.emit(index, hide)

    def restoreState(self, state):
        super().restoreState(state)
        for x in range(self.count()):
            self.section_visibility_changed.emit(x, self.isSectionHidden(x))

    def context_actions(self):
        self.ac_restore_all = QAction(ui_text.header_restore)
        self.addAction(self.ac_restore_all)
        self.ac_restore_all.triggered.connect(self.set_all_sections_visible)

        for i in range(self.model().columnCount(None)):
            action_name = f'ac_header{i}'
            setattr(self, action_name, QAction())
            action = getattr(self, action_name)
            action.setText(self.text(i))
            self.addAction(action)
            self.set_action_icon(i, self.isSectionHidden(i))

            def make_lambda(index):
                return lambda: self.setSectionHidden(index, not self.isSectionHidden(index))

            action.triggered.connect(make_lambda(i))

    def set_all_sections_visible(self):
        for x in range(self.count()):
            self.showSection(x)

    def disable_actions(self):
        if not self.hiddenSectionCount():
            self.ac_restore_all.setEnabled(False)

        # Disable action for last visible section
        # so it's impossible to hide all sections
        elif self.hiddenSectionCount() == self.count() - 1:
            section = 0
            while self.isSectionHidden(section):
                section += 1

            self.actions()[section + 1].setEnabled(False)

        else:
            for action in self.actions():
                action.setEnabled(True)

    def set_action_icon(self, index, hidden):
        if hidden:
            self.actions()[index + 1].setIcon(QIcon(get_file('blank-check-box.svg')))
        else:
            self.actions()[index + 1].setIcon(QIcon(get_file('check-box.svg')))


class JobModel(QAbstractTableModel):
    layout_changed = pyqtSignal()

    def __init__(self, parentconfig):
        """
        Can keep a job.
        """
        super().__init__()
        self.jobs = []
        self.config = parentconfig
        self._headers = None
        self.rowsInserted.connect(self.layout_changed.emit)
        self.rowsRemoved.connect(self.layout_changed.emit)

    @property
    def headers(self):
        if not self._headers:
            headers = []
            index = 0
            while True:
                try:
                    headers.append(getattr(ui_text, f'header{index}'))
                except AttributeError:
                    break
                index += 1

            self._headers = headers
        return self._headers

    def data(self, index, role):
        column = index.column()
        job = self.jobs[index.row()]
        no_icon = bool(int(self.config.value('chb_no_icon')))

        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            if column == 0 and no_icon:
                return job.src_tr.name
            if column == 1:
                return job.display_name or job.tor_id
            if column == 2:
                return job.dest_group

        if role == Qt.ItemDataRole.CheckStateRole and column == 3:
            return Qt.CheckState.Checked if job.new_dtor else Qt.CheckState.Unchecked

        if role == Qt.ItemDataRole.DecorationRole and column == 0 and not no_icon:
            return QIcon(get_file(job.src_tr.favicon))

    def rowCount(self, parent):
        if parent and parent.isValid():
            return 0
        return len(self.jobs)

    def columnCount(self, parent):
        if parent and parent.isValid():
            return 0
        return len(self.headers)

    # noinspection PyTypeChecker
    def flags(self, index):
        if index.column() == 2:
            return super().flags(index) | Qt.ItemFlag.ItemIsEditable
        if index.column() == 3:
            return super().flags(index) | Qt.ItemFlag.ItemIsUserCheckable
        else:
            return super().flags(index)

    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.headers[section]

        if role == Qt.ItemDataRole.ToolTipRole and orientation == Qt.Orientation.Horizontal:
            if section == 2:
                if bool(int(self.config.value('chb_show_tips'))):
                    return ui_text.ttm_header2
            if section == 3:
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

        if column == 3 and role == Qt.ItemDataRole.CheckStateRole:
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
            pos = len(self.jobs)
            self.beginInsertRows(QModelIndex(), pos, pos)
            self.jobs.append(item)
            self.endInsertRows()

    @staticmethod
    def continuous_slices(numbers):
        if not numbers:
            return
        numbers.sort(reverse=True)
        start_idx = 0
        for idx in range(1, len(numbers)):
            if numbers[idx - 1] > (numbers[idx] + 1):
                yield numbers[idx - 1], numbers[start_idx]
                start_idx = idx
        yield numbers[-1], numbers[start_idx]

    def clear(self):
        self.remove_jobs(0, self.rowCount(None) - 1)

    def remove_jobs(self, first, last):
        self.beginRemoveRows(QModelIndex(), first, last)
        del self.jobs[first: last + 1]
        self.endRemoveRows()

    def del_multi(self, indices):
        for first, last in self.continuous_slices(indices):
            self.remove_jobs(first, last)

    def filter_for_attr(self, attr, value):
        indices = [i for i, j in enumerate(self.jobs) if getattr(j, attr) == value]
        self.del_multi(indices)

    def __bool__(self):
        return bool(self.jobs)

    def __iter__(self):
        for j in self.jobs:
            yield j
