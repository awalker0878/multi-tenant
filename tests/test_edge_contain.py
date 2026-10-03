"""Delegated containment cannot introduce allows or replay a lost withdrawal."""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import tempfile
import unittest
from tests.test_nft_edge import fixture
from tools import edge_contain as c,nft_edge as edge
from provisioner.execution.run_files import digest,encoded,load_private,replace_private,utcnow


def state(spec):
    table,scope=edge.validate(spec)
    rows=[{'table':dict(family='inet',name=table,handle=1,comment='hosting:'+scope+':fixture:withdraw')},
          {'chain':dict(family='inet',table=table,name='forward',handle=2,type='filter',hook='forward',prio=-100,policy='accept')}]
    for interface in spec['owned_interfaces']:
        for direction in ('iifname','oifname'):
            match={'match':{'op':'==','left':{'meta':{'key':direction}},'right':interface}}
            for tail in ([{'limit':{'rate':10,'per':'second','burst':5}},{'log':{'prefix':table[:28]+' '}}],
                         [{'counter':{'packets':12,'bytes':100}},{'drop':None}]):
                rows.append({'rule':dict(family='inet',table=table,chain='forward',handle=len(rows),expr=[match,*tail])})
    return {'nftables':rows}


class Kernel:
    def __init__(self,spec): self.spec=spec; self.state={'owned':True}; self.writes=0; self.lost=False
    def inspect(self,spec): return deepcopy(self.state),digest(encoded(edge.normalized(self.state)))
    def command(self,args):
        if '--check' in args: return ''
        self.writes+=1; self.state=state(self.spec)
        if self.lost: raise OSError('native reply lost after withdrawal')
        return ''


class ContainmentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.base=Path(self.temp.name)
        self.ledger=self.base/'ledger'; self.ledger.mkdir(mode=0o700); self.spec=fixture(); self.kernel=Kernel(self.spec)
        self.authority=dict(format='hosting-edge-containment-authority/1',spec_sha256=digest(encoded(self.spec)),incident_id='incident-01',
            valid_from=(utcnow()-timedelta(seconds=1)).isoformat(),valid_until=(utcnow()+timedelta(minutes=10)).isoformat(),
            change_ref='TEST-INCIDENT',boundary_acceptance_ref='TEST-BOUNDARY')
    def operate(self,name):
        folder=self.base/name; folder.mkdir(mode=0o700)
        return c.contain(self.spec,self.authority,self.kernel,self.ledger,folder)
    def test_withdrawal_removes_exposure_and_repeat_only_observes(self):
        first=self.operate('first'); second=self.operate('second')
        self.assertEqual(first['status'],'CONTAINED_OBSERVED_NOT_QUALIFIED')
        self.assertTrue(first['write_attempted']); self.assertFalse(second['write_attempted'])
        self.assertEqual(self.kernel.writes,1)
        text=(self.base/'first/candidate.nft').read_text()
        self.assertNotIn('counter accept',text); self.assertNotIn('flush ruleset',text)
        self.assertIn('counter drop',text)

    def test_read_only_observation_cannot_initiate_incident(self):
        folder=self.base/'observation'; folder.mkdir(mode=0o700)
        with self.assertRaisesRegex(ValueError,'Observation cannot start'):
            c.contain(self.spec,self.authority,self.kernel,self.ledger,folder,observe_only=True)
        self.assertEqual(self.kernel.writes,0)
        self.operate('withdraw')
        result=c.contain(self.spec,self.authority,self.kernel,self.ledger,folder,observe_only=True)
        self.assertFalse(result['write_attempted']); self.assertEqual(self.kernel.writes,1)
    def test_lost_reply_keeps_owner_hold_and_recovers_by_observation(self):
        self.kernel.lost=True
        with self.assertRaises(OSError): self.operate('first')
        head=next(self.ledger.glob('*/head.json')); previous=head.read_bytes()
        self.assertEqual(self.operate('resume')['status'],'CONTAINED_OBSERVED_NOT_QUALIFIED')
        self.assertEqual(self.kernel.writes,1); self.assertEqual(head.read_bytes(),previous)
        self.assertEqual(load_private(head)['status'],'OUTCOME_UNKNOWN')
    def test_reopened_or_missing_drop_rules_cannot_claim_containment(self):
        original=state(self.spec)
        for mutation in (lambda x:x['nftables'][-1]['rule']['expr'].__setitem__(-1,{'accept':None}),
            lambda x:x['nftables'][0]['table'].update(flags=['dormant']),
            lambda x:x['nftables'][1]['chain'].update(prio=0),
            lambda x:x['nftables'].pop(),
            lambda x:x['nftables'][-1]['rule']['expr'][0]['match'].update(right='foreign0'),
            lambda x:x['nftables'].append({'set':{'name':'hidden'}})):
            value=deepcopy(original); mutation(value)
            with self.assertRaises(ValueError): c.observed_withdrawal(self.spec,value)
    def test_expired_or_foreign_delegation_cannot_issue_native_write(self):
        self.authority['spec_sha256']='0'*64
        with self.assertRaises(ValueError): self.operate('foreign')
        self.authority['spec_sha256']=digest(encoded(self.spec))
        self.authority['valid_until']=(utcnow()-timedelta(seconds=1)).isoformat()
        with self.assertRaises(ValueError): self.operate('expired')
        self.assertEqual(self.kernel.writes,0)

    def test_completed_containment_does_not_clear_older_unknown_forward_write(self):
        forward=self.base/'forward'; forward.mkdir(mode=0o700)
        authority=dict(spec_sha256=digest(encoded(self.spec)),mode='active',
            expected_state_sha256=self.kernel.inspect(self.spec)[1],valid_from=self.authority['valid_from'],
            valid_until=self.authority['valid_until'],change_ref='TEST-FORWARD',boundary_acceptance_ref='TEST-BOUNDARY',
            readiness_ref='TEST-READINESS')
        self.kernel.lost=True
        with self.assertRaises(OSError): edge.apply(self.spec,'active',authority,self.kernel,self.ledger,forward)
        self.kernel.lost=False
        self.assertEqual(self.operate('contain')['status'],'CONTAINED_OBSERVED_NOT_QUALIFIED')
        self.assertEqual(load_private(next(self.ledger.glob('*/head.json')))['status'],'APPLIED_EXPIRING_POLICY_NOT_QUALIFIED')
        next_spec=dict(self.spec,operation_id='new-forward',generation=2)
        authority.update(spec_sha256=digest(encoded(next_spec)),expected_state_sha256=self.kernel.inspect(self.spec)[1])
        next_run=self.base/'next'; next_run.mkdir(mode=0o700); writes=self.kernel.writes
        with self.assertRaisesRegex(ValueError,'Unresolved native edge history'):
            edge.apply(next_spec,'active',authority,self.kernel,self.ledger,next_run)
        self.assertEqual(self.kernel.writes,writes)

    def test_completed_history_allows_next_generation_and_detects_changed_receipts(self):
        self.operate('contain')
        spec=dict(self.spec,operation_id='reviewed-reopen',generation=2)
        authority=dict(spec_sha256=digest(encoded(spec)),mode='active',
            expected_state_sha256=self.kernel.inspect(spec)[1],valid_from=self.authority['valid_from'],
            valid_until=self.authority['valid_until'],change_ref='TEST-REOPEN',boundary_acceptance_ref='TEST-BOUNDARY',
            readiness_ref='TEST-READINESS')
        directory=self.base/'reopen'; directory.mkdir(mode=0o700)
        self.assertEqual(edge.apply(spec,'active',authority,self.kernel,self.ledger,directory)['status'],
                         'APPLIED_EXPIRING_POLICY_NOT_QUALIFIED')
        head=next(self.ledger.glob('*/head.json')); record=load_private(head)
        boundary=record['boundary_sha256']
        self.assertEqual(edge.completed_history(head.parent,boundary),2)
        identity=digest(encoded([record['operation_id'],record['generation'],record['mode']]))
        result_path=head.parent/(identity+'.result.json'); original=result_path.read_bytes()
        for update in ({'generation':True},{'spec_sha256':'0'*64},{'completed_at':'2000-01-01T00:00:00+00:00'}):
            replace_private(result_path,encoded(record|update))
            with self.assertRaises(ValueError): edge.completed_history(head.parent,boundary)
        replace_private(result_path,original); head.unlink()
        with self.assertRaisesRegex(ValueError,'head differs'): edge.completed_history(result_path.parent,boundary)


if __name__=='__main__': unittest.main()
