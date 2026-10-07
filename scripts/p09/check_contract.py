#!/usr/bin/env python3
"""Independent JSON Schema and domain conformance for the P09 directed matrix."""

import copy
import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'services/planning/src'), str(ROOT / 'services/planning/tests')]
from planning.domain.expansion import matrix, tranche
from planning.domain.model import Rejected
from test_expansion import baseline

subprocess.run([sys.executable, str(ROOT / 'scripts/p09/generate_contract.py'), '--check'], check=True)
schema = json.loads((ROOT / 'contracts/schemas/expansion/tranche-v1.json').read_text())
Draft202012Validator.check_schema(schema)
validator = Draft202012Validator(schema, format_checker=FormatChecker())
value = baseline()
validator.validate(value)
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
print('P09 schema/domain agree; all nine directions remain unqualified without exact native evidence.')
