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
validate_spec(spec)
validator = Draft202012Validator(spec['components']['schemas']['BoundaryRequest'], format_checker=FormatChecker())
validator.validate(fixture)
negatives = []
for field, value in [('state_serial', True), ('project_id', '*'), ('expires_at', 0), ('plan_digest', 'short')]:
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
