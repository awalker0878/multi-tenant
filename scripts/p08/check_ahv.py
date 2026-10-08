"""Validate versioned AHV discovery/review/planning wires; no native qualification."""
import copy
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate_spec

ROOT = Path(__file__).resolve().parents[2]
for name in ('inventory-v1.5.json', 'inventory-native-input-v1.1.json', 'planning-v1.2.json', 'planning-migration-v1.3.json'):
    api = json.loads((ROOT / 'contracts/openapi' / name).read_text())
    validate_spec(api)
    if name != 'inventory-native-input-v1.1.json':
        assert (ROOT / 'apps/console/resources/contracts' / name).read_bytes() == (ROOT / 'contracts/openapi' / name).read_bytes()
api = json.loads((ROOT / 'contracts/openapi/inventory-v1.5.json').read_text())
fixture = json.loads((ROOT / 'contracts/fixtures/inventory/ahv-destination-v1.json').read_text())
for schema, name in [('SourceWorkloadProfile', 'source'), ('TargetCapabilityProfile', 'target'), ('MigrationReviewInput', 'review')]:
    validator = Draft202012Validator({'$ref': '#/components/schemas/' + schema, 'components': api['components']}, format_checker=FormatChecker())
    validator.validate(fixture[name])
    for field in ('credential', 'native_write_authorized', 'api_override'):
        bad = copy.deepcopy(fixture[name]); bad[field] = 'forged'
        assert not validator.is_valid(bad)
owner = ROOT / 'contracts/schemas/planning/migration-input-v2.json'
assert owner.read_bytes() == (ROOT / 'services/planning/src/planning/infrastructure/inputs/migration-input-v2.json').read_bytes()
Draft202012Validator.check_schema(json.loads(owner.read_text()))
sys.path.insert(0, str(ROOT / 'services/inventory/src'))
from inventory.domain.ahv import destination_input
from inventory.domain.workload import profile_payload, review_input
review_input(fixture['review'], fixture['source'])
destination_input(fixture['review'], fixture['source'], fixture['target'])
profile_payload(fixture['target'], {'kind': 'target_profile', 'api_version': 'v4.3', 'shared_resource_ids': [], **{k: fixture['target'][k] for k in ('cluster_id', 'prism_central_id')}}, fixture['target']['project_id'])
print('AHV profile, all-device review and versioned contracts pass; no native support is asserted.')
