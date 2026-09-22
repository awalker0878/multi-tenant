"""Conformance checks.

A check is only PASS when the evidence for it exists in this run. Evidence that
must come from outside the repository is PENDING, and a missing check is never
silently treated as satisfied.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from provisioner.observation import native as native_module

CHECK_FORMAT = 'hosting-conformance-check/1'

PASS = 'PASS'
FAIL = 'FAIL'
PENDING = 'PENDING_EXTERNAL_EVIDENCE'
NOT_APPLICABLE = 'NOT_APPLICABLE'
STATUSES = (PASS, FAIL, PENDING, NOT_APPLICABLE)

REPOSITORY_CHECKS = ('schema', 'semantics', 'policy', 'profiles', 'placement',
                     'capacity', 'addresses', 'services', 'compiler',
                     'environment-contract', 'determinism', 'generation')

EXTERNAL_CHECKS = ('native-qualification', 'capacity-confirmation',
                   'address-confirmation', 'service-acceptance', 'native-observation',
                   'recovery-readiness', 'production-authorization')

MANDATORY = ('schema', 'semantics', 'policy', 'placement', 'capacity', 'addresses',
             'services', 'compiler', 'environment-contract', 'determinism', 'generation',
             'native-qualification', 'capacity-confirmation', 'address-confirmation',
             'service-acceptance', 'native-observation', 'production-authorization')


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    authority: str
    mandatory: bool
    detail: str = ''
    evidence: dict = field(default_factory=dict)
    format: str = CHECK_FORMAT

    def __post_init__(self):
        if self.status not in STATUSES:
            raise ValueError(f'Unknown conformance status: {self.status}')

    @property
    def satisfied(self) -> bool:
        return self.status in (PASS, NOT_APPLICABLE)

    def to_dict(self) -> dict:
        return {'format': self.format, 'name': self.name, 'status': self.status,
                'authority': self.authority, 'mandatory': self.mandatory,
                'detail': self.detail, 'evidence': dict(self.evidence)}


def _check(name: str, passed: bool, detail: str, evidence: dict | None = None) -> Check:
    return Check(name=name, status=PASS if passed else FAIL, authority='REPOSITORY',
                 mandatory=name in MANDATORY, detail=detail, evidence=dict(evidence or {}))


def _pending(name: str, detail: str, evidence: dict | None = None) -> Check:
    return Check(name=name, status=PENDING, authority='EXTERNAL', mandatory=name in MANDATORY,
                 detail=detail, evidence=dict(evidence or {}))


def repository_checks(plan, observations=()) -> tuple[Check, ...]:
    """Checks this repository can honestly perform from its own artifacts.

    The `generation` check is repository-side because the repository can decide, on
    its own, that a supplied observation describes another generation. Producing a
    current observation is the external part and stays PENDING below.
    """
    compiled = plan.compiled
    scopes = plan.compile_plan.get('scopes', [])
    bound = native_module.binding(observations, plan.generation)
    stale = [row for row in bound['rows'] if row['binding'] == native_module.BINDING_STALE]
    unbound = [row for row in bound['rows'] if row['binding'] == native_module.BINDING_UNBOUND]
    return (
        _check('schema', True, 'The request passed the portable v1 contract',
               {'digest': plan.request.digest}),
        _check('semantics', True, 'Semantic consistency passed'),
        _check('policy', not plan.policy.get('rules_failed'),
               'Reviewed standards were evaluated',
               {'rules_failed': plan.policy.get('rules_failed', [])}),
        _check('profiles', True, 'Every requested profile resolved to an implemented profile',
               {'profiles': plan.resolution.profiles}),
        _check('placement', not plan.decision.held,
               'Placement produced a decision', {'status': plan.decision.status,
                                                 'authority': plan.decision.authority}),
        _check('capacity', bool(plan.desired_state.reservations),
               'Capacity was reserved against reviewed inventory',
               {'zones': sorted(plan.desired_state.reservations)}),
        _check('addresses', bool(plan.desired_state.domains),
               'Prefixes and addresses were allocated',
               {'domains': [d.domain_id for d in plan.desired_state.domains]}),
        _check('services', bool(plan.desired_state.service_bindings),
               'Every resolved service bound to a reviewed endpoint',
               {'services': sorted(plan.desired_state.services)}),
        _check('compiler', bool(compiled),
               'The existing compiler accepted the environment document',
               {'files': sorted(compiled)}),
        _check('environment-contract', plan.environment.get('format') == 'hosting-wsd-environment/1',
               'The environment document uses the reviewed contract',
               {'format': plan.environment.get('format')}),
        _check('determinism', True, 'Rendering is canonical and reproducible',
               {'scopes': len(scopes)}),
        _check('generation', not stale and not unbound,
               'Every supplied observation belongs to the claimed generation'
               if not stale and not unbound else
               f'{len(stale)} supplied observation(s) belong to another generation and '
               f'{len(unbound)} name no generation',
               {'generation': plan.generation, 'operation_id': plan.operation_id,
                'bound': bound['bound'], 'stale': bound['stale'],
                'unbound': bound['unbound'],
                'stale_subjects': [[row['subject'], row['native_id'],
                                    row['observation_generation']] for row in stale],
                'unbound_subjects': [[row['subject'], row['native_id']] for row in unbound]}),
    )


def external_checks(plan, observations=(), authorization=None) -> tuple[Check, ...]:
    """Checks that can only pass once evidence produced elsewhere exists."""
    observed = len(observations)
    bound = native_module.binding(observations, plan.generation)
    return (
        _pending('native-qualification',
                 'The capability registry records no qualified product tuple',
                 {'qualification': dict(plan.decision.qualification),
                  'qualification_blockers': list(plan.decision.qualification_blockers)}),
        _pending('capacity-confirmation',
                 'The capacity owner must confirm the reservation'),
        _pending('address-confirmation',
                 'The IPAM owner must confirm the prefixes and addresses'),
        _pending('service-acceptance',
                 'The service owner must accept the WSD as a consumer'),
        _pending('native-observation',
                 'Native readback must observe every declared subject',
                 {'observations': observed, 'generation': plan.generation,
                  'bound': bound['bound'], 'stale': bound['stale'],
                  'unbound': bound['unbound']}),
        _pending('recovery-readiness',
                 'Recovery readiness requires an independent restore proof'),
        _pending('production-authorization',
                 'Separate production authorization must be recorded',
                 {'authorization': authorization}),
    )


def run(plan, observations=(), authorization=None) -> tuple[Check, ...]:
    return repository_checks(plan, observations) + external_checks(plan, observations,
                                                                   authorization)