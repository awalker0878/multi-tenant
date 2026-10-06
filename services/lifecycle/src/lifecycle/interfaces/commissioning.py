"""Bounded local input parser. Errors never echo input values or file paths."""

import json
import os
import stat
from pathlib import Path
from typing import Any

from lifecycle.domain.execution import Rejected


def read_regular(path: Path, limit: int) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise Rejected("regular_input_file_required", 422)
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            raw = handle.read(limit + 1)
        if len(raw) > limit:
            raise Rejected("input_size_bound", 413)
        return raw
    finally:
        os.close(descriptor)


def read_json(path: Path) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise Rejected("duplicate_json_key", 422)
            result[key] = value
        return result

    def constant(_: str) -> Any:
        raise Rejected("nonfinite_json_number", 422)

    value = json.loads(read_regular(path, 262144), object_pairs_hook=pairs, parse_constant=constant)
    if not isinstance(value, dict):
        raise Rejected("json_object_required", 422)
    return value
