"""One-time, checksum-bound source import. No subprocesses or target contact."""
import base64
import hashlib
import json
import lzma
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / '.bootstrap/terraform.json.xz.b64'
blob = base64.b64decode(''.join(source.read_text().split()), validate=True)
expected = 'dd0b3b33e23f8ff24eb29569fff270ff7c19d1469a10a776732f6020e0925f78'
if hashlib.sha256(blob).hexdigest() != expected:
    raise SystemExit('Transport checksum mismatch; nothing imported')
decoder = lzma.LZMADecompressor(memlimit=256 * 1024 * 1024)
raw = decoder.decompress(blob, max_length=2 * 1024 * 1024)
if not decoder.eof or decoder.unused_data:
    raise SystemExit('Incomplete or oversized transport')
files = json.loads(raw)
if not isinstance(files, dict) or len(files) != 50:
    raise SystemExit('Unexpected file inventory')
for name, text in files.items():
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or path.parts[0] != 'terraform':
        raise SystemExit('Invalid destination')
    if not isinstance(text, str) or '\\' in name:
        raise SystemExit('Invalid text source')
    target = ROOT / path
    if target.exists() and target.read_text() != text:
        raise SystemExit('Refusing to overwrite a changed source: ' + name)
for name, text in files.items():
    target = ROOT / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
print('Imported 50 original Terraform text files; no infrastructure operation')
