"""Real TLS/native routes and independent completion contracts; no live evidence."""
from copy import deepcopy
from dataclasses import asdict
from datetime import timedelta
import hashlib
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.reconciliation import NativeOperation
from provisioner.controlplane.reconciliation.read_enrollment import NativeReadEnrollment
from provisioner.controlplane.worker.grants import CredentialBroker
from provisioner.controlplane.worker.vault import VaultDynamicCredentialIssuer, VaultDynamicRole
from provisioner.controlplane.worker.vault_consumer import VaultCredentialConsumer
from provisioner.execution import readback_core as c, vsphere_observe as vm
from provisioner.execution.run_files import digest, encoded, utcnow, write_new
from provisioner.migration.cold_authority import ColdExportAuthority
from provisioner.migration.cold_capture import (
    ColdCaptureStore, VsphereColdCapture, VsphereExportReadbackOwner, _VsphereContact, _ca,
)
from provisioner.migration.cold_selection import ColdVmSelection
from provisioner.migration.resources import LinuxTransferResources
from provisioner.migration.vsphere_credentials import VsphereNativeCredentialOwner, VsphereNativeCredentialProfile, NativeVsphereSession
from tests.provisioning.mobility.cold_fixture import NativeTls, capture, selection
from tests.provisioning.worker.test_command_runtime import _Fixture
from provisioner.controlplane.jobs.repository import _digest
from tests.test_vsphere_observe import ref


class _ExportCurrentPort(ColdExportAuthority):
    """Explicit synthetic current SQL fact port for transport tests only."""
    def __init__(self,cold):
        self.cold=cold;self.scope=PlanScope.from_record(cold.to_dict()['source_scope'])
        self.claimed=True;self.revoked=False;self.calls=0;self.accepted_handles=[]
        self.native_send_started=False;self.native_lease_id=None
        self.command=SimpleNamespace()
        self.until=utcnow()+timedelta(seconds=60)
    def require_current(self):
        self.calls+=1
        if self.revoked:raise ValueError('Synthetic B10 revocation between actual native exchanges')
        return None,self.until
    def accepted(self,handle):self.accepted_handles.append(handle);self.native_lease_id=handle


class _CredentialsPort(VsphereNativeCredentialOwner):
    """Bounded credential facts; the shared owner's native enrollment has its own tests."""
    def __init__(self,command,profile):
        object.__setattr__(self,'commands',command);object.__setattr__(self,'profile',profile)
        object.__setattr__(self,'calls',[])
    def acquire_session(self,authority,**arguments):
        self.calls.append(arguments);_grant,deadline=authority.require_current()
        return NativeVsphereSession('dynamic-native-session',deadline)


class ColdWireTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.directory=Path(temporary.name)
        self.native=NativeTls();self.addCleanup(lambda:self.native.__exit__())
        self.cold=selection(self.directory,self.native.origin,digest(self.native.ca.read_bytes()))
        self.current=_ExportCurrentPort(self.cold)
        self.credentials=_CredentialsPort(self.current.command,
            VsphereNativeCredentialProfile(**self.cold.to_dict()['source_contact']['writer_credential_profile']))

    def contact(self):return _VsphereContact(self.current,self.cold,self.credentials,self.native.ca)

    def source_routes(self):
        value=self.cold.to_dict()['vm']
        for kind,moid,key,body in (
            ('VirtualMachine','vm-1','config',value['current_config']),
            ('VirtualMachine','vm-1','runtime',value['runtime']),
            ('VirtualMachineSnapshot','snapshot-1','config',value['snapshot_config']),
            ('VirtualMachineSnapshot','snapshot-1','vm',ref('VirtualMachine','vm-1')),
        ):self.native.routes[('GET',vm.PREFIX+kind+'/'+moid+'/'+key)]={'body':body}

    def test_selected_native_lineage_and_fixed_snapshot_export_are_actual_tls_contacts(self):
        self.source_routes()
        route=vm.PREFIX+'VirtualMachineSnapshot/snapshot-1/ExportSnapshot'
        self.native.routes[('POST',route)]={'body':ref('HttpNfcLease','nfclease-1')}
        contact=self.contact();state=contact.source_state();handle=contact.export()
        self.assertEqual(handle,'nfclease-1');self.assertEqual(self.current.accepted_handles,['nfclease-1'])
        self.assertEqual(len(state),3)
        self.assertTrue(all(request['headers'].get('vmware-api-session-id')=='dynamic-native-session'
                            for request in self.native.requests))
        self.assertFalse(any('ExportVm' in row['path'] for row in self.native.requests))
        self.assertEqual(self.native.requests[-1]['body'],b'')
        self.assertEqual(len(self.credentials.calls),5)
        self.current.revoked=True;before=len(self.native.requests)
        with self.assertRaises(ValueError):contact.source_state()
        self.assertEqual(len(self.native.requests),before)

    def test_late_genuine_handle_is_retained_before_next_current_check_denies(self):
        route=vm.PREFIX+'VirtualMachineSnapshot/snapshot-1/ExportSnapshot'
        self.native.routes[('POST',route)]={'body':ref('HttpNfcLease','nfclease-2'),
            'before_response':lambda:setattr(self.current,'revoked',True)}
        with self.assertRaisesRegex(ValueError,'revocation'):self.contact().export()
        self.assertEqual(self.current.accepted_handles,['nfclease-2'])
        self.assertEqual(len(self.native.requests),1)

    def test_changed_complete_hardware_encryption_or_snapshot_vm_blocks_capture(self):
        for change in (
            lambda body:body['hardware']['device'].append({'_typeName':'VirtualTPM','key':9000}),
            lambda body:body.update(keyId={'keyId':'encrypted'}),
            lambda body:body['hardware']['device'][1]['backing'].update(uuid='another-current-disk'),
        ):
            self.source_routes();route=vm.PREFIX+'VirtualMachine/vm-1/config'
            body=deepcopy(self.native.routes[('GET',route)]['body']);change(body)
            self.native.routes[('GET',route)]={'body':body}
            with self.subTest(change=change),self.assertRaises(ValueError):self.contact().source_state()
        self.source_routes()
        self.native.routes[('GET',vm.PREFIX+'VirtualMachineSnapshot/snapshot-1/vm')]={'body':ref('VirtualMachine','vm-9')}
        with self.assertRaises(ValueError):self.contact().source_state()

    def test_checksum_and_completion_routes_have_exact_bodies_and_no_native_retry(self):
        contact=self.contact()
        self.current.native_lease_id='nfclease-1'
        for action in ('HttpNfcLeaseSetManifestChecksumType','HttpNfcLeaseProgress','HttpNfcLeaseComplete'):
            self.native.routes[('POST',vm.PREFIX+'HttpNfcLease/nfclease-1/'+action)]={'status':204,'raw':b''}
        contact.checksums('nfclease-1',{'nfc-disk-1','nfc-disk-0'});contact.progress('nfclease-1',50);contact.complete('nfclease-1')
        self.assertEqual(c.strict_loads(self.native.requests[0]['body']),{'deviceUrlsToChecksumTypes':[
            {'key':'nfc-disk-0','value':'sha256'},{'key':'nfc-disk-1','value':'sha256'}]})
        self.assertEqual(c.strict_loads(self.native.requests[1]['body']),{'percent':50})
        self.assertEqual(self.native.requests[2]['body'],b'')
        with self.assertRaises(ValueError):contact._exchange('VirtualMachine','vm-1','Destroy_Task',method='POST')
        self.assertEqual(len(self.native.requests),3)

    def test_nfc_tls_download_does_not_forward_vcenter_or_vault_authentication(self):
        data=b'stream optimized native VMDK bytes';target='/nfc/native/disk?ticket=opaque-native-ticket'
        self.native.routes[('GET',target)]={'raw':data,'type':'application/x-vnd.vmware-streamvmdk'}
        owner=object.__new__(VsphereColdCapture);owner.authority=self.current
        contact=self.contact();row=self.cold.disk('disk-1-0')
        from cryptography.hazmat.primitives.serialization import Encoding
        from cryptography import x509
        leaf=x509.load_pem_x509_certificate((self.native.pki.root/'server.pem').read_bytes()).public_bytes(Encoding.DER)
        with patch.object(LinuxTransferResources,'require_current'):
            captured=owner._download(contact,'nfclease-1',self.native.origin+target,hashlib.sha256(leaf).hexdigest(),
                row,self.directory/'original.vmdk',_ca(self.native.ca,digest(self.native.ca.read_bytes())),0)
        self.assertEqual(captured,{'sourceSha256':digest(data),'inputBytes':len(data)})
        request=self.native.requests[-1]
        for field in ('Authorization','vmware-api-session-id','X-Auth-Token','X-Vault-Token','Cookie'):
            self.assertNotIn(field,request['headers'])
        self.assertEqual((self.directory/'original.vmdk').stat().st_mode&0o777,0o400)

    def test_nfc_wrong_certificate_redirect_ambiguous_extent_or_truncation_is_held(self):
        owner=object.__new__(VsphereColdCapture);owner.authority=self.current;row=self.cold.disk('disk-1-0')
        tls=_ca(self.native.ca,digest(self.native.ca.read_bytes()))
        for number,spec in enumerate(({'raw':b'bytes','type':'application/octet-stream','length':9},
            {'raw':b'bytes','type':'application/octet-stream','headers':[('Content-Length','5')]},
            {'status':302,'raw':b'','headers':[('Location','https://foreign.invalid/nfc/a')]},
            {'raw':b'bytes','type':'application/octet-stream','headers':[('Content-Encoding','gzip')]})):
            target='/nfc/native/'+str(number);self.native.routes[('GET',target)]=spec
            with self.subTest(spec=spec),patch.object(LinuxTransferResources,'require_current'),self.assertRaises((ValueError,OSError)):
                owner._download(self.contact(),'nfclease-1',self.native.origin+target,'',row,
                    self.directory/(str(number)+'.vmdk'),tls,0)
        self.native.routes[('GET','/nfc/cert')]={'raw':b'bytes','type':'application/octet-stream'}
        with self.assertRaisesRegex(ValueError,'certificate'):
            owner._download(self.contact(),'nfclease-1',self.native.origin+'/nfc/cert','f'*64,row,
                self.directory/'cert.vmdk',tls,0)
        self.assertFalse((self.directory/'cert.vmdk').exists())


class IndependentCompletionTests(_Fixture):
    def setUp(self):
        super().setUp()
        from dataclasses import replace
        self.source=replace(self.source,native_scope_id='datacenter-1')
        self.grant=replace(self.grant,source=self.source)
        self.select()
        body=selection(self.root).to_dict()
        fields=('organizationId','tenantId','locationId','securityDomainId','endpointId','nativeScopeId','platformFamily')
        body['source_scope']=dict(zip(fields,vars(self.source).values()))
        body['destination_scope']=dict(zip(fields,vars(self.destination).values()))
        self.cold=ColdVmSelection.from_record(body)
        self.grant=replace(self.grant,operation_scope=self.source);self.select()
        token_file=self.root/'vault-token';write_new(token_file,b'synthetic-private-vault-token')
        issuer=VaultDynamicCredentialIssuer(vault_url='https://vault.example.invalid',ca_bundle=self.pki.root/'ca.pem',
            agent_token_file=token_file,roles=(VaultDynamicRole('vault:synthetic-native-reader',
                'native/creds/synthetic-native-reader',self.source,'DISCOVER_READ',timedelta(seconds=60)),))
        self.enrollment=NativeReadEnrollment(self.runtime,self.admitted,_digest(self.selection),
            CredentialBroker(self.verifier,self.grants,issuer),VaultCredentialConsumer(issuer))
        self.store=ColdCaptureStore(self.root);self.body,self.source_state=capture(self.store,self.cold)
        self.evidence=self.root/'native-evidence';self.evidence.mkdir(mode=0o700)
        credentials=_CredentialsPort(self.runtime,
            VsphereNativeCredentialProfile(**self.cold.to_dict()['source_contact']['reader_credential_profile']))
        self.reader=VsphereExportReadbackOwner(enrollment=self.enrollment,credentials=credentials,cold=self.cold,store=self.store,
            ca_bundle=self.pki.root/'ca.pem',evidence_directory=self.evidence,
            exclusion_owner=SimpleNamespace(verify_owner_exclusion=lambda *args:None))
        fixture=self
        class Contact:
            state='ready';manifest_calls=0;changed=False
            def lease_state(self,lease):
                fixture.assertEqual(lease,'nfclease-1');return self.state
            def source_state(self):return {'changed-native-config':True} if self.changed else fixture.source_state
            def manifest(self,lease):
                fixture.assertEqual(self.state,'ready','GetManifest contacted a completed invalid native lease')
                self.manifest_calls+=1;return fixture.body['nativeManifest']
        self.contact=Contact()
        self.patch=patch.object(self.reader,'_contact',return_value=self.contact);self.patch.start();self.addCleanup(self.patch.stop)

    def finish(self):
        ready=self.reader.retain_ready('nfclease-1',self.body['disks'],self.body['nativeManifest'],self.source_state)
        self.body['readyObservationDigest']=ready;self.contact.state='done'
        return self.store.retain(self.body)

    def test_ready_manifest_is_retained_before_complete_then_only_completion_is_read(self):
        sha=self.finish();observed=self.reader.observe(sha)
        operation=NativeOperation(self.cold.to_dict()['export']['operation_id'],self.admitted.job_id,'grant-writer',
            'export-01','lease-writer',self.cold.binding(),self.cold.to_dict()['workload_id'],self.source.security_domain_id,
            'another-writer',2,'SNAPSHOT_EXPORT','a'*64,'IN_FLIGHT','nfclease-1',None)
        with patch.object(NativeReadEnrollment,'require_current',return_value=(self.grant,self.grant.expires_at)):
            self.reader.verify_native_observation(object(),operation,observed)
        self.assertEqual(self.contact.manifest_calls,1)
        self.assertEqual((observed.outcome,observed.native_quiesced),('EFFECT_PRESENT',True))
        self.assertEqual(observed.observer_subject,self.identity.subject)
        self.assertFalse(self.store.load_verified(sha,self.cold)['guestBootQualified'])

    def test_missing_ready_native_evidence_or_changed_source_cannot_complete_original(self):
        sha=self.finish();self.contact.changed=True
        with self.assertRaisesRegex(ValueError,'source configuration'):self.reader.observe(sha)
        self.contact.changed=False;(self.evidence/(self.body['readyObservationDigest']+'.json')).unlink()
        with self.assertRaises(FileNotFoundError):self.reader.observe(sha)
        self.assertEqual(self.contact.manifest_calls,1)


if __name__=='__main__':unittest.main()
