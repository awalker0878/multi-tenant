"""Environment document emission and handoff to the existing compiler.

The provisioner owns the portable half of this boundary: it renders a resolved
desired state into the reviewed `hosting-wsd-environment/1` document. The existing
`tools/compile_wsd.py` owns the other half and remains the only thing that turns an
environment document into Terraform inputs. It is reused, never reimplemented.
"""
from __future__ import annotations

from provisioner.domain.desired_state import DesiredState
from provisioner.domain.errors import ProvisioningError
from provisioner.repository import repository_module

ENVIRONMENT_FORMAT = 'hosting-wsd-environment/1'
DOMAIN_ID_MAX = 24

#: Workload inputs the provisioner computes itself rather than reading from reviewed inventory.
PROVISIONER_OWNED_INPUTS = ('boot_disk_gib', 'data_disk_gib', 'ipv4_address')


def environment_key(state: DesiredState) -> str:
    return f'{state.site_key}-{state.lifecycle}'


def domain_id(wsd: str, zone: str) -> str:
    value = f'{wsd}-{zone}'
    if len(value) > DOMAIN_ID_MAX:
        raise ProvisioningError(
            'UNSUPPORTED_FEATURE',
            f'Portable name {wsd!r} cannot form a native domain identity within {DOMAIN_ID_MAX} characters',
            path='$.metadata.name',
            details={'derived': value, 'max_length': DOMAIN_ID_MAX})
    return value


def workload_name(tenant: str, wsd: str, zone: str, index: int) -> str:
    return f'{tenant}-{wsd}-{zone.lower()}-{index + 1:02d}'


def native_variables(platform: str, phase: str = 'workloads') -> frozenset:
    """Ask the existing compiler which native inputs one reviewed module declares.

    The provisioner never restates a provider-specific field list. The compiler
    owns the native field shapes, so the provisioner asks it before deciding
    whether a computed input can be expressed on the selected platform.
    """
    return frozenset(repository_module('tools.compile_wsd').native_variables(platform, phase))


def owned_inputs(workload, declared: frozenset) -> dict:
    """The provisioner-computed native inputs the selected platform can accept."""
    computed = {'boot_disk_gib': workload.boot_disk_gib,
                'data_disk_gib': workload.data_disk_gib,
                'ipv4_address': workload.address}
    return {key: computed[key] for key in PROVISIONER_OWNED_INPUTS if key in declared}


def realization_gaps(state: DesiredState) -> tuple[str, ...]:
    """Computed facts the selected platform's reviewed module cannot accept.

    A gap is reported rather than silently dropped: an address is allocated for
    every workload, so a platform that cannot carry it must say so out loud.
    """
    declared = native_variables(state.platform)
    dropped = [key for key in PROVISIONER_OWNED_INPUTS if key not in declared]
    if not dropped:
        return ()
    return (f'{state.platform} workload realization inputs accept none of {sorted(dropped)}; '
            f'the platform realizes those facts through its domain composition instead',)


def render(state: DesiredState) -> dict:
    """Render one resolved desired state as a hosting-wsd-environment/1 document.

    Reviewed inventory supplies the platform-native inputs for the selected site.
    The provisioner adds only the inputs it computes itself, and only where the
    reviewed module for that platform declares them.
    """
    declared = native_variables(state.platform)
    domains = []
    for domain in state.domains:
        workloads = {}
        for workload in domain.workloads:
            inputs = dict(workload.inputs)
            inputs.update(owned_inputs(workload, declared))
            workloads[workload.name] = inputs
        domains.append({'id': domain.domain_id, 'zone': domain.zone,
                        'cluster': domain.cluster_id,
                        'inputs': {**domain.inputs, 'ipv4_cidr': domain.prefix,
                                   'gateway_host_number': domain.gateway_host_number},
                        'workloads': workloads})
    return {
        'format': ENVIRONMENT_FORMAT,
        'environment_key': environment_key(state),
        'site_key': state.site_key,
        'platform': state.platform,
        'lifecycle': state.lifecycle,
        'clusters': [dict(cluster) for cluster in state.clusters],
        'wsds': [{'tenant_key': state.tenant, 'wsd_key': state.wsd, 'trust': state.trust,
                  'service_class': state.service_class, 'domains': domains}],
    }


def compile_document(document: dict, phase: str = 'domains', outputs: dict | None = None,
                     vmware_bindings: dict | None = None) -> tuple[dict, dict]:
    """Hand an environment document to the existing compiler, unchanged."""
    if document.get('format') != ENVIRONMENT_FORMAT:
        raise ProvisioningError('ENVIRONMENT_CONTRACT_INVALID',
                                f'Refusing to compile unknown environment format '
                                f'{document.get("format")!r}',
                                path='environment.format')
    module = repository_module('tools.compile_wsd')
    try:
        return module.compile_environment(document, phase, outputs, vmware_bindings)
    except (ValueError, KeyError, TypeError) as exc:
        raise ProvisioningError('COMPILATION_FAILED',
                                f'The existing compiler refused the environment document: {exc}',
                                path='environment',
                                details={'phase': phase}) from exc


def compile_state(state: DesiredState, phase: str = 'domains') -> tuple[dict, dict]:
    return compile_document(render(state), phase)