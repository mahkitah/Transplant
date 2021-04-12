import os

def file_list_gen(path):
    for root, dirs, files in os.walk(path):
        for x in files:
            yield os.path.join(root, x)

def choose_the_other(optionlist):
    assert len(optionlist) == 2

    def specified(site_id):
        index_map = {0: 1, 1: 0}
        index_in = optionlist.index(site_id)
        index_out = index_map[index_in]
        return optionlist[index_out]
    return specified
