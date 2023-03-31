import sys
import logging

from PyQt6.QtWidgets import QApplication


if __name__ == "__main__":
    sys.excepthook = lambda cls, ex, tb: logger.error('', exc_info=(cls, ex, tb))

    logger = logging.getLogger('tr.GUI')
    logger.setLevel(logging.INFO)

    if hasattr(sys, 'frozen'):
        if '-log' in sys.argv:
            sys.argv.remove('-log')
            handler = logging.FileHandler('transplant.log')
            handler.setFormatter(logging.Formatter(fmt='%(asctime)s'))
            logger.addHandler(handler)
    else:
        logger.addHandler(logging.StreamHandler(stream=sys.stdout))

    QApplication.setStyle('fusion')
    app = QApplication(sys.argv)

    from GUI.main_gui import MainWindow

    window = MainWindow()
    app.aboutToQuit.connect(window.save_state)
    sys.exit(app.exec())
