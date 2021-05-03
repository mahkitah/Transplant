import sys
import os
import re
import traceback

from lib.transplant import Transplanter, Job
from lib.gazelle_api import GazelleApi

from cli_config import cli_config, api_keys
from lib import constants, ui_text


def report_back(msg, msg_verb):
    if msg_verb <= cli_config.verbosity:
        print(msg)


# noinspection PyBroadException
def operate(job, api_map):

    try:
        operation = Transplanter(job, api_map, report=report_back)
        operation.transplant()
    except Exception:
        traceback.print_exc()
        return

    if job.upl_succes:
        if job.save_dtors:
            job.save_dtorrent()
        if job.del_dtors:
            os.remove(job.dtor_path)

def main():

    api_map = {'RED': GazelleApi("RED", api_keys.get_key("RED"), report=report_back),
               'OPS': GazelleApi("OPS", api_keys.get_key("OPS"), report=report_back)}

    report_back(ui_text.start, 2)

    args = sys.argv[1:]
    batchmode = False

    job_user_settings = {'data_dir': cli_config.data_dir,
                         'dtor_save_dir': cli_config.torrent_save_dir,
                         'save_dtors': bool(cli_config.torrent_save_dir),
                         'file_check': cli_config.file_check
                         }

    for arg in args:
        report_back('', 2)
        if arg.lower() == "batch":
            batchmode = True

        match_url = re.search(r"https://(.+?)/.+torrentid=(\d+)", arg)
        if match_url:
            report_back(f"{arg}", 2)
            src_name = match_url.group(1)
            job = Job(src_id=constants.SITE_ID_MAP[src_name], tor_id=match_url.group(2), **job_user_settings)
            operate(job, api_map)

        match_id = re.fullmatch(r"(RED|OPS)(\d+)", arg)
        if match_id:
            report_back(f"{arg}", 2)
            job = Job(src_id=match_id.group(1), tor_id=match_id.group(2), **job_user_settings)
            operate(job, api_map)

    if batchmode:
        for dir_entry in os.scandir(cli_config.scan_dir):
            if dir_entry.is_file() and dir_entry.name.endswith(".torrent"):
                report_back(f"\n{dir_entry.name}", 2)
                job = Job(dtor_path=dir_entry.path, del_dtors=cli_config.del_dtors, **job_user_settings)
                operate(job, api_map)


if __name__ == "__main__":
    main()
