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

# These top-level responsibilities remain stable; dataset-specific bindings are
# appended from the reviewed data plan rather than sharing a restore receipt.
OPERATION_BINDINGS = {
    'migration-admission': 'migration-admission',
    'target-capacity': 'target-capacity-reservation',
    'target-addressing': 'target-address-allocation',
    'target-dns': 'target-dns-registration',
    'target-domain': 'target-domain-apply',
    'target-security-policy': 'target-edge-policy',
    'target-workloads': 'target-workload-apply',
    'target-guest-configuration': 'target-guest-apply',
    'dataset-transfer': 'target-service-acceptance',
    'target-services': 'target-service-acceptance',
    'cutover-qualification': 'pre-cutover-campaign',
    'cutover-authorization': 'cutover-authorization',
    'post-cutover-qualification': 'post-cutover-campaign',
}


def _target_step(name):
    return {'admission': 'migration-admission',
            'pre-activation-campaign': 'pre-cutover-campaign',
            'activation': 'cutover-authorization',
            'post-activation-campaign': 'post-cutover-campaign'}.get(name, 'target-' + name)


def _dataset_sequence(data_plan):
    steps, parameters, bindings, groups = [], {}, {}, {}
    for row in data_plan['datasets']:
        name = row['name']
        step_id = 'dataset-restore-' + name
        selected = (row['transfer_binding'] or {}) if row['delivery_kind'] == 'dataset_restore' else {}
        group_id = selected.get('consistency_group_id')
        # Missing mappings remain explicitly unbound. The plan is held and the
        # runner refuses null bindings; no grant, digest or group is invented.
        key = ('group', group_id) if group_id is not None else ('unbound', name)
        item = {'step_id': step_id, 'dataset_id': selected.get('dataset_id'),
                'target_ref': selected.get('target_ref'),
                'transfer_manifest_sha256': selected.get('transfer_manifest_sha256')}
        groups.setdefault(key, []).append(item)
        steps.append(Step(step_id, 'dataset_restore', ('target-guest-apply',)))
        parameters[step_id] = {'action': 'restore', 'source_scope': dict(row['source_scope']),
                              'dataset_id': item['dataset_id'],
                              'target_ref': item['target_ref'],
                              'consistency_group_id': group_id,
                              'transfer_manifest_sha256': item['transfer_manifest_sha256']}
        bindings['dataset-transfer-' + name] = step_id
    joins = []
    for key, datasets in sorted(groups.items()):
        join = 'dataset-group-' + digest(list(key))[:16]
        steps.append(Step(join, 'dataset_acceptance', tuple(row['step_id'] for row in datasets)))
        parameters[join] = {'group_id': key[1] if key[0] == 'group' else None,
                            'datasets': datasets}
        bindings[join] = join
        joins.append(join)
    return steps, parameters, bindings, joins


def sequence(target_plan, data_plan):
    """Reuse the ordinary native bootstrap graph and join every dataset group."""
    dataset_steps, dataset_parameters, dataset_bindings, joins = _dataset_sequence(data_plan)
    steps = []
    for step in delivery_handoff.sequence(target_plan):
        if step.id == 'backup-retention':
            steps.extend(dataset_steps)
            continue
        dependencies = []
        for predecessor in step.needs:
            dependencies.extend(joins if predecessor == 'backup-retention'
                                else [_target_step(predecessor)])
        steps.append(Step(_target_step(step.id), step.kind, tuple(dependencies)))
    parameters = {}
    references = {'prepared_step', 'prior_step', 'workload_step', 'dns_step'}
    for step_id, values in delivery_handoff.reviewed_parameters(target_plan).items():
        if step_id == 'backup-retention':
            continue
        values = dict(values)
        for key in references & values.keys():
            values[key] = _target_step(values[key])
        if 'domain_steps' in values:
            values['domain_steps'] = [_target_step(value) for value in values['domain_steps']]
        parameters[_target_step(step_id)] = values
    parameters.update(dataset_parameters)
    bindings = dict(OPERATION_BINDINGS)
    bindings.update(dataset_bindings)
    return steps, parameters, bindings


def catalog_ids(target_plan) -> dict:
    return {
        scope['scope']['phase']: scope.get('catalog_id', '')
        for scope in target_plan.terraform_scopes
        if scope.get('scope', {}).get('phase')
    }


def topology_intent(target_plan, *, policy_plan: dict, data_plan: dict,
                    cutover_plan: dict, artifact_realizations: dict) -> dict:
    """The approval-critical target delivery topology for one migration."""
    steps, parameters, bindings = sequence(target_plan, data_plan)

    body = {
        'format': FORMAT,
        'scope': dict(target_plan.identity.scope),
        'generation': target_plan.generation,
        'steps': [step.to_dict() for step in steps],
        'operation_bindings': dict(sorted(bindings.items())),
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
            'Every dataset has a distinct manifest-bound restore and all consistency groups join before service acceptance',
            'File-byte verification is separate from application consistency, native qualification and cutover authority',
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
    migration_body = {key: value for key, value in migration_plan.items() if key != 'digest'}
    if digest(migration_body) != migration_plan.get('digest'):
        from provisioner.domain.errors import ProvisioningError
        raise ProvisioningError('ARTIFACT_INTEGRITY_FAILED',
                                'Mobility plan digest does not reproduce',
                                path='$.digest')
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
