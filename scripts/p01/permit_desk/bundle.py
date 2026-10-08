"""Validate the complete fixture capture before allocating a restore destination."""
import base64
import hashlib
import json
import re

from .state import validate


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def validate_bundle(bundle, expected_digest, image, revision, config):
    if digest(encode(bundle)) != expected_digest:
        raise ValueError('Capture digest mismatch')
    if set(bundle) != {'schema_version', 'fixture', 'image_id', 'source_revision', 'config', 'database', 'attachments', 'snapshot', 'writers'}:
        raise ValueError('Unexpected capture members')
    if bundle['schema_version'] != 1 or bundle['fixture'] != 'permit-desk-v1':
        raise ValueError('Unsupported capture version')
    if bundle['image_id'] != image or not re.fullmatch(r'sha256:[0-9a-f]{64}', image) or bundle['source_revision'] != revision or not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Capture artifact identity mismatch')
    if bundle['config'] != config or config.get('native_writes') is not False:
        raise ValueError('Capture configuration mismatch')
    if bundle['writers'] != {'application': 'stopped', 'runtime_login': 'disabled', 'runtime_sessions': 0, 'other_writers': []}:
        raise ValueError('Capture writer boundary incomplete')
    archive = bundle['database']
    if set(archive) != {'base64', 'sha256', 'bytes'}:
        raise ValueError('Invalid database archive inventory')
    raw = base64.b64decode(archive['base64'], validate=True)
    if not raw.startswith(b'PGDMP') or len(raw) != archive['bytes'] or digest(raw) != archive['sha256']:
        raise ValueError('Database archive corrupt')
    files = validate(bundle['attachments'])
    snapshot = bundle['snapshot']
    if set(snapshot) != {'fixture_schema', 'tenants', 'permits', 'attachments'} or snapshot['fixture_schema'] != [{'version': 1}]:
        raise ValueError('Invalid logical database inventory')
    if snapshot['tenants'] != [{'tenant_id': 't_demo'}, {'tenant_id': 't_other'}]:
        raise ValueError('Invalid tenant inventory')
    permits = {(row['tenant_id'], row['permit_id']) for row in snapshot['permits']}
    attachments = {(row['tenant_id'], row['permit_id']) for row in snapshot['attachments']}
    if len(permits) != len(snapshot['permits']) or len(attachments) != len(snapshot['attachments']) or permits != attachments:
        raise ValueError('Incomplete permit and attachment relationships')
    expected = {row['object_key']: (row['sha256'], row['bytes']) for row in snapshot['attachments']}
    if len(expected) != len(attachments) or expected != {f['key']: (f['sha256'], f['bytes']) for f in files}:
        raise ValueError('Database and attachment inventory mismatch')
    for row in snapshot['attachments']:
        if row['tenant_id'] not in ('t_demo', 't_other') or row['object_key'] != f'{row["tenant_id"]}--{row["permit_id"]}.bin':
            raise ValueError('Invalid attachment ownership')
    return raw
