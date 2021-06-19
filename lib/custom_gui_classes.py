from PyQt5.QtWidgets import QTextEdit, QHeaderView, QAction
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, pyqtSignal
from lib import ui_text


class MyTextEdit(QTextEdit):
    plainTextChanged = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.textChanged.connect(lambda: self.plainTextChanged.emit(self.toPlainText()))


class MyHeaderView(QHeaderView):
    sectionVisibilityChanged = pyqtSignal(int, bool)

    def __init__(self, ori, headers):
        super().__init__(ori)
        self.headers = headers
        self.context_actions()
        self.sectionVisibilityChanged.connect(self.set_action_icons)
        self.sectionVisibilityChanged.connect(self.disable_last_action)
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
        self.restore_all = QAction(ui_text.header_restore)
        self.addAction(self.restore_all)
        self.restore_all.triggered.connect(self.setAllSectionsVisible)

        for n, h in enumerate(self.headers):
            action_name = f'ac_header{n}'
            setattr(self, action_name, QAction())
            action = getattr(self, action_name)
            action.setText(h)
            self.addAction(action)

            def make_lambda(index):
                return lambda: self.setSectionHidden(index, not self.isSectionHidden(index))

            action.triggered.connect(make_lambda(n))

    def setAllSectionsVisible(self):
        for x in range(self.count()):
            self.showSection(x)

    def disable_last_action(self):
        if self.hiddenSectionCount() == self.count() - 1:
            section = 0
            while self.isSectionHidden(section):
                section += 1

            self.actions()[section + 1].setEnabled(False)

        else:
            for action in self.actions():
                if not action.isEnabled():
                    action.setEnabled(True)

    def set_action_icons(self, index, hidden):
        if hidden:
            self.actions()[index + 1].setIcon(QIcon())
        else:
            self.actions()[index + 1].setIcon(QIcon('gui_files/tick.svg'))

