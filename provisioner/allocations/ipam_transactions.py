"""Compose selected NetBox allocations with one job-bound resource reservation.

The existing NetBox allocation ledger owns address effects and uncertainty;
the capacity owner's database owns resource accounting. Neither ledger is
replaced. Remote IPAM failures keep both holds and require reconciliation.
"""
from __future__ import annotations

import re
from pathlib import Path

from provisioner.allocations import netbox_ipam as ipam
from provisioner.allocations.transactions import ResourceBundle, ResourceTransactions
from provisioner.execution.run_files import digest, encoded, load_private, read_private, require
from provisioner.execution.service_http import JsonService


def selection(job):
    """The pre-admission allocation selection recorded in execution custody.

    Runtime operation/generation/parent reservation references are added only
    after the job exists, so an execution artifact never hashes its own plan.
    """
    ipam.validate(job)
    return {key:value for key,value in job.items()
            if key not in {'operation_id','generation','reservation_ref'}}


def bind_selection(bundle: ResourceBundle, owner_id: str, selected: dict):
    """Add runtime parent/operation identity to an approved IPAM selection."""
    require(isinstance(bundle,ResourceBundle), 'Exact admitted resource selection required')
    ipam.validate_selection(selected)
    parents=[request for request in bundle.requests(owner_id,current=False)
             if request['scope']==selected['scope']]
    require(len(parents)==1, 'One exact capacity reservation must own the selected IPAM scope')
    job=selected|{'operation_id':'address-'+digest(encoded([
        bundle.admitted.job_id,selected['scope'],selected['member']]))[:32],
        'generation':bundle.admitted.plan_revision,
        'reservation_ref':'capacity:'+parents[0]['reservation_id']}
    ipam.validate(job)
    return job


class NetBoxResourceTransactions:
    def __init__(self, resources: ResourceTransactions, ledger):
        require(isinstance(resources,ResourceTransactions)
                and callable(getattr(resources.authority,'locked_ipam',None)),
                'Current protected IPAM selection authority required')
        self.resources=resources
        self.ledger=Path(ledger)

    def _parent(self,bundle,job,action):
        require(isinstance(bundle,ResourceBundle), 'Exact admitted resource selection required')
        ipam.validate(job)
        result=(self.resources.require_ready(bundle) if action in {'reserve','confirm','reconcile'}
                else self.resources.inspect(bundle))
        parents=[receipt for receipt in result['receipts'] if receipt['scope']==job['scope']
                 and job['reservation_ref']=='capacity:'+receipt['reservation_id']]
        require(len(parents)==1 and job['generation']==bundle.admitted.plan_revision,
                'IPAM allocation differs from its exact resource parent')
        expected='address-'+digest(encoded([bundle.admitted.job_id,job['scope'],job['member']]))[:32]
        require(job['operation_id']==expected,
                'IPAM operation identity differs from the admitted job/member')
        members=set()
        for pool in bundle.pools:
            if pool.inputs is not None and pool.demand(current=False)['scope']==job['scope']:
                members.update(pool.inputs['members'])
        require(job['member'] in members,
                'IPAM member is absent from the immutable workload demand')
        if action=='confirm':
            require(parents[0]['status']=='CONFIRMED',
                    'Observe and confirm native resource occupancy before making its address active')
        if action in ipam.RETIREMENT_ACTIONS:
            require(parents[0]['status']=='RELEASED',
                    'Observe resource cleanup before address retirement/quarantine/release')
        return parents[0]

    def operate(self,bundle,job,action,authority,*,token_bytes,ca_bundle=None,evidence=None):
        require(action in ipam.ACTIONS, 'Unknown authoritative IPAM transition')
        self._parent(bundle,job,action)
        ca_bytes=read_private(ca_bundle) if ca_bundle is not None else None
        ipam.validate_authority(job,action,authority,token_bytes,ca_bytes,evidence)
        token=token_bytes.decode().strip()
        require(re.fullmatch(r'nbt_[A-Za-z0-9]+\.[A-Za-z0-9]+',token),
                'Scoped NetBox v2 credential required')
        client=JsonService(job['origin'],'Bearer '+token,ca_bundle)
        with self.resources.authority.locked_ipam(bundle,job,action):
            # Authority is checked again by AllocationReader before each HTTP
            # call; its uncertain attempt is durable before any POST/PATCH.
            return ipam.operate(job,action,authority,client,self.ledger,evidence)

    def require_observed(self,bundle,job,receipt,authority,*,client,required_state='reserved'):
        """Consume an owner receipt only after exact fresh native readback.

        Reserved address receipts admit an isolated target build; confirmed
        active receipts additionally depend on observed native resource IDs.
        No copied receipt grants allocation, DNS, native or activation authority.
        """
        require(required_state in {'reserved','active'}, 'Selected lifecycle state must be explicit')
        self._parent(bundle,job,'confirm' if required_state=='active' else 'reserve')
        require(isinstance(receipt,dict) and receipt.get('format')=='hosting-netbox-receipt/1'
                and receipt.get('status')=='OBSERVED'
                and receipt.get('request_sha256')==digest(encoded(job))
                and receipt.get('allocation_status')==required_state,
                'Exact current authoritative IPAM lifecycle receipt required')
        with self.resources.authority.locked_ipam(bundle,job,'reconcile'):
            reader=ipam.AllocationReader(job,authority,client)
            with ipam.allocation_lock(self.ledger,job) as directory:
                head=load_private(directory/'head.json')
                require(head==receipt,
                        'IPAM receipt changed or an uncertain native effect is unresolved')
                reader.namespace()
                row,_=reader.observed()
                require(row is not None and row['id']==receipt['native_id']
                        and reader.check(row)==receipt['allocation_status'],
                        'Authoritative IPAM allocation differs from its receipt')
        return receipt
