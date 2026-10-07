"""Independent wire validation for native profiles and administrator review separation."""
import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate_spec

ROOT = Path(__file__).resolve().parents[2]
api = json.loads((ROOT / 'contracts/openapi/inventory-v1.2.json').read_text())
validate_spec(api)
fixture = json.loads((ROOT / 'contracts/fixtures/inventory/migration-profile-v1.json').read_text())
for name, value in [('SourceWorkloadProfile', fixture['source']), ('TargetCapabilityProfile', fixture['target']), ('MigrationReviewInput', fixture['review'])]:
    validator = Draft202012Validator({'$ref': '#/components/schemas/' + name, 'components': api['components']}, format_checker=FormatChecker())
    validator.validate(value)
    for field in ('native_write_authorized', 'credential', 'api_override'):
        bad = copy.deepcopy(value)
        bad[field] = 'forged'
        assert not validator.is_valid(bad), (name, field)
owner = ROOT / 'contracts/schemas/planning/migration-input-v1.json'
assert owner.read_bytes() == (ROOT / 'services/planning/src/planning/infrastructure/inputs/migration-input-v1.json').read_bytes()
Draft202012Validator.check_schema(json.loads(owner.read_text()))
print('Profile/review OpenAPI and owner schema pass; nine native-fact/authority injections denied.')
