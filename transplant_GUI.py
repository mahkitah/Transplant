import sys
import traceback
import logging

from PyQt6.QtWidgets import QApplication

def uncaught_exceptions(ex_cls, ex, tb):
    msg = ''.join(traceback.format_tb(tb))
    msg += f'{ex_cls.__name__}: {ex}:\n\n'

    if hasattr(sys, 'frozen'):
        from datetime import datetime
        dt_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open('Transplant.log', 'a') as f:
            f.write(f'{dt_str}\n{msg}')

    logging.error(msg)
    print(msg, file=sys.stderr)


if __name__ == "__main__":
    sys.excepthook = uncaught_exceptions

    QApplication.setStyle('fusion')
    app = QApplication(sys.argv)

    from GUI.main_gui import MainWindow

    window = MainWindow()
    app.aboutToQuit.connect(window.save_state)
    sys.exit(app.exec())
