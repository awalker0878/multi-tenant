"""Private Glance v2.7 create/upload and independent original UUID readback.

No name search, web-download, remote location, image delete, target VM create or
guest boot is exposed here. Losing a response preserves its original intent;
neither a private artifact nor a 201/204 response is native acceptance.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import http.client
import os
from pathlib import Path
import re
import stat
import time
from urllib.parse import urlsplit
from uuid import uuid4

from provisioner.controlplane.jobs.repository import _tenant
from provisioner.controlplane.reconciliation import NativeObservation, RecoveryHeld
from provisioner.controlplane.reconciliation.planned_image import PlannedImageRegistry, PlannedImageLease, NativeImageObservation
from provisioner.controlplane.reconciliation.read_enrollment import NativeReadEnrollment
from provisioner.controlplane.worker.grants import CredentialBroker
from provisioner.controlplane.worker.vault_consumer import ConsumedVaultCredential, VaultCredentialConsumer
from provisioner.execution import readback_core as c, terraform_run
from provisioner.execution.run_files import encoded, load_private, private_path, require, utcnow, write_new
from .cold_authority import ColdImageAuthority
from .cold_capture import ColdCaptureStore, _ca
from .cold_selection import ColdVmSelection
from .resources import LinuxTransferResources

FORMAT = 'hosting-glance-original-image-observation/1'
_HASH_ALGORITHMS = {'sha256':'output_sha256','sha512':'output_sha512'}


class ImagePending(RecoveryHeld):
    """The selected exact image still has unfinished native upload work."""


def image_metadata(lease,inputs,cold):
    """Fixed identity/digest metadata, never caller-provided image properties."""
    return {'name':inputs['image_name'],'disk_format':'qcow2','container_format':'bare',
        'visibility':'private','protected':True,'min_ram':0,'min_disk':(inputs['virtual_bytes']+2**30-1)//2**30,
        'tags':[],'hosting_job_id':lease.owner.job_id,'hosting_image_request_digest':lease.owner.request_digest,
        'hosting_cold_selection_digest':cold.sha256,'hosting_source_capture_digest':inputs['capture_digest'],
        'hosting_source_snapshot_moid':inputs['source_snapshot_moid'],'hosting_source_disk_id':inputs['disk_id'],
        'hosting_image_sha256':inputs['output_sha256']}


def image_facts(image,native_id,scope,metadata,inputs,phase):
    require(type(image) is dict and image.get('id') == native_id and image.get('owner') == scope.native_scope_id
            and {'id','owner','file','self','schema','status','size','virtual_size','os_hash_algo','os_hash_value'} <= image.keys()
            and phase in {'CREATE','UPLOAD'}
            and not c.differences(image,metadata) and image.get('file') == '/v2/images/'+native_id+'/file'
            and image.get('self') == '/v2/images/'+native_id and image.get('schema') == '/v2/schemas/image'
            and image.get('kernel_id') is None and image.get('ramdisk_id') is None
            and image.get('locations') in (None,[]) and image.get('direct_url') is None,
            'The actual native image differs from the original UUID, project, private metadata or safe byte owner')
    if phase == 'CREATE':
        require(image.get('status') == 'queued' and image.get('size') is None
                and image.get('os_hash_algo') is None and image.get('os_hash_value') is None,
                'The original image create is not an empty quiesced queued private image')
    else:
        if image.get('status') in {'queued','saving'}:
            raise ImagePending('The original image upload is not yet natively complete')
        require(image.get('status') == 'active' and type(image.get('size')) is int
                and image['size'] == inputs['output_bytes'] and image.get('os_hash_algo') in _HASH_ALGORITHMS
                and image.get('os_hash_value') == inputs[_HASH_ALGORITHMS[image['os_hash_algo']]]
                and image.get('virtual_size') == inputs['virtual_bytes'],
                'Native image extent, virtual disk size or secure multihash differs from retained converted bytes')
    fields = set(metadata)|{'id','owner','file','self','schema','status','size','virtual_size','os_hash_algo','os_hash_value'}
    return {field:image.get(field) for field in sorted(fields)}


class _GlanceContact:
    def __init__(self,enrollment,cold,material,ca_bundle,*,cursor=None):
        require(isinstance(enrollment,(ColdImageAuthority,NativeReadEnrollment)) and isinstance(cold,ColdVmSelection)
                and isinstance(material,ConsumedVaultCredential),
                'Actual current image command or independently enrolled native reader required')
        require(cursor is None or type(enrollment) is NativeReadEnrollment,
                'Only an independently enrolled image read may reuse the original observation transaction')
        self.enrollment,self.cold,self.material,self.cursor = enrollment,cold,material,cursor
        self.selected = cold.to_dict()['destination_contact']; self.scope = enrollment.scope
        self.tls = _ca(ca_bundle,self.selected['ca_sha256'])
        require(type(material.data) is dict and material.data.keys() == {'environment','cloud'}
                and material.data['environment'] == {}, 'The dynamic image role cannot borrow backend or guest credentials')
        cloud = terraform_run.cloud_config(encoded(material.data['cloud']),self.selected['cloud_alias'])['clouds'][self.selected['cloud_alias']]
        require((cloud['auth']['auth_url'],cloud['region_name'],cloud['interface']) ==
                (self.selected['identity_endpoint'],self.selected['region'],self.selected['interface']),
                'The dynamic image credential changed the commissioned native identity/catalogue')
        self.identity_credential = cloud['auth']
        self.token,self.token_expires = None,None
        self._authenticate()

    def _current(self):
        options={'cursor':self.cursor} if self.cursor is not None else {}
        _grant,deadline = self.enrollment.require_current(**options)
        deadline = min(deadline,self.material.expires_at)
        if self.token_expires is not None: deadline = min(deadline,self.token_expires)
        require(deadline > utcnow(), 'The next native image contact has no current enrolled credential interval')
        return min(10,(deadline-utcnow()).total_seconds())

    def _json(self,endpoint,method,suffix,body=None,*,accepted=(200,)):
        address = urlsplit(endpoint); headers = {'Accept':'application/json','Accept-Encoding':'identity','Connection':'close'}
        if self.token is not None: headers['X-Auth-Token'] = self.token
        if body is not None: headers['Content-Type'] = 'application/json'
        timeout = self._current(); end = time.monotonic()+timeout
        connection = http.client.HTTPSConnection(address.hostname,address.port or 443,context=self.tls,timeout=timeout)
        try:
            connection.request(method,address.path+suffix,body=encoded(body) if body is not None else None,headers=headers)
            response = connection.getresponse(); raw = bytearray()
            lengths = response.headers.get_all('Content-Length',[])
            require(len(lengths) <= 1 and (not lengths or (lengths[0].isdigit() and int(lengths[0]) <= c.LIMIT))
                    and not (lengths and response.getheader('Transfer-Encoding')),
                    'Native image response framing is ambiguous or unbounded')
            socket = connection.sock
            while True:
                remaining = end-time.monotonic()
                require(remaining > 0, 'Native image response exceeded its bounded original interval')
                if socket and socket.fileno() >= 0: socket.settimeout(remaining)
                chunk = response.read1(min(65536,c.LIMIT+1-len(raw)))
                if not chunk: break
                raw.extend(chunk); require(len(raw) <= c.LIMIT, 'Native image response exceeded its byte bound')
            # The create owner first retains an actual late UUID. No following
            # native contact or acceptance may use an expired/revoked grant.
            if not (method == 'POST' and suffix == '/images'):
                self._current()
            require(response.status in accepted and len(raw) <= c.LIMIT
                    and (not lengths or len(raw) == int(lengths[0]))
                    and response.headers.get_content_type() == 'application/json'
                    and response.getheader('Content-Encoding','identity') == 'identity',
                    'The native image exchange failed or returned an unbounded/encoded representation')
            value = c.strict_loads(raw); require(type(value) is dict, 'Native image JSON object required')
            retained = {}
            for field in ('X-Subject-Token','X-Openstack-Request-Id'):
                values = response.headers.get_all(field,[])
                require(len(values) <= 1, 'Native identity/request header is ambiguous')
                if values:
                    c.text(values[0],length=4096); retained[field.lower()] = values[0]
            return value,retained
        finally:
            connection.close()

    def _authenticate(self):
        credential = self.identity_credential
        value,headers = self._json(self.selected['identity_endpoint'],'POST','/auth/tokens',
            {'auth':{'identity':{'methods':['application_credential'],'application_credential':{
                'id':credential['application_credential_id'],'secret':credential['application_credential_secret']}}}},accepted=(201,))
        token = value.get('token'); read = isinstance(self.enrollment,NativeReadEnrollment)
        require(type(token) is dict and token.get('methods') == ['application_credential']
                and token.get('application_credential',{}).get('id') == credential['application_credential_id']
                and token.get('project',{}).get('id') == self.scope.native_scope_id
                and token.get('system') is None and token.get('domain') is None and type(token.get('roles')) is list
                and len(token['roles']) == 1 and type(token['roles'][0]) is dict
                and {role.get('name') for role in token['roles']} == ({'reader'} if read else {'member'})
                and headers.get('x-subject-token'), 'Actual image credential is not the exact native project read/member role')
        endpoints = [endpoint for service in token.get('catalog',[]) if service.get('type') == 'image'
            for endpoint in service.get('endpoints',[]) if endpoint.get('interface') == self.selected['interface']
            and endpoint.get('region_id',endpoint.get('region')) == self.selected['region']]
        require(len(endpoints) == 1 and endpoints[0].get('url','').rstrip('/') == self.selected['glance_endpoint'],
                'The actual image catalogue escaped the commissioned HTTPS Glance v2 endpoint')
        self.token = headers['x-subject-token']; c.text(self.token,length=4096)
        require(not any(character.isspace() or ord(character)>126 for character in self.token), 'Invalid native image token header')
        self.token_expires = c.timestamp(token['expires_at']); self._current()

    def get(self,native_id):
        require(type(native_id) is str and c.UUID.fullmatch(native_id), 'Actual original native image UUID required')
        if isinstance(self.enrollment,ColdImageAuthority):
            authority=self.enrollment
            require(native_id == authority.registry.native_image(authority.command.context,authority.image_lease),
                    'The native image contact cannot borrow another response UUID')
        return self._json(self.selected['glance_endpoint'],'GET','/images/'+native_id)[0]

    def create(self,metadata):
        require(isinstance(self.enrollment,ColdImageAuthority) and self.enrollment.claimed
                and self.enrollment.phase == 'CREATE', 'Native create requires its separate original claimed image action')
        authority=self.enrollment
        inputs=authority.registry.inputs(authority.command.context,authority.image_lease)
        require(metadata == image_metadata(authority.image_lease,inputs,self.cold),
                'Native image create metadata must derive from its exact original immutable input owner')
        authority.begin_native_send()
        value,headers = self._json(self.selected['glance_endpoint'],'POST','/images',metadata,accepted=(201,))
        native_id,request_id = value.get('id'),headers.get('x-openstack-request-id')
        require(type(native_id) is str and c.UUID.fullmatch(native_id) and type(request_id) is str
                and request_id.startswith('req-') and c.UUID.fullmatch(request_id[4:]),
                'Native image create returned no genuine exact UUID/request identity')
        self.enrollment.registry.retain_created(self.enrollment.command.context,
            self.enrollment.row['operation_id'],self.enrollment.command.identity.subject,native_id,request_id)
        self._current()
        return native_id,request_id

    def upload(self,native_id,path,inputs,resources):
        require(isinstance(self.enrollment,ColdImageAuthority) and self.enrollment.claimed
                and self.enrollment.phase == 'UPLOAD' and c.UUID.fullmatch(native_id),
                'Native binary upload requires its separate original claimed image action')
        authority=self.enrollment;lease=authority.image_lease
        current_inputs=authority.registry.inputs(authority.command.context,lease)
        selected_path,converted=authority.registry.leases.captures.image(lease.capture_digest,self.cold,lease.disk_id)
        require(native_id == authority.registry.native_image(authority.command.context,lease)
                and inputs == current_inputs and Path(path) == selected_path
                and converted['outputSha256'] == inputs['output_sha256']
                and converted['outputBytes'] == inputs['output_bytes']
                and isinstance(resources,LinuxTransferResources) and resources == self.cold.transfer_resources(),
                'Native upload must use its original accepted image UUID, sealed converted bytes and commissioned I/O owner')
        resources.require_current()
        authority.begin_native_send()
        descriptor = os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
        address = urlsplit(self.selected['glance_endpoint']); connection = None
        try:
            before = os.fstat(descriptor)
            require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size == inputs['output_bytes']
                    and before.st_mode & 0o777 == 0o400, 'Original sealed converted image extent changed')
            connection = http.client.HTTPSConnection(address.hostname,address.port or 443,context=self.tls,timeout=self._current())
            connection.putrequest('PUT',address.path+'/images/'+native_id+'/file',skip_accept_encoding=True)
            for key,value in {'X-Auth-Token':self.token,'Content-Type':'application/octet-stream',
                'Content-Length':str(before.st_size),'X-Openstack-Image-Size':str(before.st_size),
                'Connection':'close'}.items(): connection.putheader(key,value)
            connection.endheaders()
            count = 0; sha = hashlib.sha256(); start = time.monotonic()
            with os.fdopen(descriptor,'rb',closefd=False) as stream:
                while True:
                    resources.require_current(); timeout = self._current()
                    if connection.sock: connection.sock.settimeout(timeout)
                    chunk = stream.read(min(1048576,before.st_size-count+1))
                    if not chunk: break
                    count += len(chunk); require(count <= before.st_size, 'Converted image grew beyond its original upload extent')
                    sha.update(chunk); connection.send(chunk)
                    due = start+count/(resources.limits.download_kib_per_second*1024)
                    while time.monotonic() < due:
                        resources.require_current();self._current();time.sleep(min(0.25,due-time.monotonic()))
            after = os.fstat(descriptor)
            require(count == before.st_size and sha.hexdigest() == inputs['output_sha256']
                    and (before.st_size,before.st_mtime_ns,before.st_ctime_ns) ==
                        (after.st_size,after.st_mtime_ns,after.st_ctime_ns),
                    'Converted image bytes changed during original native upload')
            response = connection.getresponse();self._current()
            require(response.status == 204 and not response.getheader('Transfer-Encoding')
                    and response.getheader('Content-Length') in (None,'0'),
                    'Native image upload has no known empty completed response')
            require(not response.read(1), 'Native image upload returned unexpected response bytes')
        finally:
            if connection is not None: connection.close()
            os.close(descriptor)


class GlanceImageImporter:
    def __init__(self,authority,*,broker,consumer,ca_bundle,store):
        require(isinstance(authority,ColdImageAuthority) and isinstance(broker,CredentialBroker)
                and isinstance(consumer,VaultCredentialConsumer) and isinstance(store,ColdCaptureStore)
                and authority.registry.leases.captures is store,
                'Actual original image command, dynamic credentials and retained converted byte owner required')
        self.authority,self.broker,self.consumer,self.store = authority,broker,consumer,store
        self.ca_bundle = Path(ca_bundle)

    def execute(self):
        authority = self.authority; registry = authority.registry; lease = authority.image_lease
        resources = authority.cold.transfer_resources(); resources.enter_current()
        require(resources.stage_parent == self.store.directory, 'Image upload changed its commissioned I/O/staging owner')
        authority.claim()
        try:
            material = authority.acquire(self.broker,self.consumer)
            contact = _GlanceContact(authority,authority.cold,material,self.ca_bundle)
            inputs = registry.inputs(authority.command.context,lease)
            metadata = image_metadata(lease,inputs,authority.cold)
            if lease.phase == 'CREATE':
                native_id,_request_id = contact.create(metadata)
            else:
                native_id = registry.native_image(authority.command.context,lease)
                image_facts(contact.get(native_id),native_id,lease.owner.scope,metadata,inputs,'CREATE')
                path,conversion = self.store.image(lease.capture_digest,authority.cold,lease.disk_id)
                require(conversion['outputSha256'] == inputs['output_sha256'] and
                        conversion['outputBytes'] == inputs['output_bytes'], 'Upload changed original converted image bytes')
                contact.upload(native_id,path,inputs,resources)
            end = time.monotonic()+min(60,authority.timeout(60))
            while True:
                try:
                    observed = registry.evidence.observe(authority.command.context,lease,authority.row['operation_id'])
                    break
                except ImagePending:
                    require(time.monotonic() < end, 'Original native image upload remains pending; retain its uncertainty')
                    time.sleep(min(0.25,authority.timeout()))
            return registry.acknowledge(authority.command.context,lease,authority.row['operation_id'],
                                        authority.command.identity,observed)
        except Exception:
            authority.uncertain()
            raise


class GlanceImageReadbackOwner:
    def __init__(self,connect,*,enrollment,cold,ca_bundle,directory):
        require(callable(connect) and type(enrollment) is NativeReadEnrollment and isinstance(cold,ColdVmSelection)
                and enrollment.scope == _target_scope(cold),
                'Independent actual native image reader with exact commissioned project scope required')
        self.connect,self.enrollment,self.cold = connect,enrollment,cold
        self.ca_bundle = Path(ca_bundle); self.directory = private_path(directory,directory=True)

    def _read(self,cursor,context,lease):
        require(isinstance(lease,PlannedImageLease) and lease.owner.scope == self.enrollment.scope
                and self.enrollment.subject != lease.owner.worker_id and
                (context.organization_id,context.tenant_id) == (lease.owner.organization_id,lease.owner.tenant_id),
                'Image acceptance needs another independently enrolled reader in the exact native project')
        inputs = PlannedImageRegistry._inputs(cursor,context,lease)
        receipt = PlannedImageRegistry._receipt(cursor,context,lease.owner.job_id,lease.owner.resource_id)
        require(receipt is not None, 'Native image response UUID is unknown; a name search cannot repair it')
        contact = _GlanceContact(self.enrollment,self.cold,self.enrollment.acquire(cursor=cursor),
                                 self.ca_bundle,cursor=cursor)
        metadata = image_metadata(lease,inputs,self.cold)
        facts = image_facts(contact.get(receipt[0]),receipt[0],lease.owner.scope,metadata,inputs,lease.phase)
        return receipt[0],facts,inputs

    def observe(self,context,lease,operation_id):
        with self.connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context); self.enrollment.require_current(cursor=cursor)
            native_id,facts,inputs = self._read(cursor,context,lease); at = utcnow()
            document = {'format':FORMAT,'operation_id':operation_id,'job_id':lease.owner.job_id,
                'scope':asdict(lease.owner.scope),'resource_id':lease.owner.resource_id,'phase':lease.phase,
                'request_digest':lease.request_digest,'capture_digest':lease.capture_digest,'cold_selection_digest':self.cold.sha256,
                'native_image_id':native_id,'facts':facts,'inputs':inputs,'observer_subject':self.enrollment.subject,
                'read_grant_id':self.enrollment.command.grant.grant_id,'observed_at':at.isoformat(),'guest_boot_qualified':False}
            sha = c.digest(document); write_new(self.directory/(sha+'.json'),encoded(document))
            return NativeImageObservation(NativeObservation('glance-image-read-'+uuid4().hex,sha,
                self.enrollment.subject,None,'EFFECT_PRESENT',True,at),native_id)

    def verify_image_observation(self,cursor,context,lease,operation,observed):
        self.enrollment.require_current(cursor=cursor)
        native = observed.observation; document = load_private(self.directory/(native.evidence_digest+'.json'))
        require(c.digest(document) == native.evidence_digest and document['format'] == FORMAT
                and (document['operation_id'],document['job_id'],document['resource_id'],document['phase'],
                     document['request_digest'],document['native_image_id']) ==
                    (operation.operation_id,operation.job_id,operation.resource_id,operation.phase,
                     operation.request_digest,observed.native_image_id)
                and document['scope'] == asdict(lease.owner.scope) and document['capture_digest'] == lease.capture_digest
                and document['cold_selection_digest'] == self.cold.sha256 and document['guest_boot_qualified'] is False
                and document['observer_subject'] == native.observer_subject == self.enrollment.subject
                and document['observed_at'] == native.observed_at.isoformat(),
                'Native image observation differs from the original protected operation and independent reader')
        native_id,facts,inputs = self._read(cursor,context,lease)
        require(native_id == observed.native_image_id and facts == document['facts'] and inputs == document['inputs'],
                'Actual native image or its original retained inputs changed during acceptance')


def _target_scope(cold):
    from provisioner.controlplane.authority.model import PlanScope
    return PlanScope.from_record(cold.to_dict()['destination_scope'])
