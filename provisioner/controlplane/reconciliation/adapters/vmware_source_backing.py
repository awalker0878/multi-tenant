"""Current native identity and capacity of an original detached base VMDK.

The retained selector supplies no occupancy evidence. Two fresh native sweeps
read its UUID, primary disk metadata and exact flat extent. This owner cannot
delete files, release a charge or establish source-writer exclusion.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re
import time

from provisioner.controlplane.reconciliation.read_enrollment import NativeReadEnrollment
from provisioner.execution import readback_core as c, vsphere_observe as vm
from provisioner.execution.vsphere_history import CollectorClient
from provisioner.execution.run_files import digest, read_private, require, utcnow
from provisioner.migration.vsphere_credentials import VsphereNativeCredentialOwner


def _disk_path(value):
    require(type(value) is str and len(value) <= 1024, 'One bounded original datastore file is required')
    match = re.fullmatch(r'\[([A-Za-z0-9_. -]{1,128})\] ([A-Za-z0-9_./ -]+\.vmdk)', value)
    require(match is not None, 'The original VMDK path is ambiguous or contains a search pattern')
    name, relative = match.groups()
    require(not relative.startswith('/') and all(part not in {'', '.', '..'} for part in relative.split('/')),
        'The original file escaped its exact datastore directory')
    path = PurePosixPath(relative)
    directory = '' if str(path.parent) == '.' else str(path.parent) + '/'
    return name, '[%s] %s' % (name, directory), path.name


def _uuid(value):
    require(type(value) is str and re.fullmatch(r'[0-9A-Fa-f -]{32,64}', value),
        'The actual original virtual disk UUID has no supported native representation')
    result = re.sub('[ -]', '', value).lower()
    require(re.fullmatch('[0-9a-f]{32}', result), 'The actual native virtual disk UUID is incomplete')
    return result


@dataclass(frozen=True)
class SourceBackingReadRuntime:
    enrollment: NativeReadEnrollment
    credentials: VsphereNativeCredentialOwner
    ca_file: Path
    vstorage_object_manager_id: str
    ca_sha256: str

    def __post_init__(self):
        require(type(self.enrollment) is NativeReadEnrollment and type(self.credentials) is VsphereNativeCredentialOwner
            and self.credentials.commands is self.enrollment.command
            and self.enrollment.scope.platform_family == 'vmware',
            'The actual separately enrolled current source read/credential owners are required')
        c.identifier(self.vstorage_object_manager_id)
        object.__setattr__(self, 'ca_file', Path(self.ca_file))
        require(type(self.ca_sha256) is str and c.HEX.fullmatch(self.ca_sha256)
            and digest(read_private(self.ca_file)) == self.ca_sha256,
            'The independently commissioned source file-read TLS trust differs from its immutable pin')

    def observe(self, binding, disk, *, cursor=None):
        require(binding.platform_family == 'vmware'
            and (binding.endpoint_id, binding.native_scope_id) ==
                (self.enrollment.scope.endpoint_id, self.enrollment.scope.native_scope_id)
            and binding.resource_kind == 'vm', 'The original retained VM belongs to another enrolled native scope')
        vm.moid(binding.native_id, 'vm')
        require(type(disk) is dict and disk.get('_typeName') == 'VirtualDisk'
            and type(disk.get('capacityInKB')) is int and disk['capacityInKB'] > 0
            and disk.get('capacityInBytes') == disk['capacityInKB'] * 1024,
            'The original retained disk needs exact native virtual capacity')
        backing = disk['backing']
        require(backing.get('_typeName') == 'VirtualDiskFlatVer2BackingInfo'
            and backing.get('diskMode') == 'persistent' and not backing.get('parent')
            and backing.get('sharing', 'sharingNone') == 'sharingNone'
            and not backing.get('keyId') and type(backing.get('thinProvisioned')) is bool,
            'Only an explicit unencrypted unshared persistent base VMDK is supported')
        vm.reference(backing.get('datastore'), 'Datastore', 'datastore')
        identity = backing['datastore']['value']
        name, folder, filename = _disk_path(backing['fileName'])
        expected_uuid = _uuid(backing['uuid'])
        options = {'cursor': cursor} if cursor is not None else {}
        deadline = time.monotonic() + 120
        exchanges = 0

        def exchange(method, path, payload=None, *, response_type=dict):
            nonlocal exchanges
            require(exchanges < 40 and time.monotonic() < deadline,
                'The bounded original detached-backing observation is incomplete')
            exchanges += 1
            self.enrollment.require_current(**options)
            require(digest(read_private(self.ca_file)) == self.ca_sha256,
                'The commissioned source file-read TLS trust changed before native contact')
            session = self.credentials.acquire_session(self.enrollment, native_id=binding.native_id,
                datastore_id=identity, origin=self.credentials.profile.origin, ca_file=self.ca_file, cursor=cursor)
            client = CollectorClient(self.credentials.profile.origin, self.credentials.profile.origin,
                session.token, {path}, 'TaskManager', str(self.ca_file))
            seconds = min((session.expires_at - utcnow()).total_seconds(), deadline - time.monotonic())
            require(seconds > 0, 'The current detached-backing read credential expired')
            client.timeout = min(10, seconds); client.deadline = time.monotonic() + seconds
            result, _etag = client._request(method, path, payload, response_type=response_type)
            self.enrollment.require_current(**options)
            return result

        def search(browser, pattern, *, primary):
            details = dict(_typeName='FileQueryFlags', fileType=primary,
                fileSize=True, modification=True, fileOwner=False)
            spec = dict(_typeName='HostDatastoreBrowserSearchSpec', details=details,
                searchCaseInsensitive=False, matchPattern=[pattern], sortFoldersFirst=False)
            if primary:
                spec['query'] = [dict(_typeName='VmDiskFileQuery', details=dict(
                    _typeName='VmDiskFileQueryFlags', diskType=True, capacityKb=True,
                    hardwareVersion=False, diskExtents=True, thin=True, encryption=True))]
            reference = exchange('POST', vm.PREFIX + 'HostDatastoreBrowser/' + browser + '/SearchDatastore_Task',
                dict(datastorePath=folder, searchSpec=spec))
            vm.reference(reference, 'Task', 'task')
            for _ in range(10):
                info = exchange('GET', vm.PREFIX + 'Task/' + reference['value'] + '/info')
                vm.reference(info.get('task'), 'Task', 'task')
                require(info.get('_typeName') == 'TaskInfo' and info.get('key') == reference['value']
                    and info['task']['value'] == reference['value']
                    and info.get('state') in {'queued', 'running', 'success', 'error'}
                    and info.get('cancelled') is False, 'The native datastore search task identity or state changed')
                require(info['state'] != 'error' and not info.get('error'), 'The original native datastore search failed')
                if info['state'] == 'success':
                    require(c.timestamp(info['queueTime']) <= c.timestamp(info['startTime']) <=
                        c.timestamp(info['completeTime']) <= utcnow(), 'Native search task completion is incomplete')
                    result = info['result']
                    vm.reference(result.get('datastore'), 'Datastore', 'datastore')
                    require(result['datastore']['value'] == identity and result.get('folderPath') == folder
                        and result.get('_typeName') == 'HostDatastoreBrowserSearchResults'
                        and type(result.get('file')) is list and len(result['file']) == 1,
                        'The original native search did not return its sole exact datastore file')
                    row = result['file'][0]
                    require(type(row) is dict and row.get('path') == pattern
                        and type(row.get('fileSize')) is int and 0 < row['fileSize'] <= disk['capacityInBytes']
                        and c.timestamp(row['modification']) <= utcnow(),
                        'The retained native file is missing, replaced or has incomplete current units')
                    return row
                time.sleep(min(.1, max(0, deadline - time.monotonic())))
            raise ValueError('The original native datastore search remains incomplete; no resubmission')

        def sweep():
            summary = exchange('GET', vm.PREFIX + 'Datastore/' + identity + '/summary')
            require(summary.get('name') == name and summary.get('type') == 'VMFS'
                and summary.get('accessible') is True and summary.get('multipleHostAccess') is True
                and type(summary.get('capacity')) is int and summary['capacity'] >= disk['capacityInBytes']
                and type(summary.get('freeSpace')) is int and 0 <= summary['freeSpace'] <= summary['capacity'],
                'The original detached disk datastore is unavailable, renamed or unsupported')
            browser = exchange('GET', vm.PREFIX + 'Datastore/' + identity + '/browser')
            require(type(browser) is dict and browser.get('type') == 'HostDatastoreBrowser'
                and browser.get('_typeName', 'ManagedObjectReference') == 'ManagedObjectReference',
                'The exact native datastore browser is unavailable')
            c.identifier(browser['value'])
            native_uuid = exchange('POST', vm.PREFIX + 'VcenterVStorageObjectManager/' +
                self.vstorage_object_manager_id + '/QueryVirtualDiskUuidEx',
                dict(name=backing['fileName'], datacenter=dict(type='Datacenter',
                    value=self.enrollment.scope.native_scope_id)), response_type=str)
            require(_uuid(native_uuid) == expected_uuid, 'The actual detached file has another original disk UUID')
            primary = search(browser['value'], filename, primary=True)
            require(primary.get('_typeName') == 'VmDiskFileInfo'
                and primary.get('diskType') == 'VirtualDiskFlatVer2BackingInfo'
                and type(primary.get('capacityKb')) is int and primary['capacityKb'] == disk['capacityInKB']
                and primary.get('thin') is backing['thinProvisioned']
                and type(primary.get('encryption')) is dict
                and primary['encryption'].get('_typeName') == 'VmDiskEncryptionInfo'
                and not primary['encryption'].get('keyId')
                and primary.get('diskExtents') == [folder + filename[:-5] + '-flat.vmdk'],
                'The original retained disk capacity, format, encryption or flat extent changed')
            extent = search(browser['value'], filename[:-5] + '-flat.vmdk', primary=False)
            require(extent.get('_typeName') == 'FileInfo', 'The retained extent lacks exact current native file metadata')
            return dict(datastore_id=identity, datastore_name=name, datastore_capacity=summary['capacity'],
                native_uuid=expected_uuid, primary=primary, extent=extent)

        first, second = sweep(), sweep()
        require(first == second, 'The original detached backing changed during independent native observation')
        return second
