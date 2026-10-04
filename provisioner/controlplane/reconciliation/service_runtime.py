"""Enrolled NetBox, signed DNS and quota stages through their existing owners.

Dynamic credentials originate only from the live B10 broker. Every actual HTTP
or DNS exchange rechecks the original selected packet and current grant. Native
completion additionally requires a separate enrolled reader; a writer receipt,
command result or copied approval cannot resolve the B11 intent by itself.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import re
import fcntl
import os
import time
from uuid import uuid4

from provisioner.allocations import netbox_ipam as ipam
from provisioner.allocations.ipam_transactions import NetBoxResourceTransactions, bind_selection, selection as ipam_selection
from provisioner.controlplane.jobs.repository import _digest
from provisioner.controlplane.worker.command_runtime import WorkerCommandRuntime, SelectedWorkerCommandAuthority
from provisioner.controlplane.worker.grants import CredentialBroker
from provisioner.controlplane.worker.vault_consumer import VaultCredentialConsumer, ConsumedVaultCredential
from provisioner.execution import delivery_steps, dns_change, dns_propagation, netbox_dns, openstack_quota
from provisioner.execution import readback_core as c
from provisioner.execution.run_files import (
    digest, encoded, load_private, private_path, read_private, replace_private, require, utcnow, write_new)
from provisioner.execution.service_http import JsonService
from .planned import PlannedServiceLease, service_request_digest
from .read_enrollment import NativeReadEnrollment
from .registry import NativeObservation, RecoveryHeld
from .service_registry import PlannedServiceRegistry


class PlannedServiceGuard:
    def __init__(self, runtime, admitted, selection, step):
        require(type(runtime) is EnrolledServiceProvisioningRuntime,
                'An actual enrolled selected service owner is required')
        self.runtime, self.admitted, self.selection, self.step = runtime, admitted, selection, step
        self.selection_digest, self.operation_kind = _digest(selection), runtime.command_runtime.grant.operation_kind
        self.claimed = False

    def require_current(self):
        runtime, original = self.runtime.command_runtime, self.runtime.command_runtime.grant
        require(runtime.verifier.verify(runtime.transport_evidence) == runtime.identity,
                'The current original service worker mTLS identity changed')
        def checked(_reference, grant, deadline):
            require(grant == original, 'The original selected service grant changed')
            return grant, deadline
        grant, deadline = runtime.grants.with_authorized_reference(runtime.context,
            runtime.identity, original.grant_id, **runtime.grant_arguments(self.admitted), use=checked)
        options = dict(continuation_grant=grant, continuation_identity=runtime.identity) if self.claimed else {}
        _plan, selected = runtime.authority.require_current(self.admitted,
            self.selection_digest, self.operation_kind, **options)
        require(selected == self.selection and grant.step_id == self.step['id']
                and grant.lease_epoch == self.runtime.lease.owner.epoch
                and grant.operation_scope == self.runtime.lease.owner.scope,
                'The selected service plan, exact native pool or original lease changed')
        return grant, min(deadline, self.runtime.lease.owner.expires_at)


class _ServiceContact:
    def __init__(self, authority, material, *, cursor=None):
        require(type(authority) in {SelectedWorkerCommandAuthority, NativeReadEnrollment}
                and isinstance(material, ConsumedVaultCredential),
                'An actual enrolled service contact and revocable native lease are required')
        require(cursor is None or type(authority) is NativeReadEnrollment,
                'Only the independently enrolled reader may reuse a proof transaction')
        self.authority, self.material, self.cursor = authority, material, cursor

    def current(self):
        options={'cursor':self.cursor} if self.cursor is not None else {}
        grant, deadline = self.authority.require_current(**options)
        deadline = min(deadline, self.material.expires_at)
        require(deadline > utcnow(), 'The next service exchange has no remaining original authority')
        return grant,deadline

    def timeout(self, requested=10):
        _grant,deadline=self.current()
        return min(requested, (deadline-utcnow()).total_seconds())

    def require_current(self):
        self.timeout()


def require_service_credentials(data,kind,*,reader=False):
    profiles={'ipam':{'format','netbox'},'dns':{'format','dns'} if reader else {'format','dns','netbox'},
              'dns_cutover':{'format','dns'} if reader else {'format','dns','netbox'},
              'openstack_quota':{'format','quota'}}
    require(type(data) is dict and kind in profiles and set(data)==profiles[kind]
            and data['format']=='hosting-selected-services-credential/1',
            'Only the exact enrolled native service credential projection is accepted')


class _NetBoxContact(JsonService):
    def __init__(self, contact, job, ca, *, writable):
        data = contact.material.data
        expected = {'format','scope_digest','origin','token','token_id','user_id','ca_sha256'}
        require(type(data.get('netbox')) is dict and data['netbox'].keys() == expected,
                'Exact enrolled NetBox credential payload required')
        self.data = data['netbox']
        require(self.data['format'] == 'hosting-netbox-dynamic-token/1'
                and self.data['scope_digest'] == c.digest(job['scope'])
                and self.data['origin'] == job['origin']
                and self.data['ca_sha256'] == (digest(read_private(ca)) if ca else None)
                and type(self.data['token_id']) is int and self.data['token_id'] > 0
                and type(self.data['user_id']) is int and self.data['user_id'] > 0
                and isinstance(self.data['token'],str)
                and re.fullmatch(r'nbt_[A-Za-z0-9]+\.[A-Za-z0-9]+', self.data['token']),
                'The enrolled NetBox credential belongs to another exact native namespace or trust bundle')
        self.contact, self.writable = contact, writable
        super().__init__(job['origin'], 'Bearer '+self.data['token'], ca)

    def authenticate(self):
        row, _headers = super().request('GET', f'/api/users/tokens/{self.data["token_id"]}/',
                                        timeout=self.contact.timeout())
        expires = c.timestamp(row.get('expires'))
        require(row.get('id') == self.data['token_id']
                and ipam.relation(row, 'user') == self.data['user_id']
                and row.get('enabled') is True and row.get('write_enabled') is self.writable
                and row.get('version') == 2 and utcnow() < expires <= self.contact.material.expires_at,
                'Actual native token identity, write profile or bounded expiry differs')
        self.contact.require_current()

    def request(self, method, path, body=None, *, etag=None, timeout=10):
        require(method == 'GET' or self.writable, 'The independent NetBox reader cannot write')
        self.authenticate()
        result = super().request(method,path,body,etag=etag,timeout=min(timeout,self.contact.timeout()))
        self.contact.require_current()
        return result


def _dns_binding(job, scope):
    return c.digest({'server':job['server'],'port':job['port'],'key_name':job['key_name'],
                     'zone':job['zone'],'tenant_id':job['tenant_id'],'resource_id':job['resource_id'],
                     'allowed_records':scope['allowed_records']})


class _DnsContact(dns_change.Client):
    def __init__(self, contact, job, scope):
        data = contact.material.data.get('dns')
        require(type(data) is dict and data.keys()=={'format','binding_digest','secret'}
                and data['format']=='hosting-dns-dynamic-tsig/1'
                and data['binding_digest']==_dns_binding(job,scope),
                'The fresh DNS role must bind the exact endpoint, owner, zone and selected records')
        self.contact = contact
        super().__init__(job['server'],job['port'],job['key_name'],data['secret'])

    def exchange(self, message):
        self.timeout = self.contact.timeout(5)
        result = super().exchange(message)
        self.contact.require_current()
        return result


class _QuotaContact(openstack_quota.Client):
    def __init__(self, contact, request, authority, ca):
        data=contact.material.data.get('quota')
        require(type(data) is dict and data.keys()=={'format','request_digest','token','ca_sha256'}
                and data['format']=='hosting-quota-dynamic-token/1'
                and data['request_digest']==c.digest(request) and data['ca_sha256']==digest(ca),
                'The scoped native quota credential differs from the reviewed exact entitlement request')
        self.contact=contact
        super().__init__(request,authority,data['token'].encode(),ca)

    def call(self, operation):
        self.contact.require_current()
        self.deadline=min(self.deadline, time.monotonic()+self.contact.timeout(120))
        result=super().call(operation)
        self.contact.require_current()
        return result


def _ipam_authority(job, action, contact, ca, *, evidence=None, cleanup=None):
    token=contact.material.data['netbox']['token'].encode()
    _grant, deadline=contact.current()
    return {'request_sha256':ipam.validate(job),'action':action,'valid_from':utcnow().isoformat(),
        'valid_until':min(deadline,contact.material.expires_at).isoformat(),
        'change_ref':'grant:'+_grant.grant_id,'cleanup_ref':cleanup,'evidence_sha256':digest(evidence) if evidence else None,
        'token_sha256':digest(token),'ca_sha256':digest(read_private(ca)) if ca else None}


class EnrolledServiceReadbackOwner:
    """Separate real reader and durable, content-addressed native readback custody."""
    def __init__(self, enrollment: NativeReadEnrollment, directory):
        require(type(enrollment) is NativeReadEnrollment,
                'An independently enrolled native read worker is required')
        self.enrollment=enrollment
        self.directory=private_path(directory,directory=True)

    def _read(self, descriptor, *, cursor=None):
        material=self.enrollment.acquire(cursor=cursor)
        contact=_ServiceContact(self.enrollment,material,cursor=cursor)
        kind=descriptor['kind']; ca=Path(descriptor['ca']) if descriptor.get('ca') else None
        require_service_credentials(material.data,kind,reader=True)
        if kind=='ipam':
            job,receipt=descriptor['job'],descriptor['receipt']
            client=_NetBoxContact(contact,job,ca,writable=False)
            authority=_ipam_authority(job,'reconcile',contact,ca)
            reader=ipam.AllocationReader(job,authority,client)
            reader.namespace(); row,_etag=reader.observed()
            require(row is not None and row['id']==receipt['native_id']
                    and reader.check(row)==receipt['allocation_status'],
                    'Independent native allocation differs from the exact original owner receipt')
            return {'native_id':row['id'],'allocation_status':reader.check(row),'row_digest':c.digest(row)}
        if kind in {'dns','dns_cutover'}:
            job,scope=descriptor['job'],descriptor['scope']
            client=_DnsContact(contact,job,scope)
            before=dns_change.snapshot(job,client); after=dns_change.snapshot(job,client)
            require(before==after and dns_change.matches(after,job,'after'),
                    'Independent authoritative DNS generation differs or remains uncertain')
            return {'snapshot_digest':c.digest(after)}
        require(kind=='openstack_quota', 'Only fixed selected service readers are implemented')
        request=descriptor['request']; data=material.data['quota']; token=data['token'].encode(); rawca=read_private(ca)
        grant,deadline=contact.current()
        authority={'format':'hosting-openstack-quota-authority/1','request_sha256':c.digest(request),
            'action':'observe','token_sha256':digest(token),'ca_sha256':digest(rawca),
            'valid_from':utcnow().isoformat(),'valid_until':min(deadline,material.expires_at).isoformat(),
            'change_ref':'grant:'+grant.grant_id,'writer_exclusion_ref':'read-only:'+grant.grant_id}
        client=_QuotaContact(contact,request,authority,rawca)
        openstack_quota.identities(request,client)
        before=openstack_quota.quotas(request,client.call('read'),request['after'])
        after=openstack_quota.quotas(request,client.call('read'),request['after'])
        require(before==after,'Independent quota state or usage changed while it was observed')
        return {'quotas':after}

    def observe_service(self, runtime, guard, descriptor):
        require(type(runtime) is EnrolledServiceProvisioningRuntime and
                self.enrollment.scope==runtime.lease.owner.scope and
                self.enrollment.subject!=runtime.lease.owner.worker_id,
                'Native service evidence must originate from a different exact-scope enrolled reader')
        original=runtime.registry.get(runtime.command_runtime.context,runtime.command_runtime.grant.operation_id)
        return self.observe_original(runtime.command_runtime.context,runtime.lease,original,descriptor)

    def observe_original(self,context,lease,operation,descriptor):
        from .service_registry import PlannedServiceOperation
        require(type(lease) is PlannedServiceLease and type(operation) is PlannedServiceOperation
                and self.enrollment.scope==lease.owner.scope and self.enrollment.subject!=operation.worker_id
                and (context.organization_id,context.tenant_id)==
                    (lease.owner.organization_id,lease.owner.tenant_id),
                'Independent original service observation must name this exact tenant and scope')
        observed=self._read(descriptor)
        at=utcnow()
        document={'format':'hosting-independent-service-observation/1',
            'operation_id':operation.operation_id,'job_id':operation.job_id,
            'step_id':operation.step_id,'request_digest':lease.request_digest,
            'scope':asdict(lease.owner.scope),'descriptor':descriptor,'observed':observed,
            'observer_subject':self.enrollment.subject,'observed_at':at.isoformat(),
            'read_grant_id':self.enrollment.command.grant.grant_id}
        sha=c.digest(document); write_new(self.directory/(sha+'.json'),encoded(document))
        return NativeObservation('service-observation-'+uuid4().hex,sha,self.enrollment.subject,
                                 None,'EFFECT_PRESENT',True,at)

    def verify_service_observation(self,cursor,context,lease,operation,observation):
        self.enrollment.require_current(cursor=cursor)
        record=load_private(self.directory/(observation.evidence_digest+'.json'))
        require(c.digest(record)==observation.evidence_digest
                and (record['operation_id'],record['job_id'],record['step_id'],record['request_digest'],
                     record['scope'],record['observer_subject'],record['observed_at'],record['read_grant_id'])==
                    (operation.operation_id,operation.job_id,operation.step_id,operation.request_digest,
                     asdict(lease.owner.scope),self.enrollment.subject,observation.observed_at.isoformat(),
                     self.enrollment.command.grant.grant_id)
                and self.enrollment.scope==lease.owner.scope
                and self.enrollment.subject!=operation.worker_id,
                'Copied service observation differs from independently controlled native custody')
        require(self._read(record['descriptor'],cursor=cursor)==record['observed'],
                'Current independent service state differs from its original captured observation')


class EnrolledServiceProvisioningRuntime:
    def __init__(self, *, command_runtime, lease, registry, broker, consumer, ipam_owner,
                 bundles, readback, staged_resources=None):
        from .staged_resources import StagedApplicationResourceAuthority,StagedPlannedLeaseAuthority
        staged=staged_resources is not None
        require(not staged or (type(staged_resources) is StagedApplicationResourceAuthority
                and isinstance(registry.leases,StagedPlannedLeaseAuthority)
                and registry.leases.staged_resources.get(lease.owner.job_id) is staged_resources
                and ipam_owner.resources is staged_resources.transactions()),
                'Current cutover DNS must use its exact independently verified original staged charge')
        require(type(command_runtime) is WorkerCommandRuntime and type(lease) is PlannedServiceLease
                and type(registry) is PlannedServiceRegistry and type(broker) is CredentialBroker
                and type(consumer) is VaultCredentialConsumer and type(ipam_owner) is NetBoxResourceTransactions
                and callable(bundles) and type(readback) is EnrolledServiceReadbackOwner
                and broker._identities is command_runtime.verifier and broker._grants is command_runtime.grants
                and broker._issuer is consumer.issuer and registry.grants is command_runtime.grants
                and command_runtime.grants._leases is registry.leases
                and (registry.leases.resources is ipam_owner.resources or staged) and registry.evidence is readback
                and command_runtime.grant.operation_kind==lease.operation_kind
                and command_runtime.grant.step_id==lease.step_id
                and command_runtime.grant.operation_scope==lease.owner.scope,
                'Concrete enrolled service, original intent, allocation and independent readback owners required')
        self.command_runtime,self.lease,self.registry=command_runtime,lease,registry
        self.broker,self.consumer,self.ipam_owner,self.bundles,self.readback=broker,consumer,ipam_owner,bundles,readback
        self.staged_resources=staged_resources
        from provisioner.controlplane.worker.native_retirement import CompletedNativeGrantRetirement
        self.retirement=CompletedNativeGrantRetirement(store=broker._issuer._lease_store,
            issuer=broker._issuer,grants=command_runtime.grants)

    def _bundle(self,admitted,selection):
        if self.staged_resources is None:return self.bundles(admitted,selection)
        self.staged_resources.require_ready(admitted,selection)
        return self.staged_resources.bundle_for(admitted,selection)

    def _request_digest(self,bundle,selection,step_id):
        if self.staged_resources is None:return service_request_digest(bundle,selection,step_id)
        require(bundle==self.staged_resources.bundle,
                'The staged service may not replace the original resource charge')
        return self.staged_resources.service_request_digest(selection,step_id)

    def run_step(self,admitted,selection,plan,step,packet,directory,base,root):
        return self._run(admitted,selection,plan,step,packet,directory,base,root,recover=False)

    def recover_step(self,admitted,selection,plan,step,packet,directory,base,root,**keywords):
        require(not keywords.get('recovery_authority'),
                'Caller recovery files cannot substitute the exact original service enrollment')
        self.inspect_resolved(admitted,selection,plan,step,packet,directory,base,root)
        return delivery_steps.complete(step,packet,directory,plan,load_private(Path(directory)/'result.json'),
                                       ['result.json','native-service-binding.json'])

    def inspect_resolved(self,admitted,selection,plan,step,packet,directory,base,root):
        """Fresh independent original readback; grants no original writer retry."""
        runtime=self.command_runtime
        _original,artifact=runtime.authority.require_observation(admitted,_digest(selection),self.lease.operation_kind)
        require(artifact==selection and _digest(plan)==selection['deliveryPlanDigest']
                and self._request_digest(self._bundle(admitted,selection),selection,step['id'])==self.lease.request_digest,
                'The resolved service observation changed its retained original selection')
        binding=selection['stageBindings'][step['id']]
        from provisioner.controlplane.workflow.execution_selection import _AUTHORITY_FILES
        require(binding['parametersDigest']==_digest(packet['parameters'])
                and binding['inputDigests']=={name:asset['sha256'] for name,asset in packet['files'].items()
                    if name not in _AUTHORITY_FILES},
                'The resolved service inputs differ from their retained original plan')
        delivery_steps.file_paths(packet)
        operation=self.registry.get(runtime.context,runtime.grant.operation_id)
        require(operation.state=='RESOLVED' and operation.outcome=='EFFECT_PRESENT',
                'Unresolved original DNS/service work cannot become a lifecycle traffic receipt')
        descriptor=load_private(Path(directory)/'native-service-binding.json')
        observation=self.readback.observe_original(runtime.context,self.lease,operation,descriptor)
        self.registry.reconcile_observed(runtime.context,self.lease,operation.operation_id,observation)
        return {'format':'hosting-resolved-service-inspection/1','operation_id':operation.operation_id,
                'request_digest':operation.request_digest,'receipt':load_private(Path(directory)/'result.json'),
                'service_observation_digest':observation.evidence_digest,'observed_at':observation.observed_at.isoformat()}

    def _prior_dns(self,prior_id,registration,job):
        runtime=self.command_runtime
        from provisioner.controlplane.jobs.repository import _tenant
        with self.registry.connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,runtime.context)
            cursor.execute('SELECT state,outcome,operation_kind,resolution_evidence_digest FROM '
                'hosting_controlplane.native_operation_intents WHERE organization_id=%s AND tenant_id=%s '
                'AND operation_id=%s FOR SHARE',(runtime.context.organization_id,runtime.context.tenant_id,prior_id))
            row=cursor.fetchone()
            require(row is not None and row[:3]==('RESOLVED','EFFECT_PRESENT','DNS_CHANGE'),
                    'Traffic switching requires an independently resolved original DNS_CHANGE intent')
            record=load_private(self.readback.directory/(row[3]+'.json'))
            require(c.digest(record)==row[3] and record['operation_id']==prior_id
                    and record['descriptor']['kind'] in {'dns','dns_cutover'}
                    and record['descriptor']['receipt']=={key:value for key,value in registration.items()
                        if key not in {'service_observation_digest','native_operation_id','credential_retirement_digest'}}
                    and registration.get('service_observation_digest')==row[3]
                    and registration.get('native_operation_id')==prior_id,
                    'Traffic switching parent differs from retained independent original DNS receipt')
            prior=record['descriptor']['job']
            require(job['previous_marker']==dns_change.marker_value(prior)
                    and dns_change.payload(job,'before')==dns_change.payload(prior,'after')
                    and all(job[key]==prior[key] for key in ('tenant_id','resource_id','zone','server','port')),
                    'Traffic switching may alter only the exact previously owned authoritative generation')
            return prior

    def _cutover(self,bundle,allocation,confirmation,job,scope,client,directory,base,authority,registration):
        require(len(job['records'])==1 and job['records'][0]['type'] in {'A','PTR'}
                and job['records'][0]['before'] is not None and job['records'][0]['after'] is not None
                and job['tenant_id']==allocation['scope']['tenant_key'] and job['resource_id']==allocation['member'],
                'One exact selected application A or PTR generation is supported')
        import ipaddress
        address=ipaddress.ip_interface(allocation['address']).ip; selected=job['records'][0]
        require((selected['type']=='A' and selected['after']['values']==[str(address)])
                or (selected['type']=='PTR' and selected['name']==address.reverse_pointer+'.'
                    and len(selected['after']['values'])==1),
                'Traffic switching must describe the exact confirmed target address')
        netbox_dns.confirmed(allocation,confirmation)
        ledger=delivery_steps.owner_ledger(base,'dns')
        slot=ledger/c.digest([job['zone'],job['tenant_id'],job['resource_id']])
        slot.mkdir(mode=0o700,exist_ok=True); private_path(slot,directory=True)
        lock=os.open(slot/'lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        try:
            fcntl.flock(lock,fcntl.LOCK_EX)
            path=slot/(job['operation_id']+'.json')
            require(not path.exists() and not path.is_symlink(),
                    'The original DNS update attempt exists; observe its outcome without repeating it')
            header={'format':'hosting-netbox-dns-receipt/1','status':'DNS_CUTOVER_HELD',
                    'binding_sha256':c.digest({'allocation':allocation,'confirmation':confirmation,'job':job,'scope':scope,
                                              'registration':registration}), 'action':'cutover','dns':None,
                    'activation_authorized':False,'reusable':False}
            write_new(path,encoded(header))
            def retain(report):
                authority.require_current(); header['dns']=report; replace_private(path,encoded(header))
            report=dns_change.change(job,scope,client,execute=True,record=retain)
            require(report['status'] in dns_change.STATES,
                    'Original traffic update remains uncertain; retain its intent and address charge')
            header['dns']=report; header['status']='AUTHORITATIVE_REGISTRATION_OBSERVED'
            replace_private(path,encoded(header)); return header
        finally:
            fcntl.flock(lock,fcntl.LOCK_UN); os.close(lock)

    def _run(self,admitted,selection,plan,step,packet,directory,base,root,*,recover):
        runtime=self.command_runtime; bundle=self._bundle(admitted,selection)
        require(step['kind'] in {'ipam','dns','dns_cutover','openstack_quota'} and step['id']==self.lease.step_id
                and admitted.job_id==self.lease.owner.job_id
                and (bundle.admitted.job_id==admitted.job_id or self.staged_resources is not None)
                and self._request_digest(bundle,selection,step['id'])==self.lease.request_digest,
                'The actual service request differs from its exact selected immutable resource parent')
        guard=PlannedServiceGuard(self,admitted,selection,step)
        authority=runtime.select(admitted,selection,plan,step,packet,root,intent_guard=guard)
        delivery_steps.validate_packet(step,packet,plan,base,root=root)
        files=delivery_steps.file_paths(packet); values=packet['parameters']
        directory=private_path(directory,directory=True); base=private_path(base,directory=True)
        original=self.registry.prepare(runtime.context,self.lease,grant=runtime.grant,identity=runtime.identity)
        if recover:
            require(original.state=='RESOLVED' and original.outcome=='EFFECT_PRESENT',
                    'Uncertain service effects require separately approved recovery and writer exclusion')
            guard.claimed=False
            descriptor=load_private(directory/'native-service-binding.json')
            observation=self.readback.observe_service(self,guard,descriptor)
            self.registry.reconcile_observed(runtime.context,self.lease,original.operation_id,observation)
            return delivery_steps.complete(step,packet,directory,plan,load_private(directory/'result.json'),
                                           ['result.json','native-service-binding.json'])
        require(original.state=='PREPARED','Original service intent was already claimed; observe without retry')
        handle=self.broker.acquire(runtime.transport_evidence,runtime.context,runtime.grant.grant_id,
                                   **runtime.grant_arguments(admitted))
        material=self.consumer.unwrap(handle,runtime.grant)
        require_service_credentials(material.data,step['kind'])
        contact=_ServiceContact(authority,material)
        ca=files.get('ca_bundle',files.get('ca'))
        # Credentials and namespace are verified before recording the single
        # native claim. All exchanges after claim use its exact continuation.
        if step['kind']=='ipam':
            request=load_private(files['request'])
            selected=request if request.keys()==ipam.SELECTION_FIELDS else ipam_selection(request)
            owner_id=self.ipam_owner.resources._require_accounted(bundle)['receipts'][0]['owner_id']
            job=bind_selection(bundle,owner_id,selected)
            require(request.keys()==ipam.SELECTION_FIELDS or request==job,
                    'A retained runtime IPAM request belongs to another original admitted job')
            action=values['action']; self.ipam_owner._parent(bundle,job,action)
            require(action in {'reserve','confirm'},
                    'Cleanup/reuse requires the separately approved recovery owner')
            client=_NetBoxContact(contact,job,ca,writable=True); client.authenticate()
        elif step['kind'] in {'dns','dns_cutover'}:
            job,scope=load_private(files['job']),load_private(files['scope'])
            allocation=load_private(files['allocation']); confirmation=load_private(files['confirmation'])
            require(allocation==bind_selection(bundle,
                self.ipam_owner.resources._require_accounted(bundle)['receipts'][0]['owner_id'],ipam_selection(allocation)),
                'DNS allocation belongs to another exact current resource parent')
            ipam_client=_NetBoxContact(contact,allocation,ca,writable=False)
            authority_record=_ipam_authority(allocation,'reconcile',contact,ca)
            self.ipam_owner.require_observed(bundle,allocation,confirmation,authority_record,
                client=ipam_client,required_state='active')
            client=_DnsContact(contact,job,scope)
            if step['kind']=='dns':
                require(values['action']=='register','Withdrawal requires the separately approved resource recovery owner')
                netbox_dns.validate(allocation,confirmation,job,scope,action=values['action'])
            else:
                registration=load_private(files['registration'])
                self._prior_dns(values['prior_operation_id'],registration,job)
        else:
            request=load_private(files['request']); openstack_quota.validate(request)
            require(request['project']['id']==self.lease.owner.scope.native_scope_id
                    and request['operation_id']==runtime.grant.operation_id
                    and request['source_commit']==selection['sourceCommit'],
                    'Quota ownership differs from the exact selected native project or current operation')
            data=material.data['quota']; rawca=read_private(ca)
            grant,deadline=authority.require_current()
            native_authority={'format':'hosting-openstack-quota-authority/1','request_sha256':c.digest(request),
                'action':'apply','token_sha256':digest(data['token'].encode()),'ca_sha256':digest(rawca),
                'valid_from':utcnow().isoformat(),'valid_until':min(deadline,material.expires_at).isoformat(),
                'change_ref':'grant:'+grant.grant_id,'writer_exclusion_ref':'intent:'+grant.operation_id}
            client=_QuotaContact(contact,request,native_authority,rawca)
            openstack_quota.identities(request,client)
        require(self.registry.claim_once(runtime.context,self.lease,original.operation_id,runtime.identity),
                'Original native service operation was already claimed')
        guard.claimed=True
        try:
            authority.require_current()
            if step['kind']=='ipam':
                native_authority=_ipam_authority(job,action,contact,ca)
                with self.ipam_owner.resources.authority.locked_ipam(bundle,job,action):
                    result=ipam.operate(job,action,native_authority,client,self.ipam_owner.ledger)
                descriptor={'kind':'ipam','job':job,'receipt':result,'ca':str(ca) if ca else None}
            elif step['kind']=='dns_cutover':
                result=self._cutover(bundle,allocation,confirmation,job,scope,client,directory,base,authority,registration)
                descriptor={'kind':'dns_cutover','job':job,'scope':scope,'receipt':result,'ca':str(ca) if ca else None}
            elif step['kind']=='dns':
                token=material.data['netbox']['token'].encode(); secret=material.data['dns']['secret'].encode()
                binding=netbox_dns.validate(allocation,confirmation,job,scope,action=values['action'])
                grant,deadline=authority.require_current()
                native_authority={'format':'hosting-netbox-dns-authority/1','binding_sha256':binding,
                    'action':values['action'],'valid_from':utcnow().isoformat(),
                    'valid_until':min(deadline,material.expires_at).isoformat(),'change_ref':'grant:'+grant.grant_id,
                    'token_sha256':digest(token),'ca_sha256':digest(read_private(ca)) if ca else None,
                    'tsig_sha256':digest(secret)}
                result=netbox_dns.operate(allocation,confirmation,job,scope,native_authority,
                    ipam_client,client,self.ipam_owner.ledger,action=values['action'])
                descriptor={'kind':'dns','job':job,'scope':scope,'ca':str(ca) if ca else None}
            else:
                result=openstack_quota.operate(request,native_authority,data['token'].encode(),rawca,
                    delivery_steps.owner_ledger(base,'openstack_quota'),root=root,client=client)
                descriptor={'kind':'openstack_quota','request':request,'ca':str(ca)}
            authority.require_current()
            require(result.get('native_acceptance',False) is False and result.get('production_activation',False) is False,
                    'A service owner result cannot grant native qualification or production activation')
            result.update(native_acceptance=False,production_activation=False)
            descriptor['receipt']=result
            write_new(directory/'native-service-binding.json',encoded(descriptor))
            observation=self.readback.observe_service(self,guard,descriptor)
            self.registry.acknowledge(runtime.context,self.lease,original.operation_id,runtime.identity,observation)
            retirement_digest=self.retirement.retire(self,admitted,selection)
            result=result|{'service_observation_digest':observation.evidence_digest,
                           'native_operation_id':original.operation_id,'credential_retirement_digest':retirement_digest}
            write_new(directory/'result.json',encoded(result))
            return delivery_steps.complete(step,packet,directory,plan,result,
                                           ['result.json','native-service-binding.json'])
        except BaseException:
            try: self.registry.mark_uncertain(runtime.context,original.operation_id,runtime.identity.subject)
            except Exception: pass
            raise
