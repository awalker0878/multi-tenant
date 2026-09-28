"""The platform adapter boundary.

An adapter owns the provider-specific half of the portable-to-native mapping and
nothing else. Its reviewed contracts include:

* `capability_contract`  — the qualification a platform must hold before selection
* `placement_contract`   — the native identity reviewed inventory must supply
* `phase_contract`       — what each reviewed native phase accepts and produces
* `readback_contract`    — the native identity the readback must observe
* `realization_contract` — the portable-to-native declaration, as one reviewable document
* `workload_lifecycle`   — the typed strategy and existing owner used for bootstrap
* `validate`             — the refusal of a reviewed plan this platform cannot realize

An adapter never provisions, never contacts a platform and never decides placement.
Execution and platform contact stay with the owner tools that already own them, and
`tools/compile_wsd.py` stays the authority for what a reviewed module accepts.

Nothing here restates the compiler. Every declaration is read from the module that
already owns it — `tools.compile_wsd` for the native field sets, the declared native
variables and the declared cross-phase binding rules; `scripts.build_wsd_compositions`
for the module identities; `terraform/catalog.json` for the reviewed security-edge
realization; the capability registry for qualification — so an adapter and the
compiler cannot drift apart, and a generic stage asks the adapter instead of
branching on a platform name.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from provisioner.domain.errors import ProvisioningError
from provisioner.placement import eligibility
from provisioner import repository
from provisioner.repository import ROOT

ADAPTER_FORMAT = 'hosting-platform-adapter/2'
CONTRACT_FORMAT = 'hosting-adapter-realization-contract/1'
GAP_FORMAT = 'hosting-adapter-realization-gap/1'

NOT_QUALIFIED = 'NATIVE_QUALIFICATION_ABSENT'
QUALIFIED = 'QUALIFIED'

#: Realization-gap rules. Each rule is evaluated generically against what the reviewed
#: module for the selected platform declares, so a provider-specific gap is declared as
#: data rather than branched on inside generic provisioning code.
GAP_COMPUTED_INPUT_NOT_ACCEPTED = 'COMPUTED_INPUT_NOT_ACCEPTED'
GAP_NATIVE_INPUT_UNSUPPLIED = 'NATIVE_INPUT_UNSUPPLIED'
GAP_READBACK_NOT_OBSERVED = 'READBACK_NOT_OBSERVED'
GAP_CODES = (GAP_COMPUTED_INPUT_NOT_ACCEPTED, GAP_NATIVE_INPUT_UNSUPPLIED,
             GAP_READBACK_NOT_OBSERVED)

#: The reviewed native phases every platform realization is described in.
PHASES = ('domains', 'workloads')
EDGE_SCOPE = 'security-edge'
ZONES = ('OZ', 'RZ')

#: The portable facts the provisioner computes itself, and the native field that can
#: carry each one. A platform whose reviewed module declares no field for a computed
#: fact records a gap instead of dropping the fact.
COMPUTED_FACTS = (('boot_disk_gib', 'boot_disk_gib'), ('data_disk_gib', 'data_disk_gib'),
                  ('ipv4_address', 'ipv4_address'))

_DEFAULT_REALIZATION = 'the platform realizes those facts through its domain composition instead'


def _catalog():
    from provisioner.execution import terraform
    return terraform.catalog()


def module_contract(component: str) -> dict:
    """The reviewed Terraform module configuration for one catalog component.

    The reviewed module — not this repository's prose — is the authority for what a
    native phase accepts and what it can produce, so an adapter reads it rather than
    restating it. Both the declared variables and the declared outputs are returned,
    because a readback identity must be produced by the reviewed module.
    """
    from provisioner.domain.request import loads
    from provisioner.execution import terraform
    entry = next((item for item in terraform.catalog()['entries']
                  if item['id'] == component), None)
    if entry is None:
        raise ValueError(f'No reviewed Terraform component declares {component!r}')
    path = ROOT / entry['module'] / 'main.tf.json'
    try:
        document = loads(path.read_text(encoding='utf-8'), str(path))
    except OSError as exc:
        raise ValueError(f'Unreadable reviewed module {entry["module"]!r}: {exc}') from exc
    return {'id': component, 'module': entry['module'],
            'variables': frozenset(document.get('variable', {})),
            'outputs': frozenset(document.get('output', {}))}


def edge_components(platform: str) -> tuple[str, ...]:
    """Every reviewed security-edge component one platform realization needs.

    The reviewed Terraform catalog already declares which components own the security
    edge, so the adapter asks it rather than keeping a second list that could drift.
    """
    return tuple(entry['id'] for entry in _catalog()['entries']
                 if entry['platform'] == platform and entry['owner_scope'] == EDGE_SCOPE)


def binding_requirement(platform: str) -> tuple[tuple[str, str], ...]:
    """The declared cross-phase binding one platform requires, if it declares one.

    A platform whose workload network identity is *observed* rather than produced by
    its own domain phase declares that requirement in the compiler's
    `WORKLOAD_NETWORK_BINDING` table. The adapter re-exports the same declaration, so
    the requirement a plan binds and the requirement the compiler enforces are one
    declaration rather than two opinions.
    """
    rule = repository.compiler_declarations()['workload_network_binding'].get(platform)
    return () if rule is None else tuple(sorted(rule.items()))



class WorkloadLifecycleMode(Enum):
    """How the native workload owner exposes reviewed bootstrap effects."""
    SAVED_PLAN = 'saved-plan'
    PER_MEMBER_OWNER = 'per-member-owner'


@dataclass(frozen=True)
class WorkloadLifecycle:
    """Typed execution strategy declared by the concrete native adapter.

    A saved-plan owner transitions all members through the reviewed Terraform
    lifecycle profile. A per-member owner requires a separately fenced operation
    for each applied VM. The adapter names the existing delivery executor kind;
    selecting a strategy does not authorize or qualify that executor.
    """
    mode: WorkloadLifecycleMode
    owner_kind: str

    def __post_init__(self):
        if not isinstance(self.mode, WorkloadLifecycleMode):
            raise ValueError('A typed workload lifecycle mode is required')
        if not isinstance(self.owner_kind, str) or not self.owner_kind:
            raise ValueError('An existing native workload owner kind is required')


@dataclass(frozen=True)
class Adapter:
    """One platform realization boundary."""

    platform: str
    family: str
    domains_module: str
    workloads_module: str
    placement_fields: frozenset
    network_fields: frozenset
    security_edge: str
    workload_lifecycle: WorkloadLifecycle
    edge_components: tuple[str, ...] = ()
    binding_requirement: tuple[tuple[str, str], ...] = ()
    realization_note: str = ''
    limits: tuple[str, ...] = ()
    # This version labels the realization term bound into the reviewed plan manifest.
    format: str = ADAPTER_FORMAT

    # -- identity ------------------------------------------------------------

    @property
    def product_tuple(self) -> str:
        return eligibility.product_tuple(self.platform)

    @property
    def qualified(self) -> bool:
        return self.product_tuple != 'UNSELECTED'

    @property
    def binding(self) -> dict:
        """The declared cross-phase binding, exactly as the compiler declares it."""
        return dict(self.binding_requirement)

    def module(self, phase: str) -> str:
        if phase not in PHASES:
            raise ValueError(f'Unknown native phase: {phase}')
        return self.domains_module if phase == 'domains' else self.workloads_module

    def declared_inputs(self, phase: str) -> frozenset:
        """The native variables the reviewed module for one phase declares.

        The adapter keeps no second copy of a provider field list: it asks the
        compiler, so the two can never disagree.
        """
        return repository.native_variables(self.platform, phase)

    def computed_facts(self, phase: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """The computed facts one phase can carry, and the ones it cannot.

        Only the workloads phase is ever asked to carry a provisioner-computed fact;
        the domains phase is supplied entirely from reviewed inventory.
        """
        if phase != 'workloads':
            return (), ()
        declared = self.declared_inputs(phase)
        accepted = tuple(fact for fact, native in COMPUTED_FACTS if native in declared)
        refused = tuple(fact for fact, native in COMPUTED_FACTS if native not in declared)
        return accepted, refused

    # -- reviewed contract surfaces -------------------------------------------

    def capability_contract(self, required=(), assurance_profile=None) -> dict:
        """The qualification contract a platform must hold before it may be selected.

        The requirement set comes from the reviewed request; the answer comes from the
        repository capability registry, which is the only authoritative source.
        """
        requirements = set(required)
        ok, blockers = eligibility.RepositoryQualification().gate(
            self.platform, requirements, assurance_profile)
        qualified = bool(self.qualified and ok)
        return {'format': CONTRACT_FORMAT, 'surface': 'capability',
                'platform': self.platform, 'family': self.family,
                'product_tuple': self.product_tuple,
                'qualified': qualified,
                'status': QUALIFIED if qualified else NOT_QUALIFIED,
                'required': sorted(requirements), 'blockers': list(blockers),
                'authority': 'REPOSITORY_CAPABILITY_REGISTRY',
                'source': eligibility.REPOSITORY_SOURCE,
                'native_contact': False}

    def placement_contract(self) -> dict:
        """The native placement identity reviewed inventory must supply."""
        return {'format': CONTRACT_FORMAT, 'surface': 'placement',
                'platform': self.platform, 'phase': 'placement',
                'fields': sorted(self.placement_fields),
                'supplied_by': 'reviewed inventory cluster native identity',
                'provisioner_owned': False,
                'authority': 'tools.compile_wsd.PLACEMENT',
                'native_contact': False}

    def phase_contract(self, phase: str) -> dict:
        """What one reviewed native phase accepts, and what it must produce."""
        accepted, refused = self.computed_facts(phase)
        return {'format': CONTRACT_FORMAT, 'surface': 'phase',
                'platform': self.platform, 'phase': phase,
                'module': self.module(phase),
                'declared_inputs': sorted(self.declared_inputs(phase)),
                'computed_inputs': list(accepted),
                'unavailable_inputs': list(refused),
                'readback_identity': sorted(self.network_fields) if phase == 'domains' else [],
                'binding_requirement': self.binding if phase == 'workloads' else {},
                'authority': 'tools.compile_wsd.native_variables',
                'native_contact': False}

    def readback_contract(self) -> dict:
        """The native identity the platform readback must observe after the domains phase.

        Each identity is either produced by the reviewed domain module itself or supplied
        by the declared cross-phase binding, and the contract names which, so a reviewer
        can see that the readback is one the reviewed modules can actually produce.
        """
        domains = module_contract(self.domains_module)
        binding = self.binding
        return {'format': CONTRACT_FORMAT, 'surface': 'readback',
                'platform': self.platform, 'phase': 'domains',
                'identity': sorted(self.network_fields),
                'observed_by': 'native readback after the domains phase',
                'produced_by_module': sorted(self.network_fields & domains['outputs']),
                'produced_by_binding': sorted(value for key, value in binding.items()
                                              if key == 'native_field'),
                'observed_field': binding.get('observed_field', ''),
                'binding': binding,
                'authority': 'tools.compile_wsd.NETWORK',
                'native_contact': False}

    def security_edge_contract(self) -> dict:
        """The reviewed security-edge realization that carries the isolation outcome."""
        return {'format': CONTRACT_FORMAT, 'surface': 'security-edge',
                'platform': self.platform,
                'component': self.security_edge,
                'components': list(self.edge_components),
                'owner_scope': EDGE_SCOPE,
                'realizes': 'the isolated upstream route and the quarantine boundary',
                'authority': 'terraform/catalog.json',
                'native_contact': False}

    def realization_gaps(self) -> tuple[dict, ...]:
        """Computed portable facts this platform's reviewed module cannot carry.

        A gap is declared, not dropped: an address is allocated for every workload, so
        a platform whose reviewed module declares no field for it must say so out loud
        and name how the fact is realized instead.
        """
        _, refused = self.computed_facts('workloads')
        if not refused:
            return ()
        note = self.realization_note or _DEFAULT_REALIZATION
        return ({'format': GAP_FORMAT, 'code': GAP_COMPUTED_INPUT_NOT_ACCEPTED,
                 'platform': self.platform, 'phase': 'workloads',
                 'inputs': sorted(refused), 'realized_by': note,
                 'message': f'{self.platform} workload realization inputs accept none of '
                            f'{sorted(refused)}; {note}'},)

    def realization_contract(self) -> dict:
        """The whole provider-specific realization contract, as one reviewable document."""
        return {'format': CONTRACT_FORMAT, 'platform': self.platform, 'family': self.family,
                'capability': self.capability_contract(),
                'placement': self.placement_contract(),
                'phases': {phase: self.phase_contract(phase) for phase in PHASES},
                'readback': self.readback_contract(),
                'security_edge': self.security_edge_contract(),
                'gaps': [dict(gap) for gap in self.realization_gaps()],
                'gap_codes': list(GAP_CODES),
                'limits': list(self.limits),
                'native_contact': False}

    # -- refusal -------------------------------------------------------------

    def validate(self, plan) -> tuple[str, ...]:
        """Refuse a reviewed plan this platform cannot realize, before it is approved.

        Only what the adapter can decide without native contact is decided here: that
        the reviewed composition roots exist, that the reviewed catalog declares the
        edge realization, that both zones are represented, that reviewed inventory
        supplied every declared placement input, and that no workload declares a native
        input the reviewed module does not accept.
        """
        from provisioner.execution import terraform
        problems: list[str] = []
        for phase in PHASES:
            try:
                terraform.composition(self.platform, phase)
            except ProvisioningError as exc:
                problems.append(f'{self.platform} has no reviewed {phase} composition: '
                                f'{exc.message}')
        if not self.edge_components:
            problems.append(f'{self.platform} declares no reviewed security-edge component')
        elif self.security_edge not in self.edge_components:
            problems.append(f'the declared edge realization {self.security_edge!r} is not a '
                            f'reviewed {EDGE_SCOPE} component of {self.platform}')
        state = plan.desired_state
        if state.platform != self.platform:
            problems.append(f'the plan realizes {state.platform}, not {self.platform}')
        zones = {domain.zone for domain in state.domains}
        required_zones = set(getattr(plan.resolution, 'zones', ()) or ())
        unknown = sorted(required_zones - set(ZONES))
        if unknown:
            problems.append(f'the request requires zones outside the reviewed zone '
                            f'vocabulary: {unknown}')
        for zone in sorted(required_zones):
            if zone not in zones:
                problems.append(f'the plan represents no {zone} zone')
        declared = self.declared_inputs('workloads')
        required = set(self.placement_fields)
        for cluster in state.clusters:
            missing = sorted(required - set(cluster.get('native', {})))
            if missing:
                problems.append(f'cluster {cluster["id"]} supplies no native placement '
                                f'identity {missing}')
        for domain in state.domains:
            for workload in domain.workloads:
                unknown = sorted(set(workload.inputs) - declared)
                if unknown:
                    problems.append(f'workload {workload.name} declares native inputs the '
                                    f'reviewed {self.platform} module does not accept: {unknown}')
        return tuple(problems)

def _adapter(platform: str, security_edge: str, limits: tuple[str, ...],
             realization_note: str = '', *, workload_lifecycle: WorkloadLifecycle) -> Adapter:
    modules = repository.composition_components()[platform]
    compiler = repository.compiler_declarations()
    return Adapter(platform=platform, family=eligibility.PLATFORM_FAMILY[platform],
                   domains_module=modules['domains'], workloads_module=modules['workloads'],
                   placement_fields=frozenset(compiler['placement'][platform]),
                   network_fields=frozenset(compiler['network'][platform]),
                   security_edge=security_edge, workload_lifecycle=workload_lifecycle,
                   edge_components=edge_components(platform),
                   binding_requirement=binding_requirement(platform),
                   realization_note=realization_note, limits=limits)


def adapters() -> dict[str, Adapter]:
    """Every adapter this repository currently declares."""
    from provisioner.adapters import nutanix, openstack, vmware
    return {a.platform: a for a in (nutanix.adapter(), vmware.adapter(),
                                    openstack.adapter())}


def get(platform: str) -> Adapter:
    try:
        return adapters()[platform]
    except KeyError as exc:
        raise ValueError(f'No adapter declares platform {platform!r}') from exc
