"""Bounded, lossless synthetic attachment transfer; no archive path extraction."""
import base64
import hashlib
import json
from pathlib import Path
import re
import stat
import sys

KEY = re.compile(r't_(demo|other)--[a-z][a-z0-9_]{0,47}\.bin\Z')


def validate(entries):
    if not isinstance(entries, list) or len(entries) > 100:
        raise ValueError('Invalid attachment inventory')
    seen = set()
    for item in entries:
        if not isinstance(item, dict) or set(item) != {'key', 'base64', 'sha256', 'bytes', 'mode'}:
            raise ValueError('Invalid attachment entry')
        key = item['key']
        if not isinstance(key, str) or not KEY.fullmatch(key) or key in seen or item['mode'] != 0o640:
            raise ValueError('Invalid attachment path or metadata')
        contents = base64.b64decode(item['base64'], validate=True)
        if not 1 <= len(contents) <= 65_536 or len(contents) != item['bytes'] or hashlib.sha256(contents).hexdigest() != item['sha256']:
            raise ValueError('Attachment digest or length mismatch')
        seen.add(key)
    return entries


def export_files(directory):
    entries = []
    for path in sorted(directory.iterdir()):
        if path.is_symlink() or not path.is_file():
            raise ValueError('Unexpected attachment object')
        content = path.read_bytes()
        entries.append({'key': path.name, 'base64': base64.b64encode(content).decode(),
                        'sha256': hashlib.sha256(content).hexdigest(), 'bytes': len(content),
                        'mode': stat.S_IMODE(path.stat().st_mode)})
    return validate(entries)


def import_files(directory, entries):
    validate(entries)
    if any(directory.iterdir()):
        raise ValueError('Restore requires empty attachment storage')
    for item in entries:
        target = directory/item['key']
        with target.open('xb') as file:
            file.write(base64.b64decode(item['base64'], validate=True))
        target.chmod(item['mode'])
    return export_files(directory)


if __name__ == '__main__':
    directory = Path('/attachments')
    if sys.argv[1:] == ['export']:
        print(json.dumps(export_files(directory), sort_keys=True))
    elif sys.argv[1:] == ['import']:
        raw = sys.stdin.buffer.read(10_000_001)
        if len(raw) > 10_000_000:
            raise ValueError('Attachment envelope too large')
        print(json.dumps(import_files(directory, json.loads(raw)), sort_keys=True))
    else:
        raise ValueError('Unsupported attachment operation')
