"""Plan creation.

A plan is the complete, reproducible record of one provisioning decision: the
normalized request, the resolved profiles, the policy outcome, the placement
decision, the allocations, the resolved desired state and the environment document
the existing compiler accepted. Creating a plan never contacts a platform and
never authorizes anything.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

from provisioner.compiler import desired_state as compiler_desired_state
from provisioner.compiler import environment as compiler_environment
from provisioner.compiler import normalize as compiler_normalize
from provisioner.compiler import profiles as compiler_profiles
from provisioner.domain.errors import Diagnostics, ProvisioningError
from provisioner.domain.placement import PlacementDecision
from provisioner.domain.request import Request, digest as request_digest
from provisioner.inventory.capacity import demand_for
from provisioner.inventory.model import Inventory
from provisioner.placement import resolver as placement_resolver
from provisioner.policy import diagnostics as policy_diagnostics
from provisioner.policy import semantic, standards
from provisioner.profiles.loader import Catalog
from provisioner.conformance import report as conformance_report
from provisioner.execution import ansible, delivery as delivery_plan, terraform

PLAN_FORMAT = 'hosting-provisioning-plan/1'
PLAN_STATUS = 'PLANNED_DISABLED_NOT_AUTHORIZED'


@dataclass(frozen=True)
class Plan:
    request: Request
    resolution: object
    policy: dict
    decision: PlacementDecision
    desired_state: object
    environment: dict
    compiled: dict = field(default_factory=dict)
    compile_plan: dict = field(default_factory=dict)
    terraform_scopes: tuple[dict, ...] = ()
    ansible_scopes: tuple[dict, ...] = ()
    phases: tuple[dict, ...] = ()
    delivery: dict = field(default_factory=dict)
    conformance: dict = field(default_factory=dict)
    diagnostics: Diagnostics = field(default_factory=Diagnostics)
    status: str = PLAN_STATUS
    native_contact: bool = False
    format: str = PLAN_FORMAT

    @property
    def warnings(self) -> list[dict]:
        return [w.to_dict() for w in self.diagnostics.warnings]

    @property
    def digest(self) -> str:
        """Stable identity of this exact plan.

        A plan is not identified by its request alone: it is identified by the
        request, the rendered environment the existing compiler accepted, and the
        exact reviewed profile revisions and catalog revisions it resolved against.
        Bumping a profile or catalog version therefore changes the plan identity even
        when no request field changed, which is what makes a reviewed policy change
        visible in every artifact derived from this plan.
        """
        return request_digest({
            'request': self.request.digest,
            'environment': self.environment,
            'profiles': self.resolution.profile_versions,
            'catalogs': self.resolution.catalog_versions,
            'catalog_digest': self.resolution.catalog_digest,
        })

    def to_dict(self) -> dict:
        return {'format': self.format, 'status': self.status, 'digest': self.digest,
                'request': {'source': self.request.source, 'digest': self.request.digest,
                            'tenant': self.request.tenant, 'wsd': self.request.wsd},
                'resolution': self.resolution.to_dict(),
                'policy': dict(self.policy),
                'placement': self.decision.to_dict(),
                'desired_state': self.desired_state.to_dict(),
                'environment': self.environment,
                'compiled_files': sorted(self.compiled),
                'compile_plan': self.compile_plan,
                'terraform_scopes': [dict(s) for s in self.terraform_scopes],
                'ansible_scopes': [dict(s) for s in self.ansible_scopes],
                'phases': [dict(p) for p in self.phases],
                'delivery': self.delivery,
                'conformance': self.conformance,
                'warnings': self.warnings,
                'native_contact': self.native_contact,
                'limits': ['A plan is disabled, unqualified and unauthorized',
                       'No native platform was contacted while creating this plan',
                               'Execution requires separate recorded authorization']}


def validate_request(document: dict, source: str, catalog: Catalog) -> tuple[Request, object, dict]:
    """Run the request-local stages: normalize, resolve, profile and policy validation."""
    request = compiler_normalize.normalize(document, source=source, catalog=catalog)
    resolution = compiler_profiles.resolve(request, catalog)
    diagnostics = compiler_profiles.validate(resolution, catalog)
    diagnostics.extend(semantic.validate(request.document, resolution, catalog).errors)

    rules = standards.load_rules()
    violations = policy_diagnostics.collect(request.document, rules, diagnostics)
    policy = policy_diagnostics.summary(diagnostics, violations, len(rules))
    diagnostics.raise_if_failed()
    return request, resolution, policy


def place(request: Request, resolution, decision_input: Inventory,
          qualification=None) -> PlacementDecision:
    """Place the normalized request over reviewed inventory.

    `qualification` is only for controlled tests: the reviewed registry is used for
    an authoritative inventory and the repository's declared demonstration
    assumption for a non-authoritative fixture.
    """
    demand = demand_for(resolution.compute['workloads_per_zone'], resolution.compute,
                        resolution.storage)
    placement_request = placement_resolver.PlacementRequest(
        tenant=request.tenant, wsd=request.wsd, region=request.spec['placement']['region'],
        platform_preference=request.spec['platform']['preference'],
        zones=compiler_normalize.zones(request), trust=resolution.trust,
        service_class=resolution.service_class,
        required_capabilities=resolution.required_capabilities, demand=demand,
        services=resolution.services, request_digest=request.digest,
        prefix_length=resolution.network['prefix_length'],
        site_pin=request.spec['placement'].get('site'),
        cell_pin=request.spec['placement'].get('cell'))
    return placement_resolver.place(placement_request, decision_input, qualification)


def phases(compile_environment: bool = True) -> tuple[dict, ...]:
    """Which compiler phases this repository can complete without native evidence."""
    return (
        {'phase': 'domains',
         'status': 'COMPILED_DISABLED_NOT_AUTHORIZED' if compile_environment else 'NOT_COMPILED',
         'requires': 'reviewed inventory only'},
        {'phase': 'workloads',
         'status': 'HELD_PENDING_NATIVE_DOMAIN_OUTPUTS',
         'requires': 'observed native domain members produced by the domains phase'},
    )



def create_plan(document: dict, source: str, inventory: Inventory, catalog: Catalog,
                compile_environment: bool = True, qualification=None) -> Plan:
    """Run the whole pipeline and return the complete plan."""
    request, resolution, policy = validate_request(document, source, catalog)
    decision = place(request, resolution, inventory, qualification)
    if decision.held:
        raise ProvisioningError('NO_ELIGIBLE_PLACEMENT',
                                f'Placement held with status {decision.status}',
                                path='$.spec.placement',
                                details={'status': decision.status,
                                         'reasons': list(decision.reasons),
                                         'qualification': dict(decision.qualification),
                                         'qualification_blockers': list(decision.qualification_blockers)})
    diagnostics = Diagnostics()
    state = compiler_desired_state.build(request, resolution, decision, inventory,
                                         catalog=catalog, diagnostics=diagnostics)
    environment_document = compiler_environment.render(state)
    compiled, compile_plan = (compiler_environment.compile_document(environment_document)
                              if compile_environment else ({}, {}))
    terraform_scopes = tuple(terraform.assert_scopes(compile_plan.get('scopes', []),
                                                     state.platform))
    ansible_scopes = (ansible.scope('native-linux', 'workloads'),)
    plan = Plan(request=request, resolution=resolution, policy=policy, decision=decision,
                desired_state=state, environment=environment_document, compiled=compiled,
                compile_plan=compile_plan, terraform_scopes=terraform_scopes,
                ansible_scopes=ansible_scopes, phases=phases(compile_environment),
                diagnostics=diagnostics)
    plan = replace(plan, delivery=delivery_plan.build(state, list(terraform_scopes)))
    return replace(plan, conformance=conformance_report.build(plan))