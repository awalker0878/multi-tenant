"""Delivery-runner binding for retirement review; no owner mutation occurs."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from tools import delivery_steps as steps, readback_core as c
from tools.run_files import digest, encoded, load_private, read_private, write_new


SOURCE='a'*40
SCOPE={'environment_key':'reference','site_key':'site-01','platform':'openstack',
       'tenant_key':'tenant-01','wsd_key':'science-prod'}


def retirement_plan():
    return {'format':'hosting-retirement/1','source_commit':SOURCE,'operation_id':'retire-001','generation':1,
        'scope':deepcopy(SCOPE),
        'resources':[
            {'id':'vm-01','kind':'compute','owner':'compute-owner','native_id':'server-01',
             'disposition':'remove','shared':False,'retained_data_refs':[]},
            {'id':'capacity-01','kind':'capacity','owner':'capacity-owner','native_id':'reservation-01',
             'disposition':'deprecate','shared':False,'retained_data_refs':[]}],
        'retained_data':[],
        'actions':[
            {'id':'cleanup-native','type':'cleanup_native_resources','needs':[],'resources':['vm-01']},
            {'id':'release-capacity','type':'release_capacity','needs':['cleanup-native'],'resources':['capacity-01']},
            {'id':'close-service','type':'close_service','needs':['release-capacity'],'resources':['capacity-01']}]}


def retirement_evidence(value,count):
    return {'format':'hosting-retirement-evidence/1','plan_sha256':c.digest(value),'receipts':[
        {'action_id':row['id'],'status':'COMPLETED','resource_ids':sorted(row['resources']),
         'observed_at':'2026-09-21T12:00:00+00:00','evidence_ref':'evidence/'+row['id']}
        for row in value['actions'][:count]]}


class DeliveryRetirementTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name); self.directory=self.base/'review'; self.directory.mkdir(mode=0o700)
        self.plan={'format':'hosting-delivery/1','source_commit':SOURCE,'operation_id':'delivery-retire',
                   'generation':1,'scope':deepcopy(SCOPE),
                   'steps':[{'id':'retirement','kind':'retirement_review','needs':[]}]}
        self.step=self.plan['steps'][0]
        self.retirement=retirement_plan()

    def packet(self,count=1):
        files={}
        for name,value in {'plan':self.retirement,'evidence':retirement_evidence(self.retirement,count)}.items():
            path=self.base/(name+'.json'); write_new(path,encoded(value))
            files[name]={'path':str(path),'sha256':digest(read_private(path))}
        return {'format':'hosting-delivery-step/1','plan_sha256':c.digest(self.plan),'step_id':'retirement',
                'dependencies':{},'parameters':{},'files':files}

    def test_review_stage_records_exact_pending_owner_without_native_acceptance(self):
        packet=self.packet(1)
        steps.validate_packet(self.step,packet,self.plan,self.base)
        result,names=steps.dispatch(self.step,packet,self.directory,self.base,self.plan,self.base)
        self.assertEqual(result['status'],'RETIREMENT_HELD_PENDING_OWNER_EVIDENCE')
        self.assertEqual(result['next_action'],'release-capacity')
        self.assertIn('retirement-review.json',names)
        self.assertIn('owner-completion.json',names)
        stored=load_private(self.directory/'retirement-review.json')
        self.assertEqual(stored['plan_sha256'],c.digest(self.retirement))
        self.assertFalse(stored['native_acceptance'] or stored['production_activation'])

    def test_complete_review_still_requires_external_acceptance(self):
        result,_=steps.dispatch(self.step,self.packet(3),self.directory,self.base,self.plan,self.base)
        self.assertEqual(result['status'],'RETIREMENT_EVIDENCE_COMPLETE_REQUIRES_ACCEPTANCE')

    def test_foreign_source_is_rejected_before_review(self):
        self.retirement['source_commit']='b'*40
        with self.assertRaisesRegex(ValueError,'Foreign retirement review'):
            steps.validate_packet(self.step,self.packet(1),self.plan,self.base)


if __name__=='__main__':
    unittest.main()
