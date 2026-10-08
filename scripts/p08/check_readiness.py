"""Versioned readiness/evidence contracts; legacy wire shapes remain accepted."""
import copy
import json
from pathlib import Path
from jsonschema import Draft202012Validator
from openapi_spec_validator import validate_spec

ROOT = Path(__file__).resolve().parents[2]
api = json.loads((ROOT / 'contracts/openapi/inventory-v1.6.json').read_text())
old = json.loads((ROOT / 'contracts/openapi/inventory-v1.5.json').read_text())
validate_spec(api)
assert all(api['paths'][k] == v for k, v in old['paths'].items())
for name, schema in old['components']['schemas'].items():
    before, after = copy.deepcopy(schema), copy.deepcopy(api['components']['schemas'][name])
    if name == 'AhvTargetCapabilityProfile':
        for field in ('storage_containers', 'subnets', 'vpcs', 'categories', 'policies'):
            assert after['properties'][field]['maxItems'] == 1000
            after['properties'][field]['maxItems'] = before['properties'][field]['maxItems']
    if name == 'ConfigurationQuery':
        assert after['properties']['items']['maxItems'] == 1000
        after['properties']['items']['maxItems'] = before['properties']['items']['maxItems']
    assert before == after, name

def validator(name):
    return Draft202012Validator({'$ref': '#/components/schemas/' + name, 'components': api['components']})

fixture = json.loads((ROOT / 'contracts/fixtures/inventory/operator-readiness-v1.json').read_text())
validator('ReadinessWorkspace').validate(fixture)
legacy = json.loads((ROOT / 'contracts/fixtures/inventory/operator-inputs-v1.json').read_text())
validator('OperatorWorkspace').validate(legacy)
body = {'values': {'max_outage_seconds': 0}, 'configuration_digest': None,
        'context': {'operation': 'migrate', 'method': 'VM_COLD_EXPORT'}}
validator('ReadinessInput').validate(body)
for patch in ({'native_write_authorized': True}, {'context': {'operation': 'migrate', 'method': None}},
              {'context': {'operation': 'discover', 'method': 'VM_COLD_EXPORT'}},
              {'context': {'operation': 'provision', 'method': None, 'verified': True}},
              {'values': {'max_outage_seconds': True}}):
    bad = copy.deepcopy(body); bad.update(patch)
    assert not validator('ReadinessInput').is_valid(bad), patch
schema = json.loads((ROOT / 'contracts/schemas/inventory/commissioning-evidence-v1.json').read_text())
Draft202012Validator.check_schema(schema)
report = {'schema_version': 1, 'producer_id': 'platform-owner', 'tenant_id': fixture['tenant_id'],
          'site_id': fixture['site_id'], 'packet_digest': 'a'*64, 'configuration_digest': None,
          'checks': [{'field_id': 'source_writer_ref', 'value_sha256': 'b'*64, 'result': 'verified',
                      'observed_at': 100, 'expires_at': 200, 'evidence_file': '/synthetic/observation.json', 'evidence_sha256': 'c'*64}]}
Draft202012Validator(schema).validate(report)
for patch in ({'native_write_authorized': True}, {'schema_version': 2}, {'checks': []}):
    bad = copy.deepcopy(report); bad.update(patch)
    assert not Draft202012Validator(schema).is_valid(bad), patch
print('Readiness, preserved legacy contracts, task/method consistency and evidence schemas pass.')
