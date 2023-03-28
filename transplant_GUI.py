import sys
from PyQt6.QtWidgets import QApplication

if __name__ == "__main__":
    QApplication.setStyle('fusion')
    app = QApplication(sys.argv)

    from GUI.main_gui import MainWindow

    window = MainWindow()
    app.aboutToQuit.connect(window.save_state)
    sys.exit(app.exec())
