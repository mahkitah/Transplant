import sys
import os
import re
import traceback
import logging

from lib.transplant import Transplanter, Job
from gazelle.api_classes import KeyApi, RedApi
from gazelle.tracker_data import tr

from cli_config import cli_config, api_keys
from lib import ui_text

verb_map = {
    0: logging.CRITICAL,
    1: logging.ERROR,
    2: logging.INFO,
    3: logging.DEBUG
}

logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.basicConfig(stream=sys.stdout, level=verb_map[cli_config.verbosity], format="%(message)s",)
report = logging.getLogger(__name__)

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
            report.info(arg)
            yield Job(src_dom=match_url.group(1), tor_id=match_url.group(2))

        match_id = re.fullmatch(r"(RED|OPS)(\d+)", arg)
        if match_id:
            report.info(arg)
            tracker = get_tr_by_id(match_id.group(1))
            yield Job(src_tr=tracker, tor_id=match_id.group(2))

    if batchmode:
        for scan in os.scandir(cli_config.scan_dir):
            if scan.is_file() and scan.name.endswith(".torrent"):
                report.info(f"\n{scan.name}")
                yield Job(dtor_path=scan.path, scanned=True)

def main():

    api_map = {
        tr.RED: RedApi(tr.RED, key=api_keys.get_key("RED")),
        tr.OPS: KeyApi(tr.OPS, key=api_keys.get_key("OPS")),
    }

    report.info(ui_text.start)

    trpl_settings = {
        'data_dir': cli_config.data_dir,
        'deep_search': cli_config.deep_search,
        'dtor_save_dir': cli_config.torrent_save_dir,
        'save_dtors': bool(cli_config.torrent_save_dir),
        'del_dtors': cli_config.del_dtors,
        'file_check': cli_config.file_check,
        'rel_descr_templ': cli_config.rel_descr,
        'rel_descr_own_templ': cli_config.rel_descr_own_uploads,
        'add_src_descr': cli_config.add_src_descr,
        'src_descr_templ': cli_config.src_descr,
        'img_rehost': cli_config.img_rehost,
        'whitelist': cli_config.whitelist,
        'ptpimg_key': cli_config.ptpimg_key,
        'post_compare': cli_config.post_upload_checks,
    }
    transplanter = Transplanter(api_map, **trpl_settings)
    for job in parse_input():
        # noinspection PyBroadException
        try:
            transplanter.do_your_job(job)
        except Exception:
            report.error(traceback.format_exc())
            continue

if __name__ == "__main__":
    main()
