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


def reservation_records(path: Path | str | None = None) -> dict:
    """The repository's exported reservation record evidence.

    The authoritative reservation system is external. The repository exports what
    that system recorded and already owns the contract for reading it, so the
    provisioner asks for the export instead of defining a second record model.
    """
    module = repository_module('scripts.check_reservation_records')
    return module.load(Path(path) if path is not None else module.INDEX)


def validate_reservation_records(index: dict, *, as_of, root: Path | str | None = None) -> dict:
    """Validate an exported reservation record index with the repository's checker."""
    module = repository_module('scripts.check_reservation_records')
    return module.validate(index, as_of=as_of,
                           root=Path(root) if root is not None else ROOT)