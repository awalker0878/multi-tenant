#!/usr/bin/env python3
"""Independent JSON Schema and domain conformance for the P09 directed matrix."""

import copy
import json
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'services/planning/src'), str(ROOT / 'services/planning/tests')]
from planning.domain.expansion import matrix, tranche
from planning.domain.model import Actor, Rejected
from planning.application.migration_support import MigrationSupport
from test_expansion import baseline

subprocess.run([sys.executable, str(ROOT / 'scripts/p09/generate_contract.py'), '--check'], check=True)
schema = json.loads((ROOT / 'contracts/schemas/expansion/tranche-v1.1.json').read_text())
Draft202012Validator.check_schema(schema)
validator = Draft202012Validator(schema, format_checker=FormatChecker())
package = json.loads((ROOT / 'contracts/schemas/expansion/adapter-package-v1.json').read_text())
Draft202012Validator.check_schema(package)
value = baseline()
validator.validate(value)
legacy = Draft202012Validator(
    json.loads((ROOT / 'contracts/schemas/expansion/tranche-v1.json').read_text()),
    format_checker=FormatChecker(),
)
legacy.validate(value)
extended = copy.deepcopy(value)
extended['routes'][0]['guest_outcomes_sha256'] = 'a' * 64
extended['routes'][0]['constraints']['maximum_data_loss_bytes'] = 0
validator.validate(extended)
tranche(extended)
assert not legacy.is_valid(extended), 'Published v1 must retain its original exact fields'
actor = Actor(str(uuid4()), str(uuid4()), 'plan.read', str(uuid4()), str(uuid4()))
support = MigrationSupport(lambda *_: extended, lambda *_: [], lambda: 100).read(actor, str(uuid4()))
for version in ('1.4', '1.5'):
    path = ROOT / f'contracts/openapi/planning-migration-v{version}.json'
    assert path.read_bytes() == (ROOT / 'apps/console/resources/contracts' / path.name).read_bytes()
    api = json.loads(path.read_text())
    wire = Draft202012Validator(
        {'$ref': '#/components/schemas/MigrationSupport', 'components': api['components']},
        format_checker=FormatChecker(),
    )
    assert wire.is_valid(support) == (version == '1.5'), 'Outcome extensions require the v1.5 wire contract'
for key, unsafe in [('guest_outcomes_sha256', 'invalid'), ('maximum_data_loss_bytes', -1)]:
    bad = copy.deepcopy(extended)
    owner = bad['routes'][0] if key == 'guest_outcomes_sha256' else bad['routes'][0]['constraints']
    owner[key] = unsafe
    assert not validator.is_valid(bad), key
    try:
        tranche(bad)
    except (Rejected, ValueError, TypeError):
        pass
    else:
        raise AssertionError(key + ' accepted by domain')
tranche(value)
assert len(matrix(value, [], 100)) == 9
assert not any(r['native_qualified'] for d in matrix(value, [], 100) for r in d['routes'])
for key, unsafe in [('schema_version', True), ('revision', 0), ('expires_at', -1),
                    ('release_sha256', 'unknown'), ('retest_triggers', []), ('operations', ['automatic_fallback'])]:
    bad = copy.deepcopy(value)
    bad[key] = unsafe
    assert list(validator.iter_errors(bad)), key
    try:
        tranche(bad)
    except (Rejected, ValueError, TypeError):
        pass
    else:
        raise AssertionError(key + ' accepted by domain')
print('P09 v1 stays frozen; v1.1 adds validated outcome/data-loss fields. Schema/domain agree; all nine directions remain unqualified without exact native evidence.')
