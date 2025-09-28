from functools import partial
from typing import Iterable, Iterator

from PyQt6.QtWidgets import QHeaderView, QTableView
from PyQt6.QtGui import QIcon, QKeyEvent, QAction
from PyQt6.QtCore import Qt, pyqtSignal, QAbstractTableModel, QModelIndex, QItemSelectionModel, QSignalBlocker

from GUI import gui_text
from core.img_rehost import IH
from gazelle.tracker_data import TR

try:
    # pairwise = 3.10+
    from itertools import pairwise
except ImportError:
    def pairwise(it: Iterable):
        iterator = iter(it)
        a = next(iterator, None)
        for b in iterator:
            yield a, b
            a = b


class IntRowItemSelectionModel(QItemSelectionModel):
    def selectedRows(self, column=0) -> list[int]:
        return [i.row() for i in super().selectedRows(column)]


class JobView(QTableView):
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
            event.ignore()
        else:
            super().keyPressEvent(event)


class ContextHeaderView(QHeaderView):
    section_visibility_changed = pyqtSignal(int, bool)

    def __init__(self, orientation, parent):
        super().__init__(orientation, parent)
        self.section_visibility_changed.connect(self.set_action_checked)
        self.section_visibility_changed.connect(self.disable_actions)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)

    def text(self, section):
        return self.model().headerData(section, self.orientation()).strip()

    def setSectionHidden(self, index, hide):
        if not self.isSectionHidden(index) == hide:
            super().setSectionHidden(index, hide)
            self.section_visibility_changed.emit(index, hide)

    def set_section_visible(self, index: int, visible: bool):
        self.setSectionHidden(index, not visible)

    def restoreState(self, state):
        try:
            super().restoreState(state)
        except TypeError:
            pass
        self.context_actions()

    def context_actions(self):
        ac_restore_all = QAction(gui_text.header_restore, self)
        self.addAction(ac_restore_all)
        ac_restore_all.triggered.connect(self.set_all_sections_visible)
        ac_restore_all.setEnabled(bool(self.hiddenSectionCount()))

        for i in range(self.model().columnCount()):
            action = QAction(self)
            action.setText(self.text(i))
            action.setCheckable(True)
            action.setChecked(not self.isSectionHidden(i))
            self.addAction(action)
            action.toggled.connect(partial(self.set_section_visible, i))

    def set_all_sections_visible(self):
        for i in range(self.count()):
            self.actions()[i + 1].setChecked(True)

    def disable_actions(self):
        # all visible
        if not self.hiddenSectionCount():
            self.actions()[0].setEnabled(False)

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

    def set_action_checked(self, section: int, hidden: bool):
        action = self.actions()[section + 1]
        action.setChecked(not hidden)


class JobModel(QAbstractTableModel):
    layout_changed = pyqtSignal()

    def __init__(self, parentconfig):
        super().__init__()
        self.jobs = []
        self.config = parentconfig
        self.headers = gui_text.job_list_headers
        self.icons = {t: QIcon(f':/{t.favicon}') for t in TR}
        self.rowsInserted.connect(self.layout_changed.emit)
        self.rowsRemoved.connect(self.layout_changed.emit)

    def data(self, index: QModelIndex, role: int = 0):
        column = index.column()
        job = self.jobs[index.row()]
        no_icon = self.config.value('looks/chb_no_icon')
        torrent_folder = self.config.value('looks/chb_show_tor_folder')

        if role == Qt.ItemDataRole.DisplayRole:
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

        if role == Qt.ItemDataRole.EditRole:
            return job.dest_group and str(job.dest_group)

        if role == Qt.ItemDataRole.CheckStateRole and column == 2:
            return Qt.CheckState(job.new_dtor * 2)

        if role == Qt.ItemDataRole.DecorationRole and column == 0 and not no_icon:
            return self.icons[job.src_tr]

        return None

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

        if (role == Qt.ItemDataRole.ToolTipRole
                and self.config.value('main/chb_show_tips')
                and orientation == Qt.Orientation.Horizontal
                and section in (1, 2)):
            return getattr(gui_text, f'ttm_header{section}')
        else:
            return super().headerData(section, orientation, role)

    def setData(self, index: QModelIndex, value, role: int = 0) -> bool:
        job = self.jobs[index.row()]
        column = index.column()

        if column == 1:
            if value:
                try:
                    value = int(value)
                except ValueError:
                    return False
            job.dest_group = value or None

        if column == 2 and role == Qt.ItemDataRole.CheckStateRole:
            value: int
            job.new_dtor = value == 2

        return True

    def nt_check_uncheck_all(self):
        if not self.jobs:
            return
        column = 2
        was_unchecked = []
        for i, job in enumerate(self.jobs):
            if not job.new_dtor:
                was_unchecked.append(i)
                job.new_dtor = True
        if was_unchecked:
            for first, last in self.continuous_slices(was_unchecked):
                self.dataChanged.emit(self.index(first, column), self.index(last, column), [])
        else:  # all are checked
            for job in self.jobs:
                job.new_dtor = False
            self.dataChanged.emit(self.index(0, column), self.index(len(self.jobs) - 1, column), [])

    def append_jobs(self, new_jobs: list):
        if not new_jobs:
            return
        first = len(self.jobs)
        last = first + len(new_jobs) - 1
        self.beginInsertRows(QModelIndex(), first, last)
        self.jobs.extend(new_jobs)
        self.endInsertRows()

    @staticmethod
    def continuous_slices(numbers: Iterable[int], reverse=False) -> Iterator[list[int]]:
        numbers = sorted(numbers, reverse=reverse)
        if not numbers:
            return
        start = numbers[0]
        for a, b in pairwise(numbers):
            if abs(a - b) > 1:
                yield sorted((start, a))
                start = b
        yield sorted((start, numbers[-1]))

    def clear(self):
        self.remove_jobs(0, self.rowCount() - 1)

    def remove_jobs(self, first, last):
        self.beginRemoveRows(QModelIndex(), first, last)
        del self.jobs[first: last + 1]
        self.endRemoveRows()

    def remove_this_job(self, job):
        i = self.jobs.index(job)
        self.remove_jobs(i, i)

    def del_multi(self, indices):
        for first, last in self.continuous_slices(indices, reverse=True):
            self.remove_jobs(first, last)

    def filter_for_attr(self, attr, value):
        indices = [i for i, j in enumerate(self.jobs) if getattr(j, attr) == value]
        self.del_multi(indices)

    def __bool__(self):
        return bool(self.jobs)

    def __iter__(self):
        yield from self.jobs


class RehostModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.column_names = gui_text.rehost_columns

    def rowCount(self, parent: QModelIndex = None) -> int:
        return len(IH)

    def columnCount(self, parent: QModelIndex = None) -> int:
        return len(self.column_names)

    def data(self, index: QModelIndex, role: int = 0):
        column = index.column()
        host = IH(index.row())

        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            if column == 0:
                return f' {host.name} '
            if column == 1:
                return host.key

        if role == Qt.ItemDataRole.CheckStateRole and column == 0:
            return Qt.CheckState(host.enabled * 2)

        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if index.column() == 0:
            return super().flags(index) | Qt.ItemFlag.ItemIsUserCheckable
        if index.column() == 1:
            return super().flags(index) | Qt.ItemFlag.ItemIsEditable
        else:
            return super().flags(index)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = 0):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation is Qt.Orientation.Horizontal:
                return self.column_names[section]
            else:
                return IH(section).prio + 1
        else:
            return super().headerData(section, orientation, role)

    def setData(self, index: QModelIndex, value, role: int = 0) -> bool:
        host = IH(index.row())
        column = index.column()

        if column == 1:
            if value == host.key:
                return False
            host.key = value
        if column == 0 and role == Qt.ItemDataRole.CheckStateRole:
            value: int
            host.enabled = Qt.CheckState(value) is Qt.CheckState.Checked

        self.dataChanged.emit(index, index, [role])
        return True


class RehostTable(QTableView):
    rh_data_changed = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setModel(RehostModel())
        self.setSelectionMode(QTableView.SelectionMode.NoSelection)
        self.verticalHeader().setSectionsMovable(True)
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.verticalHeader().setDefaultSectionSize(30)
        self.verticalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.verticalHeader().setFixedWidth(22)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        self.verticalHeader().sectionMoved.connect(self.update_priorities)
        self.verticalHeader().sectionMoved.connect(lambda: self.rh_data_changed.emit(IH.get_attrs()))
        self.model().dataChanged.connect(lambda: self.rh_data_changed.emit(IH.get_attrs()))

    def move_to_priority(self):
        with QSignalBlocker(self.verticalHeader()):
            for h in IH.prioritised():
                v_index = self.verticalHeader().visualIndex(h.value)
                if h.prio != v_index:
                    self.verticalHeader().moveSection(v_index, h.prio)

    def update_priorities(self):
        for host in IH:
            host.prio = self.verticalHeader().visualIndex(host.value)

    def set_rh_data(self, rh_data: dict):
        if not rh_data:
            return
        IH.set_attrs(rh_data)
        self.move_to_priority()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        height = self.horizontalHeader().height() + self.verticalHeader().length() + self.frameWidth() * 2

        self.setMaximumHeight(height)
