"""Portable security and policy capsule.

A migration must carry the security outcome with the workload, not a provider's
native firewall object. This module projects the reviewed WSD decision into the
provider-neutral requirements that a target realization must satisfy.
"""
from __future__ import annotations

from provisioner.domain.request import digest

POLICY_CAPSULE_FORMAT = 'hosting-portable-policy-capsule/2'


def _profile(plan, family: str):
    return {'name': plan.resolution.profiles.get(family),
            'version': plan.resolution.profile_versions.get(family)}


def build(plan) -> dict:
    """Return the immutable provider-neutral policy requirements of one WSD plan."""
    spec = plan.request.spec
    exposure = dict(spec.get('exposure', {}))
    services = dict(plan.resolution.services)
    body = {
        'format': POLICY_CAPSULE_FORMAT,
        'subject': {'tenant': plan.request.tenant, 'wsd': plan.request.wsd,
                    'environment': plan.desired_state.lifecycle},
        'profiles': {
            'security': _profile(plan, 'security'),
            'assurance': _profile(plan, 'assurance'),
            'availability': _profile(plan, 'availability'),
            'recovery': _profile(plan, 'recovery'),
            'network': _profile(plan, 'network'),
        },
        'requirements': {
            'trust': plan.resolution.trust,
            'service_class': plan.resolution.service_class,
            'zones': list(plan.resolution.zones),
            'capabilities': list(plan.resolution.required_capabilities),
            'capability_property_schema_digest': plan.resolution.capability_property_schema_digest,
            'capability_constraints': [r.to_dict() for r in plan.resolution.capability_constraints],
            'network': {
                'profile': plan.resolution.network['profile'],
                'address_family': plan.resolution.network['address_family'],
                'prefix_length': plan.resolution.network['prefix_length'],
            },
            'exposure': {
                'publicIngress': bool(exposure.get('publicIngress', False)),
                'internetEgress': bool(exposure.get('internetEgress', False)),
            },
            'services': services,
        },
        'policy': {
            'format': plan.policy.get('format', ''),
            'rules_digest': plan.policy.get('rules_digest', ''),
            'rules_evaluated': plan.policy.get('rules_evaluated', 0),
            'rules_failed': list(plan.policy.get('rules_failed', [])),
        },
        'catalog': {
            'digest': plan.resolution.catalog_digest,
            'versions': dict(plan.resolution.catalog_versions),
        },
        'limits': [
            'This capsule carries portable requirements, never provider-native policy identifiers',
            'Target enforcement may differ physically but must satisfy every mandatory outcome',
            'A missing mandatory target capability is a migration hold, never a silent downgrade',
        ],
        'native_contact': False,
    }
    return {**body, 'digest': digest(body)}
