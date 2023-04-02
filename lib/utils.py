import os
import platform
import subprocess


def scantree(path):
    for scan in os.scandir(path):
        if scan.is_dir(follow_symlinks=False) and not scan.name.startswith('.'):
            yield from scantree(scan.path)
        else:
            yield scan

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
