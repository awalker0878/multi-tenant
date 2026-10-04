"""Newly approved exact-ID OpenStack cleanup, independent native absence.

This owner never executes Terraform destroy, retries a claimed DELETE or infers
cleanup from expiry. Actual original UUIDs come from the existing independently
resolved creation journal. Capacity refund remains a separate all-pool proof.
"""
from dataclasses import asdict,dataclass
from contextlib import ExitStack
from datetime import datetime,timezone
import http.client
from pathlib import Path
import ssl
import time
from urllib.parse import urlsplit
from uuid import uuid4

from provisioner.allocations.transactions import ResourceBundle
from provisioner.controlplane.discovery.adapters.openstack import OpenStackServiceEndpoints
from provisioner.controlplane.jobs.repository import _digest,_json,_tenant
from provisioner.controlplane.persistence import NativeBinding,TenantContext
from provisioner.controlplane.persistence.store import OwnerLease
from provisioner.controlplane.reconciliation.read_enrollment import NativeReadEnrollment
from provisioner.controlplane.reconciliation.resource_recovery import PostgresResourceRecoveryAuthority
from provisioner.controlplane.reconciliation.registry import NativeObservation,NativeOperationRegistry,RecoveryHeld
from provisioner.controlplane.worker.command_runtime import WorkerCommandRuntime
from provisioner.controlplane.worker.grants import CredentialBroker
from provisioner.controlplane.worker.vault_consumer import VaultCredentialConsumer
from provisioner.execution import readback_core as c
from provisioner.execution.run_files import digest,encoded,load_private,private_path,read_private,require,utcnow,write_new
from provisioner.execution.terraform_run import cloud_config
from .openstack_readback import OpenStackNativeReadbackOwner,OpenStackProjectReader


_ROUTES={'vm':('compute','servers/'),'nic':('network','ports/'),'volume':('volume','volumes/')}


class NativeCleanupPending(ValueError):
    """The exact, independently visible original native deletion is unsettled."""


def _native_time(value):
    # Nova's API documents an omitted offset as UTC. Never use local timezone.
    require(type(value) is str and len(value)<=64,'An actual bounded native event time is required')
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result


def _routes(endpoints,scope):
    require(isinstance(endpoints,OpenStackServiceEndpoints)
            and (endpoints.endpoint_id,endpoints.project_id)==(scope.endpoint_id,scope.native_scope_id),
            'Actual commissioned exact-project native service endpoints required')
    return {name:getattr(endpoints,name).rstrip('/') for name in ('compute','volume','network')}


def _error_absence(service,body):
    if service in {'compute','volume'}:
        return type(body) is dict and set(body)=={'itemNotFound'} and type(body['itemNotFound']) is dict \
            and body['itemNotFound'].get('code')==404 and type(body['itemNotFound'].get('message')) is str
    return type(body) is dict and set(body)=={'NeutronError'} and type(body['NeutronError']) is dict \
        and body['NeutronError'].get('type')=='PortNotFound' and type(body['NeutronError'].get('message')) is str


@dataclass(frozen=True)
class OriginalOpenStackChild:
    binding: NativeBinding
    original_operation_id: str
    original_observation_digest: str
    member_id: str
    descriptor_json: str

    @property
    def descriptor(self): return c.strict_loads(self.descriptor_json)


def original_child(cursor,context,bundle,binding,creation_owner):
    """Derive exact selected native identity from its accepted original journal."""
    require(isinstance(bundle,ResourceBundle) and isinstance(binding,NativeBinding)
            and binding.resource_kind in _ROUTES and type(creation_owner) is OpenStackNativeReadbackOwner
            and binding.key()[:3]==(creation_owner.enrollment.scope.platform_family,
                creation_owner.enrollment.scope.endpoint_id,creation_owner.enrollment.scope.native_scope_id),
            'An original independently observed OpenStack child is required')
    cursor.execute('SELECT i.operation_id,i.request_digest,o.evidence_digest,o.created_native_bindings '
        'FROM hosting_controlplane.native_operation_intents i '
        'JOIN hosting_controlplane.native_operation_observations o USING (organization_id,tenant_id,operation_id) '
        'WHERE i.organization_id=%s AND i.tenant_id=%s AND i.job_id=%s '
        "AND i.operation_kind='VM_CREATE' AND i.state='RESOLVED' AND i.outcome='EFFECT_PRESENT' "
        "AND o.outcome='EFFECT_PRESENT' AND o.native_quiesced ORDER BY o.recorded_at DESC",
        (context.organization_id,context.tenant_id,bundle.admitted.job_id))
    matches=[]
    for row in cursor.fetchall():
        native=_json(row[3]) if row[3] is not None else []
        if asdict(binding) not in native: continue
        record=load_private(creation_owner.directory/(row[2]+'.json'))
        require(c.digest(record)==row[2] and record['format']=='hosting-openstack-native-creation-observation/1'
                and record['job_id']==bundle.admitted.job_id and record['operation_id']==row[0]
                and record['request_digest']==row[1] and record['bundle_digest']==bundle.digest
                and record['selection_digest']==bundle.selection_digest and record['bindings']==native,
                'Original native identity differs from independently controlled creation custody')
        pools=[pool for pool in bundle.pools if pool.scope==creation_owner.enrollment.scope and pool.inputs is not None]
        require(len(pools)==1,'One exact original workload demand owns this native child')
        inputs=pools[0].inputs
        for member,ids in record['outputs']['members']['value'].items():
            selected={'vm':[ids['server_id']],'nic':[ids['port_id']],
                      'volume':[ids['boot_volume_id'],*ids['data_volume_ids']]}
            if binding.native_id not in selected[binding.resource_kind]: continue
            metadata={'tenant_key':inputs['tenant_key'],'domain_key':inputs['members'][member]['domain_key'],
                      'workload_key':member}
            descriptor={'member':inputs['members'][member],'metadata':metadata,'ids':ids,
                        'pool_flavor':pools[0].catalog['flavors'][inputs['members'][member]['flavor_id']]}
            matches.append(OriginalOpenStackChild(binding,row[0],row[2],member,encoded(descriptor).decode()))
        # Older duplicate observations for this same accepted original binding
        # cannot authorize a second interpretation or different logical member.
        if matches: break
    require(len(matches)==1,'The selected native cleanup child has no exact independently resolved original creation')
    return matches[0]


class OpenStackCleanupGuard:
    def __init__(self,runtime,admitted,artifact,request):
        require(type(runtime) is EnrolledOpenStackCleanupRuntime,
                'Concrete enrolled exact original native cleanup owner required')
        self.runtime,self.admitted,self.artifact,self.request=runtime,admitted,artifact,request
        self.artifact_digest=_digest(artifact); self.request_digest=c.digest(request); self.claimed=False

    def require_current(self):
        runtime=self.runtime; command=runtime.command_runtime; original=command.grant
        require(c.digest(self.request)==self.request_digest and _digest(self.artifact)==self.artifact_digest
                and command.verifier.verify(command.transport_evidence)==command.identity,
                'The exact original cleanup request, artifact or current mTLS identity changed')
        def checked(_reference,grant,deadline):
            require(grant==original,'The newly admitted native cleanup grant changed')
            return grant,deadline
        grant,deadline=command.grants.with_authorized_reference(command.context,command.identity,
            original.grant_id,**command.grant_arguments(self.admitted),use=checked)
        options=dict(continuation_grant=grant,continuation_identity=command.identity) if self.claimed else {}
        plan,artifact=command.authority.require_current(self.admitted,self.artifact_digest,'NATIVE_CLEANUP',**options)
        selected=plan['spec'].get('resourceRecovery',{})
        require(artifact==self.artifact and artifact.get('resourceRecoverySelectionDigest')==c.digest(selected)
                and selected['originalJobId']==runtime.bundle.admitted.job_id
                and selected['resourceBundleDigest']==runtime.bundle.digest and 'cleanup' in selected['actions']
                and (grant.operation_scope,grant.worker_subject,grant.lease_epoch)==
                    (runtime.scope,runtime.lease.worker_id,runtime.lease.epoch)
                and (runtime.lease.workload_id,runtime.lease.security_domain_id)==
                    (runtime.bundle.workload_id,runtime.scope.security_domain_id),
                'The current cleanup plan or newly acquired exact native owner changed')
        deadline=min(deadline,runtime.lease.expires_at,command.identity.expires_at)
        require(deadline>utcnow(),'The next exact native DELETE or observation has no remaining original authority')
        return grant,deadline


class _CleanupWriter:
    """One fixed native DELETE; auth/catalog are independently verified first."""
    def __init__(self,runtime,guard,child):
        self.runtime,self.guard,self.child=runtime,guard,child
        command=runtime.command_runtime
        grant,deadline=guard.require_current()
        handle=runtime.broker.acquire(command.transport_evidence,command.context,grant.grant_id,
                                      **command.grant_arguments(guard.admitted))
        self.material=runtime.consumer.unwrap(handle,grant)
        data=self.material.data
        require(set(data)=={'format','request_digest','cloud'}
                and data['format']=='hosting-openstack-native-cleanup-credential/1'
                and data['request_digest']==guard.request_digest,
                'Only the enrolled exact-request native cleanup credential is accepted')
        pools=[pool for pool in runtime.bundle.pools if pool.scope==runtime.scope and pool.inputs is not None]
        require(len(pools)==1,'One selected original OpenStack workload pool is required')
        alias=pools[0].inputs['openstack_cloud']; cloud=cloud_config(encoded(data['cloud']),alias)['clouds'][alias]
        require(cloud['auth']['auth_url'].rstrip('/')==runtime.identity_endpoint.rstrip('/'),
                'The native cleanup credential belongs to another commissioned identity endpoint')
        self.tls=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT); self.tls.minimum_version=ssl.TLSVersion.TLSv1_2
        self.tls.verify_flags|=ssl.VERIFY_X509_STRICT
        self.tls.load_verify_locations(cadata=read_private(runtime.ca_bundle).decode('ascii'))
        body={'auth':{'identity':{'methods':['application_credential'],'application_credential':{
            'id':cloud['auth']['application_credential_id'],'secret':cloud['auth']['application_credential_secret']}}}}
        status,record,headers=self._exchange(runtime.identity_endpoint,'/auth/tokens',method='POST',body=body)
        token=record.get('token',{})
        require(status==201 and headers.get('X-Subject-Token')
                and token.get('project',{}).get('id')==runtime.scope.native_scope_id
                and token.get('methods')==['application_credential']
                and token.get('application_credential',{}).get('id')==cloud['auth']['application_credential_id']
                and not token.get('domain') and not token.get('system')
                and [row.get('name') for row in token.get('roles',[])]==list(runtime.cleanup_role_names),
                'Actual cleanup identity is not the exact enrolled restricted project role')
        self.token=headers['X-Subject-Token']; self.token_expires=c.timestamp(token['expires_at'])
        expected=_routes(runtime.endpoints,runtime.scope)
        for service,kind in {'compute':'compute','volume':'volumev3','network':'network'}.items():
            rows=[endpoint for entry in token.get('catalog',[]) if entry.get('type')==kind
                  for endpoint in entry.get('endpoints',[]) if endpoint.get('interface')==cloud['interface']
                  and endpoint.get('region_id',endpoint.get('region'))==cloud['region_name']]
            require(len(rows)==1 and rows[0]['url'].rstrip('/')==expected[service],
                    'Actual native cleanup catalogue differs from its commissioned exact project service')
        self.endpoints=expected

    def _timeout(self):
        _grant,deadline=self.guard.require_current()
        end=min(deadline,self.material.expires_at,getattr(self,'token_expires',deadline))
        require(end>utcnow(),'The native cleanup credential or original grant expired before contact')
        return min(10,(end-utcnow()).total_seconds())

    def _exchange(self,endpoint,path,*,method,body=None,version=None):
        address=urlsplit(endpoint)
        require(address.scheme=='https' and address.hostname and not address.username and not address.password
                and not address.query and not address.fragment and '..' not in address.path,
                'The exact cleanup endpoint must remain pinned HTTPS')
        headers={'Accept':'application/json','Accept-Encoding':'identity','Connection':'close'}
        if hasattr(self,'token'): headers['X-Auth-Token']=self.token
        if body is not None: headers['Content-Type']='application/json'
        if version: headers['OpenStack-API-Version']=version
        connection=http.client.HTTPSConnection(address.hostname,address.port or 443,context=self.tls,timeout=self._timeout())
        try:
            connection.request(method,address.path.rstrip('/')+path,body=encoded(body) if body is not None else None,headers=headers)
            response=connection.getresponse(); raw=response.read(c.LIMIT+1); self._timeout()
            require(len(raw)<=c.LIMIT and response.getheader('Content-Encoding','identity')=='identity',
                    'Native cleanup response exceeds the enrolled protocol bound')
            if version:
                require(response.getheader('OpenStack-API-Version')==version,
                        'The actual cleanup API version differs from its selected contract')
            if raw:
                require(response.headers.get_content_type()=='application/json','A native cleanup response is not bounded JSON')
                payload=c.strict_loads(raw)
            else: payload=None
            return response.status,payload,dict(response.headers.items())
        finally: connection.close()

    def delete(self):
        binding=self.child.binding; service,prefix=_ROUTES[binding.resource_kind]
        status,body,headers=self._exchange(self.endpoints[service],'/'+prefix+binding.native_id,method='DELETE',
            version={'compute':'compute 2.46','volume':'volume 3.60','network':None}[service])
        require(status==({'vm':204,'volume':202,'nic':204}[binding.resource_kind]) and body is None,
                'The single native cleanup request was not accepted with its exact installed API contract')
        # A request ID identifies this HTTP exchange, not a native task, and
        # must never populate native_operation_intents.native_task_id.
        request_id=headers.get('X-Openstack-Request-Id')
        require(type(request_id) is str and request_id.startswith('req-') and c.UUID.fullmatch(request_id[4:]),
                'The accepted original native DELETE lacks its authentic API request reference')
        return {'http_status':status,'request_id':request_id}


class _CleanupReader(OpenStackProjectReader):
    def __init__(self,owner,child,*,cursor=None):
        pool=next(pool for pool in owner.bundle.pools if pool.scope==owner.scope and pool.inputs is not None)
        super().__init__(owner.enrollment,identity_endpoint=owner.identity_endpoint,ca_bundle=owner.ca_bundle,
            alias=pool.inputs['openstack_cloud'],compute_origin=pool.catalog['origin'],cursor=cursor)
        require(self.endpoints==_routes(owner.endpoints,owner.scope),
                'Independent cleanup reader catalogue changed its commissioned native endpoints')
        self.child=child

    def native(self,service,path,*,event=False):
        # This method admits only exact fixed positive-control and original
        # object routes selected by this concrete owner, including typed 404s.
        selected=self.child.descriptor['member']; binding=self.child.binding
        allowed={_ROUTES[binding.resource_kind][0]:{_ROUTES[binding.resource_kind][1]+binding.native_id}}
        allowed.setdefault('compute',set()).add('flavors/'+selected['flavor_id'])
        allowed.setdefault('network',set()).add('security-groups/'+selected['security_group_id'])
        allowed.setdefault('volume',set()).add('types')
        if binding.resource_kind=='volume':
            allowed['volume'].update({'snapshots/detail?limit=1000','backups/detail?limit=1000'})
        if event:
            prefix='servers/'+binding.native_id+'/os-instance-actions/'
            request_id=path[len(prefix):] if path.startswith(prefix) else ''
            require(binding.resource_kind=='vm' and service=='compute' and request_id.startswith('req-')
                    and c.UUID.fullmatch(request_id[4:]),'Only the actual original delete action can be read')
        else:
            require(service in allowed and path in allowed[service],
                    'Only compiled original native object and positive-control routes can be read')
        address=urlsplit(self.endpoints[service]); version={'compute':'compute 2.51' if event else 'compute 2.46',
            'volume':'volume 3.60','network':None}[service]
        headers={'X-Auth-Token':self.token,'Accept':'application/json','Accept-Encoding':'identity','Connection':'close'}
        if version: headers['OpenStack-API-Version']=version
        connection=http.client.HTTPSConnection(address.hostname,address.port or 443,context=self.tls,timeout=self._current())
        try:
            connection.request('GET',address.path.rstrip('/')+'/'+path,headers=headers)
            response=connection.getresponse(); raw=response.read(c.LIMIT+1); self._current()
            require(response.status in ({200} if event else {200,404}) and len(raw)<=c.LIMIT
                    and response.headers.get_content_type()=='application/json'
                    and response.getheader('Content-Encoding','identity')=='identity'
                    and (version is None or response.getheader('OpenStack-API-Version')==version),
                    'Independent native cleanup visibility is unavailable or its protocol changed')
            body=c.strict_loads(raw)
            require(response.status!=404 or _error_absence(service,body),
                    'A generic missing route or permission response cannot prove native object absence')
            return response.status,body
        finally: connection.close()

    def hard_delete(self,receipt):
        request_id=receipt.get('request_id') if type(receipt) is dict else None
        require(receipt is not None and receipt.get('http_status')==204 and type(request_id) is str
                and request_id.startswith('req-') and c.UUID.fullmatch(request_id[4:]),
                'Actual original Nova DELETE response custody is required to inspect its native action')
        _status,body=self.native('compute','servers/'+self.child.binding.native_id+
                                '/os-instance-actions/'+request_id,event=True)
        action=body.get('instanceAction',{})
        require((action.get('instance_uuid'),action.get('project_id'),action.get('request_id'),action.get('action'))==
                (self.child.binding.native_id,self.enrollment.scope.native_scope_id,request_id,'delete')
                and action.get('message') is None and type(action.get('events')) is list
                and 1<=len(action['events'])<=1000,'Actual original native delete action changed or failed')
        events=action['events']
        if any(row.get('finish_time') is None or row.get('result') is None for row in events):
            raise NativeCleanupPending('The actual original native deletion event is not finished')
        require(all(row.get('result')=='Success' and row.get('traceback') is None
                    and _native_time(row['start_time'])<=_native_time(row['finish_time'])<=utcnow() for row in events)
                and len([row for row in events if row.get('event')=='compute_delete_instance'])==1
                and not any('soft_delete' in row.get('event','') for row in events),
                'A failed, partial or soft native delete cannot prove native quiescence')
        return c.digest(action)

    def control(self):
        selected=self.child.descriptor['member']; expected=self.child.descriptor['pool_flavor']
        service=_ROUTES[self.child.binding.resource_kind][0]
        if service=='compute':
            status,body=self.native('compute','flavors/'+selected['flavor_id']); flavor=body.get('flavor',{})
            require(status==200 and flavor.get('id')==selected['flavor_id'] and flavor.get('vcpus')==expected['vcpu']
                    and flavor.get('ram')==expected['ram_mib'],'The commissioned native flavor positive control changed')
            return c.digest(flavor)
        if service=='network':
            status,body=self.native('network','security-groups/'+selected['security_group_id']); group=body.get('security_group',{})
            require(status==200 and group.get('id')==selected['security_group_id']
                    and group.get('project_id')==self.enrollment.scope.native_scope_id,
                    'The selected native project policy positive control is unavailable')
            return c.digest(group)
        status,body=self.native('volume','types'); types=body.get('volume_types')
        require(status==200 and type(types) is list and len(types)<=1000
                and len([row for row in types if row.get('name')==selected['volume_type']])==1,
                'The selected native storage-type positive control is unavailable or ambiguous')
        return c.digest(next(row for row in types if row['name']==selected['volume_type']))

    def no_storage_descendants(self):
        facts={}
        for collection in ('snapshots','backups'):
            status,body=self.native('volume',collection+'/detail?limit=1000')
            rows=body.get(collection)
            require(status==200 and type(rows) is list and len(rows)<=1000
                    and not body.get(collection+'_links')
                    and all(type(row) is dict and type(row.get('volume_id')) is str for row in rows),
                    'Independent selected native storage dependency coverage is incomplete')
            require(not any(row['volume_id']==self.child.binding.native_id for row in rows),
                    'Original snapshots or native backups remain charged; native storage cleanup is incomplete')
            facts[collection]=c.digest(rows)
        return facts

    def state(self,*,receipt=None):
        before=self.control(); binding=self.child.binding
        service,prefix=_ROUTES[binding.resource_kind]
        status,body=self.native(service,prefix+binding.native_id)
        after=self.control(); require(before==after,'Native positive-control state changed during cleanup readback')
        if status==404:
            result={'status':'ABSENT','control_digest':before,'absence_error_digest':c.digest(body)}
            if binding.resource_kind=='vm': result['hard_delete_action_digest']=self.hard_delete(receipt)
            if binding.resource_kind=='volume': result['storage_dependency_digests']=self.no_storage_descendants()
            return result
        descriptor=self.child.descriptor; ids=descriptor['ids']; selected=descriptor['member']
        key={'vm':'server','nic':'port','volume':'volume'}[binding.resource_kind]; item=body.get(key,{})
        require(item.get('id')==binding.native_id,'The exact native object response changed its original UUID')
        if binding.resource_kind=='vm':
            require(item.get('tenant_id')==self.enrollment.scope.native_scope_id
                    and item.get('metadata')==descriptor['metadata'] and item.get('name')==self.child.member_id
                    and item.get('flavor',{}).get('id')==selected['flavor_id'],
                    'Original VM has unsettled work or changed its exact project, identity or allocation')
            if receipt is not None and item.get('status')=='DELETING':
                return {'status':'IN_PROGRESS','control_digest':before,'object_digest':c.digest(item)}
            require('OS-EXT-STS:task_state' in item and item['OS-EXT-STS:task_state'] is None
                    and item.get('status') in {'ACTIVE','SHUTOFF'},'Original VM native work is not settled')
            attached=sorted(row['id'] for row in item.get('os-extended-volumes:volumes_attached',[]))
            require(attached==sorted([ids['boot_volume_id'],*ids['data_volume_ids']]),
                    'Cleanup cannot delete a VM with foreign or uncharged attached storage')
        elif binding.resource_kind=='nic':
            require(item.get('project_id')==self.enrollment.scope.native_scope_id
                    and item.get('device_id') in {'',None} and item.get('device_owner') in {'',None}
                    and item.get('network_id')==selected['network_id']
                    and item.get('fixed_ips')==[{'subnet_id':selected['subnet_id'],'ip_address':selected['ipv4_address']}]
                    and item.get('security_groups')==[selected['security_group_id']]
                    and item.get('allowed_address_pairs')==[],
                    'Cleanup requires the exact original detached native port and policy/address binding')
        else:
            expected_size=selected.get('boot_disk_gib',40) if binding.native_id==ids['boot_volume_id'] else selected['data_disk_gib']
            require(item.get('os-vol-tenant-attr:tenant_id')==self.enrollment.scope.native_scope_id
                    and item.get('metadata')==descriptor['metadata'] and item.get('size')==expected_size
                    and item.get('volume_type')==selected['volume_type'] and not item.get('migration_status'),
                    'Cleanup requires the exact detached original native volume with no active migration')
            require(item.get('attachments')==[],'An original native volume remains attached')
            if receipt is not None and item.get('status')=='deleting':
                return {'status':'IN_PROGRESS','control_digest':before,'object_digest':c.digest(item)}
            require(item.get('status')=='available','Original native storage work is not settled')
            self.no_storage_descendants()
        return {'status':'PRESENT','control_digest':before,'object_digest':c.digest(item)}


class OpenStackCleanupReadbackOwner:
    def __init__(self,*,enrollment,bundle,identity_endpoint,ca_bundle,endpoints,directory,creation_owner,lease_store=None):
        require(type(enrollment) is NativeReadEnrollment and isinstance(bundle,ResourceBundle)
                and enrollment.scope.platform_family=='openstack' and type(creation_owner) is OpenStackNativeReadbackOwner,
                'Actual independent exact-project cleanup reader and original creation custody required')
        self.enrollment,self.bundle,self.scope=enrollment,bundle,enrollment.scope
        self.identity_endpoint,self.ca_bundle,self.endpoints=identity_endpoint,Path(ca_bundle),endpoints
        _routes(endpoints,self.scope)
        self.directory=private_path(directory,directory=True); self.creation_owner=creation_owner; self.lease_store=lease_store

    def child(self,cursor,context,binding):
        return original_child(cursor,context,self.bundle,binding,self.creation_owner)

    def state(self,child,*,cursor=None,receipt=None):
        reader=_CleanupReader(self,child,cursor=cursor)
        first=reader.state(receipt=receipt); second=reader.state(receipt=receipt)
        require(first==second,'The exact independent cleanup state changed between both native sweeps')
        return first

    def observe_cleanup(self,context,operation,request,child,receipt,*,cursor=None):
        require(self.enrollment.subject!=operation.worker_id and operation.binding==child.binding
                and operation.operation_kind=='NATIVE_CLEANUP' and operation.request_digest==c.digest(request),
                'Independent cleanup must inspect the exact original newly admitted DELETE')
        state=self.state(child,receipt=receipt,cursor=cursor)
        if state['status']!='ABSENT': raise NativeCleanupPending('The original native cleanup remains present')
        at=utcnow()
        record={'format':'hosting-openstack-native-cleanup-observation/1','job_id':operation.job_id,
            'operation_id':operation.operation_id,'request_digest':operation.request_digest,'request':request,
            'binding':asdict(child.binding),'original_operation_id':child.original_operation_id,
            'original_observation_digest':child.original_observation_digest,'member_id':child.member_id,
            'descriptor':child.descriptor,'state':state,'http_receipt':receipt,'observer_subject':self.enrollment.subject,
            'read_grant_id':self.enrollment.command.grant.grant_id,'observed_at':at.isoformat()}
        sha=c.digest(record); write_new(self.directory/(sha+'.json'),encoded(record))
        return NativeObservation('cleanup-read-'+uuid4().hex,sha,self.enrollment.subject,None,'EFFECT_PRESENT',True,at)

    def verify_native_observation(self,cursor,operation,observation):
        self.enrollment.require_current(cursor=cursor)
        record=load_private(self.directory/(observation.evidence_digest+'.json'))
        require(c.digest(record)==observation.evidence_digest
                and record['format']=='hosting-openstack-native-cleanup-observation/1'
                and record['binding']==asdict(operation.binding) and operation.operation_kind=='NATIVE_CLEANUP'
                and (record['operation_id'],record['job_id'],record['request_digest'],record['observer_subject'],record['observed_at'])==
                    (operation.operation_id,operation.job_id,operation.request_digest,self.enrollment.subject,observation.observed_at.isoformat())
                and record['request_digest']==c.digest(record['request'])
                and observation.observer_subject==self.enrollment.subject!=operation.worker_id
                and observation.native_task_id is None and observation.outcome=='EFFECT_PRESENT' and observation.native_quiesced,
                'Native cleanup evidence differs from its independent current original custody')
        child=self.child(cursor,TenantContext(self.scope.organization_id,self.scope.tenant_id),operation.binding)
        require((record['original_operation_id'],record['original_observation_digest'],record['descriptor'])==
                (child.original_operation_id,child.original_observation_digest,child.descriptor)
                and self.state(child,cursor=cursor,receipt=record['http_receipt'])==record['state']
                and record['state']['status']=='ABSENT',
                'The original native identity or current cleanup absence changed')

    def verify_owner_exclusion(self,cursor,lease,scope,evidence):
        require(self.lease_store is not None,'Actual newly approved original credential exclusion custody required')
        self.lease_store.verify_owner_exclusion(cursor,lease,scope,evidence)
        record=load_private(self.directory/(evidence.native_evidence_digest+'.json'))
        binding=NativeBinding(**record['binding'])
        require(binding==lease.binding and scope==self.scope and c.digest(record)==evidence.native_evidence_digest,
                'Expired cleanup writer exclusion differs from its exact original native identity')
        child=self.child(cursor,TenantContext(scope.organization_id,scope.tenant_id),binding)
        require(self.state(child,cursor=cursor,receipt=record['http_receipt'])['status']=='ABSENT',
                'Late cleanup work or a remaining original object prevents writer exclusion')


class EnrolledOpenStackCleanupRuntime:
    def __init__(self,*,command_runtime,lease,registry,recovery,bundle,readback,broker,consumer,
                 identity_endpoint,ca_bundle,endpoints,directory,cleanup_role_names=('hosting_cleanup',)):
        require(type(command_runtime) is WorkerCommandRuntime and isinstance(lease,OwnerLease)
                and isinstance(registry,NativeOperationRegistry) and type(recovery) is PostgresResourceRecoveryAuthority
                and isinstance(bundle,ResourceBundle) and type(readback) is OpenStackCleanupReadbackOwner
                and type(broker) is CredentialBroker and type(consumer) is VaultCredentialConsumer
                and command_runtime.grant.operation_kind=='NATIVE_CLEANUP'
                and command_runtime.authority is recovery.execution_authority
                and command_runtime.grants is registry._grants is broker._grants
                and broker._identities is command_runtime.verifier and broker._issuer is consumer.issuer
                and registry._evidence is readback and readback.bundle==bundle
                and lease.worker_id==command_runtime.identity.subject and lease.binding.resource_kind in _ROUTES,
                'Actual new cleanup admission, original native owner, concrete broker and separate readback required')
        self.command_runtime,self.lease,self.registry,self.recovery=command_runtime,lease,registry,recovery
        self.bundle,self.readback,self.broker,self.consumer=bundle,readback,broker,consumer
        self.scope=command_runtime.grant.operation_scope
        require(self.scope==readback.scope and lease.binding.key()[:3]==
                (self.scope.platform_family,self.scope.endpoint_id,self.scope.native_scope_id)
                and self.scope.platform_family=='openstack'
                and type(cleanup_role_names) is tuple and len(cleanup_role_names)==1
                and cleanup_role_names[0] not in {'admin','member','reader'},
                'An exact selected native cleanup role and observed project child are required')
        self.identity_endpoint,self.ca_bundle,self.endpoints=identity_endpoint,Path(ca_bundle),endpoints
        self.directory=private_path(directory,directory=True); self.cleanup_role_names=cleanup_role_names
        _routes(endpoints,self.scope)
        from provisioner.controlplane.worker.native_retirement import CompletedNativeGrantRetirement
        self.retirement=CompletedNativeGrantRetirement(store=broker._issuer._lease_store,
            issuer=broker._issuer,grants=command_runtime.grants)

    def request(self,admitted,artifact):
        require(admitted==self.recovery.admitted,'Cleanup cannot borrow a revoked original admission')
        with self.recovery.connect() as connection,connection.cursor() as cursor:
            job,plan,selected,actual,at=self.recovery.require_control(cursor,self.bundle,'cleanup',resolved=True)
            require(actual==artifact and artifact.get('resourceRecoverySelectionDigest')==c.digest(selected),
                    'Actual cleanup changed its newly approved exact original recovery purpose')
            child=self.readback.child(cursor,self.command_runtime.context,self.lease.binding)
        request={'format':'hosting-openstack-native-cleanup-request/1','admitted':asdict(admitted),
            'selection_digest':_digest(artifact),'recovery_selection_digest':c.digest(selected),
            'original_job':asdict(self.bundle.admitted),'resource_bundle_digest':self.bundle.digest,
            'binding':asdict(child.binding),'original_operation_id':child.original_operation_id,
            'original_observation_digest':child.original_observation_digest,'member_id':child.member_id,
            'descriptor':child.descriptor,'method':'DELETE','step_id':self.command_runtime.grant.step_id,
            'operation_id':self.command_runtime.grant.operation_id}
        return request,child

    def cleanup(self,admitted,artifact):
        request,child=self.request(admitted,artifact); guard=OpenStackCleanupGuard(self,admitted,artifact,request)
        command=self.command_runtime; grant,_deadline=guard.require_current()
        operation=self.registry.prepare(command.context,self.lease,self.scope,job_id=admitted.job_id,
            grant_id=grant.grant_id,step_id=grant.step_id,lease_key=grant.lease_key,worker_identity=command.identity,
            operation_id=grant.operation_id,operation_kind='NATIVE_CLEANUP',request_digest=guard.request_digest)
        if operation.state=='RESOLVED': return self.inspect_cleanup(admitted,artifact)
        require(operation.state=='PREPARED','The original native cleanup was already claimed; inspect without DELETE replay')
        state=self.readback.state(child)
        require(state['status']=='PRESENT','An already missing native resource needs original no-delete resolution, never another DELETE')
        native=_CleanupWriter(self,guard,child)
        require(self.registry.claim_once(command.context,self.lease,self.scope,grant.operation_id,command.identity),
                'Original native DELETE was already claimed')
        guard.claimed=True
        try:
            receipt=native.delete()
            write_new(self.directory/(grant.operation_id+'-http.json'),encoded(receipt))
            end=min(time.monotonic()+90,time.monotonic()+guard.require_current()[1].timestamp()-utcnow().timestamp())
            while True:
                guard.require_current()
                try:
                    observation=self.readback.observe_cleanup(command.context,
                        self.registry.get(command.context,grant.operation_id),request,child,receipt)
                    break
                except NativeCleanupPending:
                    if time.monotonic()>=end: raise
                    time.sleep(min(1,max(0,end-time.monotonic())))
            self.registry.acknowledge_current(command.context,self.lease,self.scope,grant.operation_id,
                                              command.identity,observation)
            retirement_digest=self.retirement.retire(self,admitted,artifact)
            result={'format':'hosting-openstack-native-cleanup/1','status':'EXACT_NATIVE_CHILD_CLEANED',
                'operation_id':grant.operation_id,'request_digest':guard.request_digest,'binding':asdict(child.binding),
                'observation_digest':observation.evidence_digest,'http_receipt':receipt,
                'credential_retirement_digest':retirement_digest,
                'native_acceptance':False,'production_activation':False,'capacity_refund_authorized':False}
            path=self.directory/(grant.operation_id+'.json'); write_new(path,encoded(result))
            return result
        except BaseException:
            try:self.registry.mark_uncertain(command.context,grant.operation_id,command.identity.subject)
            except Exception:pass
            raise

    def inspect_cleanup(self,admitted,artifact,*,cursor=None):
        # Read-only recovery never invokes the original writer request or
        # reacquires an expired mutation credential. It follows the immutable
        # retained original intent and its different current reader instead.
        command=self.command_runtime
        with ExitStack() as stack:
            if cursor is None:
                connection=stack.enter_context(self.registry._connect())
                cursor=stack.enter_context(connection.cursor())
            _tenant(cursor,command.context)
            _plan,actual=command.authority.require_observation(admitted,_digest(artifact),'NATIVE_CLEANUP',cursor=cursor)
            purpose=_plan['spec']['resourceRecovery']
            require(admitted==self.recovery.admitted and actual==artifact
                    and actual.get('resourceRecoverySelectionDigest')==c.digest(purpose)
                    and purpose['originalJobId']==self.bundle.admitted.job_id
                    and purpose['resourceBundleDigest']==self.bundle.digest,
                    'Original cleanup observation selection changed')
            allowed=[command.grant.operation_id,*purpose['originalOperationIds']]
            cursor.execute('SELECT operation_id FROM hosting_controlplane.native_operation_intents '
                'WHERE organization_id=%s AND tenant_id=%s AND operation_id=ANY(%s) '
                "AND operation_kind='NATIVE_CLEANUP' AND state='RESOLVED' AND outcome='EFFECT_PRESENT' "
                'AND (platform_family,endpoint_id,native_scope_id,resource_kind,native_id)=(%s,%s,%s,%s,%s) '
                'ORDER BY updated_at DESC LIMIT 1',
                (command.context.organization_id,command.context.tenant_id,allowed,*self.lease.binding.key()))
            original=cursor.fetchone(); require(original is not None,
                'The exact original DELETE needs independently fenced resolution before inspection can complete')
            operation=self.registry._get(cursor,command.context,original[0])
            cursor.execute('SELECT evidence_digest FROM hosting_controlplane.native_operation_observations '
                'WHERE organization_id=%s AND tenant_id=%s AND operation_id=%s '
                "AND outcome='EFFECT_PRESENT' AND native_quiesced ORDER BY recorded_at DESC LIMIT 1",
                (command.context.organization_id,command.context.tenant_id,operation.operation_id))
            row=cursor.fetchone(); require(row is not None,'Original independent cleanup observation custody is unavailable')
            record=load_private(self.readback.directory/(row[0]+'.json'))
            require(c.digest(record)==row[0],'Original resolved cleanup observation bytes changed')
            child=self.readback.child(cursor,command.context,self.lease.binding)
            observed=self.readback.observe_cleanup(command.context,operation,record['request'],child,
                                                  record['http_receipt'],cursor=cursor)
            self.readback.verify_native_observation(cursor,operation,observed)
        return {'format':'hosting-openstack-native-cleanup/1','status':'EXACT_NATIVE_CHILD_CLEANED',
            'operation_id':operation.operation_id,'request_digest':operation.request_digest,'binding':asdict(child.binding),
            'observation_digest':row[0],'http_receipt':record['http_receipt'],
            'native_acceptance':False,'production_activation':False,'capacity_refund_authorized':False,
            'current_observation_digest':observed.evidence_digest}
