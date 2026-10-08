"""Independent wire validation for native profiles and administrator review separation."""
import copy
import json
import sys
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
preparation = json.loads((ROOT / 'contracts/openapi/planning-migration-v1.json').read_text())
validate_spec(preparation)
sys.path.insert(0, str(ROOT / 'services/planning/src'))
from planning.domain.migration import bind_migration
from planning.domain.model import digest

profile = {'profile_sha256': digest('profile'), 'native_identity_sha256': digest('identity'), 'tuple_sha256': digest('tuple'), 'observed_at': 1000, 'expires_at': 1300}
inputs = {'current': True, 'native_write_authorized': False, 'revision': 1, 'digest': digest(fixture['review']), 'method': fixture['review']['method'], 'source': profile, 'target': profile,
          'datasets': fixture['review']['datasets'], 'disks': fixture['source']['disks'], 'target_disk_formats': ['raw'],
          'owner_inputs': fixture['review']['owner_inputs'], 'objectives': fixture['review']['objectives']}
mapping = [{'source_disk_sha256': disk['native_sha256'], 'target_key': f'aaaaaaaa-aaaa-4aaa-8aaa-{n:012d}', 'format': 'raw'} for n, disk in enumerate(inputs['disks'])]
response = {'binding': bind_migration(inputs, mapping, 1001), 'native_write_authorized': False}
request = {'site_id': 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 'review': response['binding']['review'], 'disks': mapping}
for name, value in [('PrepareMigration', request), ('Preparation', response)]:
    validator = Draft202012Validator({'$ref': '#/components/schemas/' + name, 'components': preparation['components']}, format_checker=FormatChecker())
    validator.validate(value)
    bad = copy.deepcopy(value)
    bad['native_write_authorized'] = True
    assert not validator.is_valid(bad), name
print('Profile/review/preparation OpenAPI and owner schema pass; eleven native-fact/authority injections denied.')
