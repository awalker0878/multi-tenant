"""Shared transport helpers for the hosting command line.

The CLI is a transport only. Every command delegates to the same reusable core
modules — the operations they share live in `provisioner/execution/service.py`,
which is why no command imports another — and nothing in this package decides
policy, placement or allocation.
"""
from __future__ import annotations

import json

EXIT_OK = 0
EXIT_REFUSED = 2
EXIT_INTERNAL = 3


def emit(payload: dict, stream=None, indent: int = 2) -> None:
    """Render one JSON result document, deterministically and without secrets."""
    import sys
    stream = stream if stream is not None else sys.stdout
    json.dump(payload, stream, indent=indent, sort_keys=True)
    stream.write('\n')


def refused(payload: dict) -> tuple[int, dict]:
    return EXIT_REFUSED, payload