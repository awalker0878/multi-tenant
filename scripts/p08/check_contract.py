"""Versioned migration wire assertions without changing published v1 fixtures."""
import copy
import json
import sys
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate_spec

ROOT = Path(__file__).resolve().parents[2]
fixture = json.loads((ROOT / 'contracts/fixtures/lifecycle/migration-stage-grant-v2.json').read_text())
for name,request in [('lifecycle-migration-boundary-v2.json','BoundaryRequest'),('worker-migration-effect-v2.json','EffectRequest')]:
    spec=json.loads((ROOT / 'contracts/openapi' / name).read_text())
    validate_spec(spec)
    validator=Draft202012Validator(spec['components']['schemas'][request],format_checker=FormatChecker())
    positive=fixture if request=='BoundaryRequest' else {'grant':fixture['grant']}
    validator.validate(positive)
    for key,value in [('schema_version',True),('stage','automatic_fallback'),('intent_digest','unbound'),('expires_at',0)]:
        negative=copy.deepcopy(positive)
        negative['grant'][key]=value
        assert list(validator.iter_errors(negative)), key
print('Both migration v2 OpenAPI contracts and bound fixture pass; eight unsafe requests denied.')

sys.path[:0] = [str(ROOT / 'services/lifecycle/src'), str(ROOT / 'workers/lifecycle/src')]
from lifecycle.domain.migration import BEFORE, AFTER
from lifecycle_worker.application.migration_runtime import MIGRATION_STAGES
assert set(BEFORE) == set(AFTER) == MIGRATION_STAGES
print('Lifecycle prerequisites/results and isolated worker stage registry agree exactly.')

campaign = json.loads((ROOT / 'contracts/openapi/lifecycle-migration-campaigns-v1.json').read_text())
validate_spec(campaign)
validator = Draft202012Validator({'$ref': '#/components/schemas/CommandRequest', 'components': campaign['components']}, format_checker=FormatChecker())
validator.validate({'action': 'pause', 'expected_revision': 1})
for negative in ({'action': 'force', 'expected_revision': 1}, {'action': 'schedule', 'expected_revision': True}, {'action': 'cancel', 'expected_revision': 1, 'release_allocations': True}):
    assert list(validator.iter_errors(negative))
print('Migration campaign contract is valid; bypass commands are denied.')
