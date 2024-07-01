import sys
import re
import logging
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from typing import Iterator

from lib.transplant import Transplanter, Job, JobCreationError
from lib import tp_text
from cli_config import cli_config
from lib.utils import tb_line_gen
from lib.img_rehost import ih
from gazelle.tracker_data import tr


class ColorStreamHandler(logging.StreamHandler):
    LEVEL_COLORS = {
        40: "\x1b[0;31m",  # Error
        30: "\x1b[0;33m",  # Warning
        25: "\x1b[0;32m",  # Success
    }

    @staticmethod
    def colored(text: str, color):
        return color + text + "\x1b[0m"

    def emit(self, record: logging.LogRecord) -> None:
        msg = record.msg
        color = self.LEVEL_COLORS.get(record.levelno)
        if color:
            msg = self.colored(msg, color)
        self.stream.write(msg + self.terminator)

        if record.exc_info:
            cls, ex, tb = record.exc_info
            for line in tb_line_gen(tb):
                self.stream.write(line + self.terminator)

            self.stream.write(self.colored(f'{cls.__name__}: {ex}', color) + self.terminator)


verb_map = {
    0: logging.CRITICAL,
    1: logging.ERROR,
    2: logging.INFO,
    3: logging.DEBUG
}

report = logging.getLogger('tr')
report.setLevel(verb_map[cli_config.verbosity])
if cli_config.coloured_output:
    handler = ColorStreamHandler(stream=sys.stdout)
else:
    handler = logging.StreamHandler(stream=sys.stdout)
report.addHandler(handler)


def parse_input() -> Iterator[tuple[str, dict]]:
    args = sys.argv[1:]
    batchmode = False

    for arg in args:
        if arg.lower() == "batch":
            batchmode = True
            continue

        match_id = re.fullmatch(r"(RED|OPS)(\d+)", arg)
        if match_id:
            yield arg, {'src_tr': tr[match_id.group(1)], 'tor_id': match_id.group(2)}
            continue

        parsed = urlparse(arg)
        hostname = parsed.hostname
        tor_id = parse_qs(parsed.query).get('torrentid')
        if tor_id and hostname:
            yield arg, {'src_dom': hostname, 'tor_id': tor_id[0]}
        else:
            report.info(arg)
            report.warning(tp_text.skip)

    if batchmode:
        report.info(tp_text.batch)
        for p in Path(cli_config.scan_dir).glob('*.torrent'):
            yield p.name, {'dtor_path': p, 'scanned': True}


def get_jobs() -> Iterator[Job]:
    for arg, kwarg_dict in parse_input():
        try:
            yield Job(**kwarg_dict)
        except JobCreationError as e:
            report.info(arg)
            report.warning(f'{tp_text.skip}: {e}\n')
            continue


def main():
    report.info(tp_text.start)

    trpl_settings = {
        'data_dir': Path(cli_config.data_dir),
        'deep_search': cli_config.deep_search,
        'deep_search_level': cli_config.deep_search_level,
        'dtor_save_dir': Path(tsd) if (tsd := cli_config.torrent_save_dir) else None,
        'save_dtors': bool(cli_config.torrent_save_dir),
        'del_dtors': cli_config.del_dtors,
        'file_check': cli_config.file_check,
        'rel_descr_templ': cli_config.rel_descr,
        'rel_descr_own_templ': cli_config.rel_descr_own_uploads,
        'add_src_descr': cli_config.add_src_descr,
        'src_descr_templ': cli_config.src_descr,
        'img_rehost': cli_config.img_rehost,
        'whitelist': cli_config.whitelist,
        'post_compare': cli_config.post_upload_checks,
    }
    if cli_config.img_rehost:
        ih.set_attrs(cli_config.image_hosts)

    key_dict = {trckr: getattr(cli_config, f'api_key_{trckr.name}') for trckr in tr}

    transplanter = Transplanter(key_dict, **trpl_settings)
    for job in get_jobs():
        try:
            transplanter.do_your_job(job)
        except Exception:
            report.exception('')
            continue
        finally:
            report.info('')

if __name__ == "__main__":
    main()
