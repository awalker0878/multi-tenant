"""Fixed Windows selection and actual TLS/SOAP composition; synthetic DB.

These are scoped protocol/selection regressions, never native Windows or
PostgreSQL commissioning evidence.
"""
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import timedelta
import unittest

from provisioner.controlplane.jobs.repository import _digest
from provisioner.controlplane.reconciliation.read_enrollment import NativeReadEnrollment
from provisioner.controlplane.worker.grants import CredentialBroker
from provisioner.controlplane.worker.vault import VaultDynamicCredentialIssuer, VaultDynamicRole
from provisioner.controlplane.worker.vault_consumer import VaultCredentialConsumer
from provisioner.controlplane.worker.windows_commands import ScopedWindowsGuestRuntime
from provisioner.controlplane.worker.windows_services import ScopedWindowsServiceReadRuntime
from provisioner.controlplane.worker.windows_service_activity import WindowsServiceActivities, WindowsServiceRuntimeBindings
from provisioner.controlplane.workflow.windows_service_job import WindowsServiceInput, WindowsServiceStageRequest
from provisioner.controlplane.workflow.windows_service_selection import (FORMAT,DRIVER,PLAN_FORMAT,SELECTION_FORMAT,
    METHOD,WindowsServiceSelection,WindowsOriginalServiceIntent,validate_artifact)
from provisioner.execution.run_files import encoded, load_private, write_new
from provisioner.execution.windows_guest import WindowsGuestSelection
from tests.provisioning.worker.test_windows_services import _WindowsOriginalFixture
from tests.provisioning.worker.test_command_runtime import ROOT


def purpose(native,writer_digest,reader_digest,ca_digest):
    return dict(format=SELECTION_FORMAT,action='CONFIGURE_AND_OBSERVE',machineId='target-01',nativeBinding=native,
        writerSelectionDigest=writer_digest,readerSelectionDigest=reader_digest,originalSelectionDigest=writer_digest,
        caDigest=ca_digest,write={'stepId':'windows-configure','operationId':'configure-operation','kind':'windows_guest_apply'},
        read={'stepId':'windows-observe','operationId':'observe-operation','kind':'windows_guest_observe'},original=None)


class WindowsServicePurposeTests(_WindowsOriginalFixture):
    def setUp(self):
        super().setUp()
        self.source=self.destination
        self.grant=replace(self.grant,source=self.destination,step_id='windows-configure',operation_id='configure-operation')
        self.grants.grant=self.grant; self.runtime=replace(self.runtime,grant=self.grant)
        writer=self.descriptor; reader=WindowsGuestSelection.from_record(deepcopy(self.record) | {
            'mapped_user':r'WINHOST\read-user','certificate_subject':'CN=owned-read-winrm','certificate_upn':'read-user@localhost'})
        self.writer_record=deepcopy(self.record); self.writer_descriptor=writer; self.reader_descriptor=reader
        self.reader_path=self.root/'independent-reader.json'; write_new(self.reader_path,reader.canonical)
        self.purpose=WindowsServiceSelection.from_record(purpose(self.record['native_binding'],writer.sha256,reader.sha256,
            self.record['ca_sha256']))
        self.delivery=dict(format='hosting-delivery/2',source_commit='a'*40,operation_id='service-delivery',generation=1,
            reviewed_plan_digest='c'*64,scope=self.scope,steps=[
                {'id':'windows-configure','kind':'windows_guest_apply','needs':[]},
                {'id':'windows-observe','kind':'windows_guest_observe','needs':['windows-configure']}],
            operation_bindings={},reviewed_parameters={},compiled_catalog_ids={})
        record=lambda scope:dict(zip(('organizationId','tenantId','locationId','securityDomainId','endpointId',
                                     'nativeScopeId','platformFamily'),vars(scope).values()))
        self.selection=dict(format=FORMAT,driver=DRIVER,sourceCommit='a'*40,workloadId='workload-01',workloadRevision=1,
            source=record(self.destination),destination=record(self.destination),executionScope=self.scope,
            sourceTuple={},destinationTuple={},guestProfile='windows-server-2022',qualificationDigest='1'*64,
            operationsAcceptanceDigest='2'*64,deliveryPlanDigest=_digest(self.delivery),
            stageBindings=self.purpose.expected_bindings(),windowsServices=self.purpose.to_dict())
        self.plan={'metadata':{'planDigest':self.admitted.plan_digest},'spec':{
            'workloadId':'workload-01','workloadRevision':1,'source':record(self.destination),'destination':record(self.destination),
            'sourceSnapshotId':'observed-windows','destinationSnapshotId':'observed-windows',
            'selectedMachineIds':['target-01'],'selectedDatasetIds':[],'datasetMappings':[],
            'machineMappings':[{'machineId':'target-01','targetMachineId':'target-01',
                                'sourceBinding':self.record['native_binding']}],
            'route':{'method':METHOD,'guestProfile':'windows-server-2022','qualificationDigest':'1'*64},
            'execution':{'format':'hosting-execution-selection/1','driver':DRIVER,'artifactDigest':_digest(self.selection)},
            'windowsServices':{'format':PLAN_FORMAT,'selectionDigest':self.purpose.sha256}}}
        self.execution.plan=self.plan; self.execution.selected=self.selection
        self.input=WindowsServiceInput(self.admitted,_digest(self.selection),self.purpose.sha256,
            'CONFIGURE_AND_OBSERVE',('windows-configure','windows-observe'),'target-01')
        for name in ('deliveries','inboxes','results'):
            path=self.root/name; path.mkdir(mode=0o700); setattr(self,name,path)
        write_new(self.deliveries/(_digest(self.delivery)+'.json'),encoded(self.delivery))
        self.inbox=self.inboxes/self.admitted.job_id; self.inbox.mkdir(mode=0o700)
        stages=self.inbox/'steps'; stages.mkdir(mode=0o700)
        self.packets={}
        for step in self.delivery['steps']:
            directory=stages/step['id']; directory.mkdir(mode=0o700)
            read=step['kind']=='windows_guest_observe'
            files={'windows_selection':{'path':str(self.reader_path if read else self.path),
                    'sha256':reader.sha256 if read else writer.sha256},
                   'winrm_ca':{'path':str(self.ca),'sha256':self.record['ca_sha256']}}
            if read: files['original_windows_selection']={'path':str(self.path),'sha256':writer.sha256}
            packet={'step_id':step['id'],'plan_sha256':_digest(self.delivery),
                    'parameters':{'original_operation_id':'configure-operation'} if read else {},'files':files}
            self.packets[step['id']]=packet; write_new(directory/'packet.json',encoded(packet))
        issuer=self.windows.consumer.issuer
        self.windows=ScopedWindowsGuestRuntime(self.runtime,CredentialBroker(self.verifier,self.grants,issuer),
            VaultCredentialConsumer(issuer),self.registry,self.lease)

    def activities(self,owners):
        return WindowsServiceActivities(self.execution,self.deliveries,self.inboxes,self.results,ROOT,
                                         WindowsServiceRuntimeBindings(owners))

    def reader(self):
        identity,peer=self.additional_peer()
        grant=replace(self.grant,grant_id='reader-grant',worker_subject=identity.subject,
                      step_id='windows-observe',operation_id='observe-operation',operation_kind='DISCOVER_READ')
        self.grant=grant; self.grants.grant=grant
        command=replace(self.runtime,identity=identity,transport_evidence=peer,grant=grant)
        issuer=VaultDynamicCredentialIssuer(vault_url=f'https://localhost:{self.vault.server_port}',
            ca_bundle=self.pki.root/'ca.pem',agent_token_file=self.root/'vault-token',roles=(VaultDynamicRole(
                'vault:target-read','windows/creds/target-read',self.destination,'DISCOVER_READ',timedelta(minutes=1)),))
        enrollment=NativeReadEnrollment(command,self.admitted,_digest(self.selection),
            CredentialBroker(self.verifier,self.grants,issuer),VaultCredentialConsumer(issuer))
        self.record=self.reader_descriptor.to_dict(); self.descriptor=self.reader_descriptor
        self.registry.operation=replace(self.original_operation,operation_id='configure-operation',
            step_id='windows-configure',worker_id=self.windows.command_runtime.identity.subject,
            binding=self.binding,job_id=self.admitted.job_id)
        return ScopedWindowsServiceReadRuntime(enrollment,self.registry)

    def test_actual_existing_target_configuration_and_independent_read_are_reachable_without_resources(self):
        validate_artifact(self.selection); self.purpose.require_plan(self.plan,self.selection)
        writer=self.activities({(self.admitted.job_id,'windows-configure'):self.windows})
        completed=writer.run_step(WindowsServiceStageRequest(self.input,'windows-configure'))
        self.assertEqual(completed.status,'STAGE_COMPLETED'); self.assertFalse(completed.service_postconditions_observed)
        self.assertEqual(self.winrm.commands,['IDENTITY','OBSERVE_SERVICE','SET_STARTUP','START_SERVICE','OBSERVE_SERVICE'])
        reader=self.reader(); observed=self.activities({(self.admitted.job_id,'windows-observe'):reader}).run_step(
            WindowsServiceStageRequest(self.input,'windows-observe'))
        self.assertEqual(observed.status,'STAGE_COMPLETED'); self.assertTrue(observed.service_postconditions_observed)
        self.assertEqual(self.winrm.commands[-2:],['IDENTITY','OBSERVE_SERVICE'])
        output=load_private(self.results/self.admitted.job_id/'windows-observe'/'result.json')
        self.assertFalse(output['native_acceptance']); self.assertFalse(output['native_quiesced'])
        replay=writer.run_step(WindowsServiceStageRequest(self.input,'windows-configure'))
        self.assertEqual(replay.status,'HELD'); self.assertEqual(replay.reason_code,'RECOVERY_REQUIRED')
        self.assertEqual(len(self.winrm.commands),7)

    def test_artifact_and_graph_cannot_relabel_creation_or_linux_migration_as_windows_services(self):
        for field,value in (('driver','openstack-linux-rebuild/1'),('guestProfile','linux-ubuntu-2404'),
                            ('destination',self.selection['destination'] | {'nativeScopeId':'different'})):
            with self.subTest(field=field),self.assertRaises(ValueError):
                validate_artifact(self.selection | {field:value})
        changed=deepcopy(self.delivery); changed['steps'][0]['kind']='terraform_apply'
        with self.assertRaises(ValueError): self.purpose.require_delivery(changed)
        changed=deepcopy(self.selection); changed['stageBindings']['windows-configure']['inputDigests']['windows_selection']='f'*64
        with self.assertRaises(ValueError): validate_artifact(changed)

    def test_changed_current_plan_or_missing_enrollment_cannot_dispatch_native_commands(self):
        absent=self.activities({})
        result=absent.run_step(WindowsServiceStageRequest(self.input,'windows-configure'))
        self.assertEqual(result.reason_code,'OPERATOR_HOLD')
        self.plan['spec']['selectedDatasetIds']=['undeclared-data']
        result=self.activities({(self.admitted.job_id,'windows-configure'):self.windows}).run_step(
            WindowsServiceStageRequest(self.input,'windows-configure'))
        self.assertEqual(result.reason_code,'VALIDATION_FAILED'); self.assertEqual(self.winrm.contacts,[])

    def test_queued_operation_and_physical_input_cannot_switch_fixed_owner(self):
        changed=replace(self.input,service_selection_digest='f'*64)
        actual=self.activities({(self.admitted.job_id,'windows-configure'):self.windows})
        result=actual.run_step(WindowsServiceStageRequest(changed,'windows-configure'))
        self.assertEqual(result.reason_code,'VALIDATION_FAILED')
        self.path.write_bytes(b'changed native descriptor')
        result=actual.run_step(WindowsServiceStageRequest(self.input,'windows-configure'))
        self.assertEqual(result.reason_code,'VALIDATION_FAILED'); self.assertEqual(self.winrm.contacts,[])

    def test_descriptor_digest_cannot_authorize_another_native_vm_or_machine(self):
        for reader,original in ((False,self.writer_descriptor),(True,self.reader_descriptor)):
            other_uuid='11111111-2222-3333-4444-555555555555'
            for field,changes in (('native_binding',{'native_binding':self.record['native_binding'] | {
                                    'nativeId':other_uuid},'native_uuid':other_uuid}),
                                  ('machine_id',{'machine_id':'other-machine'})):
                with self.subTest(reader=reader,field=field):
                    changed=WindowsGuestSelection.from_record(original.to_dict() | changes)
                    digests={'readerSelectionDigest':changed.sha256} if reader else {
                        'writerSelectionDigest':changed.sha256,'originalSelectionDigest':changed.sha256}
                    purpose=WindowsServiceSelection.from_record(self.purpose.to_dict() | digests)
                    with self.assertRaisesRegex(ValueError,'physical Windows descriptor'):
                        purpose.require_guest(changed,reader=reader)
        self.assertEqual(self.winrm.contacts,[])

    def follow_up(self,action):
        """Model a separately committed new admission and retained old rows."""
        old_admitted=self.admitted; old_plan=deepcopy(self.plan); old_artifact=deepcopy(self.selection)
        original=replace(self.original_operation,operation_id='configure-operation',step_id='windows-configure',
            job_id=old_admitted.job_id,state='RESOLVED' if action=='REMEDIATE_AND_OBSERVE' else 'UNCERTAIN',
            outcome='EFFECT_PRESENT' if action=='REMEDIATE_AND_OBSERVE' else None)
        self.registry.operation=original
        reference=WindowsOriginalServiceIntent.from_record(dict(originalAdmitted=asdict(old_admitted),
            artifactDigest=_digest(old_artifact),operationId=original.operation_id,stepId=original.step_id,
            requestDigest=original.request_digest,leaseKey=original.lease_key,workerSubject=original.worker_id,
            ownerEpoch=original.owner_epoch,windowsSelectionDigest=self.writer_descriptor.sha256,
            nativeBinding=self.writer_descriptor.to_dict()['native_binding']))
        self.admitted=replace(old_admitted,job_id='new-service-job',plan_id='new-service-plan',plan_digest='f'*64)
        self.grant=replace(self.grant,plan_id=self.admitted.plan_id,plan_digest=self.admitted.plan_digest,
            step_id='new-observe' if action=='OBSERVE_ORIGINAL' else 'new-remediate',
            operation_id='new-read-operation' if action=='OBSERVE_ORIGINAL' else 'new-repair-operation')
        self.grants.grant=self.grant; self.runtime=replace(self.runtime,grant=self.grant)
        body=self.purpose.to_dict() | {'action':action,'original':reference.to_dict(),
            'write':None if action=='OBSERVE_ORIGINAL' else {'stepId':'new-remediate',
                'operationId':'new-repair-operation','kind':'windows_guest_remediate'},
            'read':{'stepId':'new-observe','operationId':'new-read-operation','kind':'windows_guest_observe'}}
        self.purpose=WindowsServiceSelection.from_record(body)
        self.selection['windowsServices']=body; self.selection['stageBindings']=self.purpose.expected_bindings()
        self.delivery['steps']=[] if action=='OBSERVE_ORIGINAL' else [
            {'id':'new-remediate','kind':'windows_guest_remediate','needs':[]}]
        self.delivery['steps'].append({'id':'new-observe','kind':'windows_guest_observe',
            'needs':[] if action=='OBSERVE_ORIGINAL' else ['new-remediate']})
        self.selection['deliveryPlanDigest']=_digest(self.delivery)
        self.plan['metadata']['planDigest']=self.admitted.plan_digest
        self.plan['spec']['windowsServices']['selectionDigest']=self.purpose.sha256
        self.plan['spec']['execution']['artifactDigest']=_digest(self.selection)
        self.input=WindowsServiceInput(self.admitted,_digest(self.selection),self.purpose.sha256,action,
            tuple(row['id'] for row in self.delivery['steps']),'target-01')
        self.execution.selected=self.selection
        self.execution.calls.clear()
        def archived(admitted,selection_digest,operation):
            self.execution.calls.append((admitted,selection_digest,operation,{'purpose':'OBSERVATION'}))
            if admitted==old_admitted:
                if selection_digest!=_digest(old_artifact): raise ValueError('Archived synthetic original changed')
                return old_plan,old_artifact
            return self.plan,self.selection
        self.execution.require_observation=archived
        write_new(self.deliveries/(_digest(self.delivery)+'.json'),encoded(self.delivery))
        self.inbox=self.inboxes/self.admitted.job_id; self.inbox.mkdir(mode=0o700)
        stages=self.inbox/'steps'; stages.mkdir(mode=0o700)
        for step in self.delivery['steps']:
            directory=stages/step['id']; directory.mkdir(mode=0o700)
            read=step['kind']=='windows_guest_observe'
            packet={'step_id':step['id'],'plan_sha256':_digest(self.delivery),
                'parameters':{'original_operation_id':original.operation_id if not read or action=='OBSERVE_ORIGINAL'
                              else 'new-repair-operation'},
                'files':{'windows_selection':{'path':str(self.reader_path if read else self.path),
                    'sha256':self.reader_descriptor.sha256 if read else self.writer_descriptor.sha256},
                    'original_windows_selection':{'path':str(self.path),'sha256':self.writer_descriptor.sha256},
                    'winrm_ca':{'path':str(self.ca),'sha256':self.record['ca_sha256']}}}
            write_new(directory/'packet.json',encoded(packet))
        return reference

    def test_new_admitted_reader_rechecks_actual_original_scope_and_intent_without_reusing_old_write_grant(self):
        reference=self.follow_up('OBSERVE_ORIGINAL')
        old_operation=self.registry.operation
        reader=self.reader()
        self.registry.operation=old_operation
        grant=replace(reader.command_runtime.grant,step_id='new-observe',operation_id='new-read-operation')
        self.grant=grant; self.grants.grant=grant
        command=replace(reader.command_runtime,grant=grant)
        enrollment=replace(reader.enrollment,command=command)
        reader=ScopedWindowsServiceReadRuntime(enrollment,self.registry,reference)
        self.winrm.state='Running'; self.winrm.startup='Automatic'
        selected=self.activities({(self.admitted.job_id,'new-observe'):reader})
        result=selected.run_step(WindowsServiceStageRequest(self.input,'new-observe'))
        self.assertEqual(result.status,'STAGE_COMPLETED'); self.assertTrue(result.service_postconditions_observed)
        self.assertEqual(self.registry.contacts,[]); self.assertEqual(self.winrm.commands,['IDENTITY','OBSERVE_SERVICE'])
        old_calls=[row for row in self.execution.calls if row[0]==reference.admitted]
        self.assertGreater(len(old_calls),len(self.winrm.contacts))
        self.assertTrue(all(row[3]=={'purpose':'OBSERVATION'} for row in old_calls))

    def test_new_remediation_rechecks_actual_old_terminal_intent_and_keeps_its_own_current_claim(self):
        reference=self.follow_up('REMEDIATE_AND_OBSERVE')
        issuer=self.windows.consumer.issuer
        owner=ScopedWindowsGuestRuntime(self.runtime,CredentialBroker(self.verifier,self.grants,issuer),
            VaultCredentialConsumer(issuer),self.registry,self.lease,reference)
        actual=self.activities({(self.admitted.job_id,'new-remediate'):owner})
        result=actual.run_step(WindowsServiceStageRequest(self.input,'new-remediate'))
        self.assertEqual(result.status,'STAGE_COMPLETED'); self.assertFalse(result.service_postconditions_observed)
        self.assertEqual(self.registry.contacts[-1],('claim','new-repair-operation'))
        self.assertTrue(any(row[0]==reference.admitted for row in self.execution.calls))

    def test_retained_reference_cannot_hide_changed_actual_original_request_custody(self):
        reference=self.follow_up('REMEDIATE_AND_OBSERVE')
        self.registry.operation=replace(self.registry.operation,request_digest='e'*64)
        owner=replace(self.windows,command_runtime=self.runtime,original_intent=reference)
        result=self.activities({(self.admitted.job_id,'new-remediate'):owner}).run_step(
            WindowsServiceStageRequest(self.input,'new-remediate'))
        self.assertEqual(result.reason_code,'VALIDATION_FAILED'); self.assertEqual(self.winrm.contacts,[])
        self.assertEqual(self.registry.contacts,[])


if __name__=='__main__': unittest.main()
