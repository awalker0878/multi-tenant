"""Deterministic assessment facts derived from a single stored generation.

Normalization is not qualification: guest, network and data compatibility are
never guessed from a platform family, a selector, a VM name or a quota limit.
Both raw and normalized digests are retained so a review can bind its actual
inputs. Missing fields stay unknown; values from older generations never fill
holes in a newer observation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .model import (DiscoveryFact, DiscoveryObject, DiscoveryResult, _digest,
                    _object_json)
from .persistence import StoredGeneration, StoredObservation


NORMALIZER_VERSION = 'hosting-assessment-normalizer/1'
_MAX = 2**63 - 1
_MIB = 1024**2
_GIB = 1024**3
_PROFILE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')
_FACT_KEYS = {'name', 'state', 'value', 'reason', 'requiredPrivilege'}


class NormalizationHeld(ValueError):
    """Stored input cannot be reconstructed without losing scope or integrity."""


@dataclass(frozen=True, slots=True)
class NormalizedDiscovery:
    original: DiscoveryResult
    inventory: DiscoveryResult
    normalizer_version: str = NORMALIZER_VERSION

    def binding(self) -> dict:
        return {'rawSnapshotDigest': self.original.digest,
                'assessmentSnapshotDigest': self.inventory.digest,
                'normalizerVersion': self.normalizer_version,
                'capturedAt': self.original.captured_at.isoformat(),
                'collectionCompleteness': self.original.completeness,
                'assessmentCompleteness': self.inventory.completeness}


def hydrate_generation(generation: StoredGeneration,
                       observations: tuple[StoredObservation, ...]) -> DiscoveryResult:
    """Verify the complete pinned set, not merely individual object checksums."""
    if (not isinstance(generation, StoredGeneration)
            or type(generation.generation) is not int or generation.generation < 1
            or type(generation.object_count) is not int
            or not 0 <= generation.object_count <= 100000
            or not isinstance(observations, tuple)
            or len(observations) != generation.object_count):
        raise NormalizationHeld('Pinned generation object count is incomplete')
    objects = []
    try:
        for observation in observations:
            if (not isinstance(observation, StoredObservation)
                    or observation.generation != generation.generation
                    or not isinstance(observation.facts, tuple)):
                raise NormalizationHeld('Observation is outside the pinned generation')
            facts = []
            for item in observation.facts:
                if not isinstance(item, dict) or set(item) != _FACT_KEYS:
                    raise NormalizationHeld('Stored fact shape has changed')
                if item['state'] == 'KNOWN':
                    if item['reason'] is not None or item['requiredPrivilege'] is not None:
                        raise NormalizationHeld('Known fact has unknown provenance')
                    fact = DiscoveryFact.known(item['name'], item['value'])
                elif item['state'] == 'UNKNOWN' and item['value'] is None:
                    fact = DiscoveryFact.unknown(
                        item['name'], item['reason'],
                        required_privilege=item['requiredPrivilege'])
                else:
                    raise NormalizationHeld('Stored fact state is invalid')
                facts.append(fact)
            obj = DiscoveryObject(observation.identity, tuple(facts))
            if _digest(_object_json(obj)) != observation.object_digest:
                raise NormalizationHeld('Stored observation digest has changed')
            objects.append(obj)
        result = DiscoveryResult(
            generation.campaign_id, generation.authorization_digest,
            generation.scope, generation.captured_at, generation.completeness,
            tuple(objects), generation.collection_errors, generation.missing_privileges)
    except (TypeError, ValueError, KeyError) as exc:
        raise NormalizationHeld('Stored generation cannot be reconstructed') from exc
    if result.digest != generation.result_digest:
        raise NormalizationHeld('Stored generation digest has changed')
    return result


def _integer(value: object, *, minimum: int = 0) -> bool:
    return type(value) is int and minimum <= value <= _MAX


def _unknown(name: str, *inputs: DiscoveryFact | None) -> DiscoveryFact:
    # Preserve a concrete permission failure rather than replacing it with a
    # generic missing value when an input is explicitly unknown.
    missing = next((item for item in inputs if item is not None
                    and item.state == 'UNKNOWN'), None)
    return (DiscoveryFact.unknown(name, missing.reason,
                                  required_privilege=missing.required_privilege)
            if missing else DiscoveryFact.unknown(name, 'NOT_RETURNED'))


def _value(facts: dict[str, DiscoveryFact], name: str) -> object | None:
    item = facts.get(name)
    return item.value() if item is not None and item.state == 'KNOWN' else None


def _number(facts: dict[str, DiscoveryFact], name: str, *, minimum: int,
            alias: str | None = None, multiplier: int = 1) -> DiscoveryFact:
    item = facts.get(name)
    source = facts.get(alias) if alias else None
    if item is not None:
        if item.state == 'UNKNOWN':
            return item
        # A canonical name does not outrank a contradictory native observation.
        if source is not None and source.state == 'KNOWN':
            native = source.value()
            if (not _integer(native, minimum=minimum) or native * multiplier > _MAX
                    or item.value() != native * multiplier):
                return DiscoveryFact.unknown(name, 'COLLECTION_ERROR')
        return (item if _integer(item.value(), minimum=minimum)
                else DiscoveryFact.unknown(name, 'COLLECTION_ERROR'))
    if source is None or source.state == 'UNKNOWN':
        return _unknown(name, source)
    value = source.value()
    if not _integer(value, minimum=minimum) or value * multiplier > _MAX:
        return DiscoveryFact.unknown(name, 'COLLECTION_ERROR')
    return DiscoveryFact.known(name, value * multiplier)


def _text(facts: dict[str, DiscoveryFact], name: str, *, multiple: bool = False
          ) -> DiscoveryFact:
    item = facts.get(name)
    if item is None or item.state == 'UNKNOWN':
        return _unknown(name, item)
    value = item.value()
    values = value if multiple and isinstance(value, list) else [value]
    valid = (not multiple or isinstance(value, list)) and all(
        isinstance(part, str) and _PROFILE.fullmatch(part) for part in values)
    if not valid or multiple and len(set(values)) != len(values):
        return DiscoveryFact.unknown(name, 'COLLECTION_ERROR')
    return item


def _native_id(value: object) -> bool:
    return (isinstance(value, str) and 0 < len(value) <= 512 and bool(value.strip())
            and all(ord(char) >= 32 and ord(char) != 127 for char in value))


def _network_bindings(value: object) -> list[dict] | None:
    if not isinstance(value, list) or len(value) > 256:
        return None
    bindings = []
    for nic in value:
        if not isinstance(nic, dict):
            return None
        for canonical, native in (('nativeNicId', 'extId'),
                                  ('nativeNetworkId', 'subnetExtId')):
            if canonical in nic and native in nic and nic[canonical] != nic[native]:
                return None
        nic_id = nic.get('nativeNicId', nic.get('extId'))
        network_id = nic.get('nativeNetworkId', nic.get('subnetExtId'))
        if not _native_id(nic_id) or not _native_id(network_id):
            return None
        bindings.append({'nativeNicId': nic_id, 'nativeNetworkId': network_id})
    if len({item['nativeNicId'] for item in bindings}) != len(bindings):
        return None
    return bindings


def _vm(facts: dict[str, DiscoveryFact]) -> None:
    cpu = _number(facts, 'vcpuCount', minimum=1, alias='vcpus')
    sockets, cores = (facts.get(name) for name in ('numSockets', 'numCoresPerSocket'))
    if all(item is not None and item.state == 'KNOWN' for item in (sockets, cores)):
        valid = (_integer(sockets.value(), minimum=1) and _integer(cores.value(), minimum=1)
                 and sockets.value() * cores.value() <= _MAX)
        if not valid or cpu.state == 'KNOWN' and cpu.value() != sockets.value() * cores.value():
            cpu = DiscoveryFact.unknown('vcpuCount', 'COLLECTION_ERROR')
        elif 'vcpuCount' not in facts and 'vcpus' not in facts:
            cpu = DiscoveryFact.known('vcpuCount', sockets.value() * cores.value())
    elif 'vcpuCount' not in facts and 'vcpus' not in facts:
        cpu = _unknown('vcpuCount', sockets, cores)
    facts['vcpuCount'] = cpu
    facts['memorySizeBytes'] = _number(facts, 'memorySizeBytes', minimum=1,
                                      alias='memoryMiB', multiplier=_MIB)
    capacity = _number(facts, 'diskCapacityBytes', minimum=0)
    # AHV's collector stores a bounded, complete VM disk attachment list. Only
    # sum it when every disk is identified and every capacity is observed.
    disks = _value(facts, 'disks')
    if 'disks' in facts:
        if isinstance(disks, list) and len(disks) <= 256:
            ids = [item.get('extId') for item in disks if isinstance(item, dict)]
            sizes = [item.get('diskSizeBytes') for item in disks if isinstance(item, dict)]
            if (len(ids) == len(disks) and all(_native_id(item) for item in ids)
                    and len(set(ids)) == len(ids)
                    and all(_integer(item, minimum=1) for item in sizes)
                    and sum(sizes) <= _MAX):
                total = sum(sizes)
                if (capacity.state == 'KNOWN' and capacity.value() != total):
                    capacity = DiscoveryFact.unknown('diskCapacityBytes', 'COLLECTION_ERROR')
                elif 'diskCapacityBytes' not in facts:
                    capacity = DiscoveryFact.known('diskCapacityBytes', total)
            else:
                capacity = DiscoveryFact.unknown('diskCapacityBytes', 'COLLECTION_ERROR')
        else:
            capacity = _unknown('diskCapacityBytes', facts['disks'])
    facts['diskCapacityBytes'] = capacity
    for name in ('guestProfile', 'networkMode', 'dataMode'):
        facts[name] = _text(facts, name)
    network_input = facts.get('networkBindings', facts.get('nics'))
    if network_input is None or network_input.state == 'UNKNOWN':
        facts['networkBindings'] = _unknown('networkBindings', network_input)
    else:
        bindings = _network_bindings(network_input.value())
        native_input = facts.get('nics') if 'networkBindings' in facts else None
        if bindings is not None and native_input is not None and native_input.state == 'KNOWN':
            native = _network_bindings(native_input.value())
            if native is None or {item['nativeNicId']: item['nativeNetworkId'] for item in native} != {
                    item['nativeNicId']: item['nativeNetworkId'] for item in bindings}:
                bindings = None
        facts['networkBindings'] = (DiscoveryFact.known('networkBindings', bindings)
                                    if bindings is not None else DiscoveryFact.unknown(
                                        'networkBindings', 'COLLECTION_ERROR'))
    if 'measuredTransferBytes' in facts:
        facts['measuredTransferBytes'] = _number(facts, 'measuredTransferBytes', minimum=0)


def _capacity(facts: dict[str, DiscoveryFact]) -> None:
    for field, quota_key, scale in (
        ('availableVcpu', 'cores', 1),
        ('availableMemoryBytes', 'ram', _MIB),
        ('availableStorageBytes', 'gigabytes', _GIB),
    ):
        normalized = _number(facts, field, minimum=0)
        if field not in facts:
            # A configured quota is never available capacity. Both consumed
            # usage and pending reservations must be observed in this snapshot.
            inputs = tuple(facts.get(name) for name in ('limits', 'usage', 'reservations'))
            values = tuple(_value(facts, name) for name in ('limits', 'usage', 'reservations'))
            if all(isinstance(value, dict) and quota_key in value for value in values):
                limit, used, reserved = (value[quota_key] for value in values)
                if limit == -1 and type(limit) is int:
                    normalized = DiscoveryFact.unknown(field, 'NOT_SUPPORTED')
                elif all(_integer(value) for value in (limit, used, reserved)):
                    available = max(0, limit - used - reserved) * scale
                    normalized = (DiscoveryFact.known(field, available)
                                  if available <= _MAX else
                                  DiscoveryFact.unknown(field, 'COLLECTION_ERROR'))
                else:
                    normalized = DiscoveryFact.unknown(field, 'COLLECTION_ERROR')
            else:
                normalized = _unknown(field, *inputs)
        facts[field] = normalized
    for name in ('supportedGuestProfiles', 'supportedNetworkModes', 'supportedDataModes'):
        facts[name] = _text(facts, name, multiple=True)
    if 'measuredTransferBytesPerSecond' in facts:
        facts['measuredTransferBytesPerSecond'] = _number(
            facts, 'measuredTransferBytesPerSecond', minimum=1)


def normalize_discovery(result: DiscoveryResult) -> NormalizedDiscovery:
    """Produce bounded canonical facts without modifying the stored result."""
    if not isinstance(result, DiscoveryResult):
        raise NormalizationHeld('A verified stored discovery result is required')
    objects = []
    for obj in result.objects:
        facts = {fact.name: fact for fact in obj.facts}
        kind = obj.identity.resource_kind
        if kind == 'vm':
            _vm(facts)
        elif kind in {'pool', 'cluster', 'quota', 'datastore'}:
            _capacity(facts)
        elif kind in {'disk', 'volume'}:
            facts['diskCapacityBytes'] = _number(
                facts, 'diskCapacityBytes', minimum=0,
                alias='size_gib' if kind == 'volume' else 'diskSizeBytes',
                multiplier=_GIB if kind == 'volume' else 1)
        elif kind == 'nic':
            # OpenStack port ownership and network attachment remain separate
            # facts; neither implies a guest networking mode or security policy.
            for canonical, native in (('attachedVmId', 'device_id'),
                                      ('nativeNetworkId', 'network_id')):
                item = facts.get(canonical, facts.get(native))
                alias = facts.get(native) if canonical in facts else None
                if (item is not None and item.state == 'KNOWN'
                        and alias is not None and alias.state == 'KNOWN'
                        and item.value() != alias.value()):
                    facts[canonical] = DiscoveryFact.unknown(canonical, 'COLLECTION_ERROR')
                else:
                    facts[canonical] = (DiscoveryFact.known(canonical, item.value())
                                        if item and item.state == 'KNOWN'
                                        and _native_id(item.value()) else
                                        _unknown(canonical, item))
        if len(facts) > 64:
            raise NormalizationHeld('Normalization exceeds the object fact budget')
        objects.append(DiscoveryObject(obj.identity, tuple(sorted(
            facts.values(), key=lambda fact: fact.name))))
    completeness = result.completeness
    if completeness == 'COMPLETE' and any(fact.state == 'UNKNOWN'
                                         for obj in objects for fact in obj.facts):
        completeness = 'PARTIAL'
    normalized = DiscoveryResult(
        result.campaign_id, result.authorization_digest, result.scope,
        result.captured_at, completeness, tuple(objects), result.collection_errors,
        result.missing_privileges)
    return NormalizedDiscovery(result, normalized)
