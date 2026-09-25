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
from provisioner.allocations import addresses as address_owner
from provisioner.allocations import owner as capacity_owner
from provisioner.compiler import profiles as compiler_profiles
from provisioner.domain.generation import require_generation
from provisioner.domain.request import load as load_document
from provisioner.execution import plan as execution_plan
from provisioner.inventory import model as inventory_model
from provisioner.profiles.loader import Catalog


@dataclass(frozen=True)
class MobilitySession:
    """One fully resolved source/target mobility planning session."""

    source_plan: object
    target_plan: object
    migration_plan: dict
    mobility_document: dict
    mobility_path: Path


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


def mobility_session_for(context: Context, mobility_path, target_inventory_path=None,
                         artifact_registry_path=None) -> MobilitySession:
    """Resolve source/target plans and one immutable mobility decision.

    Planning is deliberately two-pass. The first pass selects exact source/target
    sites through the normal placement engine. The logical workload artifact is then
    resolved against those sites, and the second pass builds the reviewed plans with
    the exact platform-native image/template inputs bound to the portable artifact.
    """
    from provisioner.portability import artifacts, migration

    mobility_target = Path(mobility_path)
    mobility = load_document(mobility_target)
    migration.validate_intent(mobility)

    artifact = dict(mobility['spec']['artifact']['image'])
    target_platform = mobility['spec']['target']['platform']
    source_document = migration.source_request(context.document, mobility)
    target_document = migration.target_request(context.document, mobility)
    target_inventory = (
        inventory_model.load(target_inventory_path)
        if target_inventory_path
        else inventory_model.fixture(f'{target_platform}-reference')
    )

    source_placement = execution_plan.create_plan(
        source_document, context.source, context.inventory, context.catalog,
        compile_environment=False, generation=context.generation)
    target_placement = execution_plan.create_plan(
        target_document, context.source, target_inventory, context.catalog,
        compile_environment=False, generation=context.generation)

    source_artifact = artifacts.resolve(
        artifact, source_placement.desired_state.platform,
        source_placement.desired_state.site_key, artifact_registry_path)
    target_artifact = artifacts.resolve(
        artifact, target_placement.desired_state.platform,
        target_placement.desired_state.site_key, artifact_registry_path)

    source = execution_plan.create_plan(
        source_document, context.source, context.inventory, context.catalog,
        compile_environment=True, generation=context.generation,
        workload_artifact=artifact,
        workload_native_inputs=source_artifact['native_inputs'])
    target = execution_plan.create_plan(
        target_document, context.source, target_inventory, context.catalog,
        compile_environment=True, generation=context.generation,
        workload_artifact=artifact,
        workload_native_inputs=target_artifact['native_inputs'])

    decision = migration.build(
        source, target, mobility,
        artifact_resolutions={'source': source_artifact['reference'],
                              'target': target_artifact['reference']})
    return MobilitySession(source_plan=source, target_plan=target,
                           migration_plan=decision,
                           mobility_document=mobility,
                           mobility_path=mobility_target)


def mobility_plan_for(context: Context, mobility_path, target_inventory_path=None,
                      artifact_registry_path=None):
    """Return the reviewed mobility decision from the shared mobility session."""
    return mobility_session_for(context, mobility_path, target_inventory_path,
                                artifact_registry_path).migration_plan


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


def address_evidence(plan, reservation_index=None, allocation_index=None,
                     registration_index=None, as_of=None, resolved=False) -> dict:
    """What the reviewed addressing proposes and what the exported records say.

    Every transport that reports addressing reads it the same way: the repository's
    own compiled owner chain, reconciled against the repository's own exported
    reservation, allocation and registration evidence. Reconciling is a reading, not
    a mutation — it never reserves, confirms, registers or releases anything, and it
    reports the state the owner's own records already hold.

    The three index arguments are paths to exported owner evidence. `resolved=True`
    additionally runs the owners' own preflights, which resolve the staged sibling
    documents from the checkout; it is the handover check, not the planning path.
    """
    handoff = address_owner.handoff(plan, as_of=as_of, resolved=resolved)
    reconciliation = address_owner.reconcile(
        plan,
        reservation_index=reservation_index,
        allocation_index=allocation_index,
        registration_index=registration_index,
        as_of=as_of)
    return {'view': address_owner.address_view(plan),
            'view_digest': address_owner.view_digest(plan),
            'scope': address_owner.scope_of(plan),
            'handoff': handoff,
            'reconciliation': reconciliation,
            'review': address_owner.review(reconciliation),
            'state': reconciliation['state'],
            'confirmed': reconciliation['confirmed'],
            'registered': reconciliation['registered'],
            'may_allocate': reconciliation['may_allocate'],
            'may_register': reconciliation['may_register'],
            'limits': list(reconciliation['limits'])}