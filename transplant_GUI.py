import sys
import logging
from GUI import resources
from GUI.misc_classes import Application


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

    Application.setStyle('fusion')
    app = Application(sys.argv)
    from GUI.control_room import start_up, save_state

    start_up()
    app.aboutToQuit.connect(save_state)
    sys.exit(app.exec())
