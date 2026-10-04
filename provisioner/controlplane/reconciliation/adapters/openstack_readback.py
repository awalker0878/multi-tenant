"""Independent exact-ID Nova, Cinder and Neutron creation/occupancy readback.

Actual Keystone authentication, project-reader role and service catalogue are
checked before the known Terraform IDs are read. IDs in an output file are
selectors, never proof. This owner cannot infer absence from missing output,
search by a reusable name, accept unknown native fields or issue a mutation.
"""
from __future__ import annotations

from dataclasses import asdict
import http.client
from pathlib import Path
import ssl
from urllib.parse import urlsplit
from uuid import uuid4

from provisioner.allocations.transactions import ResourceObservation, ResourceUnits
from provisioner.controlplane.persistence import NativeBinding
from provisioner.execution import readback_core as c
from provisioner.execution.run_files import digest, encoded, load_private, private_path, read_private, require, utcnow, write_new
from provisioner.execution.terraform_run import cloud_config
from ..planned import NativeCreationObservation, creation_children, creation_request_digest, require_creation_inputs
from ..read_enrollment import NativeReadEnrollment
from ..registry import NativeObservation, RecoveryHeld

GIB=2**30
MIB=2**20


class OpenStackProjectReader:
    """One real short-lived reader token, fixed GET routes and live read gate."""
    def __init__(self,enrollment,*,identity_endpoint,ca_bundle,alias,compute_origin,cursor=None):
        require(type(enrollment) is NativeReadEnrollment and enrollment.scope.platform_family=='openstack',
                'An actually enrolled independent OpenStack reader is required')
        self.enrollment,self.cursor=enrollment,cursor
        self.identity_endpoint=identity_endpoint.rstrip('/')
        parsed=urlsplit(self.identity_endpoint)
        require(parsed.scheme=='https' and parsed.hostname and parsed.path=='/v3'
                and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment,
                'A fixed commissioned Keystone v3 authority is required')
        self.ca_bundle=Path(ca_bundle); self.ca=read_private(self.ca_bundle)
        self.tls=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self.tls.minimum_version=ssl.TLSVersion.TLSv1_2
        self.tls.verify_flags|=ssl.VERIFY_X509_STRICT
        self.tls.load_verify_locations(cadata=self.ca.decode('ascii'))
        self.material=enrollment.acquire(**({'cursor':cursor} if cursor is not None else {}))
        require(self.material.data.keys()=={'environment','cloud'} and self.material.data['environment']=={},
                'The read-only role must issue the fixed native OpenStack credential payload')
        cloud=cloud_config(encoded(self.material.data['cloud']),alias)['clouds'][alias]
        require(cloud['auth']['auth_url'].rstrip('/')==self.identity_endpoint,
                'The reader credential changed its enrolled native identity authority')
        body={'auth':{'identity':{'methods':['application_credential'],'application_credential':{
            'id':cloud['auth']['application_credential_id'],'secret':cloud['auth']['application_credential_secret']}}}}
        status,payload,headers=self._exchange(self.identity_endpoint,'/auth/tokens',method='POST',body=body)
        token=payload.get('token') if type(payload) is dict else None
        require(status==201 and type(token) is dict and headers.get('X-Subject-Token')
                and token.get('project',{}).get('id')==enrollment.scope.native_scope_id
                and token.get('methods')==['application_credential']
                and token.get('application_credential',{}).get('id')==cloud['auth']['application_credential_id']
                and not token.get('system') and not token.get('domain')
                and type(token.get('roles')) is list
                and [role.get('name') for role in token['roles']]==['reader'],
                'Actual native identity differs from the enrolled exact project-reader profile')
        self.token=headers['X-Subject-Token']; self.token_expires=c.timestamp(token['expires_at'])
        require(self.token_expires>utcnow(), 'The native read token has expired')
        self.endpoints={}
        types={'compute':'compute','volume':'volumev3','network':'network'}
        for name,service_type in types.items():
            rows=[endpoint for service in token['catalog'] if service.get('type')==service_type
                  for endpoint in service['endpoints'] if endpoint.get('interface')==cloud['interface']
                  and endpoint.get('region_id',endpoint.get('region'))==cloud['region_name']]
            require(len(rows)==1, 'Native read catalogue endpoint is absent or ambiguous')
            url=rows[0]['url'].rstrip('/'); address=urlsplit(url)
            require(address.scheme=='https' and address.hostname and not address.username
                    and not address.password and not address.query and not address.fragment
                    and '..' not in address.path,
                    'Native read catalogue endpoint escapes its exact HTTPS route')
            suffix={'compute':('/v2.1','/v2.1/'+enrollment.scope.native_scope_id),
                    'volume':('/v3/'+enrollment.scope.native_scope_id,), 'network':('/v2.0',)}[name]
            require(address.path in suffix,'Native service version/project route differs')
            self.endpoints[name]=url
        compute=urlsplit(self.endpoints['compute'])
        require(c.origin('https://'+compute.netloc)==compute_origin,
                'The native read project belongs to another commissioned compute endpoint')

    def _current(self):
        _grant,deadline=self.enrollment.require_current(**({'cursor':self.cursor} if self.cursor is not None else {}))
        deadline=min(deadline,self.material.expires_at,getattr(self,'token_expires',deadline))
        require(deadline>utcnow(), 'The next independent native GET has no remaining read authority')
        return min(10,(deadline-utcnow()).total_seconds())

    def _exchange(self,endpoint,path,*,method='GET',body=None,version=None):
        require(method in {'GET','POST'} and path.startswith('/') and '..' not in path
                and ('?' not in path) and ('#' not in path), 'A fixed independent native route is required')
        address=urlsplit(endpoint)
        headers={'Accept':'application/json','Accept-Encoding':'identity','Connection':'close'}
        if hasattr(self,'token'): headers['X-Auth-Token']=self.token
        if method=='POST': headers['Content-Type']='application/json'
        if version: headers['OpenStack-API-Version']=version
        connection=http.client.HTTPSConnection(address.hostname,address.port or 443,
            context=self.tls,timeout=self._current())
        try:
            connection.request(method,address.path+path,body=encoded(body) if body else None,headers=headers)
            response=connection.getresponse(); raw=response.read(c.LIMIT+1)
            self._current()
            lengths=response.headers.get_all('Content-Length',[])
            require(len(lengths)==1 and lengths[0].isdigit() and int(lengths[0])==len(raw)
                    and not response.headers.get_all('Transfer-Encoding',[])
                    and response.headers.get_all('Content-Encoding',[]) in ([],['identity'])
                    and all(len(response.headers.get_all(name,[]))<=1 for name in
                        ('Content-Type','X-Subject-Token','X-OpenStack-Request-Id','OpenStack-API-Version')),
                    'Independent native read has ambiguous framing or identity/version headers')
            require(response.status in {200,201} and len(raw)<=c.LIMIT
                    and response.headers.get_content_type()=='application/json'
                    and response.getheader('Content-Encoding','identity')=='identity',
                    'The exact native object is unavailable; absence/denial cannot prove completion')
            if version:
                require(response.getheader('OpenStack-API-Version')==version,
                        'The independent native read protocol differs from its selected contract')
            return response.status,c.strict_loads(raw),dict(response.headers.items())
        finally:
            connection.close()

    def get(self,service,path):
        allowed={'compute':('servers/','flavors/'), 'volume':('volumes/',),
                 'network':('ports/','security-groups/','networks/','subnets/')}
        require(service in allowed and any(path.startswith(prefix) for prefix in allowed[service])
                and all(part not in {'','..','.'} for part in path.split('/')),
                'Only compiled exact-ID native observation routes are supported')
        # 2.46 retains the actual flavor ID. The separate installed observation
        # contract must be qualified; an embedded flavor name is not an ID.
        version={'compute':'compute 2.46','volume':'volume 3.60','network':None}[service]
        return self._exchange(self.endpoints[service],'/'+path,version=version)[1]


class OpenStackNativeReadbackOwner:
    def __init__(self,*,enrollment,identity_endpoint,ca_bundle,directory,bundles,lease_store=None):
        require(type(enrollment) is NativeReadEnrollment and callable(bundles),
                'Independent native reader enrollment and protected resource custody are required')
        self.enrollment=enrollment; self.identity_endpoint=identity_endpoint; self.ca_bundle=Path(ca_bundle)
        self.directory=private_path(directory,directory=True); self.bundles=bundles
        self.lease_store=lease_store

    def _read(self,bundle,scope,outputs,*,cursor=None,occupancy=False):
        require(scope==self.enrollment.scope, 'The independent reader is enrolled in another native project')
        pools=[pool for pool in bundle.pools if pool.scope==scope and pool.inputs is not None]
        require(len(pools)==1,'One exact OpenStack workload pool is required')
        pool=pools[0]; inputs=pool.inputs
        members=outputs.get('members',{}).get('value')
        require(type(members) is dict and members.keys()==inputs['members'].keys(),
                'The retained output does not cover every selected target child')
        reader=OpenStackProjectReader(self.enrollment,identity_endpoint=self.identity_endpoint,
            ca_bundle=self.ca_bundle,alias=inputs['openstack_cloud'],compute_origin=pool.catalog['origin'],cursor=cursor)
        bindings=[]; facts={}; cpu=memory=storage=0
        for name,selected in inputs['members'].items():
            ids=members[name]
            require(type(ids) is dict and {'server_id','port_id','boot_volume_id','data_volume_ids'}<=ids.keys()
                    and type(ids['data_volume_ids']) is list
                    and len(ids['data_volume_ids'])==(1 if selected.get('data_disk_gib',0)>0 else 0),
                    'Every retained native VM/port/volume identity is required before observation')
            for identity in [ids['server_id'],ids['port_id'],ids['boot_volume_id'],*ids['data_volume_ids']]:
                require(type(identity) is str and c.UUID.fullmatch(identity), 'Actual native UUID selectors required')
            server=reader.get('compute','servers/'+ids['server_id'])['server']
            state='ACTIVE' if selected.get('lifecycle_stage','prepared')=='bootstrap' else 'SHUTOFF'
            if occupancy:
                state=server.get('status')
                require(state in {'ACTIVE','SHUTOFF'},
                        'Changing native target state cannot supply current occupancy')
            metadata={'tenant_key':inputs['tenant_key'],'domain_key':selected['domain_key'],'workload_key':name}
            require(server.get('id')==ids['server_id'] and server.get('tenant_id')==scope.native_scope_id
                    and server.get('name')==name and server.get('status')==state
                    and server.get('metadata')==metadata and server.get('flavor',{}).get('id')==selected['flavor_id']
                    and server.get('OS-EXT-AZ:availability_zone')==selected['compute_availability_zone']
                    and not server.get('OS-EXT-STS:task_state'),
                    'Actual native VM identity, project, selected flavor, state or placement differs')
            volumes=[ids['boot_volume_id'],*ids['data_volume_ids']]
            require(sorted(row['id'] for row in server['os-extended-volumes:volumes_attached'])==sorted(volumes),
                    'The actual VM has missing, foreign or uncharged attached native volumes')
            interfaces=reader.get('compute','servers/'+ids['server_id']+'/os-interface')['interfaceAttachments']
            require(type(interfaces) is list and len(interfaces)==1
                    and interfaces[0]['port_id']==ids['port_id'],
                    'Actual VM attachments differ from the selected native port')
            flavor=reader.get('compute','flavors/'+selected['flavor_id'])['flavor']
            expected=pool.catalog['flavors'][selected['flavor_id']]
            require(flavor.get('id')==selected['flavor_id'] and type(flavor.get('vcpus')) is int
                    and type(flavor.get('ram')) is int and flavor['vcpus']==expected['vcpu']
                    and flavor['ram']==expected['ram_mib'] and flavor.get('disk')==0
                    and flavor.get('OS-FLV-EXT-DATA:ephemeral')==0 and flavor.get('swap') in {0,''},
                    'The current actual flavor differs from the commissioned zero-local-disk demand')
            port=reader.get('network','ports/'+ids['port_id'])['port']
            require(port.get('id')==ids['port_id'] and port.get('project_id')==scope.native_scope_id
                    and port.get('device_id')==ids['server_id'] and port.get('network_id')==selected['network_id']
                    and port.get('port_security_enabled') is True and port.get('allowed_address_pairs')==[]
                    and port.get('security_groups')==[selected['security_group_id']]
                    and port.get('fixed_ips')==[{'subnet_id':selected['subnet_id'],'ip_address':selected['ipv4_address']}]
                    and (type(port.get('admin_state_up')) is bool if occupancy else
                         port.get('admin_state_up') is (state=='ACTIVE')),
                    'Actual native mandatory policy, address, ownership or attachment differs')
            group=reader.get('network','security-groups/'+selected['security_group_id'])['security_group']
            require(group.get('id')==selected['security_group_id'] and group.get('project_id')==scope.native_scope_id,
                    'Selected native policy belongs to another project')
            volume_facts=[]
            for number,identity in enumerate(volumes):
                volume=reader.get('volume','volumes/'+identity)['volume']
                size=selected.get('boot_disk_gib',40) if number==0 else selected.get('data_disk_gib',0)
                require(volume.get('id')==identity and volume.get('os-vol-tenant-attr:tenant_id')==scope.native_scope_id
                        and volume.get('status')=='in-use' and type(volume.get('size')) is int and volume['size']==size
                        and volume.get('availability_zone')==selected['storage_availability_zone']
                        and volume.get('volume_type')==selected['volume_type'] and volume.get('metadata')==metadata
                        and type(volume.get('attachments')) is list and len(volume['attachments'])==1
                        and volume['attachments'][0].get('server_id')==ids['server_id'],
                        'Actual native volume identity, project, size, placement or attachment differs')
                if number==0:
                    require(volume.get('volume_image_metadata',{}).get('image_id')==selected['image_id'],
                            'The actual retained boot image differs from the selected native image')
                storage+=size*GIB; volume_facts.append(volume)
                bindings.append(NativeBinding(scope.platform_family,scope.endpoint_id,scope.native_scope_id,'volume',identity))
            bindings.extend((NativeBinding(scope.platform_family,scope.endpoint_id,scope.native_scope_id,'vm',ids['server_id']),
                             NativeBinding(scope.platform_family,scope.endpoint_id,scope.native_scope_id,'nic',ids['port_id'])))
            cpu+=flavor['vcpus']; memory+=flavor['ram']*MIB
            facts[name]={'server':server,'interfaces':interfaces,'flavor':flavor,'port':port,'group':group,'volumes':volume_facts}
        require(len({binding.key() for binding in bindings})==len(bindings),
                'Two selected targets share a native resource identity')
        units=ResourceUnits.from_bytes(vcpu=cpu,memory_bytes=memory,storage_bytes=storage)
        return tuple(sorted(bindings,key=lambda item:item.key())),facts,units

    def observe_creation(self,context,lease,operation_id,bundle,prepared):
        require(self.enrollment.subject!=lease.worker_id and
                (context.organization_id,context.tenant_id)==(lease.organization_id,lease.tenant_id),
                'Creation requires a different independently enrolled observer in this tenant')
        prepared=private_path(prepared,directory=True)
        require_creation_inputs(bundle,lease.scope,lease.resource_id,load_private(prepared/'inputs.json'))
        outputs=load_private(prepared/'outputs.json')
        bindings,facts,units=self._read(bundle,lease.scope,outputs); at=utcnow()
        document={'format':'hosting-openstack-native-creation-observation/1',
            'job_id':lease.job_id,'operation_id':operation_id,'resource_id':lease.resource_id,
            'request_digest':creation_request_digest(bundle,lease.scope,lease.resource_id),
            'bundle_digest':bundle.digest,'selection_digest':bundle.selection_digest,'scope':asdict(lease.scope),
            'outputs':outputs,'facts':facts,'bindings':[asdict(item) for item in bindings],'units':asdict(units),
            'observer_subject':self.enrollment.subject,'read_grant_id':self.enrollment.command.grant.grant_id,
            'observed_at':at.isoformat()}
        sha=c.digest(document); write_new(self.directory/(sha+'.json'),encoded(document))
        return NativeCreationObservation(NativeObservation('creation-read-'+uuid4().hex,sha,
            self.enrollment.subject,None,'EFFECT_PRESENT',True,at),bindings)

    def verify_creation_observation(self,cursor,operation,observed):
        self.enrollment.require_current(cursor=cursor)
        native=observed.observation; record=load_private(self.directory/(native.evidence_digest+'.json'))
        require(c.digest(record)==native.evidence_digest and native.outcome=='EFFECT_PRESENT'
                and record['operation_id']==operation.operation_id and record['job_id']==operation.job_id
                and record['resource_id']==operation.resource_id and record['request_digest']==operation.request_digest
                and record['scope']==asdict(operation.scope) and record['observer_subject']==native.observer_subject==self.enrollment.subject
                and record['observed_at']==native.observed_at.isoformat()
                and native.observer_subject!=operation.worker_id
                and record['bindings']==[asdict(item) for item in observed.bindings],
                'The creation observation differs from independent native custody')
        artifact=self.enrollment.command.authority.selections.load_verified(record['selection_digest'])
        bundle=self.bundles_for_original(cursor,operation.job_id,artifact)
        bindings,facts,units=self._read(bundle,operation.scope,record['outputs'],cursor=cursor)
        require(bindings==observed.bindings and c.digest(facts)==c.digest(record['facts']) and asdict(units)==record['units'],
                'The actual native resources changed since their independent creation observation')

    def bundles_for_original(self,cursor,job_id,artifact):
        from provisioner.controlplane.jobs.repository import _JOB_SELECT,_job,_digest,_payload_from_job
        from provisioner.controlplane.workflow.admitted_job import AdmittedInput
        scope=self.enrollment.scope
        cursor.execute(f'SELECT {_JOB_SELECT} FROM hosting_controlplane.operation_jobs '
            'WHERE organization_id=%s AND tenant_id=%s AND job_id=%s',
            (scope.organization_id,scope.tenant_id,job_id))
        row=cursor.fetchone(); require(row is not None,'Original resource job is not visible in this tenant')
        job=_job(row)
        admitted=AdmittedInput(job.job_id,job.organization_id,job.tenant_id,job.plan_id,
            job.plan_revision,job.plan_digest,job.revocation_epoch,_digest(_payload_from_job(job)))
        return self.bundles(admitted,artifact)

    def resource_observation(self,bundle,receipt,creation):
        record=load_private(self.directory/(creation.observation.evidence_digest+'.json'))
        require(record['bundle_digest']==bundle.digest and receipt['scope']==next(
            pool.demand(current=False)['scope'] for pool in bundle.pools if pool.scope==self.enrollment.scope),
            'The observed charge belongs to another exact resource pool')
        return ResourceObservation(receipt['reservation_id'],creation.observation.evidence_digest,
            tuple(binding.native_id for binding in creation.bindings),ResourceUnits(**record['units']),
            'EFFECT_PRESENT',creation.observation.observed_at)

    def verify_resource_observation(self,cursor,bundle,action,observation):
        require(action=='confirm','Release requires independently verified cleanup and revoked-writer exclusion')
        record=load_private(self.directory/(observation.evidence_digest+'.json'))
        require(record['bundle_digest']==bundle.digest and record['job_id']==bundle.admitted.job_id
                and record['selection_digest']==bundle.selection_digest
                and record['scope']==asdict(self.enrollment.scope) and record['units']==asdict(observation.units)
                and sorted(observation.native_ids)==sorted(item['native_id'] for item in record['bindings']),
                'Capacity observation differs from the exact independently read native occupancy')
        self.enrollment.require_current(cursor=cursor)
        bindings,facts,units=self._read(bundle,self.enrollment.scope,record['outputs'],cursor=cursor)
        require(c.digest(facts)==c.digest(record['facts']) and asdict(units)==asdict(observation.units),
                'Actual native occupancy changed; preserve the original charge')

    def verify_creation_owner_exclusion(self,cursor,lease,scope,evidence):
        require(self.lease_store is not None,
                'Original dynamic native credential custody is required before excluding its writer')
        self.lease_store.verify_owner_exclusion(cursor,lease,scope,evidence)
