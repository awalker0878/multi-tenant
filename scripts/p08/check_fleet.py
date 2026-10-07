"""Validate fleet wire bounds and published contract preservation independently."""
import copy
import json
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate_spec

ROOT = Path(__file__).resolve().parents[2]
api = json.loads((ROOT / 'contracts/openapi/inventory-v1.3.json').read_text())
validate_spec(api)
old = json.loads((ROOT / 'contracts/openapi/inventory-v1.2.json').read_text())
assert all(api['paths'][key] == value for key, value in old['paths'].items())
assert all(api['components']['schemas'][key] == value for key, value in old['components']['schemas'].items())
assert (ROOT / 'contracts/openapi/planning-migration-v1.json').read_bytes() == (ROOT / 'apps/console/resources/contracts/planning-migration-v1.json').read_bytes()
uid = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
resource = 'bbbbbbbb-bbbb-5bbb-8bbb-bbbbbbbbbbbb'
value = {'name': 'Wave 1', 'application_id': uid, 'environment_id': uid, 'target_profile_id': uid, 'format': 'qcow2', 'resource_ids': [resource]}
validator = Draft202012Validator({'$ref': '#/components/schemas/MigrationGroupInput', 'components': api['components']}, format_checker=FormatChecker())
validator.validate(value)
for fault in ({'native_write_authorized': True}, {'source_identity_sha256': 'a' * 64}, {'resource_ids': []}, {'resource_ids': [resource] * 2}, {'format': 'vmdk'}):
    bad = copy.deepcopy(value); bad.update(fault)
    assert not validator.is_valid(bad), fault
print('Fleet OpenAPI passes; published operations/schemas preserved; five unsafe group inputs rejected.')
