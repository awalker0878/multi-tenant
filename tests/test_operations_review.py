"""Operations drift/health/capacity classification tests; no native mutation."""
from copy import deepcopy
import unittest

from tools import operations_review as o

NOW='2026-09-21T12:00:00+00:00'
A='a'*64
B='b'*64


def review():
    return {
        'format':'hosting-operations-review/1',
        'source_commit':'68b254d76589aadf55a0b38810e0bcc07bf12a68',
        'operation_id':'ops-review-01',
        'generation':1,
        'scope':{
            'environment_key':'reference','site_key':'site-01','platform':'openstack',
            'tenant_key':'tenant-01','wsd_key':'science-prod',
        },
        'cadence_seconds':3600,
        'authorization_ref':'OPERATING-AUTH-01',
        'routes':{
            'operations':{'owner':'platform-operations','route_ref':'route/operations'},
            'incident':{'owner':'incident-response','route_ref':'route/incident'},
            'capacity':{'owner':'capacity-owner','route_ref':'route/capacity'},
            'service':{'owner':'service-owner','route_ref':'route/service'},
        },
        'observations':[
            {
                'id':'config','kind':'configuration','owner_route':'operations',
                'observed_at':NOW,'evidence_ref':'evidence/config',
                'security_relevant':False,'containment_on_failure':False,'state':None,
                'expected_sha256':A,'observed_sha256':A,'emergency_override':None,
            },
            {
                'id':'health','kind':'health','owner_route':'service',
                'observed_at':NOW,'evidence_ref':'evidence/health',
                'security_relevant':False,'containment_on_failure':False,'state':'healthy',
                'expected_sha256':None,'observed_sha256':None,'emergency_override':None,
            },
            {
                'id':'capacity','kind':'capacity','owner_route':'capacity',
                'observed_at':NOW,'evidence_ref':'evidence/capacity',
                'security_relevant':False,'containment_on_failure':False,'state':'within_envelope',
                'expected_sha256':None,'observed_sha256':None,'emergency_override':None,
            },
            {
                'id':'telemetry','kind':'telemetry','owner_route':'operations',
                'observed_at':NOW,'evidence_ref':'evidence/telemetry',
                'security_relevant':False,'containment_on_failure':False,'state':'current',
                'expected_sha256':None,'observed_sha256':None,'emergency_override':None,
            },
        ],
    }


class OperationsReviewTests(unittest.TestCase):
    def test_healthy_review_never_grants_reconciliation_or_activation(self):
        result=o.evaluate(review(),now=NOW)
        self.assertEqual(result['status'],'OPERATIONS_HEALTHY')
        self.assertEqual(result['alerts'],[])
        self.assertFalse(result['ordinary_reconciliation_authorized'])
        self.assertFalse(result['native_acceptance'] or result['production_activation'])

    def test_benign_drift_routes_action_without_containment(self):
        value=review(); value['observations'][0]['observed_sha256']=B
        result=o.evaluate(value,now=NOW)
        self.assertEqual(result['status'],'OPERATIONS_ACTION_REQUIRED')
        self.assertEqual(result['observations'][0]['classification'],'BENIGN_DRIFT')
        self.assertEqual(result['alerts'][0]['owner'],'platform-operations')
        self.assertFalse(result['containment_required'])
        with self.assertRaises(o.OperationsHold) as held:
            o.enforce(result)
        self.assertFalse(held.exception.containment_required)

    def test_security_drift_requires_containment(self):
        value=review(); row=value['observations'][0]
        row.update(observed_sha256=B,security_relevant=True,containment_on_failure=True,owner_route='incident')
        result=o.evaluate(value,now=NOW)
        self.assertEqual(result['status'],'OPERATIONS_HOLD_CONTAINMENT_REQUIRED')
        self.assertEqual(result['observations'][0]['classification'],'SECURITY_CRITICAL')
        self.assertTrue(result['containment_required'])
        self.assertEqual(result['alerts'][0]['route_ref'],'route/incident')
        with self.assertRaises(o.OperationsHold) as held:
            o.enforce(result)
        self.assertTrue(held.exception.containment_required)

    def test_active_emergency_override_is_preserved_and_never_auto_repaired(self):
        value=review(); row=value['observations'][0]
        row['observed_sha256']=B
        row['emergency_override']={
            'ref':'EMERGENCY-CHANGE-01','expected_sha256':A,'observed_sha256':B,
            'valid_from':'2026-09-21T11:00:00+00:00','valid_until':'2026-09-21T13:00:00+00:00',
            'incident_ref':'INC-01','closure_ref':None,
        }
        result=o.evaluate(value,now=NOW)
        self.assertEqual(result['status'],'OPERATIONS_HOLD_EMERGENCY_OVERRIDE_PRESERVED')
        self.assertEqual(result['observations'][0]['classification'],'APPROVED_EMERGENCY')
        self.assertTrue(result['emergency_override_preserved'])
        self.assertFalse(result['ordinary_reconciliation_authorized'])
        self.assertFalse(result['containment_required'])

    def test_expired_emergency_override_does_not_become_desired_state(self):
        value=review(); row=value['observations'][0]
        row.update(observed_sha256=B,security_relevant=True,containment_on_failure=True,owner_route='incident')
        row['emergency_override']={
            'ref':'EMERGENCY-CHANGE-01','expected_sha256':A,'observed_sha256':B,
            'valid_from':'2026-09-21T10:00:00+00:00','valid_until':'2026-09-21T11:00:00+00:00',
            'incident_ref':'INC-01','closure_ref':None,
        }
        result=o.evaluate(value,now=NOW)
        self.assertEqual(result['observations'][0]['classification'],'SECURITY_CRITICAL')
        self.assertTrue(result['containment_required'])

    def test_stale_observation_is_unknown_and_can_require_containment(self):
        value=review(); row=value['observations'][1]
        row.update(observed_at='2026-09-21T10:00:00+00:00',security_relevant=True,
                   containment_on_failure=True,owner_route='incident')
        result=o.evaluate(value,now=NOW)
        entry=next(x for x in result['observations'] if x['id']=='health')
        self.assertEqual(entry['classification'],'UNKNOWN')
        self.assertFalse(entry['fresh'])
        self.assertTrue(result['containment_required'])

    def test_capacity_exhaustion_is_critical_action_but_not_security_containment(self):
        value=review(); value['observations'][2]['state']='exhausted'
        result=o.evaluate(value,now=NOW)
        self.assertEqual(result['status'],'OPERATIONS_ACTION_REQUIRED')
        alert=next(x for x in result['alerts'] if x['observation_id']=='capacity')
        self.assertEqual(alert['classification'],'EXHAUSTED')
        self.assertEqual(alert['severity'],'critical')
        self.assertFalse(alert['containment_required'])

    def test_telemetry_loss_holds_and_routes_to_exact_owner(self):
        value=review(); row=value['observations'][3]
        row.update(state='unavailable',containment_on_failure=True)
        result=o.evaluate(value,now=NOW)
        self.assertEqual(result['status'],'OPERATIONS_HOLD_CONTAINMENT_REQUIRED')
        alert=next(x for x in result['alerts'] if x['observation_id']=='telemetry')
        self.assertEqual(alert['owner'],'platform-operations')
        self.assertEqual(alert['classification'],'UNAVAILABLE')

    def test_security_drift_cannot_disable_containment_eligibility(self):
        value=review(); row=value['observations'][0]
        row.update(observed_sha256=B,security_relevant=True,containment_on_failure=False)
        with self.assertRaisesRegex(ValueError,'containment eligible'):
            o.validate(value)

    def test_matched_configuration_cannot_keep_old_emergency_override(self):
        value=review(); row=value['observations'][0]
        row['emergency_override']={
            'ref':'OLD-EMERGENCY','expected_sha256':A,'observed_sha256':A,
            'valid_from':'2026-09-21T11:00:00+00:00','valid_until':'2026-09-21T13:00:00+00:00',
            'incident_ref':'INC-OLD','closure_ref':None,
        }
        with self.assertRaisesRegex(ValueError,'Matched configuration'):
            o.evaluate(value,now=NOW)

    def test_capacity_cannot_request_automatic_security_containment(self):
        value=review(); value['observations'][2]['containment_on_failure']=True
        with self.assertRaisesRegex(ValueError,'not automatic security containment'):
            o.validate(value)

    def test_foreign_override_digests_are_rejected(self):
        value=review(); row=value['observations'][0]
        row['observed_sha256']=B
        row['emergency_override']={
            'ref':'EMERGENCY-CHANGE-01','expected_sha256':A,'observed_sha256':'c'*64,
            'valid_from':'2026-09-21T11:00:00+00:00','valid_until':'2026-09-21T13:00:00+00:00',
            'incident_ref':'INC-01','closure_ref':None,
        }
        with self.assertRaisesRegex(ValueError,'exact configuration drift'):
            o.validate(value)


if __name__=='__main__':
    unittest.main()
