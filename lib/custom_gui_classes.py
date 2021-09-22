from PyQt5.QtWidgets import QTextEdit, QHeaderView, QAction, QTableView
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, pyqtSignal, QAbstractTableModel
from lib import ui_text
from gazelle.tracker_data import tr

class MyTextEdit(QTextEdit):
    plainTextChanged = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.textChanged.connect(lambda: self.plainTextChanged.emit(self.toPlainText()))


class MyTableView(QTableView):
    selectionChange = pyqtSignal(list)

    def __init__(self):
        super().__init__()

    def selectionChanged(self, selected, deselected):
        super().selectionChanged(selected, deselected)
        self.selectionChange.emit(self.selectedIndexes())


class MyHeaderView(QHeaderView):
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
            if job.src_tr == tr.RED:
                return QIcon('gui_files/pth.ico')
            if job.src_tr == tr.OPS:
                return QIcon('gui_files/ops.ico')

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
