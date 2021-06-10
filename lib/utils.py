import os
import platform
import subprocess


def file_list_gen(path):
    for root, dirs, files in os.walk(path):
        for x in files:
            yield os.path.join(root, x)

def open_local_folder(path):
    if platform.system() == 'Windows':
        os.startfile(path)
    elif platform.system() == 'Darwin':
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdf-open", path])

def choose_the_other(optionlist):
    assert len(optionlist) == 2

    def specified(inp):
        index_map = {0: 1, 1: 0}
        index_in = optionlist.index(inp)
        index_out = index_map[index_in]
        return optionlist[index_out]
    return specified

def multi_replace(src_txt, replace_map, *extra_maps):
    txt = src_txt
    tmp_map = dict(replace_map)
    for x in extra_maps:
        tmp_map.update(x)

    for k, v in tmp_map.items():
        txt = txt.replace(k, v)
    return txt

def dict_replace_values(inp_dict, bad, good):
    for k, v in inp_dict.items():
        if v == bad:
            inp_dict[k] = good
        if type(v) == dict:
            dict_replace_values(v, bad, good)
