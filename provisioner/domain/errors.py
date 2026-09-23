"""Structured provisioning errors with stable codes, layers and remediation.

Every refusal carries a machine-readable code, the layer that refused it and an
actionable remediation. Nothing in this module authorizes a change; it only
explains why a decision was refused.
"""
from __future__ import annotations

# code -> (layer, default remediation)
CODES: dict[str, tuple[str, str]] = {
    'REQUEST_SOURCE_UNREADABLE': ('syntax', 'Read the request from an existing readable file.'),
    'REQUEST_SYNTAX_INVALID': ('syntax', 'Correct the request syntax; duplicate keys are refused.'),
    'UNSUPPORTED_API_VERSION': ('syntax', 'Use the reviewed apiVersion for this repository.'),
    'UNSUPPORTED_KIND': ('syntax', 'Use a supported portable request kind.'),
    'SCHEMA_VALIDATION_FAILED': ('structural', 'Correct the field named in the diagnostic.'),
    'UNSUPPORTED_PROFILE': ('structural', 'Select a profile that exists in the reviewed catalogs.'),
    'UNSUPPORTED_FEATURE': ('structural', 'This request form is deferred; remove it or request the later profile.'),
    'SEMANTIC_INCONSISTENT': ('structural', 'Make the related request fields agree.'),
    'POLICY_VIOLATION': ('standards', 'Change the request or obtain a reviewed standards exception.'),
    'CAPABILITY_NOT_QUALIFIED': ('capability', 'Complete native qualification before selecting this platform.'),
    'PLATFORM_NOT_ELIGIBLE': ('capability', 'Select an eligible platform, site or region.'),
    'NO_ELIGIBLE_PLACEMENT': ('capability', 'Record the explicit external boundary; do not force placement.'),
    'INVENTORY_INCOMPLETE': ('inventory', 'Supply reviewed inventory for the required site, cell or service.'),
    'INVENTORY_NOT_AUTHORITATIVE': ('inventory', 'Replace fixture inventory with authoritative site state.'),
    'CAPACITY_INSUFFICIENT': ('capacity', 'Free or commission capacity before reserving it.'),
    'CAPACITY_RESERVATION_CONFLICT': ('capacity', 'Resolve the overlapping reservation before proceeding.'),
    'CAPACITY_RESERVATION_UNCONFIRMED': ('capacity', 'Obtain the capacity owner confirmation before consuming the reservation.'),
    'CAPACITY_RESERVATION_UNRESOLVED': ('capacity', 'Discover the authoritative reservation outcome through its owner before any retry.'),
    'CAPACITY_SNAPSHOT_STALE': ('capacity', 'Re-plan against the current commissioned capacity view and obtain a new confirmation.'),
    'PREFIX_POOL_EXHAUSTED': ('allocation', 'Extend the reviewed address pool; do not substitute a prefix.'),
    'ADDRESS_CONFLICT': ('allocation', 'Resolve the overlapping prefix or address before proceeding.'),
    'SERVICE_UNAVAILABLE': ('allocation', 'Commission the shared service or choose a supported profile.'),
    'IPAM_ALLOCATION_CONFLICT': ('allocation', 'Resolve the conflicting authoritative allocation before proceeding.'),
    'IPAM_ALLOCATION_UNRESOLVED': ('allocation', 'Discover the authoritative IPAM outcome through its owner before any retry.'),
    'IPAM_ALLOCATION_UNCONFIRMED': ('allocation', 'Obtain the IPAM owner confirmation before the allocation is used.'),
    'DNS_REGISTRATION_CONFLICT': ('allocation', 'Resolve the conflicting authoritative registration before proceeding.'),
    'DNS_REGISTRATION_UNRESOLVED': ('allocation', 'Discover the authoritative DNS outcome through its owner before any retry.'),
    'DNS_REGISTRATION_UNCONFIRMED': ('allocation', 'Obtain the authoritative registration before withdrawing the name.'),
    'ADDRESS_RELEASE_ORDER_VIOLATION': ('allocation', 'Withdraw every dependent registration and complete cleanup before releasing reusable addressing.'),
    'COMPILATION_FAILED': ('compilation', 'Correct the resolved desired state; the existing compiler refused it.'),
    'ENVIRONMENT_CONTRACT_INVALID': ('compilation', 'Correct the environment document fields the compiler refused.'),
    'REALIZATION_INPUT_UNAVAILABLE': ('compilation', 'Complete the reviewed platform module or record the gap as an explicit boundary; do not invent the input.'),
    'REALIZATION_CONTRACT_UNSATISFIED': ('compilation', 'Select a platform whose declared realization contract covers the reviewed request, or complete the missing reviewed module.'),
    'OUTPUT_PATH_NOT_PRIVATE': ('compilation', 'Write generated inputs outside the repository.'),
    'DETERMINISM_VIOLATION': ('compilation', 'Remove the nondeterministic input; output must be reproducible.'),
    'EXECUTION_REFUSED': ('execution', 'Planning only: this repository holds no execution authority.'),
    'AUTHORITY_REQUIRED': ('authority', 'Obtain separate, recorded production authorization.'),
    'ACTIVATION_REFUSED': ('authority', 'Activation requires independent conformance and authorization.'),
    'ARTIFACT_INTEGRITY_FAILED': ('execution', 'Regenerate the artifact from its reviewed request digest.'),
    'GENERATION_CONFLICT': ('generation', 'Claim the next generation of the WSD identity instead.'),
    'GENERATION_IDENTITY_MISMATCH': ('generation', 'Claim the generation against the identity that holds it.'),
    'STALE_GENERATION': ('generation', 'Use the generation the authoritative record currently holds.'),
}

LAYERS = ('syntax', 'structural', 'standards', 'capability', 'inventory', 'capacity',
          'allocation', 'compilation', 'execution', 'authority', 'generation')


class ProvisioningError(Exception):
    """One refused provisioning decision."""

    def __init__(self, code: str, message: str, path: str | None = None,
                 details: dict | None = None, remediation: str | None = None):
        if code not in CODES:
            raise ValueError(f'Unknown provisioning error code: {code}')
        super().__init__(message)
        self.code = code
        self.layer = CODES[code][0]
        self.message = message
        self.path = path
        self.details = dict(details or {})
        self.remediation = remediation or CODES[code][1]

    def to_dict(self) -> dict:
        row = {'code': self.code, 'layer': self.layer, 'message': self.message,
               'remediation': self.remediation}
        if self.path:
            row['path'] = self.path
        if self.details:
            row['details'] = self.details
        return row

    def __str__(self) -> str:
        return f'{self.code}: {self.message}'


class Diagnostics:
    """Accumulates errors so one run reports every actionable refusal."""

    def __init__(self) -> None:
        self.errors: list[ProvisioningError] = []
        self.warnings: list[ProvisioningError] = []

    def add(self, code: str, message: str, path: str | None = None,
            details: dict | None = None, remediation: str | None = None) -> None:
        self.errors.append(ProvisioningError(code, message, path, details, remediation))

    def add_error(self, error: ProvisioningError) -> None:
        self.errors.append(error)

    def add_warning(self, error: ProvisioningError) -> None:
        self.warnings.append(error)

    def extend(self, errors) -> None:
        for error in errors:
            self.errors.append(error if isinstance(error, ProvisioningError)
                               else ProvisioningError(*error))

    @property
    def ok(self) -> bool:
        return not self.errors

    def raise_if_failed(self) -> None:
        if self.errors:
            first = self.errors[0]
            raise ProvisioningError(first.code, first.message, first.path,
                                    {'diagnostics': [e.to_dict() for e in self.errors]},
                                    first.remediation)

    def to_dict(self) -> dict:
        return {'errors': [e.to_dict() for e in self.errors],
                'warnings': [w.to_dict() for w in self.warnings],
                'layers': sorted({e.layer for e in self.errors})}