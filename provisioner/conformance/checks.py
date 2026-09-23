"""Conformance checks.

A check is only PASS when the evidence for it exists in this run. Evidence that
must come from outside the repository is PENDING, and a missing check is never
silently treated as satisfied.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from provisioner.adapters import base as adapter_module
from provisioner.allocations import addresses as address_module
from provisioner.allocations import owner as capacity_module
from provisioner.observation import native as native_module

CHECK_FORMAT = 'hosting-conformance-check/1'

PASS = 'PASS'
FAIL = 'FAIL'
PENDING = 'PENDING_EXTERNAL_EVIDENCE'
NOT_APPLICABLE = 'NOT_APPLICABLE'
STATUSES = (PASS, FAIL, PENDING, NOT_APPLICABLE)

REPOSITORY_CHECKS = ('schema', 'semantics', 'policy', 'profiles', 'placement',
                     'capacity', 'addresses', 'services', 'compiler',
                     'environment-contract', 'determinism', 'generation',
                     'adapter-contract', 'adapter-readback', 'security-edge')

EXTERNAL_CHECKS = ('native-qualification', 'capacity-confirmation',
                   'address-confirmation', 'dns-registration', 'service-acceptance',
                   'native-observation', 'recovery-readiness', 'production-authorization')

MANDATORY = ('schema', 'semantics', 'policy', 'placement', 'capacity', 'addresses',
             'services', 'compiler', 'environment-contract', 'determinism', 'generation',
             'adapter-contract', 'adapter-readback', 'security-edge',
             'native-qualification', 'capacity-confirmation', 'address-confirmation',
             'dns-registration', 'service-acceptance', 'native-observation',
             'production-authorization')


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


def _refused(name: str, detail: str, evidence: dict | None = None) -> Check:
    """An external answer that is a definite no, reported as the owner's answer."""
    return Check(name=name, status=FAIL, authority='EXTERNAL', mandatory=name in MANDATORY,
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
               'The reviewed capacity arithmetic holds; the reservation is an intent, '
               'not a held reservation',
               {'zones': sorted(plan.desired_state.reservations),
                'view_digest': capacity_module.view_digest(plan) if plan.inventory
                else '',
                'state': capacity_module.PROPOSED,
                'authority': 'CAPACITY_OWNER'}),
        _address_check(plan),
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
        _adapter_contract_check(plan),
        _adapter_readback_check(plan),
        _security_edge_check(plan),
    )


def _adapter_contract_check(plan) -> Check:
    """Whether the selected platform's adapter covers the reviewed plan.

    The adapter owns the provider-specific half of the portable-to-native boundary.
    This reports whether the reviewed plan is one that platform's declared realization
    contract covers — the reviewed composition roots exist, both zones the request
    requires are represented, reviewed inventory supplied every declared placement
    input and no workload declares a native input the reviewed module does not accept.
    """
    adapter = adapter_module.get(plan.desired_state.platform)
    problems = adapter.validate(plan)
    contract = adapter.realization_contract()
    return _check('adapter-contract', not problems,
                  'The selected adapter covers the reviewed plan'
                  if not problems else
                  f'The selected adapter refuses the reviewed plan: {list(problems)}',
                  {'adapter': contract['format'], 'platform': adapter.platform,
                   'family': adapter.family, 'surfaces': sorted(contract),
                   'problems': list(problems), 'native_contact': False})


def _adapter_readback_check(plan) -> Check:
    """Whether the adapter's declared readback and binding agree with the reviewed modules.

    A readback identity is only real if the reviewed domain module actually produces it,
    either as its own output or through the cross-phase binding the platform declares. A
    binding is only usable if the reviewed workload module accepts the native field it
    populates, and the field the binding observes must be one the reviewed domain module
    outputs. The compiler's declared native field sets must also equal the reviewed
    modules' declared variables, so a declaration cannot drift away from the artifact
    that would actually be applied.
    """
    adapter = adapter_module.get(plan.desired_state.platform)
    contract = adapter.readback_contract()
    binding = adapter.binding
    domains = adapter_module.module_contract(adapter.domains_module)
    workloads = adapter_module.module_contract(adapter.workloads_module)
    accounted = set(contract['produced_by_module']) | set(contract['produced_by_binding'])
    problems = {
        'readback_not_produced': sorted(set(adapter.network_fields) - accounted),
        'observed_field_not_output': sorted(value for key, value in binding.items()
                                            if key in ('observed_field', 'binding_field')
                                            and value not in domains['outputs']),
        'binding_target_not_accepted': sorted(value for key, value in binding.items()
                                              if key == 'native_field'
                                              and value not in workloads['variables']),
        'declared_inputs_not_declared_by_module': sorted(
            (adapter.declared_inputs('domains') - domains['variables'])
            | (adapter.declared_inputs('workloads') - workloads['variables'])),
    }
    ok = not any(problems.values())
    return _check('adapter-readback', ok,
                  'Every declared readback identity is produced by a reviewed module and '
                  'every declared binding is accepted by one' if ok else
                  f'The adapter declares identities the reviewed modules do not realize: '
                  f'{problems}',
                  {'platform': adapter.platform, 'readback': sorted(adapter.network_fields),
                   'modules': [domains['module'], workloads['module']],
                   'binding': binding, 'problems': problems,
                   'authority': 'reviewed Terraform module configuration'})


def _security_edge_check(plan) -> Check:
    """Whether the reviewed catalog realizes the adapter's declared security edge.

    The isolation outcome of a domain is carried by a security-edge component the
    reviewed Terraform catalog owns, and handed over by a security-edge owner
    operation in the delivery graph. The check proves the reviewed catalog declares
    that component and that the plan hands it over; it does not claim the edge was
    realized, which requires native qualification.
    """
    from provisioner.execution import terraform
    adapter = adapter_module.get(plan.desired_state.platform)
    declared = adapter.edge_components
    entries = {entry['id']: entry for entry in terraform.catalog()['entries']
               if entry['platform'] == adapter.platform
               and entry['owner_scope'] == adapter_module.EDGE_SCOPE}
    problems = []
    if not declared:
        problems.append('no reviewed security-edge component is declared')
    if adapter.security_edge not in declared:
        problems.append(f'the declared edge realization {adapter.security_edge!r} is not a '
                        f'reviewed {adapter_module.EDGE_SCOPE} component')
    if sorted(entries) != sorted(declared):
        problems.append('the adapter and the reviewed catalog disagree about the '
                        'security-edge components')
    operations = [op['name'] for op in plan.delivery.get('operations', [])
                  if op.get('owner') == 'security-edge-owner']
    if not operations:
        problems.append('the delivery graph hands over no security-edge operation')
    return _check('security-edge', not problems,
                  'The reviewed catalog declares the security-edge realization and the '
                  'plan hands it over' if not problems else
                  f'The security-edge realization is not declared: {problems}',
                  {'platform': adapter.platform, 'component': adapter.security_edge,
                   'components': sorted(declared), 'owner_scope': adapter_module.EDGE_SCOPE,
                   'operations': sorted(operations), 'problems': problems,
                   'authority': 'terraform/catalog.json',
                   'realized': False})


def _address_check(plan) -> Check:
    """The repository's own reading of the reviewed addressing proposal.

    Compiling the proposal validates it against the owners' declared vocabulary, so a
    proposal that could not be handed to an owner fails here. This says the proposal is
    internally consistent and carries no ownership authority ? it cannot say the owner
    granted it, which is what `address-confirmation` below answers.
    """
    view = address_module.address_view(plan)
    return _check('addresses', bool(view['domains']),
                  'The proposed prefixes and addresses are internally consistent; they '
                  'are planning intent, not authoritative ownership',
                  {'domains': [domain['zone'] for domain in view['domains']],
                   'view_digest': view['digest'],
                   'authority': view['authority']})


def _address_owner_evidence(plan, addresses) -> dict:
    """The owner-facing evidence both addressing checks report."""
    reconciliation = addresses['reconciliation']
    return {'state': reconciliation['state'],
            'owner': 'ipam-owner',
            'operation_id': plan.operation_id,
            'generation': plan.generation,
            'reservation_id': reconciliation['reservation_id'],
            'view_digest': reconciliation['view_digest'],
            'authority': address_module.PROPOSAL_AUTHORITY,
            'parent_state': reconciliation['parent']['state'],
            'records_checked': reconciliation['records_checked'],
            'confirmed': reconciliation['confirmed'],
            'registered': reconciliation['registered'],
            'zones': [[item['zone'], item['state'], item['registration_state']]
                      for item in reconciliation['allocations']]}


def _address_check_confirmation(plan, addresses) -> Check:
    """The IPAM owner's own answer about the allocation, reported as the owner's.

    Without reconciled owner evidence the check is PENDING and says what the owner
    still has to supply. With it, the check reports the owner's state: a confirmed
    allocation in every zone is the only state that satisfies it.
    """
    if addresses is None:
        return _pending('address-confirmation',
                        'The IPAM owner must reserve and confirm every prefix',
                        {'state': address_module.HOLD_PARENT,
                         'owner': 'ipam-owner',
                         'operation_id': plan.operation_id,
                         'generation': plan.generation,
                         'view_digest': address_module.view_digest(plan),
                         'authority': address_module.PROPOSAL_AUTHORITY})
    evidence = _address_owner_evidence(plan, addresses)
    if evidence['confirmed']:
        return Check(name='address-confirmation', status=PASS, authority='EXTERNAL',
                     mandatory=True,
                     detail='The IPAM owner confirmed every allocation in this operation',
                     evidence=evidence)
    refusals = _allocation_refusals(addresses['reconciliation'])
    if address_module.REFUSAL_CONFLICT in refusals:
        return _refused('address-confirmation',
                        'The IPAM owner refused an allocation that carries a different identity',
                        dict(evidence, refusals=refusals))
    if refusals:
        return _pending('address-confirmation',
                        'The IPAM owner has not settled every allocation outcome',
                        dict(evidence, refusals=refusals))
    return _pending('address-confirmation',
                    'The IPAM owner must reserve and confirm every prefix', evidence)


def _allocation_refusals(reconciliation) -> list[str]:
    """Every refusal the stopping allocation and registration states raise."""
    refusals = {address_module.REFUSING_STATES[item['state']]
                for item in reconciliation['allocations']
                if item['state'] in address_module.REFUSING_STATES}
    refusals |= {address_module.REGISTRATION_REFUSING_STATES[item['registration_state']]
                 for item in reconciliation['allocations']
                 if item['registration_state'] in address_module.REGISTRATION_REFUSING_STATES}
    return sorted(refusals)


def _dns_check(plan, addresses) -> Check:
    """The DNS owner's own answer about the registration, reported as the owner's.

    A registration is only usable once the allocation it depends on is confirmed, so
    the owner's preflight refuses to evaluate the intent before that. An unconfirmed
    allocation is therefore PENDING here, never PASS.
    """
    if addresses is None:
        return _pending('dns-registration',
                        'The DNS owner must register every name against a confirmed allocation',
                        {'state': address_module.REGISTRATION_HOLD_IPAM,
                         'owner': 'dns-owner',
                         'operation_id': plan.operation_id,
                         'generation': plan.generation,
                         'view_digest': address_module.view_digest(plan),
                         'required_observations': list(address_module.REQUIRED_OBSERVATIONS)})
    evidence = dict(_address_owner_evidence(plan, addresses), owner='dns-owner')
    if evidence['registered']:
        return Check(name='dns-registration', status=PASS, authority='EXTERNAL',
                     mandatory=True,
                     detail='The DNS owner registered every name against the confirmed allocation',
                     evidence=evidence)
    refusals = _allocation_refusals(addresses['reconciliation'])
    if address_module.REGISTRATION_REFUSAL_CONFLICT in refusals:
        return _refused('dns-registration',
                        'The DNS owner refused a registration that carries a different identity',
                        dict(evidence, refusals=refusals))
    if refusals:
        return _pending('dns-registration',
                        'The DNS owner has not settled every registration outcome',
                        dict(evidence, refusals=refusals))
    return _pending('dns-registration',
                    'The DNS owner must register every name against a confirmed allocation',
                    evidence)


def _capacity_check(plan, capacity) -> Check:
    """The capacity owner's own answer, reported as the owner's and never as ours.

    Without reconciled owner evidence the check is PENDING and says what the owner
    still has to supply. With it, the check reports the owner's state: a confirmed
    reservation is the only state that can satisfy it.
    """
    if capacity is None:
        return _pending('capacity-confirmation',
                        'The capacity owner must confirm the reservation',
                        {'state': capacity_module.PROPOSED,
                         'operation_id': plan.operation_id,
                         'generation': plan.generation,
                         'required_facts': list(capacity_module.REQUIRED_FACTS)})
    reconciliation = capacity['reconciliation']
    evidence = {'state': reconciliation['state'],
                'owner': 'capacity-owner',
                'operation_id': plan.operation_id,
                'generation': plan.generation,
                'reservation_id': capacity['binding']['reservation_id'],
                'view_digest': capacity['view']['digest'],
                'records_checked': reconciliation['records_checked'],
                'confirmed': reconciliation['confirmed']}
    if reconciliation['confirmed']:
        return Check(name='capacity-confirmation', status=PASS, authority='EXTERNAL',
                     mandatory=True,
                     detail='The capacity owner confirmed this reservation identity',
                     evidence=evidence)
    refusal = capacity_module.REFUSING_STATES.get(reconciliation['state'])
    if refusal == capacity_module.REFUSAL_CONFLICT:
        return _refused('capacity-confirmation',
                        'The capacity owner refused this reservation identity',
                        dict(evidence, refusal=refusal))
    if refusal:
        return _pending('capacity-confirmation',
                        'The capacity owner has not settled this reservation outcome',
                        dict(evidence, refusal=refusal))
    return _pending('capacity-confirmation',
                    'The capacity owner must confirm the reservation',
                    evidence)


def external_checks(plan, observations=(), authorization=None, capacity=None,
                    addresses=None) -> tuple[Check, ...]:
    """Checks that can only pass once evidence produced elsewhere exists.

    `capacity` and `addresses` are the reconciled owner evidence the transport read,
    if any. Passing them changes only what this repository reports about the owners'
    state; it never makes a confirmation or a registration exist.
    """
    observed = len(observations)
    bound = native_module.binding(observations, plan.generation)
    return (
        _pending('native-qualification',
                 'The capability registry records no qualified product tuple',
                 {'qualification': dict(plan.decision.qualification),
                  'qualification_blockers': list(plan.decision.qualification_blockers)}),
        _capacity_check(plan, capacity),
        _address_check_confirmation(plan, addresses),
        _dns_check(plan, addresses),
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


def run(plan, observations=(), authorization=None, capacity=None,
        addresses=None) -> tuple[Check, ...]:
    return repository_checks(plan, observations) + external_checks(plan, observations,
                                                                   authorization,
                                                                   capacity, addresses)