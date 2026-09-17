#!/usr/bin/env python3
"""One-time, hash-checked transport import; never invokes infrastructure tools."""
from pathlib import Path
import base64
import hashlib
import json
import lzma

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = 'd25cddaff191fcaf9fd4c0611cad615f177ab1af071ec3077323e523f03c7b27'
parts = [ROOT / f'provenance/import/terraform-{n:02d}.b64' for n in range(4)]
encoded = ''.join(p.read_text(encoding='ascii').strip() for p in parts)
payload = base64.b64decode(encoded, validate=True)
if hashlib.sha256(payload).hexdigest() != EXPECTED:
    raise SystemExit('Import transport hash mismatch; no source written.')
files = json.loads(lzma.decompress(payload, memlimit=256 * 1024 * 1024))
if not isinstance(files, dict) or len(files) != 51:
    raise SystemExit('Unexpected source inventory.')
prepared = []
manifest = []
for name, content in sorted(files.items()):
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts or '\\' in name:
        raise SystemExit('Unsafe import path.')
    if not (name.startswith('terraform/') or name == 'tools/verify_terraform.py'):
        raise SystemExit('Unexpected import scope.')
    if not isinstance(content, str):
        raise SystemExit('Import contains a non-text source.')
    target = ROOT / 'implementation' / relative
    data = content.encode('utf-8')
    if target.is_symlink() or (target.exists() and target.read_bytes() != data):
        raise SystemExit(f'Existing source differs; refusing overwrite: {name}')
    prepared.append((target, data))
    manifest.append({'path': 'implementation/' + name, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
for target, data in prepared:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
record = ROOT / 'provenance/terraform-import.json'
record.write_text(json.dumps({'source': 'Implementation Increment 04', 'transport_sha256': EXPECTED, 'files': manifest}, indent=2) + '\n')
print(f'Imported {len(prepared)} original source files. No deployment performed.')
