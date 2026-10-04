"""Actual enrolled read-only DNS authority and resolver propagation owner."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import time

import dns.opcode

from provisioner.controlplane.jobs.repository import _tenant
from provisioner.controlplane.worker.command_runtime import WorkerCommandRuntime,SelectedWorkerCommandAuthority
from provisioner.controlplane.worker.grants import CredentialBroker
from provisioner.controlplane.worker.vault_consumer import VaultCredentialConsumer,ConsumedVaultCredential
from provisioner.execution import delivery_steps,dns_propagation
from provisioner.execution import readback_core as c
from provisioner.execution.run_files import digest,encoded,load_private,private_path,require,utcnow,write_new


def view_binding(target,job,scope):
    return c.digest({'format':'hosting-enrolled-dns-view/1',
        'target':{key:value for key,value in target.items() if key!='tsig_sha256'},
        'zone':job['zone'],'tenant_id':job['tenant_id'],'resource_id':job['resource_id'],
        'records':[{'name':row['name'],'type':row['type']} for row in job['records']],
        'scope':scope['allowed_records']})


class EnrolledDnsPropagationContext:
    """Only refresh authentication; retain every approved view and RR selector."""
    def __init__(self,runtime,authority,material,config,job,scope,receipt):
        require(type(runtime) is EnrolledDnsPropagationRuntime
                and type(authority) is SelectedWorkerCommandAuthority
                and type(material) is ConsumedVaultCredential
                and material.data.keys()=={'format','dns_views'}
                and material.data['format']=='hosting-selected-dns-views-credential/1'
                and type(material.data['dns_views']) is dict,
                'Actual current enrolled DNS read contact required')
        self.runtime,self.authority,self.material=runtime,authority,material
        self.original=deepcopy(config); self.job,self.scope,self.receipt=map(deepcopy,(job,scope,receipt))
        self.original_digest=c.digest(config); self.effective=deepcopy(config); self.secrets={}
        views=material.data['dns_views']
        require(views.keys()=={target['id'] for target in config['targets']},
                'Fresh DNS read role changed its exact independent view set')
        for target in self.effective['targets']:
            native=views[target['id']]
            require(type(native) is dict and native.keys()=={'format','binding_digest','secret'}
                    and native['format']=='hosting-dns-dynamic-view/1'
                    and native['binding_digest']==view_binding(target,job,scope)
                    and type(native['secret']) is str,
                    'Dynamic TSIG material changed its selected server, view, owner or RR scope')
            self.secrets[target['id']]=native['secret']
            target['tsig_sha256']=digest(native['secret'].encode())
        self.document_digests=tuple(c.digest(value) for value in (self.original,self.effective,self.job,self.scope,self.receipt))
        self.require_current()

    def require_current(self):
        require(tuple(c.digest(value) for value in (self.original,self.effective,self.job,self.scope,self.receipt))==self.document_digests,
                'The immutable enrolled DNS view or original generation changed')
        grant,deadline=self.authority.require_current()
        require(grant.operation_kind=='DISCOVER_READ' and grant==self.runtime.command_runtime.grant,
                'DNS propagation cannot borrow a write or another reader grant')
        deadline=min(deadline,self.material.expires_at)
        require(deadline>utcnow(),'The next DNS observation has no remaining original read authority')
        return deadline

    def validate(self,config,job,scope,receipt):
        require((config,job,scope,receipt)==(self.original,self.job,self.scope,self.receipt),
                'DNS propagation contact differs from the complete selected generation')
        dns_propagation.validate(self.effective,job,scope,receipt,self.secrets)

    def client(self,target,config,end):
        require(config==self.effective and target in self.effective['targets'],
                'The native DNS client cannot switch its selected observer view')
        return _EnrolledViewClient(target,self.secrets[target['id']],config,end,self)


class _EnrolledViewClient(dns_propagation.Client):
    def __init__(self,target,secret,config,end,context):
        super().__init__(target,secret,config,end); self.context=context

    def exchange(self,message):
        require(message.opcode()==dns.opcode.QUERY, 'The enrolled propagation owner cannot issue an UPDATE')
        deadline=self.context.require_current()
        self.end=min(self.end,time.monotonic()+(deadline-utcnow()).total_seconds())
        response=super().exchange(message); self.context.require_current(); return response


class EnrolledDnsPropagationRuntime:
    def __init__(self,*,command_runtime,broker,consumer,services,registry,directory):
        from .service_runtime import EnrolledServiceReadbackOwner
        from .service_registry import PlannedServiceRegistry
        require(type(command_runtime) is WorkerCommandRuntime and type(broker) is CredentialBroker
                and type(consumer) is VaultCredentialConsumer and type(services) is EnrolledServiceReadbackOwner
                and command_runtime.grant.operation_kind=='DISCOVER_READ'
                and broker._grants is command_runtime.grants and broker._identities is command_runtime.verifier
                and broker._issuer is consumer.issuer,
                'Actual enrolled DNS observer grant, dynamic broker and independent service custody required')
        require(type(registry) is PlannedServiceRegistry and registry.grants is command_runtime.grants
                and registry.evidence is services,
                'The existing selected service journal and independent reader must share this native enrollment')
        self.command_runtime,self.broker,self.consumer,self.registry=command_runtime,broker,consumer,registry
        self.services=services; self.directory=private_path(directory,directory=True)

    def _primary(self,receipt):
        runtime=self.command_runtime; context=runtime.context
        operation_id=receipt.get('native_operation_id'); sha=receipt.get('service_observation_digest')
        require(type(operation_id) is str and type(sha) is str and c.HEX.fullmatch(sha),
                'Propagation requires the retained independently resolved primary receipt')
        with self.registry.connect() as connection,connection.cursor() as cursor:
            _tenant(cursor,context)
            cursor.execute('SELECT state,outcome,operation_kind,resolution_evidence_digest,worker_id,request_digest '
                'FROM hosting_controlplane.native_operation_intents WHERE organization_id=%s AND tenant_id=%s '
                'AND operation_id=%s FOR SHARE',(context.organization_id,context.tenant_id,operation_id))
            row=cursor.fetchone()
            require(row is not None and row[:4]==('RESOLVED','EFFECT_PRESENT','DNS_CHANGE',sha)
                    and row[4]!=runtime.identity.subject,
                    'Primary UPDATE must be independently resolved before a different reader observes propagation')
            record=load_private(self.services.directory/(sha+'.json'))
            require(c.digest(record)==sha and record['operation_id']==operation_id
                    and record['request_digest']==row[5]
                    and record['descriptor']['receipt']=={key:value for key,value in receipt.items()
                        if key not in {'native_operation_id','service_observation_digest','credential_retirement_digest'}},
                    'Propagation changed the original authoritative primary handoff')
            return row[5]

    def _collect(self,admitted,selection,plan,step,packet,base,root):
        runtime=self.command_runtime
        require(step['kind']=='dns_propagation' and step['id']==runtime.grant.step_id,
                'The enrolled observer supports only its originally selected propagation step')
        authority=runtime.select(admitted,selection,plan,step,packet,root)
        files=delivery_steps.file_paths(packet)
        job,scope,receipt=delivery_steps.dns_handoff(step,packet,plan,base)
        request_digest=self._primary(receipt); config=load_private(files['config'])
        handle=self.broker.acquire(runtime.transport_evidence,runtime.context,runtime.grant.grant_id,
                                   **runtime.grant_arguments(admitted))
        material=self.consumer.unwrap(handle,runtime.grant)
        context=EnrolledDnsPropagationContext(self,authority,material,config,job,scope,receipt)
        delivery_steps.validate_packet(step,packet,plan,base,root=root,enrolled_dns_context=context)
        observed=dns_propagation.observe(context.effective,job,scope,receipt,context.secrets,enrolled_context=context)
        result={'format':'hosting-enrolled-dns-propagation/1','primary_operation_id':receipt['native_operation_id'],
            'primary_request_digest':request_digest,'primary_receipt_digest':c.digest(receipt),
            'original_config_digest':context.original_digest,'reader_subject':runtime.identity.subject,
            'read_grant_id':runtime.grant.grant_id,'credential_lease_digest':material.lease_digest,
            'observation':observed,'native_acceptance':False,'production_activation':False}
        sha=c.digest(result); write_new(self.directory/(sha+'.json'),encoded(result))
        return result

    def inspect_resolved(self,admitted,selection,plan,step,packet,directory,base,root):
        """Repeat only native QUERYs under fresh actual reader authority."""
        previous=load_private(Path(directory)/'dns-observation.json')
        result=self._collect(admitted,selection,plan,step,packet,base,root)
        require(all(previous[key]==result[key] for key in ('format','primary_operation_id',
            'primary_request_digest','primary_receipt_digest','original_config_digest')),
            'Fresh resolver observations differ from the retained exact original DNS generation')
        return result

    def run_step(self,admitted,selection,plan,step,packet,directory,base,root):
        result=self._collect(admitted,selection,plan,step,packet,base,root); sha=c.digest(result)
        retained=Path(directory)/'dns-observation.json'
        names=['dns-observation.json']
        if retained.exists():
            previous=load_private(retained)
            require(all(previous[key]==result[key] for key in ('format','primary_operation_id',
                'primary_request_digest','primary_receipt_digest','original_config_digest')),
                'The interrupted original propagation observation changed its selected generation')
            name='dns-observation-'+sha+'.json'; delivery_steps.retain(Path(directory)/name,encoded(result)); names.append(name)
        else: write_new(retained,encoded(result))
        return delivery_steps.complete(step,packet,directory,plan,result,names)

    def recover_step(self,admitted,selection,plan,step,packet,directory,base,root,**keywords):
        require(not keywords.get('recovery_authority'), 'Queue-supplied resolver credentials cannot renew read authority')
        # A current newly issued read sweep is safe; it never repeats UPDATE.
        # Preserve the old sweep and publish a separate fresh custody document.
        return self.run_step(admitted,selection,plan,step,packet,directory,base,root)
