import os
import math
from multiprocessing import pool
from hashlib import sha1

from lib.utils import scantree


class Torrent:
    def __init__(self, path):
        self.path = os.path.normpath(path)
        self._file_list = []
        self._total_size = 0
        self._piece_size = None
        self.data = None
        self._pool = pool.ThreadPool()
        self.generate_data()

    def scan_files(self):
        if os.path.isdir(self.path):
            for scan in scantree(self.path):
                fsize = scan.stat().st_size
                self._total_size += fsize
                self._file_list.append((scan.path, fsize))

    @property
    def file_list(self):
        if not self._file_list:
            self.scan_files()
        return self._file_list

    @property
    def total_size(self):
        if not self._total_size:
            self.scan_files()
        return self._total_size

    @property
    def piece_size(self):
        if not self._piece_size:
            min_piece_size = 2 ** 14
            max_piece_size = 2 ** 26

            piece_size = 2 ** math.ceil(math.log2(self.total_size / 1500))
            if piece_size < min_piece_size:
                piece_size = min_piece_size
            elif piece_size > max_piece_size:
                piece_size = max_piece_size
            self._piece_size = piece_size

        return self._piece_size

    def file_objects(self):
        for path, _ in self.file_list:
            with open(path, 'rb') as f:
                yield f

    def file_chunks(self):
        ps = self.piece_size
        read_size = ps
        chunks = []
        chunks_size = 0
        for f in self.file_objects():
            for chunk in iter(lambda: f.read(read_size), b''):
                chunks_size += len(chunk)
                chunks.append(chunk)
                if chunks_size == ps:
                    yield chunks
                    chunks_size = 0
                    read_size = ps
                    chunks = []
                else:
                    read_size = ps - chunks_size
        if chunks_size:
            yield chunks

    @staticmethod
    def list_hasher(chunks: list[bytes]):
        h = sha1()
        for chunk in chunks:
            h.update(chunk)
        return h.digest()

    def file_hashes(self):
        for chsum in self._pool.imap(self.list_hasher, self.file_chunks(), 10):
            yield chsum

    def generate_data(self):
        info = {
            'files': [],
            'name': os.path.basename(self.path),
            'pieces': b''.join(self.file_hashes()),
            'piece length': self.piece_size,
            'private': 1
        }
        for path, size in self.file_list:
            fx = {'length': size,
                  'path': os.path.relpath(path, self.path).split(os.sep)}
            info['files'].append(fx)

        self.data = {'info': info}
