#!/usr/bin/env python3
"""Validate the internal native wire contract using the existing locked contract toolchain."""
import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate_spec

ROOT = Path(__file__).resolve().parents[2]
spec = json.loads((ROOT / 'contracts/openapi/lifecycle-native-boundary-v1.json').read_text())
fixture = json.loads((ROOT / 'contracts/fixtures/lifecycle/native-stage-grant-v1.json').read_text())
worker_fixture = json.loads((ROOT / 'workers/lifecycle/tests/fixtures/native-stage-grant-v1.json').read_text())
assert worker_fixture == fixture, 'isolated worker fixture differs from the published contract'
validate_spec(spec)
validator = Draft202012Validator(spec['components']['schemas']['BoundaryRequest'], format_checker=FormatChecker())
validator.validate(fixture)
negatives = []
for field, value in [('custody_generation', True), ('project_id', '*'), ('expires_at', 0), ('plan_digest', 'short')]:
    case = copy.deepcopy(fixture)
    case['grant']['native_binding'][field] = value
    negatives.append(case)
case = copy.deepcopy(fixture)
del case['grant']['native_binding']
negatives.append(case)
case = copy.deepcopy(fixture)
case['grant']['stage'] = 'retire'
negatives.append(case)
case = copy.deepcopy(fixture)
case['worker_id'] = 'caller-controlled'
negatives.append(case)
for case in negatives:
    assert list(validator.iter_errors(case)), 'unsafe contract accepted'
print('Native contract: OpenAPI and golden provision request pass; seven unsafe variants denied.')

effect = json.loads((ROOT / 'contracts/openapi/worker-native-effect-v1.json').read_text())
validate_spec(effect)
expected_grant = copy.deepcopy(spec['components']['schemas']['BoundaryRequest']['properties']['grant'])
expected_grant['properties']['stage'] = {'type': 'string', 'const': 'provision'}
expected_grant['required'].append('native_binding')
assert effect['components']['schemas']['EffectRequest']['properties']['grant'] == expected_grant
effect_validator = Draft202012Validator(effect['components']['schemas']['EffectRequest'], format_checker=FormatChecker())
effect_validator.validate({'grant': fixture['grant']})
for case in negatives:
    request = {k: v for k, v in case.items() if k != 'boundary'}
    assert list(effect_validator.iter_errors(request)), 'unsafe worker request accepted'
print('Native effect contract: same exact provision grant; unsafe variants denied.')

for filename, component, positive in (
    ('planning-native-v1.json', 'NativeProposal', {k: '10000000-0000-4000-8000-000000000001' for k in ('site_id', 'base_plan_id', 'recipe_id')}),
    ('lifecycle-native-jobs-v1.json', 'PlanReference', {'plan_id': '10000000-0000-4000-8000-000000000001', 'approval_id': '10000000-0000-4000-8000-000000000002', 'plan_revision': 1, 'plan_digest': 'a' * 64}),
    ('lifecycle-native-jobs-v1.json', 'Stop', {'expected_revision': 1}),
):
    product = json.loads((ROOT / 'contracts/openapi' / filename).read_text())
    validate_spec(product)
    v = Draft202012Validator(product['components']['schemas'][component], format_checker=FormatChecker())
    v.validate(positive)
    assert list(v.iter_errors(positive | {'native_write_authorized': True}))
    assert list(v.iter_errors({}))
print('Native product proposal/admission/stop contracts pass; inline authority and incomplete requests rejected.')
