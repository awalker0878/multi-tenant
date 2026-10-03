"""Real loopback TLS IPAM requests with real SQLite resource accounting.

All NetBox responses and admitted authority are local-only fixtures. This does
not verify a deployed NetBox token, conditional-update installation or native
OpenStack project; the transport, owner ledger and parent gates really execute.
"""
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests import test_netbox_ipam as ipam_fixture
from tests import test_resource_transactions as resource_fixture
from provisioner.allocations.ipam_transactions import NetBoxResourceTransactions, bind_selection, selection
from provisioner.allocations import netbox_ipam
from provisioner.allocations.transactions import ResourceTransactions
from provisioner.execution.run_files import digest, encoded, load_private, read_private


class LocalIPAMAuthority(resource_fixture.LocalAuthority):
    def __init__(self, source, destination):
        super().__init__(source,destination)
        self.ipam_selection=None

    @contextmanager
    def locked_ipam(self,bundle,job,action):
        if self.refused or bundle.digest!=self.allowed_bundle or selection(job)!=self.ipam_selection:
            raise ValueError('Synthetic IPAM selection rejected')
        yield None


class IPAMResourceTransactionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ipam_fixture.NetboxTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        ipam_fixture.NetboxTests.tearDownClass()

    def setUp(self):
        self.ipam=ipam_fixture.NetboxTests()
        self.ipam.setUp(); self.addCleanup(self.ipam.doCleanups)
        self.resources=resource_fixture.ResourceTransactionTests()
        self.resources.setUp(); self.addCleanup(self.resources.doCleanups)
        self.bundle=self.resources.bundle
        self.guard=LocalIPAMAuthority(self.resources.source,self.resources.destination)
        self.guard.allowed_bundle=self.bundle.digest
        self.owner=ResourceTransactions(self.resources.path,self.guard)
        self.adapter=NetBoxResourceTransactions(self.owner,self.ipam.ledger)
        self.selected={key:value for key,value in self.ipam.job.items()
                       if key not in {'operation_id','generation','reservation_ref'}}
        self.selected.update(scope=self.resources.request['scope'],member='processor-01')
        self.guard.ipam_selection=deepcopy(self.selected)
        self.job=bind_selection(self.bundle,'capacity-01',self.selected)
        self.token=b'nbt_local.fixture'
        self.ca=Path(self.resources.temp.name)/'ipam-ca.pem'
        self.ca.write_bytes((self.ipam.base/'ca.pem').read_bytes())
        self.ca.chmod(0o600)

    def authority(self,action):
        return self.ipam.authority|{'request_sha256':ipam_fixture.validate(self.job),
            'action':action,'change_ref':'LOCAL-ONLY','cleanup_ref':None,
            'evidence_sha256':None,'token_sha256':digest(self.token),
            'ca_sha256':digest(read_private(self.ca))}

    def operate(self,action):
        return self.adapter.operate(self.bundle,self.job,action,self.authority(action),
                                    token_bytes=self.token,ca_bundle=self.ca)

    def test_pre_admission_selection_requires_no_runtime_identity_or_service_contact(self):
        with patch.object(netbox_ipam,'JsonService',side_effect=AssertionError('Service construction is not parsing')):
            self.assertEqual(netbox_ipam.validate_selection(self.selected),digest(encoded(self.selected)))
            with self.assertRaises(ValueError): netbox_ipam.validate_selection(self.selected|{'generation':1})
            with self.assertRaises(ValueError): netbox_ipam.validate_selection(self.selected|{'tenant_id':True})
        self.assertEqual(self.ipam.calls,[])

    def test_no_ipam_contact_without_exact_reserved_parent_or_current_selection(self):
        with self.assertRaises(ValueError): self.operate('reserve')
        self.assertEqual(self.ipam.calls,[])
        self.owner.reserve(self.bundle)
        self.guard.ipam_selection['address']='192.0.2.21/24'
        with self.assertRaisesRegex(ValueError,'selection rejected'): self.operate('reserve')
        self.assertEqual(self.ipam.calls,[])

    def test_live_parent_then_authoritative_ipam_receipt_and_native_readback(self):
        parent=self.owner.reserve(self.bundle)['receipts'][0]
        receipt=self.operate('reserve')
        self.assertEqual(receipt['allocation_status'],'reserved')
        repeated=self.operate('reserve')
        self.assertEqual(repeated['native_id'],receipt['native_id'])
        receipt=repeated
        self.assertEqual(sum(method=='POST' for method,_ in self.ipam.calls),1)
        self.assertEqual(self.adapter.require_observed(self.bundle,self.job,receipt,
            self.authority('reconcile'),client=self.ipam.client),receipt)
        with self.assertRaisesRegex(ValueError,'confirm native resource occupancy'):
            self.operate('confirm')
        observation=self.resources.observation(parent)
        self.guard.evidence.add(observation.evidence_digest)
        self.owner.confirm(self.bundle,(observation,))
        active=self.operate('confirm')
        self.assertEqual(active['allocation_status'],'active')
        self.assertEqual(self.adapter.require_observed(self.bundle,self.job,active,
            self.authority('reconcile'),client=self.ipam.client,required_state='active'),active)

    def test_lost_ipam_reply_keeps_resource_charge_and_reconciles_without_another_post(self):
        self.owner.reserve(self.bundle)
        original=ipam_fixture.JsonService.request
        def lost(client,method,*args,**kwargs):
            result=original(client,method,*args,**kwargs)
            if method=='POST': raise TimeoutError('Synthetic lost successful response')
            return result
        with patch.object(ipam_fixture.JsonService,'request',lost),self.assertRaises(TimeoutError):
            self.operate('reserve')
        head=load_private(next(self.ipam.ledger.glob('*/head.json')))
        self.assertEqual(head['status'],'OUTCOME_UNKNOWN')
        self.assertEqual(self.owner.inspect(self.bundle)['receipts'][0]['status'],'RESERVED')
        with self.assertRaises(ValueError): self.operate('reserve')
        reconciled=self.operate('reconcile')
        self.assertEqual(reconciled['allocation_status'],'reserved')
        self.assertEqual(sum(method=='POST' for method,_ in self.ipam.calls),1)

    def test_foreign_parent_or_member_cannot_reuse_selected_allocation(self):
        self.owner.reserve(self.bundle)
        for change in ({'reservation_ref':'capacity:foreign'},
                       {'generation':2},{'member':'foreign-member'}):
            original=self.job
            self.job=self.job|change
            with self.subTest(change=change),self.assertRaises(ValueError): self.operate('reserve')
            self.job=original
        self.assertEqual(self.ipam.calls,[])

    def test_changed_native_owner_invalidates_a_copied_confirmed_receipt(self):
        self.owner.reserve(self.bundle)
        receipt=self.operate('reserve')
        ipam_fixture.NetboxTests.row['tenant']={'id':99}
        with self.assertRaisesRegex(ValueError,'ownership or allocation changed'):
            self.adapter.require_observed(self.bundle,self.job,receipt,
                self.authority('reconcile'),client=self.ipam.client)


if __name__=='__main__': unittest.main()
