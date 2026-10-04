"""Native snapshot/disk identity and retained byte custody, not boot evidence."""
from copy import deepcopy
import os
from pathlib import Path
import tempfile
import unittest

from provisioner.domain.enterprise_records import plan_digest
from provisioner.execution import readback_core as c
from provisioner.execution.run_files import encoded, write_new
from provisioner.migration.cold_capture import ColdCaptureStore, _native_manifest, nfc_target
from provisioner.migration.cold_selection import ColdVmSelection, DRIVER, FileColdSelectionStore, backing_chain
from tests.provisioning.mobility.cold_fixture import capture, selection
from tests.provisioning.schema.test_enterprise_records import plan


class ColdSelectionTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.directory=Path(temporary.name);self.cold=selection(self.directory)

    def test_exact_native_snapshot_parent_chain_and_all_disks_are_retained(self):
        value=self.cold.to_dict()
        disks=[row for row in value['vm']['snapshot_config']['hardware']['device'] if row['_typeName']=='VirtualDisk']
        self.assertEqual(len(disks),2)
        for disk in disks:
            chain=backing_chain(disk['backing'])
            self.assertEqual(len(chain),2);self.assertEqual(chain[0]['type'],'VirtualDiskSeSparseBackingInfo')
            self.assertEqual(chain[-1]['type'],'VirtualDiskFlatVer2BackingInfo')
            self.assertNotEqual(chain[0]['uuid'],chain[-1]['uuid'])
        value['disks'][0]['nfc_key']='changed-after-load'
        self.assertNotEqual(value,self.cold.to_dict())
        write_new(self.directory/(self.cold.sha256+'.json'),encoded(self.cold.to_dict()))
        self.assertEqual(FileColdSelectionStore(self.directory).load_verified(self.cold.sha256),self.cold)

    def test_hardware_unknown_encrypted_shared_cyclic_missing_lineage_or_partial_disks_hold(self):
        mutations=(
            lambda value:value['vm']['snapshot_config'].update(keyId={'keyId':'encrypted'}),
            lambda value:value['vm']['snapshot_config']['hardware']['device'].append({'_typeName':'VirtualTPM','key':9000}),
            lambda value:value['vm']['snapshot_config']['hardware']['device'][0].update(sharedBus='physicalSharing'),
            lambda value:value['vm']['snapshot_config']['hardware']['device'][1]['backing'].update(sharing='sharingMultiWriter'),
            lambda value:value['vm']['snapshot_config']['hardware']['device'][1]['backing']['parent'].pop('uuid'),
            lambda value:value['vm']['snapshot_config']['hardware']['device'][1]['backing'].update(parent=None),
            lambda value:value['vm']['snapshot_config']['hardware']['device'][1]['backing']['parent'].update(
                fileName=value['vm']['snapshot_config']['hardware']['device'][1]['backing']['fileName']),
            lambda value:value['vm']['snapshot_config']['hardware']['device'][1].update(capacityInKB=1),
            lambda value:value['vm']['runtime'].update(powerState='poweredOn'),
            lambda value:value['vm']['runtime'].pop('consolidationNeeded'),
            lambda value:value['disks'].pop(),
        )
        for mutate in mutations:
            body=self.cold.to_dict();mutate(body)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):ColdVmSelection.from_record(body)

    def test_no_scope_disk_intent_extent_or_additive_resource_inheritance(self):
        for mutate in (
            lambda value:value['destination_scope'].update(tenantId='foreign-tenant'),
            lambda value:value['source_scope'].update(platformFamily='openstack'),
            lambda value:value['disks'][1].update(nfc_key=value['disks'][0]['nfc_key']),
            lambda value:value['disks'][1].update(device_key=value['disks'][0]['device_key']),
            lambda value:value['disks'][0]['phases']['CREATE'].update(operation_id=value['export']['operation_id']),
            lambda value:value['capture_resources']['limits'].update(expected_bytes=1),
            lambda value:value['sandbox']['tools'].update(qemu_img='qemu-img'),
            lambda value:value['source_contact']['nfc_origins'].append('http://host.invalid'),
        ):
            body=self.cold.to_dict();mutate(body)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):ColdVmSelection.from_record(body)

    def test_exact_plan_digest_route_and_native_mapping_cannot_be_changed(self):
        body=self.cold.to_dict();approved=plan(source=body['source_scope'],target=body['destination_scope'])
        for mapping in approved['spec']['machineMappings']:
            mapping['sourceBinding']['nativeScopeId']=body['source_scope']['nativeScopeId']
        approved['spec']['route'].update(method='COLD_VM_CONVERSION',guestProfile=body['guest_profile'])
        approved['spec']['selectedMachineIds']=['machine-1']
        approved['spec']['machineMappings']=approved['spec']['machineMappings'][:1]
        approved['spec']['selectedDatasetIds']=[]; approved['spec']['datasetMappings']=[]
        approved['spec']['coldCapture']={'format':'hosting-cold-capture-purpose/1','selectionDigest':self.cold.sha256}
        approved['spec']['execution']={'format':'hosting-execution-selection/1',
                                      'driver':DRIVER,'artifactDigest':'f'*64}
        approved['metadata']['planDigest']=plan_digest(approved)
        artifact={'driver':DRIVER,'coldCaptureSelectionDigest':self.cold.sha256,'resourceBundleDigest':body['resource_bundle_sha256']}
        self.cold.require_plan(approved,artifact)
        for change in (
            lambda value:value['spec']['machineMappings'][0]['sourceBinding'].update(nativeId='vm-9'),
            lambda value:value['spec']['machineMappings'][0]['diskMappings'].pop(),
            lambda value:value['spec']['route'].update(guestProfile='windows-server-2022'),
            lambda value:value['spec'].update(sourceSnapshotId='newer-unapproved-snapshot'),
        ):
            changed=deepcopy(approved);change(changed);changed['metadata']['planDigest']=plan_digest(changed)
            with self.subTest(change=change),self.assertRaises(ValueError):self.cold.require_plan(changed,artifact)
        with self.assertRaises(ValueError):self.cold.require_plan(approved,artifact|{'resourceBundleDigest':'f'*64})

    def test_only_exact_canonical_schema_and_supported_capture_guest_profile(self):
        body=self.cold.to_dict();body['guest_profile']='windows-server-2022'
        self.assertEqual(ColdVmSelection.from_record(body).to_dict()['guest_profile'],'windows-server-2022')
        body['guest_profile']='generic-windows'
        with self.assertRaises(ValueError):ColdVmSelection.from_record(body)
        with self.assertRaises(ValueError):ColdVmSelection(self.cold.canonical.rstrip())
        body=self.cold.to_dict();body['import_defaults']={}
        with self.assertRaises(ValueError):ColdVmSelection.from_record(body)

    def test_nfc_ticket_only_uses_selected_https_origins_and_native_route(self):
        origin='https://vcenter.example.invalid'
        self.assertEqual(nfc_target('https://*/nfc/opaque/disk?ticket=opaque',[origin],origin),
            (origin,'/nfc/opaque/disk?ticket=opaque'))
        for url in ('https://foreign.invalid/nfc/a','https://user:pass@vcenter.example.invalid/nfc/a',
            'http://vcenter.example.invalid/nfc/a','https://vcenter.example.invalid/nfc/../secrets',
            'https://vcenter.example.invalid/nfc/%2e%2e/a','https://vcenter.example.invalid/nfc/a#fragment',
            'https://vcenter.example.invalid/elsewhere/a','https://vcenter.example.invalid/nfc/a\r\nX:bad'):
            with self.subTest(url=url),self.assertRaises(ValueError):nfc_target(url,[origin],origin)


class RetainedColdBytesTests(unittest.TestCase):
    def setUp(self):
        ColdSelectionTests.setUp(self)
        self.store=ColdCaptureStore(self.directory);self.body,_source=capture(self.store,self.cold)
        self.sha=self.store.retain(self.body)

    def test_native_sha256_and_virtual_extent_binding_include_every_disk(self):
        self.assertEqual(self.store.load_verified(self.sha,self.cold),self.body)
        path,converted=self.store.image(self.sha,self.cold,'disk-1-0')
        self.assertEqual(path.stat().st_mode&0o777,0o400)
        self.assertFalse(converted['guestBootQualified']);self.assertFalse(converted['nativeContact'])
        for mutate in (
            lambda rows:rows[0].update(checksumType='sha1'),
            lambda rows:rows[0].update(checksum='f'*64),
            lambda rows:rows[0].update(capacity=1),
            lambda rows:rows[0].update(size=1),
            lambda rows:rows.append(deepcopy(rows[0])),
        ):
            manifest=deepcopy(self.body['nativeManifest']);mutate(manifest)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):_native_manifest(manifest,self.cold,self.body['disks'])

    def test_writable_tampered_hardlinked_or_path_escaped_originals_never_supply_image(self):
        row=self.body['disks']['disk-1-0'];path=self.directory/row['inputPath']
        path.chmod(0o600)
        with self.assertRaisesRegex(ValueError,'sealed'):self.store.load_verified(self.sha,self.cold)
        path.chmod(0o400);os.link(path,self.directory/'alias')
        with self.assertRaisesRegex(ValueError,'sealed'):self.store.load_verified(self.sha,self.cold)
        (self.directory/'alias').unlink();path.chmod(0o600);path.write_bytes(b'changed');path.chmod(0o400)
        with self.assertRaises(ValueError):self.store.load_verified(self.sha,self.cold)
        with self.assertRaises(ValueError):self.store._file('../outside','a'*64,1,2)

    def test_conversion_virtual_size_toolchain_or_guest_success_cannot_be_forged(self):
        for change in (
            lambda value:value['disks']['disk-1-0']['conversion'].update(virtualSize=1),
            lambda value:value['disks']['disk-1-0']['conversion']['toolchain'].update(qemu_img_sha256='f'*64),
            lambda value:value['disks']['disk-1-0']['conversion'].update(guestBootQualified=True),
            lambda value:value['disks'].pop('disk-1-0'),
        ):
            changed=deepcopy(self.body);change(changed);sha=c.digest(changed)
            write_new(self.directory/(sha+'.json'),encoded(changed))
            with self.subTest(change=change),self.assertRaises(ValueError):self.store.load_verified(sha,self.cold)


if __name__=='__main__':unittest.main()
