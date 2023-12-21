from functools import partial

from PyQt6.QtWidgets import QHeaderView, QTableView
from PyQt6.QtGui import QIcon, QKeyEvent, QAction
from PyQt6.QtCore import Qt, pyqtSignal, QAbstractTableModel, QModelIndex, QItemSelectionModel

from lib import ui_text
from lib.img_rehost import ih
from GUI.misc_classes import ThemeIcon
from gazelle.tracker_data import tr


class IntRowItemSelectionModel(QItemSelectionModel):
    def selectedRows(self, column=0) -> list[int]:
        return [i.row() for i in super().selectedRows(column)]


class JobView(QTableView):
    key_override_sig = pyqtSignal(QKeyEvent)

    def __init__(self, model):
        super().__init__()
        self.setModel(model)
        self.setSelectionModel(IntRowItemSelectionModel(self.model()))
        self.setEditTriggers(QTableView.EditTrigger.SelectedClicked | QTableView.EditTrigger.DoubleClicked |
                             QTableView.EditTrigger.AnyKeyPressed)
        self.setHorizontalHeader(ContextHeaderView(Qt.Orientation.Horizontal, self))
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.verticalHeader().hide()
        self.verticalHeader().setMinimumSectionSize(12)
        self.horizontalHeader().setSectionsMovable(True)
        self.horizontalHeader().setMinimumSectionSize(18)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

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
        ac_restore_all = QAction(ui_text.header_restore, self)
        self.addAction(ac_restore_all)
        ac_restore_all.triggered.connect(self.set_all_sections_visible)
        ac_restore_all.setObjectName('restore_all')

        for i in range(self.model().columnCount(None)):
            action = QAction(self)
            action.setText(self.text(i))
            self.addAction(action)
            # 'i' must be evaluated at loop time. isSectionHidden() must be evaluateed at run time.
            # Hence, the lambda in a partial.
            action.triggered.connect(partial(lambda x: self.setSectionHidden(x, not self.isSectionHidden(x)), i))

    def set_all_sections_visible(self):
        for x in range(self.count()):
            self.showSection(x)

    def disable_actions(self):
        # all visible
        if not self.hiddenSectionCount():
            self.findChild(QAction, 'restore_all', Qt.FindChildOption.FindDirectChildrenOnly).setEnabled(False)

        # 1 visible
        elif self.hiddenSectionCount() == self.count() - 1:
            # Disable action for last visible section,
            # so it's impossible to hide all sections
            section = 0
            while self.isSectionHidden(section):
                section += 1

            self.actions()[section + 1].setEnabled(False)

        else:
            for action in self.actions():
                action.setEnabled(True)

    def set_action_icon(self, index, hidden):
        icon = 'blank-check-box.svg' if hidden else 'check-box.svg'
        self.actions()[index + 1].setIcon(ThemeIcon(icon))


class JobModel(QAbstractTableModel):
    layout_changed = pyqtSignal()

    def __init__(self, parentconfig):
        super().__init__()
        self.jobs = []
        self.config = parentconfig
        self._headers = None
        self.icons = {t: QIcon(f':/{t.favicon}') for t in tr}
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

    def data(self, index: QModelIndex, role: int = 0):
        column = index.column()
        job = self.jobs[index.row()]
        no_icon = self.config.value('chb_no_icon') == 2
        torrent_folder = self.config.value('chb_show_tor_folder') == 2

        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            if column == 0:
                if job.dtor_dict and torrent_folder:
                    show_name = job.dtor_dict['info']['name']
                else:
                    show_name = job.display_name or job.tor_id
                if no_icon:
                    show_name = f'{job.src_tr.name} - {show_name}'
                return show_name
            if column == 1:
                return job.dest_group

        if role == Qt.ItemDataRole.CheckStateRole and column == 2:
            return Qt.CheckState.Checked if job.new_dtor else Qt.CheckState.Unchecked

        if role == Qt.ItemDataRole.DecorationRole and column == 0 and not no_icon:
            return self.icons[job.src_tr]

    def rowCount(self, parent: QModelIndex = None) -> int:
        return len(self.jobs)

    def columnCount(self, parent: QModelIndex = None) -> int:
        return len(self.headers)

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if index.column() == 1:
            return super().flags(index) | Qt.ItemFlag.ItemIsEditable
        if index.column() == 2:
            return super().flags(index) | Qt.ItemFlag.ItemIsUserCheckable
        else:
            return super().flags(index)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = 0):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.headers[section]

        if role == Qt.ItemDataRole.ToolTipRole and orientation == Qt.Orientation.Horizontal:
            if section == 1:
                if bool(int(self.config.value('chb_show_tips'))):
                    return ui_text.ttm_header1
            if section == 2:
                if bool(int(self.config.value('chb_show_tips'))):
                    return ui_text.ttm_header2
        else:
            return super().headerData(section, orientation, role)

    def setData(self, index: QModelIndex, value, role: int = 0) -> bool:
        job = self.jobs[index.row()]
        column = index.column()

        if column == 1:
            if value:
                try:
                    value = str(int(value))
                except ValueError:
                    return False
            job.dest_group = value or None

        if column == 2 and role == Qt.ItemDataRole.CheckStateRole:
            job.new_dtor = Qt.CheckState(value) == Qt.CheckState.Checked

        return True

    def header_double_clicked(self, column: int):
        if column == 2:
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

    def append_jobs(self, new_jobs: list):
        if not new_jobs:
            return

        dupes = set(self.jobs) & set(new_jobs)
        for d in dupes:
            new_jobs.remove(d)
        if new_jobs:
            first = len(self.jobs)
            last = first + len(new_jobs) - 1
            self.beginInsertRows(QModelIndex(), first, last)
            self.jobs.extend(new_jobs)
            self.endInsertRows()
            return True

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

    def remove_this_job(self, job):
        i = self.jobs.index(job)
        self.remove_jobs(i, i)

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


class RehostModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.column_names = ui_text.rehost_columns

    def rowCount(self, parent: QModelIndex = None) -> int:
        return len(ih)

    def columnCount(self, parent: QModelIndex = None) -> int:
        return len(self.column_names)

    def data(self, index: QModelIndex, role: int = 0):
        column = index.column()
        host = ih[index.row()]

        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            if column == 0:
                return f' {host.name} '
            if column == 1:
                return host.key

        if role == Qt.ItemDataRole.CheckStateRole and column == 0:
            return Qt.CheckState.Checked if host.enabled else Qt.CheckState.Unchecked

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if index.column() == 0:
            return super().flags(index) | Qt.ItemFlag.ItemIsUserCheckable
        if index.column() == 1:
            return super().flags(index) | Qt.ItemFlag.ItemIsEditable
        else:
            return super().flags(index)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = 0):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.column_names[section]
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Vertical:
            return ih[section].prio + 1
        else:
            return super().headerData(section, orientation, role)

    def setData(self, index: QModelIndex, value, role: int = 0) -> bool:
        host = ih[index.row()]
        column = index.column()

        if column == 1:
            if value == host.key:
                return False
            host.key = value
        if column == 0 and role == Qt.ItemDataRole.CheckStateRole:
            host.enabled = True if value == Qt.CheckState.Checked.value else False
        self.dataChanged.emit(index, index, [role])
        return True


class RehostTable(QTableView):
    def __init__(self, model: RehostModel):
        super().__init__()
        self.setModel(model)
        self.setSelectionMode(QTableView.SelectionMode.NoSelection)
        self.verticalHeader().setSectionsMovable(True)
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.verticalHeader().setDefaultSectionSize(30)
        self.verticalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.verticalHeader().setFixedWidth(22)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

    def move_to_priority(self):
        for h in ih.prioritised():
            v_index = self.verticalHeader().visualIndex(h.value)
            if h.prio != v_index:
                self.verticalHeader().moveSection(v_index, h.prio)
        self.verticalHeader().sectionMoved.connect(self.update_priorities)

    def update_priorities(self):
        for host in ih:
            host.prio = self.verticalHeader().visualIndex(host.value)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        height = self.horizontalHeader().height() + self.verticalHeader().length() + self.frameWidth() * 2

        self.setMaximumHeight(height)
