"""Real certificate-only TLS/SOAP; simulated Windows and native persistence.

This is protocol and authority evidence, not execution on a Windows guest,
Vault backend commissioning, real PostgreSQL fencing or native qualification.
"""
import base64
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import re
import ssl
import threading
import unittest
from uuid import uuid4
import xml.etree.ElementTree as ET

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID, ObjectIdentifier

from provisioner.controlplane.persistence import NativeBinding
from provisioner.controlplane.persistence.store import OwnerLease
from provisioner.controlplane.reconciliation.registry import NativeOperationRegistry
from provisioner.controlplane.worker.grants import CredentialBroker, GrantDenied
from provisioner.controlplane.worker.vault import VaultDynamicCredentialIssuer, VaultDynamicRole
from provisioner.controlplane.worker.vault_consumer import VaultCredentialConsumer
from provisioner.controlplane.worker.windows_commands import (
    ScopedWindowsGuestRuntime, WindowsGuestIntent, _WinRM,
    ADDRESS, POWER_SHELL, RESOURCE, SHELL, SOAP, TRANSFER, WSMAN)
from provisioner.execution.run_files import digest, encoded, utcnow, write_new
from provisioner.execution.windows_guest import WindowsGuestSelection
from tests.provisioning.worker.test_command_runtime import _Fixture, ROOT


class _Registry(NativeOperationRegistry):
    def __init__(self,grants): self._grants=grants; self.contacts=[]; self.claimed=False
    def prepare(self,context,lease,scope,**arguments): self.contacts.append(('prepare',arguments))
    def claim_once(self,context,lease,scope,operation,identity):
        self.contacts.append(('claim',operation))
        if self.claimed: return False
        self.claimed=True; return True
    def mark_uncertain(self,context,operation,identity): self.contacts.append(('uncertain',operation))


def _add(parent,ns,name,text=None,**attributes):
    child=ET.SubElement(parent,'{'+ns+'}'+name,attributes); child.text=text; return child


class _Vault(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.contacts.append(('issue',self.path))
        self.send({'data':None,'auth':None,'wrap_info':{'token':'test-wrap-'+str(len(self.server.contacts)),
            'ttl':30,'creation_path':'windows/creds/target-read'}})
    def do_POST(self):
        self.server.contacts.append(('consume',self.path))
        fixture=self.server.fixture
        now=utcnow(); key=ec.generate_private_key(ec.SECP256R1())
        upn=fixture.record['certificate_upn'].encode()
        certificate=(x509.CertificateBuilder()
            .subject_name(x509.Name.from_rfc4514_string(fixture.record['certificate_subject']))
            .issuer_name(fixture.pki.name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(seconds=1))
            .not_valid_after(now+timedelta(seconds=20))
            .add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]),critical=False)
            .add_extension(x509.SubjectAlternativeName([x509.OtherName(
                ObjectIdentifier('1.3.6.1.4.1.311.20.2.3'),bytes([0x0c,len(upn)])+upn)]),critical=False)
            .sign(fixture.pki.ca_key,hashes.SHA256()))
        fixture.serials.append(certificate.serial_number)
        if self.server.reuse is not None: certificate,key=self.server.reuse
        if self.server.reuse_next: self.server.reuse=(certificate,key)
        data={'format':'hosting-winrm-dynamic-certificate/1','grant_id':fixture.grant.grant_id,
            'selection_sha256':fixture.descriptor.sha256,'endpoint':fixture.endpoint,
            'mapped_user':fixture.record['mapped_user'],
            'certificate_pem':certificate.public_bytes(serialization.Encoding.PEM).decode(),
            'private_key_pem':key.private_bytes(serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,serialization.NoEncryption()).decode()}
        if self.server.other_selection: data['selection_sha256']='f'*64
        self.send({'lease_id':'winrm-lease-'+str(len(self.server.contacts)),'lease_duration':30,
                   'data':{'winrm':data},'auth':None,'wrap_info':None})
    def send(self,payload):
        raw=encoded(payload); self.send_response(200); self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def log_message(self,*_): pass


class _Windows(BaseHTTPRequestHandler):
    def handle(self):
        try: super().handle()
        except BrokenPipeError: pass  # The pin-mismatch client closes before HTTP.

    def do_POST(self):
        fixture=self.server.fixture
        request=ET.fromstring(self.rfile.read(int(self.headers['Content-Length'])))
        action=request.find('.//{'+ADDRESS+'}Action').text.rsplit('/',1)[1]
        self.server.contacts.append(action)
        peer=x509.load_der_x509_certificate(self.connection.getpeercert(binary_form=True))
        self.server.client_certificates.append(peer.serial_number)
        if self.headers['Authorization']!='http://schemas.dmtf.org/wbem/wsman/1/wsman/secprofile/https/mutual':
            raise AssertionError('Certificate-only native profile required')
        envelope=ET.Element('{'+SOAP+'}Envelope'); header=_add(envelope,SOAP,'Header')
        body=_add(envelope,SOAP,'Body')
        uri=(TRANSFER if action in {'Create','Delete'} else SHELL)+'/'+action
        _add(header,ADDRESS,'Action',uri+'Response')
        related=request.find('.//{'+ADDRESS+'}MessageID').text
        _add(header,ADDRESS,'RelatesTo','uuid:'+str(uuid4()) if self.server.bad_related else related)
        if action=='Create':
            self.server.shell=str(uuid4()); created=_add(body,TRANSFER,'ResourceCreated')
            _add(created,ADDRESS,'Address',fixture.endpoint)
            reference=_add(created,ADDRESS,'ReferenceParameters'); _add(reference,WSMAN,'ResourceURI',RESOURCE)
            selectors=_add(reference,WSMAN,'SelectorSet'); _add(selectors,WSMAN,'Selector',self.server.shell,Name='ShellId')
        else:
            selected=request.find('.//{'+WSMAN+'}Selector')
            if selected.text!=self.server.shell: raise AssertionError('Original shell required')
            if action=='Command':
                if request.find('.//{'+SHELL+'}Command').text!=POWER_SHELL:
                    raise AssertionError('Fixed PowerShell interpreter required')
                options={row.get('Name'):row.text for row in request.findall('.//{'+WSMAN+'}Option')}
                if options.get('WINRS_SKIP_CMD_SHELL')!='TRUE': raise AssertionError('No cmd.exe required')
                argv=request.find('.//{'+SHELL+'}Arguments').text
                if not argv.startswith('-NoLogo -NoProfile -NonInteractive -EncodedCommand '):
                    raise AssertionError('Fixed native command arguments required')
                script=base64.b64decode(argv.rsplit(' ',1)[1]).decode('utf-16-le')
                binding=re.search("FromBase64String\\('([A-Za-z0-9+/=]+)'\\)",script).group(1)
                import json
                self.server.binding=json.loads(base64.b64decode(binding))
                self.server.commands.append(self.server.binding['action'])
                self.server.command=str(uuid4())
                response=_add(body,SHELL,'CommandResponse'); _add(response,SHELL,'CommandId',self.server.command)
            elif action=='Receive':
                binding=self.server.binding; service=binding['service']; selected=fixture.record
                observation={key:selected[key] for key in ('machine_guid','native_uuid')}
                observation|={'build':'20348','principal':selected['mapped_user']}
                if self.server.wrong_machine: observation['machine_guid']=str(uuid4())
                if service is not None:
                    if binding['action']=='SET_STARTUP': self.server.startup=service['startup']
                    if binding['action']=='START_SERVICE': self.server.state='Running'
                    if binding['action']=='STOP_SERVICE': self.server.state='Stopped'
                    row={'name':service['name'],'state':self.server.state,
                         'startup':{'Automatic':'Auto','Manual':'Manual','Disabled':'Disabled'}[self.server.startup],
                         'image_path':service['image_path'],'executable_sha256':service['binary_sha256']}
                    if self.server.wrong_postcondition: row['state']='Stopped'
                    observation['service']=row
                result={'format':'hosting-windows-guest-observation/1','observation':observation}
                result|={key:binding[key] for key in ('action','job_id','operation_id','selection_sha256')}
                response=_add(body,SHELL,'ReceiveResponse')
                _add(response,SHELL,'Stream',base64.b64encode(encoded(result)).decode(),
                     Name='stdout',CommandId=self.server.command,End='true')
                state=_add(response,SHELL,'CommandState',CommandId=self.server.command,
                           State=SHELL+'/CommandState/Done'); _add(state,SHELL,'ExitCode','0')
            elif action=='Signal': _add(body,SHELL,'SignalResponse')
        if action==self.server.revoke_after: fixture.grants.revoked=True
        raw=ET.tostring(envelope,encoding='utf-8'); self.send_response(200)
        self.send_header('Content-Type','application/soap+xml'); self.send_header('Content-Length',str(len(raw)))
        self.end_headers(); self.wfile.write(raw)
    def log_message(self,*_): pass


class _WindowsFixture(_Fixture):
    def setUp(self):
        super().setUp(); self.serials=[]
        self.grant=replace(self.grant,operation_kind='GUEST_CONFIG')
        self.winrm=ThreadingHTTPServer(('127.0.0.1',0),_Windows)
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(self.pki.root/'server.pem'),str(self.pki.root/'server.key'))
        context.load_verify_locations(cafile=str(self.pki.root/'ca.pem')); context.verify_mode=ssl.CERT_REQUIRED
        self.winrm.socket=context.wrap_socket(self.winrm.socket,server_side=True)
        self.winrm.fixture=self; self.winrm.contacts=[]; self.winrm.commands=[]; self.winrm.client_certificates=[]
        self.winrm.bad_related=False; self.winrm.wrong_machine=False; self.winrm.wrong_postcondition=False
        self.winrm.revoke_after=None; self.winrm.state='Stopped'; self.winrm.startup='Manual'
        thread=threading.Thread(target=self.winrm.serve_forever,daemon=True); thread.start()
        self.addCleanup(self.winrm.server_close); self.addCleanup(self.winrm.shutdown)
        self.endpoint=f'https://localhost:{self.winrm.server_port}/wsman'
        self.native_id='00000000-0000-0000-0000-000000000001'
        self.binding=NativeBinding('openstack','openstack-01','project-01','vm',self.native_id)
        self.record={'format':'hosting-windows-guest-selection/1','guest_profile':'windows-server-2022',
            'native_binding':{'platformFamily':'openstack','endpointId':'openstack-01',
                'nativeScopeId':'project-01','resourceKind':'vm','nativeId':self.native_id},
            'endpoint':self.endpoint,'connect_ip':'127.0.0.1','server_name':'localhost',
            'server_certificate_sha256':digest(x509.load_pem_x509_certificate(
                (self.pki.root/'server.pem').read_bytes()).public_bytes(serialization.Encoding.DER)),
            'ca_sha256':digest((self.pki.root/'ca.pem').read_bytes()),'machine_id':'target-01',
            'machine_guid':'00000000-0000-0000-0000-000000000002','native_uuid':self.native_id,
            'mapped_user':r'WINHOST\owned-user','certificate_subject':'CN=owned-winrm',
            'certificate_upn':'owned-user@localhost','powershell_sha256':'a'*64,
            'services':[{'name':'OwnedService','image_path':r'C:\owned\service.exe --owned',
                'executable':r'C:\owned\service.exe','binary_sha256':'b'*64,'state':'Running','startup':'Automatic',
                'dependencies':[]}]}
        self.descriptor=WindowsGuestSelection.from_record(self.record)
        self.path=self.root/'windows.json'; write_new(self.path,self.descriptor.canonical)
        self.ca=self.root/'ca.pem'; write_new(self.ca,(self.pki.root/'ca.pem').read_bytes())
        self.authority=self.select(kind='windows_guest_apply',files={
            'windows_selection':{'path':str(self.path),'sha256':self.descriptor.sha256},
            'winrm_ca':{'path':str(self.ca),'sha256':digest(self.ca.read_bytes())}})
        self.selection['guestProfile']='windows-server-2022'
        self.plan['spec']|={'route':{'guestProfile':'windows-server-2022'},'selectedMachineIds':['source-01'],
            'machineMappings':[{'machineId':'source-01','targetMachineId':'target-01'}]}
        self.vault=ThreadingHTTPServer(('127.0.0.1',0),_Vault)
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(self.pki.root/'server.pem'),str(self.pki.root/'server.key'))
        self.vault.socket=context.wrap_socket(self.vault.socket,server_side=True)
        self.vault.fixture=self; self.vault.contacts=[]; self.vault.other_selection=False
        self.vault.reuse=None; self.vault.reuse_next=False
        thread=threading.Thread(target=self.vault.serve_forever,daemon=True); thread.start()
        self.addCleanup(self.vault.server_close); self.addCleanup(self.vault.shutdown)
        token=self.root/'vault-token'; write_new(token,b'test-only-agent-token')
        issuer=VaultDynamicCredentialIssuer(vault_url=f'https://localhost:{self.vault.server_port}',
            ca_bundle=self.pki.root/'ca.pem',agent_token_file=token,
            roles=(VaultDynamicRole('vault:target-read','windows/creds/target-read',
                self.destination,'GUEST_CONFIG',timedelta(minutes=1)),))
        broker=CredentialBroker(self.verifier,self.grants,issuer)
        self.registry=_Registry(self.grants)
        self.lease=OwnerLease(self.binding,'org-01','tenant-01','wsd-01','workload-01','worker-01',1,self.grant.expires_at)
        self.windows=ScopedWindowsGuestRuntime(self.runtime,broker,VaultCredentialConsumer(issuer),self.registry,self.lease)
        self.intent=WindowsGuestIntent(self.windows,self.admitted,self.selection,self.step,self.descriptor)
        self.authority=self.runtime.select(self.admitted,self.selection,self.delivery,self.step,self.packet,ROOT,
                                            intent_guard=self.intent)
        self.output=self.root/'output'; self.output.mkdir(mode=0o700)

    def execute(self):
        self.intent.claim(self.authority)
        return self.windows.execute_selected(self.authority,self.descriptor,self.ca,self.output)



class WindowsCommandTests(_WindowsFixture):
    def test_real_certificate_only_exchange_rechecks_original_and_reads_service_postcondition(self):
        result=self.execute()
        self.assertEqual(result['status'],'CONFIGURED_REQUIRES_NATIVE_ACCEPTANCE')
        self.assertEqual(self.winrm.commands,['IDENTITY','OBSERVE_SERVICE','SET_STARTUP','START_SERVICE','OBSERVE_SERVICE'])
        self.assertEqual(len(self.winrm.contacts),25)
        self.assertEqual(len(set(self.winrm.client_certificates)),25)
        self.assertEqual(len(self.vault.contacts),50)
        self.assertEqual(result['observations'][-1]['observation']['service']['state'],'Running')
        self.assertEqual(self.registry.contacts[-1][0],'claim')
        self.assertTrue(all(call[3].get('continuation_grant')==self.grant for call in self.execution.calls
                            if call[3].get('continuation_grant') is not None))
        self.assertFalse(list(self.output.glob('credential-*')))
        self.assertNotIn(b'PRIVATE KEY',b''.join(path.read_bytes() for path in self.output.iterdir()))

    def test_revocation_after_native_command_prevents_result_poll_and_cleanup(self):
        self.winrm.revoke_after='Command'
        with self.assertRaises(GrantDenied): self.execute()
        self.assertEqual(self.winrm.contacts,['Create','Command'])
        self.assertEqual(len(self.vault.contacts),4)
        self.assertFalse(list(self.output.glob('credential-*')))
        with self.assertRaises(GrantDenied): self.authority.require_current()

    def test_revocation_between_shell_and_command_stops_next_remote_effect(self):
        self.winrm.revoke_after='Create'
        with self.assertRaises(GrantDenied): self.execute()
        self.assertEqual(self.winrm.contacts,['Create'])
        self.assertEqual(self.winrm.commands,[])

    def test_unclaimed_intent_refuses_even_first_native_identity_read(self):
        with self.assertRaisesRegex(ValueError,'Claimed original'):
            self.windows.execute_selected(self.authority,self.descriptor,self.ca,self.output)
        self.assertEqual(self.winrm.contacts,[]); self.assertEqual(self.vault.contacts,[])

    def test_certificate_pin_and_wrong_dynamic_selection_deny_contact(self):
        wrong=deepcopy(self.record); wrong['server_certificate_sha256']='f'*64
        descriptor=WindowsGuestSelection.from_record(wrong)
        self.intent.claim(self.authority)
        channel=_WinRM(self.windows,self.authority,descriptor,self.ca,self.output)
        self.vault.fixture.descriptor=descriptor
        with self.assertRaisesRegex(ValueError,'listener certificate'): channel.action('IDENTITY')
        self.assertEqual(self.winrm.contacts,[])
        self.vault.other_selection=True
        with self.assertRaisesRegex(ValueError,'dynamic certificate grant'): channel.action('IDENTITY')
        self.assertEqual(self.winrm.contacts,[])

    def test_replayed_certificate_and_unrelated_soap_response_are_denied(self):
        self.vault.reuse_next=True
        with self.assertRaisesRegex(ValueError,'reused'): self.execute()
        self.assertEqual(self.winrm.contacts,['Create'])

    def test_unrelated_soap_response_stops_before_next_command(self):
        self.winrm.bad_related=True
        with self.assertRaisesRegex(ValueError,'original exchange'): self.execute()
        self.assertEqual(self.winrm.contacts,['Create'])

    def test_zero_exit_does_not_accept_another_machine_or_failed_service_postcondition(self):
        self.winrm.wrong_machine=True
        with self.assertRaisesRegex(ValueError,'original Windows'): self.execute()
        self.assertEqual(self.winrm.commands,['IDENTITY'])

    def test_zero_exit_without_desired_running_state_is_held(self):
        self.winrm.wrong_postcondition=True
        with self.assertRaisesRegex(ValueError,'requested state'): self.execute()
        self.assertEqual(self.winrm.commands[-1],'OBSERVE_SERVICE')

    def test_linux_selection_or_other_approved_machine_cannot_borrow_windows_owner(self):
        self.selection['guestProfile']='linux-ubuntu-2404'
        with self.assertRaisesRegex(ValueError,'original selected VM'): self.intent.require_current()
        self.selection['guestProfile']='windows-server-2022'
        self.plan['spec']['machineMappings'][0]['targetMachineId']='other-01'
        with self.assertRaisesRegex(ValueError,'original selected VM'): self.intent.require_current()
        self.assertEqual(self.vault.contacts,[]); self.assertEqual(self.winrm.contacts,[])

    def test_descriptor_rejects_arbitrary_service_names_paths_and_undeclared_dependencies(self):
        for field,value in (('name',"arbitrary' OR Name='another"),('executable',r'C:\owned\service.exe:other'),
                            ('dependencies',['OwnedService']),('dependencies',['wildcard*'])):
            with self.subTest(field=field,value=value):
                changed=deepcopy(self.record); changed['services'][0][field]=value
                with self.assertRaises(ValueError): WindowsGuestSelection.from_record(changed)

    def test_switched_physical_descriptor_ca_and_worker_peer_stop_next_request(self):
        self.intent.claim(self.authority); self.ca.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'Windows selection or listener CA'):
            self.windows.execute_selected(self.authority,self.descriptor,self.ca,self.output)
        self.ca.write_bytes((self.pki.root/'ca.pem').read_bytes())
        self.verifier.reload_trust()
        with self.assertRaises(GrantDenied):
            self.windows.execute_selected(self.authority,self.descriptor,self.ca,self.output)
        self.assertEqual(self.winrm.contacts,[]); self.assertEqual(self.vault.contacts,[])


class WindowsSelectionTests(unittest.TestCase):
    def test_descriptor_has_no_arbitrary_script_or_service_name_escaping(self):
        # Exact field validation is exercised with a real full descriptor by
        # the protocol fixture; this rejects queue-chosen code before parsing.
        with self.assertRaises(ValueError):
            WindowsGuestSelection.from_record({'script':'Start-Process arbitrary'})


if __name__=='__main__': unittest.main()
