import json
import os
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from app.digests import encode
from app.problems import Rejection


class CutArchive:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def read(self, key):
        if not re.fullmatch('[0-9a-f]{64}', key):
            raise Rejection('NO_RUN', '交付档案不存在', 404)
        try:
            return json.loads((self.root / f'{key}.json').read_bytes())
        except FileNotFoundError as error:
            raise Rejection('NO_RUN', '交付档案不存在', 404) from error

    def publish(self, key, record):
        with NamedTemporaryFile(dir=self.root, prefix='.draft-', delete=False) as draft:
            path = Path(draft.name)
            try:
                draft.write(encode(record))
                draft.flush()
                os.fsync(draft.fileno())
                try:
                    os.link(path, self.root / f'{key}.json')
                except FileExistsError:
                    return self.read(key), True
                descriptor = os.open(self.root, os.O_RDONLY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
            finally:
                path.unlink(missing_ok=True)
        return record, False

    def inventory(self):
        stamps = [self.read(file.stem)['manifest'] for file in self.root.glob('*.json')
                  if re.fullmatch('[0-9a-f]{64}', file.stem)]
        return sorted(stamps, key=lambda row: (row['created_at'], row['id']), reverse=True)
