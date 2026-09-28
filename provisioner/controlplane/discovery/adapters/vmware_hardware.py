"""Whitelisted vCenter VM-info observations, not SOAP ConfigInfo or guest facts.

Schema: vSphere Automation API GET /api/vcenter/vm/{vm}. The REST VM-info
response does not establish ISA, vTPM/key custody, guest encryption, shared-disk
writer exclusion or application memory-state requirements. Never ingest arbitrary
extraConfig, user data, datastore paths, connection information or native secrets.
"""
from __future__ import annotations

import re
from provisioner.controlplane.authority.model import PlanScope
from ..model import DiscoveryFact, DiscoveryObject, NativeIdentity

_MAX = 2**63 - 1
_MAC = re.compile(r'(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\Z')


def _text(value: object) -> bool:
    return (isinstance(value, str) and 1 <= len(value) <= 128
            and bool(value.strip()) and all(32 <= ord(c) != 127 for c in value))


def _integer(value: object, minimum: int = 0) -> bool:
    return type(value) is int and minimum <= value <= _MAX


def _fact(name: str, value: object, valid=lambda v: True) -> DiscoveryFact:
    if value is None:
        return DiscoveryFact.unknown(name, 'NOT_RETURNED')
    if not valid(value):
        return DiscoveryFact.unknown(name, 'COLLECTION_ERROR')
    try:
        return DiscoveryFact.known(name, value)
    except (ValueError, TypeError):
        return DiscoveryFact.unknown(name, 'COLLECTION_ERROR')


def _devices(raw: object) -> list[tuple[str, dict]] | None:
    if raw is None:
        return None
    if (not isinstance(raw, dict) or len(raw) > 256
            or any(not _text(k) or not isinstance(v, dict) for k, v in raw.items())):
        raise ValueError('Malformed device map')
    return sorted(raw.items())  # stable inventory order, never guest boot order


def _disks(raw: object) -> tuple[DiscoveryFact, ...]:
    names = ('disks', 'diskCapacityBytes', 'diskLayout')
    try:
        devices = _devices(raw)
        if devices is None:
            return tuple(DiscoveryFact.unknown(n, 'NOT_RETURNED') for n in names)
        disks, layout, slots, total = [], [], set(), 0
        size_missing, layout_missing = False, False
        for key, device in devices:
            size = device.get('capacity')
            if size is None:
                size_missing = True
            elif not _integer(size, 1) or total + size > _MAX:
                raise ValueError('Invalid disk capacity')
            else:
                total += size
            backing = device.get('backing')
            backing_type = backing.get('type') if isinstance(backing, dict) else None
            if backing_type is not None and not _text(backing_type):
                raise ValueError('Invalid disk backing')
            disks.append({'extId': key, 'diskSizeBytes': size, 'backingType': backing_type})
            kind = device.get('type')
            if kind not in ('SCSI', 'SATA', 'NVME', 'IDE'):
                layout_missing = True
                continue
            address = device.get(kind.lower())
            if address is None:
                layout_missing = True
                continue
            fields = ('primary', 'master') if kind == 'IDE' else ('bus', 'unit')
            if (not isinstance(address, dict) or
                    any(not (type(address.get(f)) is bool if kind == 'IDE'
                             else _integer(address.get(f))) for f in fields)):
                raise ValueError('Invalid device address')
            slot = (kind, *(address[f] for f in fields))
            if slot in slots:
                raise ValueError('Conflicting disk address')
            slots.add(slot)
            layout.append({'extId': key, 'busType': kind, **{f: address[f] for f in fields}})
        return (_fact('disks', disks), _fact('diskCapacityBytes', None if size_missing else total),
                _fact('diskLayout', None if layout_missing else layout))
    except ValueError:
        return tuple(DiscoveryFact.unknown(n, 'COLLECTION_ERROR') for n in names)


def _nics(raw: object) -> tuple[DiscoveryFact, ...]:
    names = ('nics', 'networkBindings', 'nicHardware')
    try:
        devices = _devices(raw)
        if devices is None:
            return tuple(DiscoveryFact.unknown(n, 'NOT_RETURNED') for n in names)
        nics, hardware, macs = [], [], set()
        network_missing, hardware_missing = False, False
        for key, device in devices:
            backing = device.get('backing')
            network = backing.get('network') if isinstance(backing, dict) else None
            if network is not None and not _text(network):
                raise ValueError('Malformed native network identity')
            network_missing |= network is None
            # A port ID, switch UUID, display name or opaque-network ID is not
            # the vCenter Network resource ID. Do not silently substitute one.
            nics.append({'nativeNicId': key, 'nativeNetworkId': network})
            mac = device.get('mac_address')
            model, state = device.get('type'), device.get('state')
            connected = device.get('start_connected')
            if any(v is None for v in (mac, model, state, connected)):
                hardware_missing = True
                continue
            if (not isinstance(mac, str) or not _MAC.fullmatch(mac)
                    or not _text(model) or not _text(state) or type(connected) is not bool):
                raise ValueError('Malformed NIC hardware')
            if mac.lower() in macs:
                raise ValueError('Duplicate MAC identity')
            macs.add(mac.lower())
            hardware.append({'nativeNicId': key, 'model': model,
                             'macAddress': mac.lower(), 'state': state,
                             'startConnected': connected})
        return (_fact('nics', nics), _fact('networkBindings', None if network_missing else nics),
                _fact('nicHardware', None if hardware_missing else hardware))
    except ValueError:
        return tuple(DiscoveryFact.unknown(n, 'COLLECTION_ERROR') for n in names)


def observe_vm(scope: PlanScope, vm_id: str, instance_uuid: str, detail: dict) -> DiscoveryObject:
    """Capture only the already identity-checked VM-info response's own facts."""
    cpu = detail.get('cpu') if isinstance(detail.get('cpu'), dict) else {}
    memory = detail.get('memory') if isinstance(detail.get('memory'), dict) else {}
    boot = detail.get('boot') if isinstance(detail.get('boot'), dict) else {}
    size = memory.get('size_mib')
    memory_fact = _fact('memorySizeBytes', size, lambda v: _integer(v, 1) and v <= _MAX // 1024**2)
    if memory_fact.state == 'KNOWN':
        memory_fact = DiscoveryFact.known('memorySizeBytes', size * 1024**2)
    firmware = {'BIOS': 'bios', 'EFI': 'uefi'}.get(boot.get('type')) if isinstance(boot.get('type'), str) else None
    facts = (
        _fact('displayName', detail.get('name'), lambda v: isinstance(v, str) and 1 <= len(v) <= 256),
        DiscoveryFact.known('instanceUuid', instance_uuid),
        _fact('powerState', detail.get('power_state'), _text),
        _fact('nativeGuestOS', detail.get('guest_os'), _text),
        _fact('vcpuCount', cpu.get('count'), lambda v: _integer(v, 1)),
        _fact('numCoresPerSocket', cpu.get('cores_per_socket'), lambda v: _integer(v, 1)),
        memory_fact, _fact('firmware', firmware),
        *_disks(detail.get('disks')), *_nics(detail.get('nics')),
        # REST's efi_legacy_boot is not SOAP's efiSecureBootEnabled.
        DiscoveryFact.unknown('secureBootEnabled', 'NOT_RETURNED'),
        DiscoveryFact.unknown('vtpmEnabled', 'NOT_RETURNED'),
        DiscoveryFact.unknown('architecture', 'NOT_RETURNED'),
        DiscoveryFact.unknown('storageEncrypted', 'NOT_RETURNED'),
        DiscoveryFact.unknown('sharedDisks', 'NOT_RETURNED'),
        DiscoveryFact.unknown('passthroughDevices', 'NOT_RETURNED'),
    )
    return DiscoveryObject(NativeIdentity(scope.endpoint_id, scope.native_scope_id,
                                          'vmware', 'vm', vm_id), facts)
