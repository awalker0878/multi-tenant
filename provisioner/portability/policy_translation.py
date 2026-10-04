"""Compile portable policy outcomes into a target-platform realization plan."""
from __future__ import annotations

from provisioner.adapters import base as adapters
from provisioner.domain.request import digest
from provisioner.domain.capability_properties import contract_digest, entails, merge_requirements, parse_requirements

FORMAT = 'hosting-portable-policy-realization/2'

CONTROL_OUTCOMES = {
    'network_domain': 'isolated workload security domain',
    'ipv4': 'portable IPv4 workload reachability inside the approved domain',
    'ipv6': 'portable IPv6 workload reachability inside the approved domain',
    'distributed_firewall': 'workload-level east-west policy enforcement',
    'gateway_policy': 'deny-first north-south security-edge policy',
    'dynamic_routing': 'approved routed reachability with controlled advertisements',
    'service_insertion': 'approved service-chain insertion',
    'native_load_balancer': 'load-balancing outcome for the declared service',
    'dedicated_edge_context': 'dedicated security-edge context',
    'audit_logging': 'security and platform audit event production',
}


def compile(capsule: dict, target_plan) -> dict:
    """Translate portable requirements into target-native responsibilities.

    The result carries outcomes and the target adapter surfaces, not native rule IDs.
    Qualification decides whether the target may claim the outcome.
    """
    if capsule.get('format') != 'hosting-portable-policy-capsule/2':
        raise ValueError('Capability properties require a current policy capsule')
    if (capsule['requirements']['capability_property_schema_digest'] != contract_digest()
            or target_plan.resolution.capability_property_schema_digest != contract_digest()):
        raise ValueError('Capability property interpretation changed; reassessment required')
    adapter = adapters.get(target_plan.desired_state.platform)
    required = tuple(capsule['requirements']['capabilities'])
    capability = adapter.capability_contract(required=required)
    source_constraints = parse_requirements(
        capsule['requirements']['capability_constraints'], list(required))
    try:
        constraints = merge_requirements(source_constraints, target_plan.resolution.capability_constraints)
        property_conflict = []
    except ValueError:
        constraints = source_constraints
        property_conflict = ['CAPABILITY_PROPERTY_CONFLICT']
    # Even compatible requirements need target-plan enforcement. A weaker
    # target profile must not silently erase source obligations at migration.
    target_constraints = target_plan.resolution.capability_constraints
    property_conflict.extend('SOURCE_PROPERTY_NOT_ENFORCED:' + r.property
                             for r in source_constraints if not entails(target_constraints, r))
    controls = []
    blockers = list(capability['blockers']) + property_conflict
    for name in required:
        controls.append({
            'capability': name,
            'outcome': CONTROL_OUTCOMES.get(name, f'portable capability {name}'),
            'mandatory': True,
            'qualified': capability['qualified'] and name not in capability['blockers'],
        })

    target_services = {
        row['service']: {
            'binding_class': row['binding_class'],
            'site': row['site'],
            'endpoints': dict(row['endpoints']),
        }
        for row in target_plan.desired_state.service_bindings
    }
    source_profiles = capsule['requirements']['services']
    missing_services = sorted(set(source_profiles) - set(target_services))
    blockers.extend(f'SERVICE_BINDING_MISSING:{name}' for name in missing_services)

    body = {
        'format': FORMAT,
        'policy_digest': capsule['digest'],
        'target': {
            'platform': target_plan.desired_state.platform,
            'site': target_plan.desired_state.site_key,
            'security_edge': adapter.security_edge_contract(),
        },
        'controls': controls,
        'capability_constraints': [r.to_dict() for r in constraints],
        'services': {
            name: {
                'required_profile': source_profiles[name],
                'target_binding': target_services.get(name),
            }
            for name in sorted(source_profiles)
        },
        'exposure': dict(capsule['requirements']['exposure']),
        'blockers': sorted(set(blockers)),
        'qualified': not blockers,
        'limits': [
            'Portable policy expresses required outcomes, never native firewall or route IDs',
            'Target service endpoints are re-resolved at the target and are not copied from source',
            'A mandatory control may change enforcement location but may not be dropped',
        ],
        'native_contact': False,
    }
    return {**body, 'digest': digest(body)}
