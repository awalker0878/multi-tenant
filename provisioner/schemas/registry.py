"""Versioned schema registry and a bounded, deterministic validator.

The validator deliberately supports a reviewed subset of JSON Schema. Anything
outside that subset fails closed rather than being silently ignored.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_ROOT = ROOT / 'provisioner' / 'schemas'

SCHEMAS = {
    'workload-security-domain': 'v1/workload-security-domain.schema.json',
    'resolved-desired-state': 'v1/resolved-desired-state.schema.json',
    'placement-decision': 'v1/placement-decision.schema.json',
    'conformance-report': 'v1/conformance-report.schema.json',
    'workload-mobility': 'v1/workload-mobility.schema.json',
}

SUPPORTED_KEYWORDS = {
    '$schema', '$id', 'title', 'description', 'type', 'const', 'enum', 'required',
    'properties', 'additionalProperties', 'patternProperties', 'items', 'minItems',
    'maxItems', 'uniqueItems', 'minLength', 'maxLength', 'pattern', 'minimum',
    'minProperties', 'maxProperties',
    'maximum', 'exclusiveMinimum', 'exclusiveMaximum', 'allOf', 'anyOf', 'oneOf',
    'not', '$ref', 'definitions', 'default',
}

_TYPES = {
    'object': dict, 'array': list, 'string': str, 'boolean': bool,
    'integer': int, 'number': (int, float), 'null': type(None),
}

_cache: dict[str, dict] = {}


def load_schema(name: str) -> dict:
    if name not in SCHEMAS:
        raise ValueError(f'Unknown schema: {name}')
    if name not in _cache:
        path = SCHEMA_ROOT / SCHEMAS[name]
        _cache[name] = json.loads(path.read_text(encoding='utf-8'))
    return _cache[name]


def _matches_type(value, expected: str) -> bool:
    if expected == 'boolean':
        return isinstance(value, bool)
    if expected == 'integer':
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == 'number':
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, _TYPES[expected])


def _resolve(schema: dict, root: dict) -> dict:
    seen = 0
    while '$ref' in schema:
        ref = schema['$ref']
        if not ref.startswith('#/'):
            raise ValueError(f'Unsupported external schema reference: {ref}')
        node = root
        for part in ref[2:].split('/'):
            node = node[part]
        schema = node
        seen += 1
        if seen > 32:
            raise ValueError('Schema reference loop')
    return schema


def _unsupported(schema: dict, path: str, problems: list) -> None:
    unknown = set(schema) - SUPPORTED_KEYWORDS
    if unknown:
        problems.append({'path': path, 'message': f'Unsupported schema keyword: {sorted(unknown)[0]}'})


def validate(instance, schema: dict, path: str = '$', problems: list | None = None) -> list[dict]:
    """Return every schema violation as {'path', 'message'} in document order."""
    if problems is None:
        problems = []
    return _validate(instance, schema, schema, path, problems)


def _validate(instance, schema: dict, root: dict, path: str,
              problems: list) -> list[dict]:
    schema = _resolve(schema, root)
    _unsupported(schema, path, problems)
    if 'const' in schema and instance != schema['const']:
        problems.append({'path': path, 'message': f'Must equal {schema["const"]!r}'})
    if 'enum' in schema and instance not in schema['enum']:
        problems.append({'path': path, 'message': f'Must be one of {schema["enum"]}'})
    expected = schema.get('type')
    if expected is not None:
        allowed = expected if isinstance(expected, list) else [expected]
        if not any(_matches_type(instance, t) for t in allowed):
            problems.append({'path': path, 'message': f'Must be of type {expected}'})
            return problems
    if isinstance(instance, str):
        if 'minLength' in schema and len(instance) < schema['minLength']:
            problems.append({'path': path, 'message': f'Shorter than {schema["minLength"]}'})
        if 'maxLength' in schema and len(instance) > schema['maxLength']:
            problems.append({'path': path, 'message': f'Longer than {schema["maxLength"]}'})
        if 'pattern' in schema and not re.search(schema['pattern'], instance):
            problems.append({'path': path, 'message': f'Does not match {schema["pattern"]}'})
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if 'minimum' in schema and instance < schema['minimum']:
            problems.append({'path': path, 'message': f'Below minimum {schema["minimum"]}'})
        if 'maximum' in schema and instance > schema['maximum']:
            problems.append({'path': path, 'message': f'Above maximum {schema["maximum"]}'})
    if isinstance(instance, list):
        if 'minItems' in schema and len(instance) < schema['minItems']:
            problems.append({'path': path, 'message': f'Fewer than {schema["minItems"]} items'})
        if 'maxItems' in schema and len(instance) > schema['maxItems']:
            problems.append({'path': path, 'message': f'More than {schema["maxItems"]} items'})
        if schema.get('uniqueItems'):
            rendered = [json.dumps(v, sort_keys=True) for v in instance]
            if len(set(rendered)) != len(rendered):
                problems.append({'path': path, 'message': 'Duplicate items are not allowed'})
        if 'items' in schema:
            for index, item in enumerate(instance):
                _validate(item, schema['items'], root, f'{path}[{index}]', problems)
    if isinstance(instance, dict):
        if 'minProperties' in schema and len(instance) < schema['minProperties']:
            problems.append({'path': path,
                             'message': f'Fewer than {schema["minProperties"]} properties'})
        if 'maxProperties' in schema and len(instance) > schema['maxProperties']:
            problems.append({'path': path,
                             'message': f'More than {schema["maxProperties"]} properties'})
        for key in schema.get('required', []):
            if key not in instance:
                problems.append({'path': f'{path}.{key}', 'message': 'Required property is missing'})
        properties = schema.get('properties', {})
        patterns = schema.get('patternProperties', {})
        extra = schema.get('additionalProperties', True)
        for key, value in instance.items():
            child = f'{path}.{key}'
            if key in properties:
                _validate(value, properties[key], root, child, problems)
                continue
            matched = [spec for pattern, spec in patterns.items() if re.search(pattern, key)]
            if matched:
                for spec in matched:
                    _validate(value, spec, root, child, problems)
                continue
            if extra is False:
                problems.append({'path': child, 'message': 'Unknown property is not allowed'})
            elif isinstance(extra, dict):
                _validate(value, extra, root, child, problems)
    for spec in schema.get('allOf', []):
        _validate(instance, spec, root, path, problems)
    for keyword in ('anyOf', 'oneOf'):
        specs = schema.get(keyword, [])
        if not specs:
            continue
        matched = 0
        for spec in specs:
            branch: list[dict] = []
            _validate(instance, spec, root, path, branch)
            if not branch:
                matched += 1
        if keyword == 'anyOf' and matched == 0:
            problems.append({'path': path, 'message': 'No anyOf branch matched'})
        if keyword == 'oneOf' and matched != 1:
            problems.append({'path': path,
                             'message': f'oneOf requires exactly one match, found {matched}'})

    if 'not' in schema:
        branch = []
        _validate(instance, schema['not'], root, path, branch)
        if not branch:
            problems.append({'path': path, 'message': 'Forbidden by "not" schema'})
    return problems


def validate_named(instance, name: str, path: str = '$') -> list[dict]:
    return validate(instance, load_schema(name), path=path)