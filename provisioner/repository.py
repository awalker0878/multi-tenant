"""Access to reviewed source assets and installed owner tooling."""
from __future__ import annotations

import importlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = Path(__file__).resolve().parent / '_assets'


def asset_path(relative_path: str) -> Path:
    """Locate a reviewed runtime asset in the package or source checkout."""
    path = Path(relative_path)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError(f'Unsafe runtime asset path: {relative_path}')
    packaged = ASSET_ROOT / path
    return packaged if packaged.is_file() else ROOT / path

def repository_module(name: str):
    """Import an installed owner module, failing loudly if it is absent."""
    return importlib.import_module(name)


def reviewed_source(path: Path | str) -> str:
    """The request path as a reviewed input rather than as an invocation.

    A reviewed plan must not depend on how an operator spelled the path, so the
    manifest binds the path relative to the repository root in POSIX form, and
    falls back to the resolved path when the document lives outside the checkout.
    """
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    try:
        resolved = candidate.resolve()
    except OSError:
        return str(path).replace('\\', '/')
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def source_commit(root: Path | str | None = None) -> dict:
    """The clean checkout commit the existing release verifier reports.

    A delivery handoff binds one exact clean source commit. The repository
    already owns that answer, so the provisioner asks for it instead of
    computing a second opinion.
    """
    verifier = repository_module('tools.check_release')
    result = verifier.verify(Path(root) if root is not None else ROOT)
    return {'status': result.get('status', ''), 'commit': result.get('commit', ''),
            'issues': list(result.get('issues', []))}


def reservation_records(path: Path | str | None = None) -> dict:
    """The repository's exported reservation record evidence.

    The authoritative reservation system is external. The repository exports what
    that system recorded and already owns the contract for reading it, so the
    provisioner asks for the export instead of defining a second record model.
    """
    module = repository_module('scripts.check_reservation_records')
    return module.load(Path(path) if path is not None else module.INDEX)


def validate_reservation_records(index: dict, *, as_of, root: Path | str | None = None) -> dict:
    """Validate an exported reservation record index with the repository's checker."""
    module = repository_module('scripts.check_reservation_records')
    return module.validate(index, as_of=as_of,
                           root=Path(root) if root is not None else ROOT)


def ipam_allocation_records(path: Path | str | None = None) -> dict:
    """The repository's exported authoritative IPAM allocation evidence.

    The authoritative IPAM system is external. The repository exports what that
    system recorded and already owns the contract for reading it, so the
    provisioner asks for the export instead of defining a second record model.
    The exported record deliberately carries no allocated address or prefix value.
    """
    module = repository_module('scripts.check_ipam_allocation_records')
    return module.load(Path(path) if path is not None else module.INDEX)


def validate_ipam_allocation_records(index: dict, *, as_of,
                                     root: Path | str | None = None) -> dict:
    """Validate an exported IPAM allocation index with the repository's checker."""
    module = repository_module('scripts.check_ipam_allocation_records')
    return module.validate(index, as_of=as_of,
                           root=Path(root) if root is not None else ROOT)


def dns_registration_records(path: Path | str | None = None) -> dict:
    """The repository's exported authoritative DNS registration evidence."""
    module = repository_module('scripts.check_dns_registration_records')
    return module.load(Path(path) if path is not None else module.INDEX)


def validate_dns_registration_records(index: dict, *, ipam_index=None, as_of,
                                      root: Path | str | None = None) -> dict:
    """Validate an exported DNS registration index with the repository's checker.

    The checker cross-checks every registration against the confirmed IPAM
    allocation it was derived from, so a registration whose bound allocation is
    absent, unconformed or of another family is refused here rather than used.
    """
    module = repository_module('scripts.check_dns_registration_records')
    return module.validate(index, ipam_index=ipam_index, as_of=as_of,
                           root=Path(root) if root is not None else ROOT)


def ipam_allocation_preflight(intent: dict, *, reservation_index=None,
                              allocation_index=None, as_of=None) -> dict:
    """Run the repository's authoritative IPAM allocation preflight on an intent.

    The preflight is the repository's own contract for an allocation *intent*: it
    validates the shape, resolves the declared parent reservation and reports what
    the authoritative IPAM system has recorded. It never returns an address.
    """
    module = repository_module('scripts.check_ipam_allocation_preflight')
    return module.evaluate(intent, reservation_index=reservation_index,
                           allocation_index=allocation_index, as_of=as_of)


def ipam_allocation_spec(intent: dict, *, as_of, parent_envelope_record_sha256=None) -> dict:
    """Normalize a portable IPAM allocation intent with the owner's own preflight.

    The owner normalizes a submitted intent before it hashes it, so the provisioner
    asks for the normalization instead of restating the contract. The declared parent
    reservation intent and its capacity request must resolve inside the checkout.
    """
    module = repository_module('scripts.check_ipam_allocation_preflight')
    return module.normalized_spec(intent, as_of=as_of,
                                  parent_envelope_record_sha256=parent_envelope_record_sha256)


def dns_registration_preflight(intent: dict, *, ipam_index=None, dns_index=None,
                               as_of=None) -> dict:
    """Run the repository's authoritative DNS registration preflight on an intent."""
    module = repository_module('scripts.check_dns_registration_preflight')
    return module.evaluate(intent, ipam_index=ipam_index, dns_index=dns_index,
                           as_of=as_of)


def declared_contracts() -> dict:
    """The repository's declared portable lifecycle contracts, read from the owners.

    The provisioner must compile documents the existing owner contracts accept. It
    does not restate those contracts: it asks the modules that already own them for
    the declared vocabulary, so a compiled document and the checker that will judge
    it can never disagree about a key set, a status or an identifier grammar.
    """
    site = repository_module('scripts.check_site_service_eligibility')
    capacity = repository_module('scripts.check_site_service_capacity')
    reservation = repository_module('scripts.check_reservation_preflight')
    allocation = repository_module('scripts.check_ipam_allocation_preflight')
    allocation_records = repository_module('scripts.check_ipam_allocation_records')
    registration = repository_module('scripts.check_dns_registration_preflight')
    registration_records = repository_module('scripts.check_dns_registration_records')
    records = repository_module('scripts.check_reservation_records')
    return {
        'identifier': site.ID.pattern,
        'capacity_request': {
            'format': site.FORMAT, 'status': site.STATUS, 'authority': 'NOT_ASSESSED',
            'keys': sorted(site.REQUEST_KEYS), 'demand_keys': sorted(site.DEMAND_KEYS),
            'platforms': sorted(capacity.PLATFORMS),
            'profile_keys': sorted(capacity.PROFILE_KEYS)},
        'reservation_intent': {
            'format': reservation.FORMAT, 'status': reservation.STATUS,
            'authority': 'NOT_ASSESSED', 'keys': sorted(reservation.INTENT_KEYS),
            'spec_keys': sorted(reservation.SPEC_KEYS),
            'owner_keys': sorted(records.OWNER_KEYS),
            'resource_keys': sorted(records.RESOURCE_KEYS),
            'dependency_keys': sorted(reservation.DEPENDENCY_KEYS),
            'statuses': sorted({reservation.READY, reservation.HOLD_ENVELOPE,
                                reservation.HOLD_CONFLICT, reservation.HOLD_UNCERTAIN,
                                reservation.HOLD_TERMINAL, reservation.EXISTING_HELD,
                                reservation.EXISTING_CONSUMED})},
        'allocation_intent': {
            'format': allocation.FORMAT, 'status': allocation.STATUS,
            'authority': 'NOT_ASSESSED', 'keys': sorted(allocation.INTENT_KEYS),
            'spec_keys': sorted(allocation.SPEC_KEYS),
            'owner_keys': sorted(allocation_records.OWNER_KEYS),
            'policies': sorted(allocation_records.POLICIES),
            'families': sorted(allocation_records.FAMILIES),
            'kinds': sorted(allocation_records.KINDS),
            'statuses': sorted({allocation.READY, allocation.HOLD_PARENT,
                                allocation.HOLD_CONFLICT, allocation.HOLD_UNCERTAIN,
                                allocation.HOLD_RELEASE, allocation.HOLD_TERMINAL,
                                allocation.EXISTING_RESERVED, allocation.EXISTING_CONFIRMED})},
        'registration_intent': {
            'format': registration.FORMAT, 'status': registration.STATUS,
            'authority': 'NOT_ASSESSED', 'keys': sorted(registration.INTENT_KEYS),
            'spec_keys': sorted(registration.SPEC_KEYS),
            'owner_keys': sorted(registration_records.OWNER_KEYS),
            'record_types': sorted(registration_records.RECORD_TYPES),
            'observations': sorted(registration_records.OBSERVATIONS),
            'statuses': sorted({registration.READY, registration.HOLD_IPAM,
                                registration.HOLD_CONFLICT, registration.HOLD_UNCERTAIN,
                                registration.HOLD_RELEASE, registration.HOLD_TERMINAL,
                                registration.EXISTING_REGISTERED})},
        'allocation_record': {
            'states': sorted(allocation_records.STATES),
            'cleanup_states': sorted(allocation_records.CLEANUP_STATES),
            'cleanup_keys': sorted(allocation_records.CLEANUP_KEYS)},
        'registration_record': {
            'states': sorted(registration_records.STATES),
            'observation_states': sorted(registration_records.OBS_STATES)},
        'reservation_record': {'states': sorted(records.STATES)},
    }


def capacity_request_shape(document: dict) -> dict:
    """Validate a portable site-service capacity request with the repository checker."""
    module = repository_module('scripts.check_site_service_eligibility')
    module.validate_request(document, None)
    return document


def reservation_intent_spec(intent: dict, capacity_request: dict, *, as_of,
                            envelope_record_sha256=None) -> dict:
    """Normalize a portable reservation intent in memory with its capacity request.

    The owner's own preflight normalizes the pair, so the provisioner asks for the
    normalized spec instead of restating the contract. The declared
    `capacity_request_ref` must still resolve inside the checkout, which is why a
    compiled chain is staged before it is handed to the owner.
    """
    module = repository_module('scripts.check_reservation_preflight')
    return module.normalized_spec(intent, capacity_request, as_of=as_of,
                                  envelope_record_sha256=envelope_record_sha256)


def dns_registration_spec(intent: dict, *, as_of, ipam_confirmation_sha256=None) -> dict:
    """Normalize a portable DNS registration intent in memory with the owner's preflight."""
    module = repository_module('scripts.check_dns_registration_preflight')
    return module.normalized_spec(intent, as_of=as_of,
                                  ipam_confirmation_sha256=ipam_confirmation_sha256)


def allocation_prefix_shape(family, kind, prefix_length) -> None:
    """Refuse an IPAM prefix shape the authoritative record contract would refuse."""
    module = repository_module('scripts.check_ipam_allocation_records')
    module.validate_prefix_shape(family, kind, prefix_length)


def opaque_external_ref(value, label) -> str:
    """Refuse an opaque external reference the IPAM contract would refuse."""
    module = repository_module('scripts.check_ipam_allocation_records')
    return module.opaque_external_ref(value, label)


def opaque_dns_ref(value, label) -> str:
    """Refuse an opaque DNS reference the registration contract would refuse."""
    module = repository_module('scripts.check_dns_registration_records')
    return module.opaque_ref(value, label)


def instant(value, label):
    """Read a timezone-aware instant with the repository record contract."""
    module = repository_module('scripts.check_reservation_records')
    return module.instant(value, label)


def canonical_record_digest(document: dict) -> str:
    """The repository's canonical digest of a reservation-shaped document."""
    module = repository_module('scripts.check_reservation_records')
    return module.canonical_digest(document)


def canonical_dns_intent_digest(document: dict) -> str:
    """The repository's canonical digest of a normalized DNS registration intent."""
    module = repository_module('scripts.check_dns_registration_preflight')
    return module.canonical_digest(document)


def repository_document(relative_path: Path | str) -> dict:
    """Load one reviewed document from inside the checkout by relative path.

    A declared repository reference is only meaningful if it resolves inside the
    checkout, so the reference contract and the loader agree here.
    """
    target = Path(relative_path)
    if target.is_absolute() or '..' in target.parts or '\\' in str(relative_path):
        raise ValueError(f'Repository reference must be normalized and relative: {relative_path}')
    return json.loads((ROOT / target).read_text(encoding='utf-8'))


def document_exists(relative_path: Path | str) -> bool:
    """Whether a declared repository reference resolves inside the checkout."""
    target = Path(str(relative_path))
    if target.is_absolute() or '..' in target.parts or '\\' in str(relative_path):
        return False
    return (ROOT / target).is_file()
