"""Validate the additive operator contract and reject forged facts/authority."""
import copy
import json
from pathlib import Path
from jsonschema import Draft202012Validator
from openapi_spec_validator import validate_spec

ROOT = Path(__file__).resolve().parents[2]
api = json.loads((ROOT / 'contracts/openapi/inventory-v1.4.json').read_text())
old = json.loads((ROOT / 'contracts/openapi/inventory-v1.3.json').read_text())
validate_spec(api)
assert all(api['paths'][k] == v for k, v in old['paths'].items())
assert all(api['components']['schemas'][k] == v for k, v in old['components']['schemas'].items())
def validator(name):
    return Draft202012Validator({'$ref': '#/components/schemas/' + name, 'components': api['components']})
fixture = json.loads((ROOT / 'contracts/fixtures/inventory/operator-inputs-v1.json').read_text())
validator('OperatorWorkspace').validate(fixture)
fields = api['components']['schemas']['OperatorValues']['properties']
assert set(fields) == {f['id'] for f in fixture['fields']} == set(fixture['missing_fields'])
body = {'values': {'max_outage_seconds': 0, 'max_data_loss_bytes': 0}, 'configuration_digest': None}
validator('OperatorInput').validate(body)
for patch in ({'native_write_authorized': True}, {'values': {'api_version': 'invented'}}, {'values': {'max_outage_seconds': True}}, {'values': {'max_outage_seconds': -1}}, {'values': {'source_writer_ref': 'Bearer secret'}}):
    bad = copy.deepcopy(body); bad.update(patch)
    assert not validator('OperatorInput').is_valid(bad), patch
print('Operator contract passes; all published paths/schemas preserved; zero targets accepted; five invalid packets rejected.')
