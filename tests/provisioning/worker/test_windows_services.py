"""Independent actual certificate-only SOAP boundaries; synthetic native DB.

The fixture models native Windows execution and registry persistence. It never
qualifies a Windows image, a certificate backend or old WinRM shell exclusion.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
import unittest

from provisioner.controlplane.jobs.repository import _digest
from provisioner.controlplane.reconciliation.read_enrollment import NativeReadEnrollment
from provisioner.controlplane.reconciliation.registry import NativeOperation, RecoveryHeld
from provisioner.controlplane.worker.grants import CredentialBroker, GrantDenied
from provisioner.controlplane.worker.vault import VaultDynamicCredentialIssuer, VaultDynamicRole
from provisioner.controlplane.worker.vault_consumer import VaultCredentialConsumer
from provisioner.controlplane.worker.windows_commands import ScopedWindowsGuestRuntime, WindowsGuestIntent, _WinRM
from provisioner.controlplane.worker.windows_services import ScopedWindowsServiceReadRuntime, WindowsServiceReadAuthority
from provisioner.execution.run_files import write_new
from provisioner.execution import delivery_steps
from provisioner.execution.windows_guest import WindowsGuestSelection
from tests.provisioning.worker.test_command_runtime import ROOT
from tests.provisioning.worker.test_windows_commands import _WindowsFixture, _Registry


class _OriginalRegistry(_Registry):
    def __init__(self, grants, operation):
        super().__init__(grants); self.operation=operation; self.lookups=[]

    @contextmanager
    def _connect(self):
        class Cursor:
            def __init__(self,connection): self.connection=connection
            def execute(self,*_arguments): pass
            def fetchone(self): return (False,False)
        class Connection:
            autocommit=False
            @contextmanager
            def cursor(self): yield Cursor(self)
        yield Connection()

    def _get(self,cursor,context,operation_id):
        self.lookups.append((context,operation_id))
        if operation_id != self.operation.operation_id: raise RecoveryHeld('Actual synthetic original is absent')
        return self.operation


class _WindowsOriginalFixture(_WindowsFixture):
    def setUp(self):
        super().setUp()
        self.original_descriptor=self.descriptor
        self.original_path=self.path
        self.original_step=deepcopy(self.step)
        self.original_binding=deepcopy(self.selection['stageBindings'][self.step['id']])
        self.original_operation=NativeOperation('original-windows-01',self.admitted.job_id,'original-grant-01',
            self.step['id'],'original-lease-01',self.binding,'workload-01','wsd-01',self.identity.subject,
            1,'GUEST_CONFIG','c'*64,'IN_FLIGHT',None,None)
        self.registry=_OriginalRegistry(self.grants,self.original_operation)

    def graph(self,kind,parameters,files):
        self.step={'id':'independent-'+kind,'kind':kind,'needs':[self.original_step['id']]}
        self.delivery={'source_commit':'a'*40,'scope':self.scope,'steps':[self.original_step,self.step]}
        self.packet={'step_id':self.step['id'],'plan_sha256':_digest(self.delivery),
                     'parameters':parameters,'files':files}
        self.selection['deliveryPlanDigest']=_digest(self.delivery)
        self.selection['source']=self.plan['spec']['source']
        self.selection['destination']=self.plan['spec']['destination']
        self.selection['stageBindings']={self.original_step['id']:self.original_binding,
            self.step['id']:{'kind':kind,'parametersDigest':_digest(parameters),
                            'inputDigests':{name:row['sha256'] for name,row in files.items()}}}


class IndependentWindowsReadTests(_WindowsOriginalFixture):
    def setUp(self):
        super().setUp()
        self.identity,self.peer=self.additional_peer()
        self.grant=replace(self.grant,operation_kind='DISCOVER_READ',worker_subject=self.identity.subject,
                           step_id='independent-windows_guest_observe',operation_id='windows-read-01')
        self.grants.grant=self.grant
        self.runtime=replace(self.runtime,identity=self.identity,transport_evidence=self.peer,grant=self.grant)
        self.record=deepcopy(self.record) | {'mapped_user':r'WINHOST\read-user',
            'certificate_subject':'CN=owned-read-winrm','certificate_upn':'read-user@localhost'}
        self.descriptor=WindowsGuestSelection.from_record(self.record)
        self.path=self.root/'read-windows.json'; write_new(self.path,self.descriptor.canonical)
        self.graph('windows_guest_observe',{'original_operation_id':self.original_operation.operation_id},{
            'windows_selection':{'path':str(self.path),'sha256':self.descriptor.sha256},
            'original_windows_selection':{'path':str(self.original_path),'sha256':self.original_descriptor.sha256},
            'winrm_ca':{'path':str(self.ca),'sha256':self.record['ca_sha256']}})
        issuer=VaultDynamicCredentialIssuer(vault_url=f'https://localhost:{self.vault.server_port}',
            ca_bundle=self.pki.root/'ca.pem',agent_token_file=self.root/'vault-token',roles=(VaultDynamicRole(
                'vault:target-read','windows/creds/target-read',self.destination,'DISCOVER_READ',timedelta(minutes=1)),))
        self.enrollment=NativeReadEnrollment(self.runtime,self.admitted,_digest(self.selection),
            CredentialBroker(self.verifier,self.grants,issuer),VaultCredentialConsumer(issuer))
        self.reader=ScopedWindowsServiceReadRuntime(self.enrollment,self.registry)
        self.authority=WindowsServiceReadAuthority(self.reader,self.admitted,self.selection,self.delivery,
            self.step,self.packet,ROOT)
        self.winrm.state='Running'; self.winrm.startup='Automatic'

    def read(self):
        return self.reader.observe_selected(self.authority,self.descriptor,self.ca,self.output)

    def test_independent_actual_winrm_reads_service_but_never_infers_native_quiescence_or_acceptance(self):
        result,names=self.reader.run_step(self.admitted,self.selection,self.delivery,self.step,self.packet,
                                         self.output,self.root,ROOT)
        self.assertEqual(self.winrm.commands,['IDENTITY','OBSERVE_SERVICE'])
        self.assertEqual(len(self.winrm.contacts),10)
        self.assertEqual(len(set(self.winrm.client_certificates)),10)
        self.assertEqual(len(self.vault.contacts),20)
        self.assertEqual(result['reader_subject'],self.identity.subject)
        self.assertNotEqual(result['reader_subject'],result['original_worker_subject'])
        self.assertEqual(result['original_request_digest'],self.original_operation.request_digest)
        self.assertFalse(result['native_acceptance']); self.assertFalse(result['native_quiesced'])
        self.assertEqual(self.registry.contacts,[])
        self.assertFalse(list(self.output.glob('credential-*')))
        self.assertIn('owner-completion.json',names)

    def test_portable_dispatch_cannot_construct_independent_native_read_enrollment(self):
        with self.assertRaisesRegex(ValueError,'actual enrolled runtime'):
            delivery_steps.dispatch(self.step,self.packet,self.output,self.root,self.delivery,ROOT)
        self.assertEqual(self.winrm.contacts,[]); self.assertEqual(self.vault.contacts,[])

    def test_completion_rejects_native_exclusion_claim_and_false_successful_service_state(self):
        result=self.read()
        for change in ('native_quiesced','wrong_service','original_input'):
            with self.subTest(change=change):
                altered=deepcopy(result)
                if change=='native_quiesced': altered['native_quiesced']=True
                elif change=='original_input': altered['original_selection_sha256']='f'*64
                else: altered['observations'][-1]['observation']['service']['state']='Stopped'
                with self.assertRaises(ValueError):
                    delivery_steps.typed_postcondition(self.step,altered,self.output,self.packet,self.delivery)

    def test_read_owner_cannot_send_any_service_mutation(self):
        channel=_WinRM(self.reader,self.authority,self.descriptor,self.ca,self.output)
        for action in ('SET_STARTUP','START_SERVICE','STOP_SERVICE'):
            with self.subTest(action=action),self.assertRaisesRegex(ValueError,'cannot dispatch'):
                channel.action(action,self.record['services'][0])
        self.assertEqual(self.winrm.contacts,[]); self.assertEqual(self.vault.contacts,[])

    def test_read_revocation_stops_command_and_cleanup_after_first_real_shell_contact(self):
        self.winrm.revoke_after='Create'
        with self.assertRaises(GrantDenied): self.read()
        self.assertEqual(self.winrm.contacts,['Create']); self.assertEqual(self.winrm.commands,[])

    def test_matching_transport_with_wrong_service_state_does_not_verify_postcondition(self):
        self.winrm.state='Stopped'
        with self.assertRaisesRegex(ValueError,'service postconditions'): self.read()
        self.assertEqual(self.registry.contacts,[])

    def test_original_intent_native_binding_or_input_cannot_be_replaced_between_reads(self):
        self.registry.operation=replace(self.original_operation,request_digest='f'*64)
        with self.assertRaisesRegex(ValueError,'original Windows intent custody'): self.read()
        self.registry.operation=self.original_operation
        self.original_path.write_bytes(b'replaced original descriptor')
        with self.assertRaisesRegex(ValueError,'Delivery input bytes changed'): self.read()
        self.assertEqual(self.winrm.contacts,[])

    def test_native_read_identity_cannot_borrow_writer_account_or_change_existing_services(self):
        changed=deepcopy(self.record) | {'mapped_user':self.original_descriptor.to_dict()['mapped_user']}
        changed=WindowsGuestSelection.from_record(changed)
        self.path.write_bytes(changed.canonical)
        with self.assertRaises(ValueError): self.read()
        self.path.write_bytes(self.descriptor.canonical)
        self.registry.operation=replace(self.original_operation,worker_id=self.identity.subject)
        with self.assertRaisesRegex(ValueError,'independent identity'): self.read()
        self.assertEqual(self.vault.contacts,[])


class WindowsRemediationTests(_WindowsOriginalFixture):
    def setUp(self):
        super().setUp()
        self.registry.operation=replace(self.original_operation,state='RESOLVED',outcome='EFFECT_PRESENT')
        self.grant=replace(self.grant,step_id='independent-windows_guest_remediate',operation_id='windows-repair-01')
        self.grants.grant=self.grant; self.runtime=replace(self.runtime,grant=self.grant)
        self.graph('windows_guest_remediate',{'original_operation_id':self.original_operation.operation_id},{
            'windows_selection':{'path':str(self.path),'sha256':self.descriptor.sha256},
            'original_windows_selection':{'path':str(self.original_path),'sha256':self.original_descriptor.sha256},
            'winrm_ca':{'path':str(self.ca),'sha256':self.record['ca_sha256']}})
        issuer=self.windows.consumer.issuer
        self.windows=ScopedWindowsGuestRuntime(self.runtime,CredentialBroker(self.verifier,self.grants,issuer),
            VaultCredentialConsumer(issuer),self.registry,self.lease)
        self.intent=WindowsGuestIntent(self.windows,self.admitted,self.selection,self.step,self.descriptor,packet=self.packet)

    def select_remediation(self):
        return self.runtime.select(self.admitted,self.selection,self.delivery,self.step,self.packet,ROOT,intent_guard=self.intent)

    def test_new_fixed_remediation_rechecks_resolved_predecessor_before_every_soap_request(self):
        authority=self.select_remediation(); self.intent.claim(authority)
        result=self.windows.execute_selected(authority,self.descriptor,self.ca,self.output)
        self.assertEqual(self.winrm.commands,['IDENTITY','OBSERVE_SERVICE','SET_STARTUP','START_SERVICE','OBSERVE_SERVICE'])
        self.assertEqual(result['operation_id'],'windows-repair-01')
        self.assertFalse(result['native_acceptance'])
        self.assertGreater(len(self.registry.lookups),len(self.winrm.contacts))
        self.assertEqual(self.registry.contacts[-1],('claim','windows-repair-01'))
        delivery_steps.typed_postcondition(self.step,result,self.output,self.packet,self.delivery)

    def test_portable_dispatch_cannot_remediate_without_current_enrolled_native_authority(self):
        with self.assertRaisesRegex(ValueError,'actual enrolled runtime'):
            delivery_steps.dispatch(self.step,self.packet,self.output,self.root,self.delivery,ROOT)
        self.assertEqual(self.registry.contacts,[]); self.assertEqual(self.winrm.contacts,[])

    def test_original_uncertainty_cannot_become_an_automatic_repair_or_new_claim(self):
        self.registry.operation=replace(self.original_operation,state='UNCERTAIN',outcome=None)
        with self.assertRaisesRegex(RecoveryHeld,'fenced recovery'): self.select_remediation()
        self.assertEqual(self.registry.contacts,[]); self.assertEqual(self.winrm.contacts,[])

    def test_predecessor_uncertainty_cannot_be_switched_after_new_claim(self):
        authority=self.select_remediation(); self.intent.claim(authority)
        self.registry.operation=replace(self.original_operation,state='UNCERTAIN')
        with self.assertRaises(RecoveryHeld): self.windows.execute_selected(authority,self.descriptor,self.ca,self.output)
        self.assertEqual(self.winrm.contacts,[])

    def test_separately_admitted_remediation_cannot_change_original_service_policy(self):
        changed=deepcopy(self.record)
        changed['services'][0]['startup']='Disabled'; changed['services'][0]['state']='Stopped'
        descriptor=WindowsGuestSelection.from_record(changed)
        path=self.root/'different-remediation.json'; write_new(path,descriptor.canonical)
        files=deepcopy(self.packet['files'])
        files['windows_selection']={'path':str(path),'sha256':descriptor.sha256}
        self.graph('windows_guest_remediate',self.packet['parameters'],files)
        intent=WindowsGuestIntent(self.windows,self.admitted,self.selection,self.step,descriptor,packet=self.packet)
        with self.assertRaisesRegex(ValueError,'requested policy'):
            self.runtime.select(self.admitted,self.selection,self.delivery,self.step,self.packet,ROOT,intent_guard=intent)
        self.assertEqual(self.registry.contacts,[]); self.assertEqual(self.winrm.contacts,[])


if __name__ == '__main__': unittest.main()
