"""One selected Windows Server 2022 VM through current, certificate-only WinRM.

The enrolled Vault role issues a new short-lived client certificate for each
SOAP exchange. Shell creation, command execution, result polling and cleanup
all recheck the same original B10 grant and claimed B11 intent. A successful
process is readback material, never independent native acceptance.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import http.client
from pathlib import Path
import socket
import ssl
import time
from urllib.parse import urlsplit
from uuid import UUID, uuid4
import xml.etree.ElementTree as ET

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.x509.oid import ExtendedKeyUsageOID, ObjectIdentifier

from provisioner.controlplane.jobs.repository import _digest
from provisioner.controlplane.persistence.store import NativeBinding, OwnerLease
from provisioner.controlplane.reconciliation.registry import NativeOperationRegistry
from provisioner.execution.neutron_observe import strict_loads
from provisioner.execution.run_files import digest, encoded, private_path, read_private, require, sync_directory, utcnow, write_new
from provisioner.execution.windows_guest import WindowsGuestSelection
from .command_runtime import SelectedWorkerCommandAuthority, WorkerCommandRuntime
from .grants import CredentialBroker
from .vault import VaultDynamicCredentialIssuer
from .vault_consumer import VaultCredentialConsumer

SOAP = 'http://www.w3.org/2003/05/soap-envelope'
ADDRESS = 'http://schemas.xmlsoap.org/ws/2004/08/addressing'
WSMAN = 'http://schemas.dmtf.org/wbem/wsman/1/wsman.xsd'
WINDOWS = 'http://schemas.microsoft.com/wbem/wsman/1/wsman.xsd'
SHELL = 'http://schemas.microsoft.com/wbem/wsman/1/windows/shell'
TRANSFER = 'http://schemas.xmlsoap.org/ws/2004/09/transfer'
RESOURCE = SHELL + '/cmd'
POWER_SHELL = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
_UPN = ObjectIdentifier('1.3.6.1.4.1.311.20.2.3')


def _node(parent, namespace, name, text=None, **attributes):
    child = ET.SubElement(parent, '{'+namespace+'}'+name, attributes)
    child.text = text
    return child


def _one(parent, namespace, name):
    nodes = parent.findall('.//{'+namespace+'}'+name)
    require(len(nodes) == 1, 'WinRM response has no unique original '+name)
    return nodes[0]


def _guid(value):
    require(type(value) is str and len(value) <= 41, 'Bounded native WinRM GUID required')
    normalized = value[5:] if value.startswith('uuid:') else value
    require(str(UUID(normalized)) == normalized.lower(), 'Canonical native WinRM GUID required')
    return value


class WindowsGuestIntent:
    """The actual original resource lease and one-time native intent claim."""
    def __init__(self, runtime, admitted, selection, step, descriptor, *, packet=None):
        require(type(runtime) is ScopedWindowsGuestRuntime and type(descriptor) is WindowsGuestSelection
                and step['kind'] in {'windows_guest_apply', 'windows_guest_remediate'},
                'Concrete original Windows stage required')
        self.runtime, self.admitted, self.selection, self.step = runtime, admitted, selection, step
        self.descriptor, self.selection_digest = descriptor, _digest(selection)
        self.operation_kind, self.claimed = 'GUEST_CONFIG', False
        self.remediation_packet = packet
        require(step['kind'] != 'windows_guest_remediate' or type(packet) is dict,
                'The exact separately approved Windows remediation packet is required')

    def require_current(self):
        runtime, original = self.runtime.command_runtime, self.runtime.command_runtime.grant
        require(runtime.verifier.verify(runtime.transport_evidence) == runtime.identity,
                'Original Windows worker mTLS peer changed')
        def checked(_reference, grant, deadline):
            require(grant == original, 'The original Windows grant changed')
            return grant, deadline
        grant, deadline = runtime.grants.with_authorized_reference(runtime.context, runtime.identity,
            original.grant_id, **runtime.grant_arguments(self.admitted), use=checked)
        options = dict(continuation_grant=grant, continuation_identity=runtime.identity) if self.claimed else {}
        plan, current = runtime.authority.require_current(self.admitted, self.selection_digest,
                                                         self.operation_kind, **options)
        from provisioner.controlplane.workflow.windows_service_selection import DRIVER,WindowsServiceSelection
        if current.get('driver')==DRIVER:
            purpose=WindowsServiceSelection.from_record(current['windowsServices'])
            purpose.require_guest(self.descriptor)
            require(purpose.to_dict()['write']=={'stepId':self.step['id'],'kind':self.step['kind'],
                'operationId':grant.operation_id}, 'Windows native intent differs from the exact approved fixed service operation')
        lease = self.runtime.lease
        mappings = [row for row in plan['spec']['machineMappings']
                    if row['targetMachineId'] == self.descriptor.to_dict()['machine_id']]
        require(current == self.selection and current['guestProfile'] == 'windows-server-2022'
                and plan['spec']['route']['guestProfile'] == 'windows-server-2022'
                and len(mappings) == 1 and mappings[0]['machineId'] in plan['spec']['selectedMachineIds']
                and grant.operation_kind == 'GUEST_CONFIG' and grant.operation_scope == grant.destination
                and grant.step_id == self.step['id']
                and (lease.organization_id,lease.tenant_id,lease.worker_id,lease.epoch,lease.workload_id) ==
                    (grant.organization_id,grant.tenant_id,grant.worker_subject,grant.lease_epoch,self.selection['workloadId'])
                and lease.binding == NativeBinding.from_record(self.descriptor.to_dict()['native_binding'])
                and (lease.binding.platform_family,lease.binding.endpoint_id,lease.binding.native_scope_id,
                     lease.security_domain_id) ==
                    (grant.operation_scope.platform_family,grant.operation_scope.endpoint_id,
                     grant.operation_scope.native_scope_id,grant.operation_scope.security_domain_id),
                'Windows commands changed the original selected VM, purpose, grant or resource lease')
        deadline = min(deadline,lease.expires_at,runtime.identity.expires_at)
        require(deadline > utcnow(), 'Original Windows native authority has expired')
        if self.step['kind'] == 'windows_guest_remediate':
            from .windows_services import require_remediation
            require_remediation(self.runtime, self.admitted, self.selection, self.step, self.remediation_packet)
        return grant, deadline

    def claim(self, authority):
        require(type(authority) is SelectedWorkerCommandAuthority and authority.intent_guard is self
                and authority.runtime is self.runtime.command_runtime and not self.claimed,
                'Only the concrete original selected Windows command may claim its intent')
        grant, _deadline = authority.require_current()
        runtime = self.runtime
        runtime.registry.prepare(authority.runtime.context,runtime.lease,grant.operation_scope,
            job_id=self.admitted.job_id,grant_id=grant.grant_id,step_id=self.step['id'],
            lease_key=grant.lease_key,worker_identity=authority.runtime.identity,
            operation_id=grant.operation_id,operation_kind=self.operation_kind,
            request_digest=_digest({'selection':self.selection_digest,'windows':self.descriptor.sha256,
                                   'packet':authority.packet,'purpose':'selected-windows-service-configuration'}))
        require(runtime.registry.claim_once(authority.runtime.context,runtime.lease,grant.operation_scope,
                    grant.operation_id,authority.runtime.identity), 'Original Windows intent already claimed')
        self.claimed = True
        authority.require_current()


@dataclass(frozen=True)
class ScopedWindowsGuestRuntime:
    command_runtime: WorkerCommandRuntime
    broker: CredentialBroker
    consumer: VaultCredentialConsumer
    registry: NativeOperationRegistry
    lease: OwnerLease
    original_intent: object | None = None

    def __post_init__(self):
        from provisioner.controlplane.workflow.windows_service_selection import WindowsOriginalServiceIntent
        require(self.original_intent is None or type(self.original_intent) is WindowsOriginalServiceIntent,
                'Windows remediation may retain exact original references, never hydrated native authority')
        command = self.command_runtime
        require(type(command) is WorkerCommandRuntime and type(self.broker) is CredentialBroker
                and type(self.consumer) is VaultCredentialConsumer
                and isinstance(self.consumer.issuer,VaultDynamicCredentialIssuer)
                and isinstance(self.registry,NativeOperationRegistry) and type(self.lease) is OwnerLease
                and self.registry._grants is command.grants
                and self.broker._grants is command.grants and self.broker._identities is command.verifier
                and self.broker._issuer is self.consumer.issuer and command.grant.operation_kind == 'GUEST_CONFIG',
                'Concrete enrolled Windows worker, dynamic role, native registry and resource lease required')
        matching = [role for role in self.consumer.issuer._roles.values()
                    if role.scope == command.grant.operation_scope and role.operation_kind == 'GUEST_CONFIG']
        require(len(matching) == 1, 'One exact commissioned Windows certificate role required')

    def run_step(self, admitted, selection, plan, step, packet, directory, base, root):
        from provisioner.execution import delivery_steps
        require(step['kind'] in {'windows_guest_apply', 'windows_guest_remediate'}
                and selection['guestProfile'] == 'windows-server-2022',
                'Only the separately selected Windows Server 2022 service stage is implemented')
        original = self.command_runtime.authority.require_packet(admitted,_digest(selection),plan,step,packet,'GUEST_CONFIG')
        delivery_steps.validate_packet(step,packet,plan,base,root=root)
        paths = delivery_steps.file_paths(packet)
        descriptor = WindowsGuestSelection(read_private(paths['windows_selection']))
        require(original['spec']['destination']['platformFamily'] == self.lease.binding.platform_family,
                'Windows stage changed its selected destination platform')
        guard = WindowsGuestIntent(self,admitted,selection,step,descriptor,packet=packet)
        authority = self.command_runtime.select(admitted,selection,plan,step,packet,root,intent_guard=guard)
        output = private_path(directory,directory=True)
        guard.claim(authority)
        try:
            result = self.execute_selected(authority,descriptor,paths['winrm_ca'],output)
            write_new(output/'result.json',encoded(result))
            return delivery_steps.complete(step,packet,output,plan,result,['result.json'])
        except BaseException:
            self.registry.mark_uncertain(self.command_runtime.context,
                self.command_runtime.grant.operation_id,self.command_runtime.identity.subject)
            raise

    def execute_selected(self, authority, descriptor, ca_path, output):
        require(type(authority) is SelectedWorkerCommandAuthority and authority.runtime is self.command_runtime
                and type(authority.intent_guard) is WindowsGuestIntent
                and authority.intent_guard.runtime is self and authority.intent_guard.claimed is True
                and authority.intent_guard.descriptor == descriptor,
                'Claimed original selected Windows native intent required before remote contact')
        directory = private_path(output,directory=True)
        descriptor_file = authority.packet['files']['windows_selection']
        ca_file = authority.packet['files']['winrm_ca']
        require(descriptor_file['sha256'] == descriptor.sha256
                and read_private(descriptor_file['path']) == descriptor.canonical
                and Path(ca_file['path']) == Path(ca_path)
                and digest(read_private(ca_path)) == ca_file['sha256'] == descriptor.to_dict()['ca_sha256'],
                'Original Windows selection or listener CA changed')
        channel = _WinRM(self,authority,descriptor,Path(ca_path),directory)
        observations = [channel.action('IDENTITY')]
        for service in descriptor.to_dict()['services']:
            observations.append(channel.action('OBSERVE_SERVICE',service))
            observations.append(channel.action('SET_STARTUP',service))
            observations.append(channel.action('START_SERVICE' if service['state']=='Running' else 'STOP_SERVICE',service))
            current = channel.action('OBSERVE_SERVICE',service)
            require(current['observation']['service']['state'] == service['state']
                    and current['observation']['service']['startup'] ==
                        {'Automatic':'Auto','Manual':'Manual','Disabled':'Disabled'}[service['startup']],
                    'Windows service readback differs from its original requested state or startup mode')
            observations.append(current)
        authority.require_current()
        result = {'format':'hosting-windows-guest-result/1','status':'CONFIGURED_REQUIRES_NATIVE_ACCEPTANCE',
                'native_acceptance':False,'production_activation':False,'guest_profile':'windows-server-2022',
                'job_id':authority.admitted.job_id,'operation_id':self.command_runtime.grant.operation_id,
                'selection_sha256':descriptor.sha256,'native_binding':descriptor.to_dict()['native_binding'],
                'source_commit':authority.selection['sourceCommit'],'scope':authority.selection['executionScope'],
                'observations':observations,'exchanges':channel.receipts}
        if authority.step['kind']=='windows_guest_remediate':
            from .windows_services import require_remediation
            original=require_remediation(self,authority.admitted,authority.selection,authority.step,authority.packet)
            result.update(original_operation_id=original.operation_id,original_request_digest=original.request_digest,
                original_selection_sha256=WindowsGuestSelection(read_private(
                    authority.packet['files']['original_windows_selection']['path'])).sha256)
        return result


class _PinnedWinRMConnection(http.client.HTTPSConnection):
    def __init__(self, descriptor, context, timeout):
        value = descriptor.to_dict(); endpoint = urlsplit(value['endpoint'])
        super().__init__(value['server_name'],endpoint.port,context=context,timeout=timeout)
        self.selection = value

    def connect(self):
        raw = socket.create_connection((self.selection['connect_ip'],self.port),self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw,server_hostname=self.selection['server_name'])
            require(digest(self.sock.getpeercert(binary_form=True)) == self.selection['server_certificate_sha256'],
                    'The actual commissioned WinRM listener certificate differs')
        except BaseException:
            raw.close()
            if self.sock is not None: self.sock.close()
            self.sock = None
            raise


def _upn(cert):
    names = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    values = [name.value for name in names if isinstance(name,x509.OtherName) and name.type_id == _UPN]
    require(len(values) == 1, 'One exact WinRM certificate UPN required')
    value = values[0]
    # The Microsoft UPN otherName is a bounded ASN.1 UTF8String.
    require(len(value) >= 2 and value[0] == 0x0c, 'WinRM certificate UPN is not a UTF8String')
    start, length = 2, value[1]
    if length & 0x80:
        count = length & 0x7f
        require(1 <= count <= 2 and len(value) >= 2+count, 'Bounded WinRM UPN length required')
        start, length = 2+count, int.from_bytes(value[2:2+count],'big')
    require(start+length == len(value) and 1 <= length <= 320, 'Bounded complete WinRM UPN required')
    return value[start:].decode('utf-8')


class _WinRM:
    def __init__(self,runtime,authority,descriptor,ca,directory):
        self.runtime,self.authority,self.descriptor,self.ca,self.directory = runtime,authority,descriptor,ca,directory
        self.receipts = []; self.seen = set()

    def _credential(self):
        grant, deadline = self.authority.require_current()
        handle = self.runtime.broker.acquire(self.authority.runtime.transport_evidence,
            self.authority.runtime.context,grant_id=grant.grant_id,
            **self.authority.runtime.grant_arguments(self.authority.admitted))
        self.authority.require_current()
        material = self.runtime.consumer.unwrap(handle,grant)
        self.authority.require_current()
        value, data = self.descriptor.to_dict(),material.data.get('winrm')
        require(type(data) is dict and data.keys() == {'format','grant_id','selection_sha256','endpoint',
            'mapped_user','certificate_pem','private_key_pem'}
            and data['format']=='hosting-winrm-dynamic-certificate/1' and data['grant_id']==grant.grant_id
            and data['selection_sha256']==self.descriptor.sha256 and data['endpoint']==value['endpoint']
            and data['mapped_user']==value['mapped_user']
            and all(type(data[key]) is str and 1 <= len(data[key].encode()) <= 16384
                    for key in ('certificate_pem','private_key_pem')),
            'The exact selected WinRM listener, guest identity and dynamic certificate grant are required')
        cert = x509.load_pem_x509_certificate(data['certificate_pem'].encode())
        key = serialization.load_pem_private_key(data['private_key_pem'].encode(),password=None)
        require(cert.subject.rfc4514_string()==value['certificate_subject']
                and _upn(cert)==value['certificate_upn']
                and cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca is False
                and set(cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value)=={ExtendedKeyUsageOID.CLIENT_AUTH}
                and cert.public_key().public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)==
                    key.public_key().public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)
                and cert.not_valid_before_utc <= utcnow() < cert.not_valid_after_utc <= min(deadline,material.expires_at),
                'WinRM certificate identity, key, client-only usage or actual bounded expiry differs')
        require(cert.serial_number not in self.seen, 'WinRM role reused a previously consumed certificate')
        self.seen.add(cert.serial_number)
        return material,data,min(deadline,material.expires_at,cert.not_valid_after_utc)

    def request(self, action, body=None, *, shell=None, options=None):
        require(action in {'Create','Command','Receive','Signal','Delete'}
                and (shell is None) == (action=='Create'), 'One exact owned WinRM protocol action required')
        material,data,deadline = self._credential()
        message = 'uuid:'+str(uuid4())
        uri = (TRANSFER if action in {'Create','Delete'} else SHELL)+'/'+action
        envelope = ET.Element('{'+SOAP+'}Envelope')
        header = _node(envelope,SOAP,'Header'); packet = _node(envelope,SOAP,'Body')
        _node(header,ADDRESS,'To',self.descriptor.to_dict()['endpoint'])
        _node(header,ADDRESS,'Action',uri,**{'{'+SOAP+'}mustUnderstand':'true'})
        _node(header,ADDRESS,'MessageID',message)
        reply = _node(header,ADDRESS,'ReplyTo')
        _node(reply,ADDRESS,'Address',ADDRESS+'/role/anonymous')
        _node(header,WSMAN,'ResourceURI',RESOURCE,**{'{'+SOAP+'}mustUnderstand':'true'})
        _node(header,WSMAN,'MaxEnvelopeSize','153600',**{'{'+SOAP+'}mustUnderstand':'true'})
        seconds = min(10,(deadline-utcnow()).total_seconds())
        require(seconds > .1, 'No remaining original WinRM exchange authority')
        _node(header,WSMAN,'OperationTimeout',f'PT{seconds:.3f}S')
        for namespace in (WSMAN,WINDOWS):
            _node(header,namespace,'Locale' if namespace==WSMAN else 'DataLocale',
                  **{'{http://www.w3.org/XML/1998/namespace}lang':'en-US'})
        if shell is not None:
            selectors = _node(header,WSMAN,'SelectorSet')
            _node(selectors,WSMAN,'Selector',_guid(shell),Name='ShellId')
        if options:
            selected = _node(header,WSMAN,'OptionSet')
            for name,value in options.items(): _node(selected,WSMAN,'Option',value,Name=name)
        if body is not None: packet.append(body)
        raw = ET.tostring(envelope,encoding='utf-8',xml_declaration=True)
        require(len(raw) <= 153600, 'Owned WinRM request exceeds its bound')
        folder = self.directory/('credential-'+uuid4().hex); folder.mkdir(mode=0o700)
        connection = None
        try:
            write_new(folder/'certificate.pem',data['certificate_pem'].encode())
            write_new(folder/'private-key.pem',data['private_key_pem'].encode())
            require(digest(read_private(self.ca))==self.descriptor.to_dict()['ca_sha256'],
                    'Original WinRM listener CA changed before contact')
            tls = ssl.create_default_context(cadata=read_private(self.ca).decode('ascii'))
            tls.minimum_version = ssl.TLSVersion.TLSv1_2
            tls.load_cert_chain(str(folder/'certificate.pem'),str(folder/'private-key.pem'))
            self.authority.require_current()
            timeout = min(12,(deadline-utcnow()).total_seconds())
            require(timeout > 0, 'Original WinRM credential expired before contact')
            connection = _PinnedWinRMConnection(self.descriptor,tls,timeout)
            connection.connect()
            self.authority.require_current()
            connection.request('POST','/wsman',body=raw,headers={
                'Content-Type':'application/soap+xml;charset=UTF-8',
                'Authorization':'http://schemas.dmtf.org/wbem/wsman/1/wsman/secprofile/https/mutual',
                'Connection':'close','Accept':'application/soap+xml'})
            response = connection.getresponse(); payload = response.read(153601)
            self.authority.require_current()
            require(len(payload)<=153600 and response.status in {200,500}
                    and response.headers.get_content_type()=='application/soap+xml'
                    and b'<!DOCTYPE' not in payload.upper() and b'<!ENTITY' not in payload.upper(),
                    'WinRM did not return one bounded original SOAP response')
            parsed = ET.fromstring(payload)
            require(parsed.tag=='{'+SOAP+'}Envelope'
                    and _one(parsed,ADDRESS,'RelatesTo').text==message,
                    'WinRM response does not belong to this original exchange')
            fault = parsed.find('.//{'+SOAP+'}Fault')
            if fault is not None:
                code = parsed.find('.//{http://schemas.microsoft.com/wbem/wsman/1/wsmanfault}WSManFault')
                require(action=='Receive' and code is not None and code.get('Code')=='2150858793',
                        'Original WinRM request failed; retain native uncertainty')
                timeout_fault = True
            else:
                require(response.status==200 and _one(parsed,ADDRESS,'Action').text==uri+'Response',
                        'WinRM response changed its original action')
                timeout_fault = False
            receipt = {'action':action,'message_id':message,'request_sha256':digest(raw),
                       'response_sha256':digest(payload),'credential_lease_digest':material.lease_digest,
                       'role_reference':material.role_reference,'observed_at':utcnow().isoformat()}
            self.receipts.append(receipt)
            write_new(self.directory/f'exchange-{len(self.receipts):04d}.json',encoded(receipt))
            return None if timeout_fault else _one(parsed,SOAP,'Body')
        finally:
            if connection is not None: connection.close()
            (folder/'certificate.pem').unlink(missing_ok=True)
            (folder/'private-key.pem').unlink(missing_ok=True)
            folder.rmdir(); sync_directory(self.directory)

    def action(self, action, service=None):
        from .windows_services import WindowsServiceReadAuthority
        if type(self.authority) is WindowsServiceReadAuthority:
            require(action in {'IDENTITY', 'OBSERVE_SERVICE'},
                    'Independent Windows reader cannot dispatch a native service mutation')
        selected = self.descriptor.to_dict(); grant = self.authority.runtime.grant
        script = self.descriptor.script(action,job_id=self.authority.admitted.job_id,
                                        operation_id=grant.operation_id,service=service)
        opened = ET.Element('{'+SHELL+'}Shell')
        _node(opened,SHELL,'InputStreams','stdin'); _node(opened,SHELL,'OutputStreams','stdout stderr')
        _node(opened,SHELL,'IdleTimeOut','PT30S')
        response = self.request('Create',opened,options={'WINRS_NOPROFILE':'TRUE','WINRS_CODEPAGE':'65001'})
        created = _one(response,TRANSFER,'ResourceCreated')
        require(_one(created,WSMAN,'ResourceURI').text==RESOURCE
                and _one(created,ADDRESS,'Address').text==selected['endpoint'],
                'Created WinRM shell changed its fixed native listener or resource URI')
        selector = _one(created,WSMAN,'Selector')
        require(selector.get('Name') in {'ShellId','ShellID'}, 'Original WinRM shell selector required')
        shell = _guid(selector.text)
        line = ET.Element('{'+SHELL+'}CommandLine'); _node(line,SHELL,'Command',POWER_SHELL)
        _node(line,SHELL,'Arguments','-NoLogo -NoProfile -NonInteractive -EncodedCommand '+script)
        response = self.request('Command',line,shell=shell,
                                options={'WINRS_CONSOLEMODE_STDIN':'FALSE','WINRS_SKIP_CMD_SHELL':'TRUE'})
        command = _guid(_one(response,SHELL,'CommandId').text)
        stdout,stderr = bytearray(),bytearray(); finished = False
        deadline = time.monotonic()+60
        for _poll in range(32):
            require(time.monotonic()<deadline, 'WinRM command result interval expired; retain uncertainty')
            receive = ET.Element('{'+SHELL+'}Receive')
            _node(receive,SHELL,'DesiredStream','stdout stderr',CommandId=command)
            response = self.request('Receive',receive,shell=shell)
            if response is None: continue
            for stream in response.findall('.//{'+SHELL+'}Stream'):
                require(stream.get('CommandId')==command and stream.get('Name') in {'stdout','stderr'},
                        'WinRM output belongs to another command or unselected stream')
                decoded = base64.b64decode(stream.text or '',validate=True)
                target = stdout if stream.get('Name')=='stdout' else stderr
                target.extend(decoded)
                require(len(stdout)<=65536 and len(stderr)<=16384,'Windows command output exceeds its bound')
            state = _one(response,SHELL,'CommandState')
            require(state.get('CommandId')==command and state.get('State') in
                    {SHELL+'/CommandState/Running',SHELL+'/CommandState/Done'},
                    'WinRM readback changed its original command identity or state')
            if state.get('State')==SHELL+'/CommandState/Done':
                require(_one(state,SHELL,'ExitCode').text=='0' and not stderr,
                        'Windows command has no successful bounded readback; retain uncertainty')
                finished = True; break
        require(finished,'WinRM command did not finish inside its current polling bound')
        # Protocol cleanup remains an original authorized request, never a
        # revocation exemption or a newly fabricated cleanup permission.
        signal = ET.Element('{'+SHELL+'}Signal',{'CommandId':command})
        _node(signal,SHELL,'Code',SHELL+'/signal/terminate')
        self.request('Signal',signal,shell=shell); self.request('Delete',shell=shell)
        observed = strict_loads(bytes(stdout).decode('utf-8-sig').strip().encode('utf-8'))
        require(type(observed) is dict and observed.keys()=={'format','action','job_id','operation_id',
            'selection_sha256','observation'} and observed['format']=='hosting-windows-guest-observation/1'
            and (observed['action'],observed['job_id'],observed['operation_id'],observed['selection_sha256'])==
                (action,self.authority.admitted.job_id,grant.operation_id,self.descriptor.sha256),
                'PowerShell readback changed its original guest selection, job or action')
        identity = observed['observation']
        require(type(identity) is dict and identity.keys()==({'build','machine_guid','native_uuid','principal'} |
                ({'service'} if service is not None else set())) and identity['build']=='20348'
                and identity['machine_guid']==selected['machine_guid'] and identity['native_uuid']==selected['native_uuid']
                and identity['principal'].lower()==selected['mapped_user'].lower(),
                'Readback is not the original Windows Server 2022 native guest or mapped identity')
        if service is not None:
            row = identity['service']
            require(type(row) is dict and row.keys()=={'name','state','startup','image_path','executable_sha256'}
                    and row['name']==service['name'] and row['image_path']==service['image_path']
                    and row['executable_sha256']==service['binary_sha256']
                    and row['state'] in {'Running','Stopped'} and row['startup'] in {'Auto','Manual','Disabled'},
                    'Windows service readback changed its original binary or exact existing service')
        self.authority.require_current()
        return observed
