"""Shared transport helpers for the hosting command line.

The CLI is a transport only. Every command delegates to the same reusable core
modules; nothing in this package decides policy, placement or allocation.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from provisioner.compiler import profiles as compiler_profiles
from provisioner.domain.request import load as load_document
from provisioner.inventory import model as inventory_model
from provisioner.profiles.loader import Catalog

EXIT_OK = 0
EXIT_REFUSED = 2
EXIT_INTERNAL = 3


@dataclass(frozen=True)
class Context:
    """Everything a command needs before it runs: the request and its reviewed inputs."""

    request_path: Path
    document: dict
    inventory: object
    catalog: Catalog

    @property
    def source(self) -> str:
        return str(self.request_path)


def build_context(request_path, inventory_path=None, profiles_root=None) -> Context:
    """Load the request, the reviewed inventory and the profile catalogs."""
    path = Path(request_path)
    inventory = (inventory_model.load(inventory_path) if inventory_path
                 else inventory_model.fixture())
    return Context(request_path=path, document=load_document(path),
                   inventory=inventory,
                   catalog=compiler_profiles.catalogs(profiles_root))


def emit(payload: dict, stream=None, indent: int = 2) -> None:
    """Render one JSON result document, deterministically and without secrets."""
    import sys
    stream = stream if stream is not None else sys.stdout
    json.dump(payload, stream, indent=indent, sort_keys=True)
    stream.write('\n')


def refused(payload: dict) -> tuple[int, dict]:
    return EXIT_REFUSED, payload