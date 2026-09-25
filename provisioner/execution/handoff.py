"""The reviewed delivery handoff.

`hosting apply` does not execute anything and never will. What it can do is compile
the reviewed plan into the exact graph the repository's persistent delivery runner
already accepts, so an operator holding the recorded authority stages the typed
stage packets and resumes one delivery instead of re-deciding the sequence by hand.

The compiler is a pure function of the reviewed plan plus the clean source commit.
`hosting-delivery/2` carries the approval-bound topology, operation bindings,
reviewed parameter subset and compiled catalog identities. Private runtime paths,
credentials, executable bindings and predecessor receipts still belong to the stage
packet its owner prepares. What this module does add is the
mapping from the plan's owner operations to the typed steps that discharge them,
so a reviewer can see that no responsibility is missing, that every step is a
declared kind of the existing runner, and that no second runner exists.

This module also owns the *reviewed topology intent*: the sequence, the kinds, the
dependencies, the operation bindings and the parameters the reviewed decision
fixes. The plan manifest binds its digest, and `build` refuses any graph whose
projection is not that approved topology, so the approval an operator holds covers
the exact sequence that would be staged.

Nothing here executes, contacts a platform or holds authority.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from provisioner.domain.errors import ProvisioningError
from provisioner.domain.generation import SCOPE_KEYS, claim, record_for
from provisioner.domain.request import digest
from provisioner.placement.eligibility import PLATFORMS

#: The graph format the existing runner validates. It is the declared contract.
HANDOFF_FORMAT = 'hosting-delivery/2'
HANDOFF_KEYS = ('format', 'source_commit', 'operation_id', 'generation', 'scope', 'steps',
                'operation_bindings', 'reviewed_parameters', 'compiled_catalog_ids')
STEP_KEYS = ('id', 'kind', 'needs')
SOURCE_COMMIT = re.compile(r'^[0-9a-f]{40}$')

#: The reviewed topology intent format. This is the approval-relevant half of the
#: handoff: the sequence, the kinds, the dependencies, the operation bindings and the
#: parameters the reviewed decision fixes. It carries no commit, no generation, no
#: scope and no operation identity, because none of those is a reviewed decision.
TOPOLOGY_FORMAT = 'hosting-delivery-topology-intent/1'
TOPOLOGY_KEYS = ('format', 'steps', 'operationBindings', 'reviewedParameters',
                 'compiledCatalogIds')

#: Mirrors `tools.delivery_steps.KINDS`, the declared typed-step contract, and
#: `tools.readback_core.ID`, the declared identifier grammar. The tools are the
#: owners; `tests/provisioning/unit/test_delivery_handoff.py` compares every mirror
#: against them, so a kind or a grammar the runner adds cannot drift unnoticed.
KINDS = frozenset({
    'openstack_quota', 'edge_containment', 'remote_owner', 'restic',
    'platform_transition', 'workload_inputs', 'capacity', 'acceptance',
    'retirement_review', 'operations_review', 'operations_alerts', 'terraform_plan',
    'terraform_apply', 'guest_plan', 'guest_apply', 'vsphere_power', 'target_campaign',
    'edge_policy', 'ipam', 'dns', 'dns_propagation',
})
IDENTIFIER = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$')
ACCEPTANCE_PURPOSES = frozenset({'admission', 'domain', 'bootstrap', 'services',
                                 'activation', 'post_activation', 'recovery', 'retirement'})
CAPACITY_ACTIONS = frozenset({'reserve', 'confirm', 'release'})
IPAM_ACTIONS = frozenset({'reserve', 'confirm', 'reconcile', 'retire', 'quarantine',
                          'release'})
DNS_ACTIONS = frozenset({'register', 'reconcile', 'withdraw', 'reconcile-withdrawal'})
RESTIC_ACTIONS = frozenset({'backup', 'restore'})
EDGE_MODES = frozenset({'withdraw', 'bootstrap', 'active'})
TRANSITION_STAGES = frozenset({'prepared', 'bootstrap'})
GUEST_MODES = frozenset({'check', 'configure'})


@dataclass(frozen=True)
class Step:
    """One typed stage of the reviewed delivery sequence."""

    id: str
    kind: str
    needs: tuple = ()

    def to_dict(self) -> dict:
        return {'id': self.id, 'kind': self.kind, 'needs': list(self.needs)}


#: The reviewed ordinary-WSD delivery sequence, topologically ordered.
#:
#: It follows the required delivery sequence: admit the allocation, reserve capacity
#: and allocate addresses, register the intended names, plan and apply the domain
#: scope, accept the domain natively, attach the isolated edge policy, plan and apply
#: the workloads, run the narrow bootstrap, configure the guest, bind the shared
#: services, campaign before activation, record the production authorization, and
#: campaign again after it.
#:
#: Two orderings are load-bearing rather than cosmetic. The workload phase descends
#: from the capacity reservation, so `tools.capacity_demand.check_ancestors` still
#: proves the workload shape against its reservation instead of silently skipping
#: the check. The narrow bootstrap and the workload build descend from the edge
#: attachment, so no workload is created outside the isolated route.
STEPS = (
    Step('admission', 'acceptance'),
    Step('capacity-reservation', 'capacity', ('admission',)),
    Step('address-allocation', 'ipam', ('capacity-reservation',)),
    Step('dns-registration', 'dns', ('address-allocation',)),
    Step('dns-propagation', 'dns_propagation', ('dns-registration',)),
    Step('domain-plan', 'terraform_plan', ('address-allocation',)),
    Step('domain-apply', 'terraform_apply', ('domain-plan',)),
    Step('domain-acceptance', 'acceptance', ('domain-apply',)),
    Step('edge-policy', 'edge_policy', ('domain-acceptance',)),
    Step('workload-inputs', 'workload_inputs', ('domain-apply', 'edge-policy')),
    Step('workload-plan', 'terraform_plan', ('workload-inputs',)),
    Step('workload-apply', 'terraform_apply', ('workload-plan',)),
    Step('bootstrap', 'platform_transition', ('domain-apply', 'edge-policy')),
    Step('bootstrap-acceptance', 'acceptance', ('bootstrap',)),
    Step('guest-plan', 'guest_plan', ('workload-apply',)),
    Step('guest-apply', 'guest_apply', ('guest-plan',)),
    Step('backup-retention', 'restic', ('guest-apply',)),
    Step('service-acceptance', 'acceptance',
         ('guest-apply', 'dns-propagation', 'backup-retention')),
    Step('pre-activation-campaign', 'target_campaign', ('service-acceptance',)),
    Step('activation', 'acceptance', ('pre-activation-campaign', 'bootstrap-acceptance')),
    Step('post-activation-campaign', 'target_campaign', ('activation',)),
)

#: Owner operation -> the reviewed step that discharges it.
#:
#: Every operation the delivery plan names is discharged by a declared step. The
#: mapping is total by construction: `uncovered()` reports any operation this table
#: does not map, so a new operation cannot appear in a handoff without a step that
#: owns it.
OPERATION_STEPS = {
    'state-backend': 'domain-plan',
    'capacity-reservation': 'capacity-reservation',
    'address-allocation': 'address-allocation',
    'dns-registration': 'dns-registration',
    'security-edge-route': 'edge-policy',
    'shared-service-handoff': 'service-acceptance',
    'backup-retention': 'backup-retention',
    'native-qualification': 'pre-activation-campaign',
    'production-authorization': 'activation',
    'guest-configuration': 'guest-plan',
}

#: Parameters the reviewed decision already fixes, per step.
REVIEWED_PARAMETERS = {
    'admission': {'purpose': 'admission'},
    'capacity-reservation': {'action': 'reserve'},
    'address-allocation': {'action': 'reserve'},
    'dns-registration': {'action': 'register'},
    'dns-propagation': {'dns_step': 'dns-registration'},
    'domain-apply': {'prepared_step': 'domain-plan'},
    'domain-acceptance': {'purpose': 'domain'},
    'edge-policy': {'mode': 'bootstrap'},
    'workload-inputs': {'domain_steps': ['domain-apply']},
    'workload-apply': {'prepared_step': 'workload-plan'},
    'bootstrap': {'prior_step': 'domain-apply', 'stage': 'bootstrap'},
    'bootstrap-acceptance': {'purpose': 'bootstrap'},
    'guest-plan': {'workload_step': 'workload-apply', 'mode': 'configure'},
    'guest-apply': {'prepared_step': 'guest-plan'},
    'backup-retention': {'action': 'backup'},
    'service-acceptance': {'purpose': 'services'},
    'activation': {'purpose': 'activation'},
}

#: Parameters the existing compiler supplies, per step, once the environment
#: compiled. They are named here so the three sets below account for every declared
#: parameter of every reviewed step.
COMPILED_PARAMETERS = {
    'domain-plan': ('catalog_id',),
    'workload-plan': ('catalog_id',),
    'workload-inputs': ('selected_input',),
}

#: Parameters that are host or private facts, never reviewed decisions. They are
#: named so the operator knows exactly what a stage packet must add, and so the
#: reviewed, compiled and operator sets together account for every declared
#: parameter.
OPERATOR_PARAMETERS = {
    'capacity-reservation': ('database',),
    'domain-plan': ('terraform', 'terraform_sha256'),
    'workload-plan': ('terraform', 'terraform_sha256'),
    'edge-policy': ('nft', 'nft_sha256'),
    'guest-plan': ('python', 'python_sha256', 'ssh', 'ssh_sha256', 'max_seconds'),
    'backup-retention': ('restic', 'restic_sha256', 'target'),
    'pre-activation-campaign': ('ssh', 'ssh_sha256'),
    'post-activation-campaign': ('ssh', 'ssh_sha256'),
}


def step_of(step_id: str) -> Step:
    for step in STEPS:
        if step.id == step_id:
            return step
    raise ProvisioningError('SCHEMA_VALIDATION_FAILED',
                            f'Unknown delivery step {step_id!r}', path='$.handoff.steps')


def uncovered(operations) -> list[str]:
    """Operations the reviewed sequence does not discharge, sorted by name."""
    return sorted(name for name in operations if name not in OPERATION_STEPS)


def predecessors(step_id: str) -> tuple:
    """The steps one step depends on.

    The graph binds topology only. The *receipts* of these predecessors are bound by
    the stage packet the runner validates, which carries each predecessor's exact
    digest in `dependencies`; the repository never restates a receipt the owner
    produced.
    """
    return step_of(step_id).needs


def operation_names(plan) -> list[str]:
    """The reviewed owner operations a plan declares, in declaration order."""
    operations = plan.delivery.get('operations', [])
    if isinstance(operations, dict):
        return list(operations)
    return [operation['name'] for operation in operations]


def validate(graph: dict) -> dict:
    """Refuse any graph the declared `hosting-delivery/2` contract would refuse.

    This mirrors the pure shape contract `tools.delivery_run.validate` enforces, so
    the transport can refuse a malformed handoff without importing the runner.
    `tests/provisioning/unit/test_delivery_handoff.py` compares the two on the same
    graphs, so the mirror cannot drift from the owner.
    """
    def refuse(message, **details):
        raise ProvisioningError('SCHEMA_VALIDATION_FAILED', message,
                                path='$.handoff', details=details)

    if not isinstance(graph, dict) or set(graph) != set(HANDOFF_KEYS):
        refuse('A delivery handoff carries exactly the declared keys',
               keys=sorted(graph) if isinstance(graph, dict) else None)
    if graph['format'] != HANDOFF_FORMAT:
        refuse(f'Unknown delivery handoff format {graph["format"]!r}')
    if not isinstance(graph['source_commit'], str) or not SOURCE_COMMIT.match(graph['source_commit']):
        refuse('A delivery handoff binds one exact clean source commit',
               source_commit=graph['source_commit'])
    if not isinstance(graph['operation_id'], str) or not IDENTIFIER.match(graph['operation_id']):
        refuse('A delivery operation identity is a scoped identifier',
               operation_id=graph['operation_id'])
    generation = graph['generation']
    if isinstance(generation, bool) or not isinstance(generation, int) or generation < 1:
        refuse('A delivery generation is a positive integer', generation=generation)
    scope = graph['scope']
    if not isinstance(scope, dict) or set(scope) != set(SCOPE_KEYS):
        refuse('A delivery scope carries exactly the declared keys',
               keys=sorted(scope) if isinstance(scope, dict) else None)
    for name, value in scope.items():
        if not isinstance(value, str) or not IDENTIFIER.match(value):
            refuse(f'Delivery scope component {name} is not a scoped identifier', value=value)
    if scope['platform'] not in PLATFORMS:
        refuse(f'Unknown delivery platform {scope["platform"]!r}', platforms=list(PLATFORMS))
    steps = graph['steps']
    if not isinstance(steps, list) or not 1 <= len(steps) <= 100:
        refuse('A bounded delivery graph is required')
    operation_bindings = graph['operation_bindings']
    reviewed_parameters = graph['reviewed_parameters']
    compiled_catalog_ids = graph['compiled_catalog_ids']
    if not isinstance(operation_bindings, dict) or not isinstance(reviewed_parameters, dict) \
            or not isinstance(compiled_catalog_ids, dict):
        refuse('Delivery approval projections must be mappings')
    seen: set[str] = set()
    for step in steps:
        if not isinstance(step, dict) or set(step) != set(STEP_KEYS):
            refuse('A delivery step carries exactly the declared keys', step=step)
        if not isinstance(step['id'], str) or not IDENTIFIER.match(step['id']):
            refuse('A delivery step identity is a scoped identifier', step=step)
        if step['id'] in seen or step['kind'] not in KINDS:
            refuse('Duplicate or unsupported delivery step', step=step)
        needs = step['needs']
        if not isinstance(needs, list) or len(needs) != len(set(needs)) or not set(needs) <= seen:
            refuse('A delivery graph is topologically ordered without missing dependencies',
                   step=step)
        if seen and not needs:
            refuse('Every subsequent step retains a dependency', step=step)
        seen.add(step['id'])
    if not set(operation_bindings.values()) <= seen:
        refuse('Every operation binding must name a delivery step',
               operation_bindings=operation_bindings)
    if not set(reviewed_parameters) <= seen:
        refuse('Reviewed parameters must name delivery steps',
               reviewed_parameters=sorted(reviewed_parameters))
    for step_id, values in reviewed_parameters.items():
        if not isinstance(values, dict):
            refuse('Reviewed step parameters must be mappings', step_id=step_id)
        declared = _declared_parameters(step_of(step_id).kind)
        if not set(values) <= declared:
            refuse('Reviewed parameters must be declared by the step kind',
                   step_id=step_id, parameters=sorted(values), declared=sorted(declared))
    if any(not isinstance(k, str) or not isinstance(v, str)
           for k, v in compiled_catalog_ids.items()):
        refuse('Compiled catalog identities must be text mappings')
    return graph


def catalog_ids(plan) -> dict:
    """The reviewed Terraform catalog entry per compiled phase, when compiled."""
    result: dict[str, str] = {}
    for scope in plan.terraform_scopes:
        phase = scope.get('scope', {}).get('phase')
        if phase:
            result[phase] = scope.get('catalog_id', '')
    return result


def reviewed_parameters(plan) -> dict:
    """The stage parameters the reviewed decision fixes, per step.

    A value that the reviewed plan does not fix is absent rather than invented: the
    catalog identity of a Terraform step exists only once the environment compiled,
    and an unqualified value would stage a packet the runner must refuse.
    """
    catalogs = catalog_ids(plan)
    values = {step_id: dict(parameters) for step_id, parameters in REVIEWED_PARAMETERS.items()}
    inputs = {scope.get('scope', {}).get('phase'): scope.get('input', '')
              for scope in plan.terraform_scopes}
    if catalogs.get('domains'):
        values['domain-plan'] = {'catalog_id': catalogs['domains']}
    if catalogs.get('workloads'):
        values['workload-plan'] = {'catalog_id': catalogs['workloads']}
    if inputs.get('workloads'):
        values['workload-inputs'] = {**values['workload-inputs'],
                                     'selected_input': inputs['workloads']}
    for step in STEPS:
        declared = _declared_parameters(step.kind)
        if step.id in values and not set(values[step.id]) <= declared:
            raise ProvisioningError(
                'COMPILATION_FAILED',
                f'Reviewed parameters for step {step.id!r} are not declared for kind '
                f'{step.kind!r}',
                path='$.handoff.parameters',
                details={'step': step.id, 'kind': step.kind,
                         'declared': sorted(declared), 'given': sorted(values[step.id])})
    return values


def topology_intent(plan) -> dict:
    """The reviewed delivery topology, as one canonical declaration.

    The manifest binds the digest of this document, so an external approval that
    cites the plan cites the exact sequence, kinds, dependencies, operation bindings
    and reviewed parameters that will be staged. A change to any of them changes the
    approved identity, which is what makes the approval provable rather than
    descriptive.

    Everything here is a reviewed decision. The clean source commit, the generation,
    the scope and the derived operation identity are execution-time bindings and are
    deliberately absent: they are not decisions a reviewer approved.
    """
    return {
        'format': TOPOLOGY_FORMAT,
        'steps': [step.to_dict() for step in STEPS],
        'operationBindings': dict(sorted(OPERATION_STEPS.items())),
        'reviewedParameters': {step_id: dict(parameters) for step_id, parameters
                               in sorted(reviewed_parameters(plan).items())},
        'compiledCatalogIds': dict(sorted(catalog_ids(plan).items())),
    }


def topology_digest(plan) -> str:
    """The approved identity of the reviewed delivery topology."""
    return digest(topology_intent(plan))


def approval_projection(plan, graph: dict) -> dict:
    """The reviewed topology as the compiled `hosting-delivery/2` graph states it.

    `build` compares the digest of this projection with the digest the manifest
    binds. The projection is deliberately built by *reading the graph*, not by
    restating the declaration: a comparison that read `STEPS` on both sides would
    prove nothing about what would actually execute.
    """
    projection = topology_intent(plan)
    projection['steps'] = [{key: (list(step[key]) if key == 'needs' else step[key])
                            for key in STEP_KEYS} for step in graph['steps']]
    projection['operationBindings'] = dict(graph['operation_bindings'])
    projection['reviewedParameters'] = {
        step_id: dict(values)
        for step_id, values in sorted(graph['reviewed_parameters'].items())
    }
    projection['compiledCatalogIds'] = dict(sorted(graph['compiled_catalog_ids'].items()))
    return projection


def _declared_parameters(kind: str) -> frozenset:
    """Mirror of the declared parameter set of one kind.

    Held here rather than imported so the transport never reaches into the runner's
    module graph; `test_delivery_handoff` compares every entry with
    `tools.delivery_steps.KINDS`.
    """
    return _DECLARED_PARAMETERS[kind]


_DECLARED_PARAMETERS = {
    'openstack_quota': frozenset(),
    'edge_containment': frozenset({'nft', 'nft_sha256'}),
    'remote_owner': frozenset({'ssh', 'ssh_sha256'}),
    'restic': frozenset({'action', 'restic', 'restic_sha256', 'target'}),
    'platform_transition': frozenset({'prior_step', 'stage'}),
    'workload_inputs': frozenset({'domain_steps', 'selected_input'}),
    'capacity': frozenset({'action', 'database'}),
    'acceptance': frozenset({'purpose'}),
    'retirement_review': frozenset(),
    'operations_review': frozenset(),
    'operations_alerts': frozenset(),
    'terraform_plan': frozenset({'catalog_id', 'terraform', 'terraform_sha256'}),
    'terraform_apply': frozenset({'prepared_step'}),
    'guest_plan': frozenset({'workload_step', 'python', 'python_sha256', 'ssh',
                             'ssh_sha256', 'mode', 'max_seconds'}),
    'guest_apply': frozenset({'prepared_step'}),
    'vsphere_power': frozenset(),
    'target_campaign': frozenset({'ssh', 'ssh_sha256'}),
    'edge_policy': frozenset({'nft', 'nft_sha256', 'mode'}),
    'ipam': frozenset({'action'}),
    'dns': frozenset({'action'}),
    'dns_propagation': frozenset({'dns_step'}),
}


def build(plan, source_commit: str, ledger=None) -> dict:
    """Compile the reviewed plan into the declared delivery graph.

    Deterministic and derived: the same reviewed plan and the same clean commit
    always produce the same graph, so a resumed delivery recognises its own plan
    instead of creating a second one.

    `ledger` is the authoritative generation record, when the caller holds one. A
    stale generation, or a generation whose unfinished operation is still open, is
    refused *before* a graph exists, so no handoff can be compiled for a superseded
    claim. The repository itself holds no authoritative ledger and therefore passes
    none; the interface is the one the generation model already declares.

    The compiled topology must be the topology the reviewed plan binds. The approval
    an operator holds cites the plan digest, so a step, a dependency, an operation
    binding or a reviewed parameter that differs from the approved one would stage a
    delivery the approval does not cover. That mismatch is refused here, before the
    graph leaves this module, rather than discovered by the runner mid-delivery.
    """
    if ledger is not None:
        claim(ledger, record_for(plan))
    graph = {'format': HANDOFF_FORMAT, 'source_commit': source_commit,
             'operation_id': plan.operation_id, 'generation': plan.generation,
             'scope': plan.identity.scope,
             'steps': [step.to_dict() for step in STEPS],
             'operation_bindings': dict(sorted(OPERATION_STEPS.items())),
             'reviewed_parameters': reviewed_parameters(plan),
             'compiled_catalog_ids': dict(sorted(catalog_ids(plan).items()))}
    missing = uncovered(operation_names(plan))
    if missing:
        raise ProvisioningError(
            'COMPILATION_FAILED',
            'Every reviewed owner operation needs a typed delivery step',
            path='$.handoff.steps', details={'uncovered': sorted(missing)})
    approved = plan.manifest.get('delivery', {}).get('topology_digest', '')
    compiled = digest(approval_projection(plan, graph))
    if compiled != approved:
        raise ProvisioningError(
            'APPROVAL_TOPOLOGY_MISMATCH',
            'The compiled delivery topology is not the topology the reviewed plan binds',
            path='$.handoff.steps',
            details={'approved_topology_digest': approved,
                     'compiled_topology_digest': compiled})
    return validate(graph)


def review(graph: dict) -> dict:
    """The reviewer-facing summary of a compiled handoff."""
    return {'format': HANDOFF_FORMAT, 'steps': len(graph['steps']),
            'kinds': sorted({step['kind'] for step in graph['steps']}),
            'operations': dict(graph['operation_bindings']),
            'reviewed_parameters': {
                step_id: dict(values)
                for step_id, values in sorted(graph['reviewed_parameters'].items())
            },
            'compiled_catalog_ids': dict(sorted(graph['compiled_catalog_ids'].items())),
            'source_commit': graph['source_commit'], 'operation_id': graph['operation_id'],
            'generation': graph['generation'], 'scope': dict(graph['scope']),
            'limits': ['Reviewed parameter values are part of the delivery-plan digest '
                       'and are enforced against owner stage packets',
                       'Private file bindings, credentials, executable paths and predecessor '
                       'receipts remain stage-packet inputs',
                       'The existing delivery runner is the only engine',
                       'This repository compiles the handoff and executes nothing']}