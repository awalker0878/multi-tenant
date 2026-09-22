"""The shared operations every hosting transport calls.

The command line is a transport: `validate`, `resolve`, `plan`, `apply`, `status`,
`verify` and `evidence` all reach the same operations here, so no command decides
policy, placement, allocation or authority for itself and no command has to import a
peer. Keeping the session load and the plan entry point below the transport is what
makes the direction checkable rather than merely stated —
`tests/provisioning/unit/test_architecture.py` fails if a command imports another
command or if any module outside `provisioner/cli` imports the transport.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from provisioner.compiler import profiles as compiler_profiles
from provisioner.domain.request import load as load_document
from provisioner.execution import plan as execution_plan
from provisioner.inventory import model as inventory_model
from provisioner.profiles.loader import Catalog


@dataclass(frozen=True)
class Context:
    """Everything an operation needs before it runs: the request and its reviewed inputs."""

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


def plan_for(context: Context, compile_environment: bool = True):
    """Create the plan from an already built context."""
    return execution_plan.create_plan(context.document, context.source, context.inventory,
                                      context.catalog, compile_environment=compile_environment)