import sys
import os
import re
import logging

from lib.transplant import Transplanter, Job
from gazelle.tracker_data import tr

from cli_config import cli_config
from lib import ui_text

verb_map = {
    0: logging.CRITICAL,
    1: logging.ERROR,
    2: logging.INFO,
    3: logging.DEBUG
}

report = logging.getLogger('tr')
report.setLevel(verb_map[cli_config.verbosity])
report.addHandler(logging.StreamHandler(stream=sys.stdout))

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
                try:
                    report.info(f"{scan.name}")
                    yield Job(dtor_path=scan.path, scanned=True)
                except (AssertionError, TypeError, AttributeError, KeyError):
                    report.warning(ui_text.skip)
                    continue

def main():
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
    key_dict = {trckr: getattr(cli_config, f'api_key_{trckr.name}') for trckr in tr}

    transplanter = Transplanter(key_dict, **trpl_settings)
    for job in parse_input():
        try:
            transplanter.do_your_job(job)
        except Exception:
            report.exception('')
            continue
        finally:
            report.info('')

if __name__ == "__main__":
    main()
