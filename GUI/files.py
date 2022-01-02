import sys
import os

if hasattr(sys, 'frozen'):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(__file__)

def get_file(name):
    return os.path.join(base_path, 'gui_files', name)
