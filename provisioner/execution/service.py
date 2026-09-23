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

from provisioner import repository
from provisioner.allocations import owner as capacity_owner
from provisioner.compiler import profiles as compiler_profiles
from provisioner.domain.generation import require_generation
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
    generation: int = 1

    @property
    def source(self) -> str:
        return str(self.request_path)


def build_context(request_path, inventory_path=None, profiles_root=None,
                  generation: int = 1) -> Context:
    """Load the request, the reviewed inventory and the profile catalogs.

    `generation` is the change counter the caller claims for this WSD identity. The
    transport carries the claim; it never decides whether the claim is current, and
    nothing here reads a local counter as authority.
    """
    path = Path(request_path)
    inventory = (inventory_model.load(inventory_path) if inventory_path
                 else inventory_model.fixture())
    return Context(request_path=path, document=load_document(path),
                   inventory=inventory,
                   catalog=compiler_profiles.catalogs(profiles_root),
                   generation=require_generation(generation))


def plan_for(context: Context, compile_environment: bool = True):
    """Create the plan from an already built context."""
    return execution_plan.create_plan(context.document, context.source, context.inventory,
                                      context.catalog, compile_environment=compile_environment,
                                      generation=context.generation)


def capacity_evidence(plan, reservation_index=None, as_of=None, facts_path=None) -> dict:
    """What the reviewed capacity arithmetic claims and what the exported records say.

    Every transport that reports capacity reads it the same way: the repository's own
    compiled binding, reconciled against the repository's own exported reservation
    evidence. Reconciling is a reading, not a mutation — it never creates, confirms or
    releases anything, and it reports the state the owner's own records already hold.

    `facts_path` is the recorded owner facts document. Without it the envelope is
    unbound, the handoff cannot be compiled and the reconciliation says so instead of
    assuming a confirmation.
    """
    facts = capacity_owner.load_facts(facts_path) if facts_path else None
    envelope = ({'envelope_id': facts['envelope_id'],
                 'envelope_record_sha256': facts['envelope_record_sha256']}
                if facts else {})
    identity = capacity_owner.binding(plan, **envelope)
    index = (repository.reservation_records(reservation_index)
             if reservation_index else None)
    reconciliation = capacity_owner.reconcile(identity, index, as_of=as_of)
    return {'binding': identity,
            'view': capacity_owner.capacity_view(plan),
            'units': capacity_owner.units(plan),
            'scope': capacity_owner.scope_of(plan),
            'facts': dict(facts) if facts else None,
            'handoff': (capacity_owner.handoff_from_facts(plan, facts)
                        if facts else None),
            'reconciliation': reconciliation,
            'review': capacity_owner.review(reconciliation),
            'state': reconciliation['state'],
            'confirmed': reconciliation['confirmed'],
            'may_allocate': reconciliation['may_allocate'],
            'required_facts': list(capacity_owner.REQUIRED_FACTS),
            'limits': list(capacity_owner.LIMITS)}