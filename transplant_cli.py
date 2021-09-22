import sys
import os
import re
import traceback

from lib.transplant import Transplanter, Job
from gazelle.api_classes import KeyApi, RedApi, HtmlApi
from gazelle.tracker_data import tr, tr_data

from cli_config import cli_config, api_keys
from lib import ui_text


def report_back(msg, msg_verb):
    if msg_verb <= cli_config.verbosity:
        print(msg)

def get_tr_by_id(id):
    for t in tr:
        if t.name == id:
            return t

def parse_input():
    args = sys.argv[1:]
    batchmode = False

    for arg in args:
        if arg.lower() == "batch":
            batchmode = True

        match_url = re.search(r"https://(.+?)/.+torrentid=(\d+)", arg)
        if match_url:
            report_back(f"{arg}", 2)
            yield Job(src_dom=match_url.group(1), tor_id=match_url.group(2))

        match_id = re.fullmatch(r"(RED|OPS)(\d+)", arg)
        if match_id:
            report_back(f"{arg}", 2)
            tracker = get_tr_by_id(match_id.group(1))
            yield Job(src_tr=tracker, tor_id=match_id.group(2))

    if batchmode:
        for scan in os.scandir(cli_config.scan_dir):
            if scan.is_file() and scan.name.endswith(".torrent"):
                report_back(f"\n{scan.name}", 2)
                yield Job(dtor_path=scan.path, del_dtors=cli_config.del_dtors)

def cred_prompt():
    u_name = input('username: ')
    passw = input('password: ')
    return u_name, passw

def main():

    api_map = {
        tr.RED: RedApi(tr.RED, key=api_keys.get_key("RED")),
        tr.OPS: KeyApi(tr.OPS, key=api_keys.get_key("OPS")),
        # tr.bB: HtmlApi(tr.bB, f=cred_prompt)
    }

    report_back(ui_text.start, 2)

    trpl_settings = {
        'data_dir': cli_config.data_dir,
        'dtor_save_dir': cli_config.torrent_save_dir,
        'save_dtors': bool(cli_config.torrent_save_dir),
        'file_check': cli_config.file_check,
        'rel_descr_templ': cli_config.rel_descr,
        'add_src_descr': cli_config.add_src_descr,
        'src_descr_templ': cli_config.src_descr,
        'img_rehost': cli_config.img_rehost,
        'whitelist': cli_config.whitelist,
        'ptpimg_key': cli_config.ptpimg_key,
        'report': report_back
    }
    transplanter = Transplanter(api_map, **trpl_settings)
    for job in parse_input():
        # noinspection PyBroadException
        try:
            transplanter.do_your_job(job)
        except Exception:
            traceback.print_exc()
            continue

if __name__ == "__main__":
    main()
