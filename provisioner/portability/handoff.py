"""Reviewed target-side delivery topology for cross-platform mobility.

Mobility reuses the existing delivery runner and its typed step kinds. This module
only declares the migration-specific ordered topology and approval-relevant
parameters; it owns no executor, journal or native mutation.
"""
from __future__ import annotations

from provisioner.domain.request import digest
from provisioner.execution import handoff as delivery_handoff
from provisioner.execution.handoff import Step

FORMAT = 'hosting-mobility-delivery-topology/1'

STEPS = (
    Step('migration-admission', 'acceptance'),
    Step('target-capacity-reservation', 'capacity', ('migration-admission',)),
    Step('target-address-allocation', 'ipam', ('target-capacity-reservation',)),
    Step('target-dns-registration', 'dns', ('target-address-allocation',)),
    Step('target-dns-propagation', 'dns_propagation', ('target-dns-registration',)),
    Step('target-domain-plan', 'terraform_plan', ('target-address-allocation',)),
    Step('target-domain-apply', 'terraform_apply', ('target-domain-plan',)),
    Step('target-domain-acceptance', 'acceptance', ('target-domain-apply',)),
    Step('target-edge-policy', 'edge_policy', ('target-domain-acceptance',)),
    Step('target-workload-inputs', 'workload_inputs',
         ('target-domain-apply', 'target-edge-policy')),
    Step('target-workload-plan', 'terraform_plan', ('target-workload-inputs',)),
    Step('target-workload-apply', 'terraform_apply', ('target-workload-plan',)),
    Step('target-bootstrap', 'platform_transition',
         ('target-domain-apply', 'target-edge-policy')),
    Step('target-bootstrap-acceptance', 'acceptance', ('target-bootstrap',)),
    Step('target-guest-plan', 'guest_plan', ('target-workload-apply',)),
    Step('target-guest-apply', 'guest_apply', ('target-guest-plan',)),
    Step('dataset-restore', 'restic', ('target-guest-apply',)),
    Step('target-service-acceptance', 'acceptance',
         ('target-guest-apply', 'target-dns-propagation', 'dataset-restore')),
    Step('pre-cutover-campaign', 'target_campaign', ('target-service-acceptance',)),
    Step('cutover-authorization', 'acceptance',
         ('pre-cutover-campaign', 'target-bootstrap-acceptance')),
    Step('post-cutover-campaign', 'target_campaign', ('cutover-authorization',)),
)

OPERATION_BINDINGS = {
    'migration-admission': 'migration-admission',
    'target-capacity': 'target-capacity-reservation',
    'target-addressing': 'target-address-allocation',
    'target-dns': 'target-dns-registration',
    'target-domain': 'target-domain-apply',
    'target-security-policy': 'target-edge-policy',
    'target-workloads': 'target-workload-apply',
    'target-guest-configuration': 'target-guest-apply',
    'dataset-transfer': 'dataset-restore',
    'target-services': 'target-service-acceptance',
    'cutover-qualification': 'pre-cutover-campaign',
    'cutover-authorization': 'cutover-authorization',
    'post-cutover-qualification': 'post-cutover-campaign',
}

REVIEWED_PARAMETERS = {
    'migration-admission': {'purpose': 'admission'},
    'target-capacity-reservation': {'action': 'reserve'},
    'target-address-allocation': {'action': 'reserve'},
    'target-dns-registration': {'action': 'register'},
    'target-dns-propagation': {'dns_step': 'target-dns-registration'},
    'target-domain-apply': {'prepared_step': 'target-domain-plan'},
    'target-domain-acceptance': {'purpose': 'domain'},
    'target-edge-policy': {'mode': 'bootstrap'},
    'target-workload-inputs': {'domain_steps': ['target-domain-apply']},
    'target-workload-apply': {'prepared_step': 'target-workload-plan'},
    'target-bootstrap': {'prior_step': 'target-domain-apply', 'stage': 'bootstrap'},
    'target-bootstrap-acceptance': {'purpose': 'bootstrap'},
    'target-guest-plan': {'workload_step': 'target-workload-apply', 'mode': 'configure'},
    'target-guest-apply': {'prepared_step': 'target-guest-plan'},
    'dataset-restore': {'action': 'restore'},
    'target-service-acceptance': {'purpose': 'services'},
    'cutover-authorization': {'purpose': 'activation'},
}


def catalog_ids(target_plan) -> dict:
    return {
        scope['scope']['phase']: scope.get('catalog_id', '')
        for scope in target_plan.terraform_scopes
        if scope.get('scope', {}).get('phase')
    }


def topology_intent(target_plan, *, policy_plan: dict, data_plan: dict,
                    cutover_plan: dict, artifact_realizations: dict) -> dict:
    """The approval-critical target delivery topology for one migration."""
    catalogs = catalog_ids(target_plan)
    parameters = {key: dict(value) for key, value in REVIEWED_PARAMETERS.items()}
    if catalogs.get('domains'):
        parameters['target-domain-plan'] = {'catalog_id': catalogs['domains']}
    if catalogs.get('workloads'):
        parameters['target-workload-plan'] = {'catalog_id': catalogs['workloads']}

    body = {
        'format': FORMAT,
        'scope': dict(target_plan.identity.scope),
        'generation': target_plan.generation,
        'steps': [step.to_dict() for step in STEPS],
        'operation_bindings': dict(sorted(OPERATION_BINDINGS.items())),
        'reviewed_parameters': parameters,
        'policy_digest': policy_plan['digest'],
        'data_transfer_digest': data_plan['digest'],
        'cutover_digest': cutover_plan['digest'],
        'artifact_realizations': {
            side: dict(reference)
            for side, reference in sorted(artifact_realizations.items())
        },
        'source_retirement': 'separate-source-scope-after-target-acceptance',
        'limits': [
            'This topology is executed only by the existing hosting-delivery/2 runner',
            'Private binaries, credentials, runtime paths and predecessor receipts remain owner packet inputs',
            'Source retirement is deliberately not mixed into the target platform scope',
        ],
    }
    return {**body, 'digest': digest(body)}


def build(target_plan, migration_plan: dict, source_commit: str) -> dict:
    """Compile one reviewed mobility decision into the existing delivery-v2 graph.

    The full mobility digest is the graph's reviewed-plan binding. The graph carries
    only the target execution scope; source fencing/retirement remain separately
    authorized source-side responsibilities recorded by the mobility decision.
    """
    topology = migration_plan.get('delivery', {})
    if not isinstance(topology, dict) or 'digest' not in topology:
        from provisioner.domain.errors import ProvisioningError
        raise ProvisioningError('COMPILATION_FAILED',
                                'Mobility plan carries no reviewed delivery topology',
                                path='$.delivery')
    body = {key: value for key, value in topology.items() if key != 'digest'}
    if digest(body) != topology['digest']:
        from provisioner.domain.errors import ProvisioningError
        raise ProvisioningError('ARTIFACT_INTEGRITY_FAILED',
                                'Mobility delivery topology digest does not reproduce',
                                path='$.delivery.digest')
    if topology.get('scope') != target_plan.identity.scope:
        from provisioner.domain.errors import ProvisioningError
        raise ProvisioningError('PORTABILITY_POLICY_MISMATCH',
                                'Mobility delivery scope differs from the target WSD scope',
                                path='$.delivery.scope')

    operation_id = (
        f'mobility-{target_plan.identity.wsd_key}-g{target_plan.generation}-'
        f'{migration_plan["digest"][:12]}'
    )
    graph = {
        'format': delivery_handoff.HANDOFF_FORMAT,
        'source_commit': source_commit,
        'operation_id': operation_id,
        'generation': target_plan.generation,
        'scope': dict(target_plan.identity.scope),
        'reviewed_plan_digest': migration_plan['digest'],
        'steps': [dict(step) for step in topology['steps']],
        'operation_bindings': dict(topology['operation_bindings']),
        'reviewed_parameters': {
            step_id: dict(values)
            for step_id, values in topology['reviewed_parameters'].items()
        },
        'compiled_catalog_ids': dict(sorted(catalog_ids(target_plan).items())),
    }
    return delivery_handoff.validate(graph)
