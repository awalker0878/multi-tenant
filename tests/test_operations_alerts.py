"""Operations alert acknowledgement, escalation and containment-release tests."""
from copy import deepcopy
import unittest

from provisioner.execution import operations_alerts as a
from provisioner.execution import operations_review as o

NOW='2026-09-21T12:00:00+00:00'
LATE='2026-09-21T13:00:00+00:00'
MID='2026-09-21T12:30:00+00:00'
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
        ],
    }


def benign_drift():
    value=review(); value['observations'][0]['observed_sha256']=B
    return value


def security_drift():
    value=benign_drift(); value['observations'][0].update(
        security_relevant=True,containment_on_failure=True,owner_route='incident')
    return value


def acknowledgement(result, *, observation_id='config', classification='BENIGN_DRIFT',
                    owner='platform-operations', at=NOW, review_sha256=None):
    return {
        'format':a.ACK_FORMAT,'review_sha256':review_sha256 or result['review_sha256'],
        'observation_id':observation_id,'classification':classification,'owner':owner,
        'acknowledged_by':'ops-oncall','acknowledged_at':at,'response_ref':'INCIDENT-RESPONSE-01',
    }


def release_record(result, *, observation_ids=('config',), at=NOW):
    return {
        'format':a.RELEASE_FORMAT,'review_sha256':result['review_sha256'],
        'observation_ids':list(observation_ids),'authority_ref':'OPERATING-AUTH-01',
        'released_at':at,'restoration_ref':'EDGE-RESTORATION-01',
    }


class AcknowledgementTests(unittest.TestCase):
    def test_healthy_review_has_no_alerts_to_acknowledge(self):
        outcome=a.evaluate(review(),o.evaluate(review(),now=NOW),[],now=NOW)
        self.assertEqual(outcome['status'],'ALERTS_NONE')
        self.assertEqual(outcome['alerts'],[])
        self.assertFalse(outcome['escalation_owner_required'])
        self.assertFalse(outcome['native_acceptance'] or outcome['production_activation'])
        a.enforce(outcome)

    def test_unacknowledged_alert_is_pending_within_its_cadence(self):
        value=benign_drift(); result=o.evaluate(value,now=NOW)
        outcome=a.evaluate(value,result,[],now=NOW)
        self.assertEqual(outcome['status'],'ALERTS_PENDING')
        self.assertEqual(outcome['alerts'][0]['state'],'PENDING')
        self.assertEqual(outcome['alerts'][0]['owner'],'platform-operations')
        self.assertEqual(outcome['alerts'][0]['escalate_by'],LATE)
        with self.assertRaises(a.AlertHold) as held:
            a.enforce(outcome)
        self.assertFalse(held.exception.escalate)

    def test_unacknowledged_alert_escalates_after_one_cadence(self):
        value=benign_drift(); result=o.evaluate(value,now=NOW)
        outcome=a.evaluate(value,result,[],now=LATE)
        self.assertEqual(outcome['status'],'ALERTS_ESCALATED')
        self.assertEqual(outcome['alerts'][0]['state'],'ESCALATED')
        self.assertTrue(outcome['escalation_owner_required'])
        with self.assertRaises(a.AlertHold) as held:
            a.enforce(outcome)
        self.assertTrue(held.exception.escalate)

    def test_acknowledgement_from_the_alert_owner_closes_it(self):
        value=benign_drift(); result=o.evaluate(value,now=NOW)
        outcome=a.evaluate(value,result,[acknowledgement(result)],now=NOW)
        self.assertEqual(outcome['status'],'ALERTS_ACKNOWLEDGED')
        self.assertEqual(outcome['alerts'][0]['state'],'ACKNOWLEDGED')
        self.assertEqual(outcome['alerts'][0]['acknowledged_by'],'ops-oncall')
        a.enforce(outcome)

    def test_acknowledgement_from_another_owner_is_rejected(self):
        value=benign_drift(); result=o.evaluate(value,now=NOW)
        with self.assertRaisesRegex(ValueError,'accountable alert owner'):
            a.evaluate(value,result,[acknowledgement(result,owner='service-owner')],now=NOW)

    def test_acknowledgement_for_a_foreign_review_is_rejected(self):
        value=benign_drift(); result=o.evaluate(value,now=NOW)
        with self.assertRaisesRegex(ValueError,'does not bind this operations review'):
            a.evaluate(value,result,[acknowledgement(result,review_sha256='c'*64)],now=NOW)

    def test_acknowledgement_cannot_rebind_a_different_classification(self):
        value=benign_drift(); result=o.evaluate(value,now=NOW)
        with self.assertRaisesRegex(ValueError,'exact alert classification'):
            a.evaluate(value,result,[acknowledgement(result,classification='SECURITY_CRITICAL')],now=NOW)

    def test_acknowledgement_for_an_observation_without_an_alert_is_rejected(self):
        value=benign_drift(); result=o.evaluate(value,now=NOW)
        with self.assertRaisesRegex(ValueError,'no alert'):
            a.evaluate(value,result,[acknowledgement(result,observation_id='health')],now=NOW)

    def test_duplicate_acknowledgement_is_rejected(self):
        value=benign_drift(); result=o.evaluate(value,now=NOW)
        with self.assertRaisesRegex(ValueError,'Duplicate acknowledgement'):
            a.evaluate(value,result,[acknowledgement(result),acknowledgement(result)],now=NOW)

    def test_late_acknowledgement_records_escalation(self):
        value=benign_drift(); result=o.evaluate(value,now=NOW)
        outcome=a.evaluate(value,result,[acknowledgement(result,at=LATE)],now=LATE)
        self.assertEqual(outcome['status'],'ALERTS_ESCALATED')
        self.assertEqual(outcome['alerts'][0]['state'],'LATE')
        with self.assertRaises(a.AlertHold) as held:
            a.enforce(outcome)
        self.assertTrue(held.exception.escalate)

    def test_future_acknowledgement_is_rejected(self):
        value=benign_drift(); result=o.evaluate(value,now=NOW)
        with self.assertRaisesRegex(ValueError,'cannot postdate'):
            a.evaluate(value,result,[acknowledgement(result,at=LATE)],now=NOW)

    def test_alert_hold_never_requests_containment_withdrawal(self):
        value=security_drift(); result=o.evaluate(value,now=NOW)
        outcome=a.evaluate(value,result,[],now=NOW)
        with self.assertRaises(a.AlertHold) as held:
            a.enforce(outcome)
        self.assertFalse(getattr(held.exception,'containment_required',True))

    def test_result_cannot_authorize_reconciliation_or_activation(self):
        value=benign_drift(); result=deepcopy(o.evaluate(value,now=NOW))
        result['ordinary_reconciliation_authorized']=True
        with self.assertRaisesRegex(ValueError,'cannot authorize reconciliation'):
            a.evaluate(value,result,[],now=NOW)

    def test_result_must_bind_the_exact_review_digest(self):
        value=benign_drift(); result=o.evaluate(value,now=NOW)
        other=benign_drift(); other['generation']=2
        with self.assertRaisesRegex(ValueError,'does not bind this review'):
            a.evaluate(other,result,[],now=NOW)


class ContainmentReleaseTests(unittest.TestCase):
    def test_release_requires_every_contained_alert_acknowledged(self):
        value=security_drift(); result=o.evaluate(value,now=NOW)
        outcome=a.evaluate(value,result,[],release=release_record(result),now=NOW)
        self.assertFalse(outcome['containment_release_authorized'])
        self.assertEqual(outcome['release_blocked_reason'],'CONTAINED_ALERT_NOT_ACKNOWLEDGED')
        with self.assertRaisesRegex(a.AlertHold,'unacknowledged'):
            a.enforce(outcome)

    def test_release_is_authorized_after_accountable_acknowledgement(self):
        value=security_drift(); result=o.evaluate(value,now=NOW)
        record=acknowledgement(result,classification='SECURITY_CRITICAL',owner='incident-response')
        outcome=a.evaluate(value,result,[record],release=release_record(result),now=NOW)
        self.assertEqual(outcome['status'],'ALERTS_ACKNOWLEDGED')
        self.assertTrue(outcome['containment_release_authorized'])
        self.assertIsNone(outcome['release_blocked_reason'])
        a.enforce(outcome)

    def test_release_must_bind_the_exact_contained_alert_set(self):
        value=security_drift(); result=o.evaluate(value,now=NOW)
        record=acknowledgement(result,classification='SECURITY_CRITICAL',owner='incident-response')
        outcome=a.evaluate(value,result,[record],release=release_record(result,observation_ids=('config','health')),now=NOW)
        self.assertFalse(outcome['containment_release_authorized'])
        self.assertEqual(outcome['release_blocked_reason'],'RELEASE_DOES_NOT_BIND_EXACT_CONTAINED_ALERTS')

    def test_release_cannot_precede_the_accountable_response(self):
        value=security_drift(); result=o.evaluate(value,now=NOW)
        record=acknowledgement(result,classification='SECURITY_CRITICAL',owner='incident-response',at=MID)
        outcome=a.evaluate(value,result,[record],
                           release=release_record(result,at='2026-09-21T12:15:00+00:00'),now='2026-09-21T12:40:00+00:00')
        self.assertEqual(outcome['alerts'][0]['state'],'ACKNOWLEDGED')
        self.assertFalse(outcome['containment_release_authorized'])
        self.assertEqual(outcome['release_blocked_reason'],'RELEASE_PRECEDES_ACCOUNTABLE_RESPONSE')

    def test_release_without_containment_is_rejected(self):
        value=benign_drift(); result=o.evaluate(value,now=NOW)
        outcome=a.evaluate(value,result,[acknowledgement(result)],release=release_record(result),now=NOW)
        self.assertFalse(outcome['containment_release_authorized'])
        self.assertEqual(outcome['release_blocked_reason'],'NO_CONTAINMENT_TO_RELEASE')

    def test_release_for_a_foreign_review_is_rejected(self):
        value=security_drift(); result=o.evaluate(value,now=NOW)
        record=release_record(result); record['review_sha256']='c'*64
        with self.assertRaisesRegex(ValueError,'does not bind this operations review'):
            a.evaluate(value,result,[],release=record,now=NOW)


if __name__=='__main__':
    unittest.main()