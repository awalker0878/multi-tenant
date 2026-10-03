"""Delivery-runner binding for operations alert accountability; no owner mutation occurs."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from tests.test_operations_alerts import NOW, acknowledgement, benign_drift, release_record, review, security_drift
from provisioner.execution import readback_core as c
from provisioner.execution import delivery_steps as steps, operations_alerts as a, operations_review as o
from provisioner.execution.run_files import digest, encoded, load_private, read_private, write_new

SOURCE='68b254d76589aadf55a0b38810e0bcc07bf12a68'
SCOPE={'environment_key':'reference','site_key':'site-01','platform':'openstack',
       'tenant_key':'tenant-01','wsd_key':'science-prod'}


class DeliveryAlertsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name); self.directory=self.base/'alerts'; self.directory.mkdir(mode=0o700)
        self.plan={'format':'hosting-delivery/2','source_commit':SOURCE,'operation_id':'delivery-alerts',
                   'generation':1,'reviewed_plan_digest':'0'*64,'scope':deepcopy(SCOPE),
                   'steps':[{'id':'alerts','kind':'operations_alerts','needs':[]}], 'operation_bindings':{},'reviewed_parameters':{},'compiled_catalog_ids':{}}
        self.step=self.plan['steps'][0]

    def packet(self, value, result, records, *, release=None):
        payload={'review':value,'result':result,'acknowledgements':records}
        if release is not None: payload['release']=release
        files={}
        for name,record in payload.items():
            path=self.base/(name+'.json'); write_new(path,encoded(record))
            files[name]={'path':str(path),'sha256':digest(read_private(path))}
        return {'format':'hosting-delivery-step/1','plan_sha256':c.digest(self.plan),'step_id':'alerts',
                'dependencies':{},'parameters':{},'files':files}

    def acknowledged(self):
        value=benign_drift(); result=o.evaluate(value,now=NOW)
        return value,result,[acknowledgement(result)]

    def test_healthy_review_completes_without_alerts(self):
        value=review(); result=o.evaluate(value,now=NOW)
        packet=self.packet(value,result,[])
        steps.validate_packet(self.step,packet,self.plan,self.base)
        outcome,names=steps.dispatch(self.step,packet,self.directory,self.base,self.plan,self.base)
        self.assertEqual(outcome['status'],'ALERTS_NONE')
        self.assertIn('alert-accounting.json',names)
        self.assertFalse(outcome['native_acceptance'] or outcome['production_activation'])
        stored=load_private(self.directory/'alert-accounting.json')
        self.assertEqual(stored['review_sha256'],c.digest(value))

    def test_acknowledged_alert_completes_and_never_asserts_acceptance(self):
        value,result,records=self.acknowledged()
        packet=self.packet(value,result,records)
        outcome,names=steps.dispatch(self.step,packet,self.directory,self.base,self.plan,self.base)
        self.assertEqual(outcome['status'],'ALERTS_ACKNOWLEDGED')
        self.assertEqual(outcome['alerts'][0]['acknowledged_by'],'ops-oncall')
        self.assertFalse(outcome['escalation_owner_required'])
        self.assertIn('owner-completion.json',names)

    def test_unacknowledged_alert_holds_the_stage_before_completion(self):
        value=benign_drift(); result=o.evaluate(value,now=NOW)
        packet=self.packet(value,result,[])
        with self.assertRaises(a.AlertHold):
            steps.dispatch(self.step,packet,self.directory,self.base,self.plan,self.base)
        self.assertTrue((self.directory/'alert-accounting.json').exists())
        self.assertFalse((self.directory/'owner-completion.json').exists())

    def test_alert_hold_never_requests_containment_withdrawal(self):
        value=security_drift(); result=o.evaluate(value,now=NOW)
        packet=self.packet(value,result,[])
        try:
            steps.dispatch(self.step,packet,self.directory,self.base,self.plan,self.base)
        except a.AlertHold as error:
            self.assertFalse(error.containment_required)
            self.assertTrue(error.escalate)
        else:
            self.fail('Escalated security alert must hold the delivery stage')

    def test_authorized_release_requires_the_exact_acknowledged_alert(self):
        value=security_drift(); result=o.evaluate(value,now=NOW)
        records=[acknowledgement(result,classification='SECURITY_CRITICAL',owner='incident-response')]
        release=release_record(result)
        outcome,names=steps.dispatch(self.step,self.packet(value,result,records,release=release),
                                     self.directory,self.base,self.plan,self.base)
        self.assertTrue(outcome['containment_release_authorized'])
        self.assertIsNone(outcome['release_blocked_reason'])
        self.assertIn('alert-accounting.json',names)

    def test_unacknowledged_containment_blocks_release_before_completion(self):
        value=security_drift(); result=o.evaluate(value,now=NOW)
        release=release_record(result)
        with self.assertRaises(a.AlertHold):
            steps.dispatch(self.step,self.packet(value,result,[],release=release),
                           self.directory,self.base,self.plan,self.base)

    def test_foreign_review_is_rejected_before_any_artifact(self):
        value,result,records=self.acknowledged(); value['source_commit']='b'*40
        packet=self.packet(value,result,records)
        with self.assertRaisesRegex(ValueError,'Foreign operations alert review'):
            steps.validate_packet(self.step,packet,self.plan,self.base)
            self.assertEqual(list(self.directory.iterdir()),[])

    def test_recovery_reuses_durable_accounting_and_escalates_held_alerts(self):
        value=security_drift(); result=o.evaluate(value,now=NOW)
        packet=self.packet(value,result,[])
        with self.assertRaises(a.AlertHold):
            steps.dispatch(self.step,packet,self.directory,self.base,self.plan,self.base)
        with self.assertRaises(a.AlertHold):
            steps.recover(self.step,packet,self.directory,self.base,self.plan,self.base)

    def test_recovery_completes_durable_acknowledged_alerts(self):
        value,result,records=self.acknowledged()
        packet=self.packet(value,result,records)
        steps.dispatch(self.step,packet,self.directory,self.base,self.plan,self.base)
        (self.directory/'owner-completion.json').unlink()
        outcome,names=steps.recover(self.step,packet,self.directory,self.base,self.plan,self.base)
        self.assertEqual(outcome['status'],'ALERTS_ACKNOWLEDGED')
        self.assertIn('owner-completion.json',names)

    def test_recovery_rejects_changed_acknowledgement(self):
            value,result,records=self.acknowledged()
            packet=self.packet(value,result,records)
            steps.dispatch(self.step,packet,self.directory,self.base,self.plan,self.base)
            (self.directory/'owner-completion.json').unlink()
            stored=load_private(self.directory/'alert-accounting.json')
            stored['alerts'][0]['acknowledged_by']='other-oncall'
            (self.directory/'alert-accounting.json').unlink()
            write_new(self.directory/'alert-accounting.json',encoded(stored))
            with self.assertRaisesRegex(ValueError,'Interrupted operations alert acknowledgement changed'):
                steps.recover(self.step,packet,self.directory,self.base,self.plan,self.base)


if __name__=='__main__':
    unittest.main()