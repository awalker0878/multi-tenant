"""Access to the existing repository tooling.

The provisioner reuses the repository's mature tools instead of reimplementing
them. This module is the single place that puts the repository root on the import
path so those tools can be imported by name.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def repository_module(name: str):
    """Import an existing repository module, failing loudly if it is absent."""
    return importlib.import_module(name)


def relative(path: Path | str) -> str:
    path = Path(path)
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def source_commit(root: Path | str | None = None) -> dict:
    """The clean checkout commit the existing release verifier reports.

    A delivery handoff binds one exact clean source commit. The repository
    already owns that answer, so the provisioner asks for it instead of
    computing a second opinion.
    """
    verifier = repository_module('tools.check_release')
    result = verifier.verify(Path(root) if root is not None else ROOT)
    return {'status': result.get('status', ''), 'commit': result.get('commit', ''),
            'issues': list(result.get('issues', []))}