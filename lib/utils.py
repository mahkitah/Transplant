import os
import re
import platform
import subprocess
import traceback

def scantree(path):
    for scan in os.scandir(path):
        if scan.is_dir(follow_symlinks=False) and not scan.name.startswith('.'):
            yield from scantree(scan.path)
        else:
            yield scan

def subdirs_gen(path, maxlevel=1, level=1):
    for entry in os.scandir(path):
        if entry.is_dir():
            yield os.path.split(entry.path)
            if level < maxlevel:
                yield from subdirs_gen(entry.path, maxlevel=maxlevel, level=level + 1)

def open_local_folder(path):
    if platform.system() == 'Windows':
        os.startfile(path)
    elif platform.system() == 'Darwin':
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdf-open", path])

def multi_replace(src_txt, replace_map, *extra_maps):
    txt = src_txt
    if extra_maps:
        replace_map = replace_map.copy()
        for x in extra_maps:
            replace_map.update(x)

    for k, v in replace_map.items():
        txt = txt.replace(k, v)
    return txt

STUPID_3_11_TB = re.compile(r'[\s^~]+')
def tb_line_gen(tb):
    for line in traceback.format_tb(tb):
        for sub_line in line.splitlines():
            if STUPID_3_11_TB.fullmatch(sub_line):
                continue
            yield sub_line
