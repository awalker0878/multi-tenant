#!/usr/bin/env python3
"""Validate P00 input records without network access, native calls or permissions.

The schema describes input completeness, not authorization or experiment success.
This standard-library validator implements only the JSON Schema keywords used by
the checked-in schema. Actual evidence bytes and accountable identity are reviewed
in the protected operating record, never inferred from syntactically valid JSON.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECORD = ROOT / "docs/qualification/feasibility/p00-input-record.json"
DEFAULT_SCHEMA = ROOT / "docs/qualification/feasibility/p00-input-schema.json"
PROTECTED_URI = re.compile(r"evidence://[A-Za-z0-9_-]+/[A-Za-z0-9._/-]+\Z")
REPOSITORY_URI = re.compile(
    r"git://awalker0878/multi-tenant/[a-f0-9]{40}/[A-Za-z0-9._/-]+\Z"
)
WILDCARD_SCOPE = re.compile(r"[*?\[\]]|^(all|any|unrestricted)$", re.I)
RECOVERY_METHODS = {"source_return_with_reconciliation", "target_forward_recovery"}


def matches_type(value: object, kind: str) -> bool:
    return {
        "null": value is None,
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "boolean": isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool)
                  and (not isinstance(value, float) or math.isfinite(value)),
        "integer": isinstance(value, int) and not isinstance(value, bool),
    }.get(kind, False)


def schema_errors(value: object, spec: dict, schema: dict, path: str = "$") -> list[str]:
    """Apply the documented subset; reject unknown validation keywords."""
    known = {
        "$schema", "$id", "$defs", "$ref", "title", "description", "type",
        "required", "additionalProperties", "properties", "items", "minItems",
        "minLength", "pattern", "enum", "const",
    }
    errors = [f"{path}: unsupported schema keyword {key}" for key in spec
              if key not in known and not key.startswith("x-")]
    if "$ref" in spec:
        ref = spec["$ref"]
        if not ref.startswith("#/$defs/") or ref[8:] not in schema["$defs"]:
            return errors + [f"{path}: unsupported schema reference {ref}"]
        return errors + schema_errors(value, schema["$defs"][ref[8:]], schema, path)
    kinds = spec.get("type")
    if kinds and not any(matches_type(value, kind) for kind in
                         (kinds if isinstance(kinds, list) else [kinds])):
        return errors + [f"{path}: expected {kinds}"]
    if "const" in spec and (type(value) is not type(spec["const"]) or value != spec["const"]):
        errors.append(f"{path}: expected constant {spec['const']!r}")
    if "enum" in spec and value not in spec["enum"]:
        errors.append(f"{path}: expected one of {spec['enum']}")
    if isinstance(value, str):
        if len(value) < spec.get("minLength", 0) or not value.strip():
            errors.append(f"{path}: expected a nonempty string")
        if "pattern" in spec and not re.search(spec["pattern"], value):
            errors.append(f"{path}: invalid format")
    if isinstance(value, dict):
        for key in spec.get("required", []):
            if key not in value:
                errors.append(f"{path}.{key}: required field missing")
        properties = spec.get("properties", {})
        for key, item in value.items():
            if key in properties:
                errors.extend(schema_errors(item, properties[key], schema, f"{path}.{key}"))
            elif spec.get("additionalProperties") is False:
                errors.append(f"{path}.{key}: unrecognized field")
    if isinstance(value, list):
        if len(value) < spec.get("minItems", 0):
            errors.append(f"{path}: expected at least {spec['minItems']} items")
        for index, item in enumerate(value):
            errors.extend(schema_errors(item, spec.get("items", {}), schema, f"{path}[{index}]"))
    return errors


def valid_timestamp(value: str | None) -> bool:
    if value is None:
        return False
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).utcoffset() is not None
    except ValueError:
        return False


def cell_errors(cell: dict, path: str) -> list[str]:
    errors = []
    status = cell["status"]
    observed = status in {"OBSERVED", "BLOCKED"}
    if status == "UNKNOWN" and any(cell[key] is not None for key in
                                    ("value", "observed_at", "observed_by", "scope")):
        errors.append(f"{path}: UNKNOWN must not carry an asserted value or observation")
    if status == "UNKNOWN" and cell["evidence"]:
        errors.append(f"{path}: UNKNOWN must not claim supplied evidence")
    if status != "UNKNOWN" and cell["value"] is None:
        errors.append(f"{path}: {status} requires an explicit value; false is distinct from unknown")
    if status == "PROPOSED" and (cell["observed_at"] or cell["observed_by"]):
        errors.append(f"{path}: a proposal cannot claim an observation")
    if observed and not all([cell["evidence"], cell["observed_by"], cell["scope"],
                             valid_timestamp(cell["observed_at"])]):
        errors.append(f"{path}: {status} requires evidence, observer, zoned observation time and scope")
    for stamp in ("observed_at",):
        if cell[stamp] is not None and not valid_timestamp(cell[stamp]):
            errors.append(f"{path}.{stamp}: expected an ISO 8601 timestamp with timezone")
    for index, ref in enumerate(cell["evidence"]):
        pattern = PROTECTED_URI if ref["kind"] == "protected" else REPOSITORY_URI
        if not pattern.fullmatch(ref["uri"]) or ".." in ref["uri"].split("/"):
            errors.append(f"{path}.evidence[{index}]: expected an opaque protected reference or pinned repository source")
        if ref["revision"].lower() in {"latest", "main", "master", "head", "current"}:
            errors.append(f"{path}.evidence[{index}]: mutable revision is not evidence identity")
        if ref["kind"] == "repository" and REPOSITORY_URI.fullmatch(ref["uri"]):
            if ref["revision"] != ref["uri"].split("/")[4]:
                errors.append(f"{path}.evidence[{index}]: repository revision must match the pinned URI commit")
    scope = cell["scope"]
    if scope:
        if len(scope["resource_ids"]) != len(set(scope["resource_ids"])):
            errors.append(f"{path}.scope: duplicate resource IDs")
        for resource in scope["resource_ids"]:
            if WILDCARD_SCOPE.search(resource) or "://" in resource:
                errors.append(f"{path}.scope: resource IDs must be explicit opaque IDs without wildcard or endpoint")
    value = cell["value"]
    if isinstance(value, str) and "://" in value:
        errors.append(f"{path}.value: keep endpoint addresses and locations in protected evidence")
    review = cell["review"]
    reviewed = review["disposition"] != "NOT_REVIEWED"
    if reviewed and not (review["reviewed_by"] and valid_timestamp(review["reviewed_at"])):
        errors.append(f"{path}.review: disposition requires actual reviewer and zoned review time")
    if not reviewed and (review["reviewed_by"] is not None or review["reviewed_at"] is not None):
        errors.append(f"{path}.review: unreviewed input cannot name a completed review")
    if review["disposition"] == "ACCEPTED" and status != "OBSERVED":
        errors.append(f"{path}: only a supplied OBSERVED input can have an accepted review")
    if path.endswith("RT10.post_write_recovery_method") and observed and value not in RECOVERY_METHODS:
        errors.append(f"{path}: select source_return_with_reconciliation or target_forward_recovery")
    if path.endswith(("RT10.permitted_resource_scope", "RT10.permitted_effects", "RT02.permitted_reads_effects")):
        if isinstance(value, str) and WILDCARD_SCOPE.search(value):
            errors.append(f"{path}: blanket or wildcard authority is not a bounded input")
    return errors


def validate(record: dict, schema: dict, scope: str = "route") -> dict:
    errors = schema_errors(record, schema, schema)
    base = {"schema_version": 1, "scope": scope, "record_valid": not errors,
            "input_ready": False, "authorizes_execution": False,
            "establishes_feasibility": False, "errors": errors,
            "missing_inputs": [], "packages": {}}
    if errors:
        return base
    missing = []
    ready_groups = {}
    for group_id, group in record["groups"].items():
        ready_groups[group_id] = True
        for field, cell in group["fields"].items():
            path = f"{group_id}.{field}"
            errors.extend(cell_errors(cell, path))
            if cell["status"] != "OBSERVED" or cell["review"]["disposition"] != "ACCEPTED":
                ready_groups[group_id] = False
                missing.append({"input": path, "status": cell["status"],
                                "review": cell["review"]["disposition"],
                                "accountable_role": group["accountable_role"]})
    packages = schema["x-input-packages"]
    for package, groups in packages.items():
        base["packages"][package] = {"input_ready": all(ready_groups[g] for g in groups),
                                    "groups": groups,
                                    "missing_inputs": [m["input"] for m in missing if m["input"].split(".")[0] in groups]}
    selected = (list(ready_groups) if scope == "all" else schema["x-route-groups"]
                if scope == "route" else packages[scope])
    route_ready = all(ready_groups[g] for g in schema["x-route-groups"])
    if record["claimed_input_readiness"] == "READY" and not route_ready:
        errors.append("claimed_input_readiness: READY contradicts incomplete route inputs")
    base.update(record_valid=not errors, input_ready=not errors and all(ready_groups[g] for g in selected),
                missing_inputs=[m for m in missing if m["input"].split(".")[0] in selected])
    # Invalid records cannot have a ready package even if their statuses say otherwise.
    if errors:
        for package in base["packages"].values():
            package["input_ready"] = False
    return base


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, default=DEFAULT_RECORD)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--scope", choices=["route", "all", *[f"IP0{i}" for i in range(1, 8)]], default="route")
    parser.add_argument("--require-ready", action="store_true", help="Fail on incomplete selected inputs; grants no execution authority")
    parser.add_argument("--report", type=Path, help="Write JSON report; otherwise print JSON to stdout")
    args = parser.parse_args(argv)
    try:
        report = validate(load_json(args.record), load_json(args.schema), args.scope)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Cannot validate P00 input record: {exc}", file=sys.stderr)
        return 1
    output = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.write_text(output)
    else:
        print(output, end="")
    if not report["record_valid"]:
        return 1
    return 2 if args.require_ready and not report["input_ready"] else 0


def reject_nonfinite(value: str) -> None:
    raise ValueError(f"Nonstandard JSON numeric constant: {value}")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(), parse_constant=reject_nonfinite)


if __name__ == "__main__":
    sys.exit(main())
