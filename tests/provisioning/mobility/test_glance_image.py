"""Actual TLS Keystone/Glance and sealed-file limits with synthetic SQL facts."""
from copy import deepcopy
from datetime import timedelta
import hashlib
import http.client
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.persistence import TenantContext
from provisioner.controlplane.reconciliation.planned import PlannedResourceLease
from provisioner.controlplane.reconciliation.planned_image import PlannedImageLease, image_input, image_phase_digest
from provisioner.controlplane.worker.vault_consumer import ConsumedVaultCredential
from provisioner.execution.run_files import digest, utcnow
from provisioner.migration.cold_authority import ColdImageAuthority
from provisioner.migration.cold_capture import ColdCaptureStore
from provisioner.migration.glance_image import _GlanceContact, image_metadata, image_facts, ImagePending
from provisioner.migration.resources import LinuxTransferResources
from tests.provisioning.mobility.cold_fixture import NativeTls, capture, selection, native_image, token
from provisioner.execution import readback_core as c


class _ReceiptFacts:
    def __init__(self):self.receipts=[]
    def retain_created(self,*values):self.receipts.append(values)
    def inputs(self,*values):return self.original_inputs
    def native_image(self,*values):return self.original_native_id


class _ImageCurrentPort(ColdImageAuthority):
    """Explicit SQL current-fact test port; native wire contacts remain real."""
    def __init__(self,cold,lease):
        self.cold,self.image_lease,self.phase=cold,lease,lease.phase;self.scope=lease.owner.scope
        self.claimed=True;self.revoked=False;self.current_calls=0;self.until=lease.owner.expires_at
        self.native_send_started=False
        self.row=cold.disk(lease.disk_id)['phases'][lease.phase];self.registry=_ReceiptFacts()
        self.command=SimpleNamespace(context=TenantContext(self.scope.organization_id,self.scope.tenant_id),
            identity=SimpleNamespace(subject=lease.owner.worker_id))
    def require_current(self):
        self.current_calls+=1
        if self.revoked:raise ValueError('Synthetic original B10 image grant revoked')
        return None,self.until


class GlanceWireTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.directory=Path(temporary.name)
        self.native=NativeTls();self.addCleanup(lambda:self.native.__exit__())
        self.cold=selection(self.directory,self.native.origin,digest(self.native.ca.read_bytes()))
        self.store=ColdCaptureStore(self.directory);body,_state=capture(self.store,self.cold);self.capture_sha=self.store.retain(body)
        self.inputs=image_input(self.cold,self.capture_sha,body,self.store,'disk-1-0')
        self.scope=PlanScope.from_record(self.cold.to_dict()['destination_scope'])
        owner=PlannedResourceLease(self.scope.organization_id,self.scope.tenant_id,'job-01','planned-image-0','image',
            'a'*64,'b'*64,'c'*64,self.scope,'workload-01','writer-01',1,utcnow()+timedelta(seconds=60))
        self.lease=PlannedImageLease(owner,'disk-1-0','CREATE','image-0-create',
            image_phase_digest(owner.request_digest,self.cold,'disk-1-0','CREATE'),self.capture_sha)
        self.current=_ImageCurrentPort(self.cold,self.lease)
        contact=self.cold.to_dict()['destination_contact']
        data={'environment':{},'cloud':{'clouds':{'cold':{'auth_type':'v3applicationcredential','verify':True,
            'region_name':contact['region'],'interface':contact['interface'],
            'auth':{'auth_url':contact['identity_endpoint'],'application_credential_id':'dynamic-app',
                'application_credential_secret':'synthetic-vault-native-secret'}}}}}
        self.material=ConsumedVaultCredential(data,self.current.until,'d'*64,'vault:synthetic-image-role')
        self.metadata=image_metadata(self.lease,self.inputs,self.cold)
        self.native_id='00000000-0000-0000-0000-000000000001'
        self.request_id='req-00000000-0000-0000-0000-000000000002'
        self.bind_originals()
        self.native.routes[('POST','/v3/auth/tokens')]={'status':201,'body':token(self.cold),
            'headers':[('X-Subject-Token','actual-synthetic-native-token')]}

    def contact(self):return _GlanceContact(self.current,self.cold,self.material,self.native.ca)

    def bind_originals(self):
        self.current.registry.original_inputs=self.inputs
        self.current.registry.original_native_id=self.native_id
        self.current.registry.leases=SimpleNamespace(captures=self.store)

    def test_real_native_project_member_auth_and_private_metadata_create_preserve_actual_uuid(self):
        self.native.routes[('POST','/v2/images')]={'status':201,'body':native_image(self.native_id,self.metadata),
            'headers':[('X-Openstack-Request-Id',self.request_id)]}
        contact=self.contact();native_id,request_id=contact.create(self.metadata)
        self.assertEqual((native_id,request_id),(self.native_id,self.request_id))
        self.assertEqual(self.current.registry.receipts,[
            (self.current.command.context,self.current.row['operation_id'],'writer-01',self.native_id,self.request_id)])
        create=self.native.requests[-1]
        self.assertEqual(c.strict_loads(create['body']),self.metadata)
        self.assertEqual(create['headers']['X-Auth-Token'],'actual-synthetic-native-token')
        self.assertEqual(self.metadata['visibility'],'private');self.assertTrue(self.metadata['protected'])
        self.assertNotIn('kernel_id',self.metadata);self.assertNotIn('locations',self.metadata)
        self.assertNotIn('synthetic-vault-native-secret',str(self.current.registry.receipts))

    def test_late_actual_uuid_is_retained_then_revocation_denies_acceptance_or_next_native_use(self):
        self.native.routes[('POST','/v2/images')]={'status':201,'body':{'id':self.native_id},
            'headers':[('X-Openstack-Request-Id',self.request_id)],
            'before_response':lambda:setattr(self.current,'revoked',True)}
        contact=self.contact()
        with self.assertRaisesRegex(ValueError,'revoked'):contact.create(self.metadata)
        self.assertEqual(self.current.registry.receipts[-1][-2:],(self.native_id,self.request_id))
        before=len(self.native.requests)
        with self.assertRaises(ValueError):contact.get(self.native_id)
        self.assertEqual(len(self.native.requests),before)

    def test_bad_native_project_admin_reader_catalog_or_duplicate_role_never_reaches_create(self):
        for change in (
            lambda value:value['token']['project'].update(id='foreign-project'),
            lambda value:value['token'].update(roles=[{'name':'admin'}]),
            lambda value:value['token'].update(roles=[{'name':'reader'}]),
            lambda value:value['token']['roles'].append({'name':'member'}),
            lambda value:value['token']['catalog'][0]['endpoints'][0].update(url='https://foreign.invalid/v2'),
            lambda value:value['token'].update(system={'all':True}),
        ):
            value=token(self.cold);change(value)
            self.native.routes[('POST','/v3/auth/tokens')]['body']=value
            with self.subTest(change=change),self.assertRaises(ValueError):self.contact()
        self.assertEqual({row['path'] for row in self.native.requests},{'/v3/auth/tokens'})
        self.assertFalse(self.current.registry.receipts)

    def test_ambiguous_framing_duplicate_native_uuid_or_request_header_never_retains_receipt(self):
        contact=self.contact()
        for spec in (
            {'status':201,'body':{'id':self.native_id},'headers':[
                ('X-Openstack-Request-Id',self.request_id),('X-Openstack-Request-Id',self.request_id)]},
            {'status':201,'body':{'id':self.native_id},'headers':[
                ('X-Openstack-Request-Id',self.request_id),('Content-Length','1')]},
            {'status':201,'raw':b'{"id":"'+self.native_id.encode()+b'","id":"'+self.native_id.encode()+b'"}',
                'headers':[('X-Openstack-Request-Id',self.request_id)]},
            {'status':201,'body':{'id':'invented-image-name'},'headers':[('X-Openstack-Request-Id',self.request_id)]},
            {'status':201,'body':{'id':self.native_id},'headers':[('X-Openstack-Request-Id','unknown')]},
        ):
            self.current.native_send_started=False  # Each shape has isolated synthetic SQL intent facts.
            self.native.routes[('POST','/v2/images')]=spec
            with self.subTest(spec=spec),self.assertRaises((ValueError,http.client.HTTPException)):contact.create(self.metadata)
        self.assertEqual(self.current.registry.receipts,[])

    def test_native_uuid_project_status_private_digest_extent_and_secure_hash_are_exact(self):
        queued=native_image(self.native_id,self.metadata)
        self.assertEqual(image_facts(queued,self.native_id,self.scope,self.metadata,self.inputs,'CREATE')['status'],'queued')
        active=native_image(self.native_id,self.metadata,inputs=self.inputs)
        self.assertEqual(image_facts(active,self.native_id,self.scope,self.metadata,self.inputs,'UPLOAD')['os_hash_algo'],'sha512')
        active.update(os_hash_algo='sha256',os_hash_value=self.inputs['output_sha256'])
        image_facts(active,self.native_id,self.scope,self.metadata,self.inputs,'UPLOAD')
        for change in (
            lambda value:value.update(id='00000000-0000-0000-0000-000000000009'),
            lambda value:value.update(owner='foreign-project'),
            lambda value:value.update(visibility='public'),
            lambda value:value.update(hosting_source_capture_digest='f'*64),
            lambda value:value.update(os_hash_algo='md5',os_hash_value='a'*32),
            lambda value:value.update(os_hash_value='f'*64),
            lambda value:value.update(size=True),
            lambda value:value.update(virtual_size=1),
            lambda value:value.pop('virtual_size'),
            lambda value:value.update(kernel_id='foreign-kernel'),
            lambda value:value.update(direct_url='https://foreign.invalid/disk'),
            lambda value:value.update(locations=[{'url':'https://foreign.invalid/disk'}]),
        ):
            changed=deepcopy(active);change(changed)
            with self.subTest(change=change),self.assertRaises(ValueError):image_facts(changed,self.native_id,self.scope,self.metadata,self.inputs,'UPLOAD')
        for status in ('queued','saving'):
            with self.assertRaises(ImagePending):image_facts(active|{'status':status},self.native_id,self.scope,self.metadata,self.inputs,'UPLOAD')

    def upload_phase(self):
        from dataclasses import replace
        self.lease=replace(self.lease,phase='UPLOAD',step_id='image-0-upload',
            request_digest=image_phase_digest(self.lease.owner.request_digest,self.cold,'disk-1-0','UPLOAD'))
        self.current=_ImageCurrentPort(self.cold,self.lease)
        self.bind_originals()
        return self.contact()

    def test_native_upload_sends_only_original_sealed_bytes_under_its_separate_action(self):
        contact=self.upload_phase();path,_converted=self.store.image(self.capture_sha,self.cold,'disk-1-0')
        self.native.routes[('PUT','/v2/images/'+self.native_id+'/file')]={'status':204,'raw':b''}
        resources=self.cold.transfer_resources()
        with patch.object(LinuxTransferResources,'require_current'):
            contact.upload(self.native_id,path,self.inputs,resources)
        uploaded=self.native.requests[-1]
        self.assertEqual(uploaded['method'],'PUT');self.assertEqual(uploaded['body'],path.read_bytes())
        self.assertEqual(uploaded['headers']['Content-Type'],'application/octet-stream')
        self.assertEqual(uploaded['headers']['Content-Length'],str(self.inputs['output_bytes']))
        self.assertEqual(uploaded['headers']['X-Openstack-Image-Size'],str(self.inputs['output_bytes']))
        self.assertNotIn('X-Vault-Token',uploaded['headers']);self.assertEqual(self.current.registry.receipts,[])

    def test_native_upload_late_revocation_ambiguous_response_or_changed_bytes_is_held(self):
        contact=self.upload_phase();path,_converted=self.store.image(self.capture_sha,self.cold,'disk-1-0')
        resources=self.cold.transfer_resources()
        current_io=patch.object(LinuxTransferResources,'require_current');current_io.start();self.addCleanup(current_io.stop)
        route=('PUT','/v2/images/'+self.native_id+'/file')
        self.native.routes[route]={'status':204,'raw':b'','before_response':lambda:setattr(self.current,'revoked',True)}
        with self.assertRaisesRegex(ValueError,'revoked'):contact.upload(self.native_id,path,self.inputs,resources)
        self.assertEqual(len([row for row in self.native.requests if row['method']=='PUT']),1)
        before=len(self.native.requests)
        with self.assertRaises(ValueError):contact.upload(self.native_id,path,self.inputs,resources)
        self.assertEqual(len(self.native.requests),before)
        self.current.revoked=False
        self.current.native_send_started=False  # A separate synthetic original attempt for this framing case.
        self.native.routes[route]={'status':204,'raw':b'','headers':[('Transfer-Encoding','chunked')]}
        with self.assertRaises(ValueError):contact.upload(self.native_id,path,self.inputs,resources)
        self.current.native_send_started=False
        self.native.routes[route]={'status':204,'raw':b''}
        before=len(self.native.requests)
        with self.assertRaisesRegex(ValueError,'original accepted image'):
            contact.upload(self.native_id,path,self.inputs|{'output_sha256':'f'*64},resources)
        self.assertEqual(len(self.native.requests),before)

    def test_wrong_phase_unsealed_extent_or_host_trust_denies_before_native_image_contact(self):
        contact=self.contact();path,_converted=self.store.image(self.capture_sha,self.cold,'disk-1-0')
        before=len(self.native.requests)
        with self.assertRaises(ValueError):contact.upload(self.native_id,path,self.inputs,object())
        self.assertEqual(len(self.native.requests),before)
        contact=self.upload_phase();path.chmod(0o600);before=len(self.native.requests)
        with self.assertRaisesRegex(ValueError,'sealed'):contact.upload(self.native_id,path,self.inputs,self.cold.transfer_resources())
        self.assertEqual(len(self.native.requests),before)
        foreign=deepcopy(self.material.data);foreign['environment']={'TF_HTTP_PASSWORD':'foreign-secret'}
        with self.assertRaises(ValueError):_GlanceContact(self.current,self.cold,
            ConsumedVaultCredential(foreign,self.material.expires_at,self.material.lease_digest,self.material.role_reference),self.native.ca)
        self.assertEqual(len(self.native.requests),before)


if __name__=='__main__':unittest.main()
