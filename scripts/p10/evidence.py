"""Bounded local evidence reads. Integrity is not provenance or receiving acceptance."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path, PurePosixPath


class Held(ValueError):
    pass


def require(value, reason):
    if not value:
        raise Held(reason)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result

    return json.loads(
        raw,
        object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(Held("nonfinite_json")),
    )


def bounded_file(root, relative, limit=16 * 1024 * 1024):
    root = Path(root).resolve()
    p = PurePosixPath(relative)
    require(
        isinstance(relative, str)
        and relative
        and str(p) == relative
        and not p.is_absolute()
        and ".." not in p.parts
        and "\\" not in relative,
        "unsafe_evidence_path",
    )
    path = root / relative
    require(
        not any(q.is_symlink() for q in (path, *path.parents))
        and path.resolve().is_relative_to(root),
        "symlinked_evidence",
    )
    require(
        path.is_file() and path.stat().st_size <= limit, "missing_or_unbounded_evidence"
    )
    raw = path.read_bytes()
    require(len(raw) <= limit, "unbounded_evidence")
    return raw


def reference(root, value):
    require(
        isinstance(value, dict) and set(value) == {"path", "sha256"},
        "invalid_evidence_ref",
    )
    raw = bounded_file(root, value["path"])
    require(digest(raw) == value["sha256"], "changed_evidence:" + value["path"])
    return decode(raw)


def number(value, minimum=0):
    require(
        type(value) in (float, int) and math.isfinite(value) and value >= minimum,
        "invalid_measurement",
    )
    return value
