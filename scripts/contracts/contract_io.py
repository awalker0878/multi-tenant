"""Read unambiguous JSON-compatible contract documents; no permissive fallback."""
from __future__ import annotations

import json
import math
from pathlib import Path

import yaml


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if not isinstance(key, str):
            raise ValueError("Contract object keys must be strings")
        if key in result:
            raise ValueError(f"Duplicate contract key: {key}")
        result[key] = value
    return result


def _constant(value):
    raise ValueError(f"Non-JSON contract number: {value}")


class _ContractLoader(yaml.SafeLoader):
    pass


def _mapping(loader, node):
    # Contract mappings must not depend on override order, including YAML merges.
    loader.flatten_mapping(node)
    return _pairs((loader.construct_object(key), loader.construct_object(value))
                  for key, value in node.value)


_ContractLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def _json_value(value, ancestors=None):
    ancestors = set() if ancestors is None else ancestors
    if isinstance(value, (dict, list)):
        if id(value) in ancestors:
            raise ValueError("Recursive contract values are not JSON")
        ancestors = ancestors | {id(value)}
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("Contract object keys must be strings")
        for child in value.values():
            _json_value(child, ancestors)
    elif isinstance(value, list):
        for child in value:
            _json_value(child, ancestors)
    elif type(value) is float and not math.isfinite(value):
        raise ValueError("Non-JSON contract number")
    elif value is not None and type(value) not in {str, int, float, bool}:
        raise ValueError("Contract contains a non-JSON value")


def loads(text: str, *, yaml_document: bool = False):
    value = (yaml.load(text, Loader=_ContractLoader) if yaml_document else
             json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant))
    _json_value(value)
    return value


def read(path: Path):
    return loads(path.read_text(encoding="utf-8"), yaml_document=path.suffix in {".yaml", ".yml"})
