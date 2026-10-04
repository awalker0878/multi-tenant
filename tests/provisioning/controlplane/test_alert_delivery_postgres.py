"""Real monitor SQL role, immutable attempts, concurrent dispatch and signed HTTPS receipts."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime,timezone
import os
import threading
import unittest

from provisioner.controlplane.discovery.alert_delivery import AlertDeliveryRepository
from provisioner.controlplane.discovery.alert_transport import AlertDeliveryHeld
from provisioner.controlplane.discovery.freshness_history import FreshnessHistoryRepository
from provisioner.controlplane.discovery.freshness_monitor import alert_projection
from provisioner.controlplane.discovery.monitor_runtime import require_monitor_role
from provisioner.controlplane.discovery.persistence import DiscoveryRepository
from provisioner.controlplane.persistence.store import AuditContext,TenantContext
from tests.provisioning.controlplane import test_discovery_persistence as support
from tests.provisioning.discovery.test_alert_delivery import OwnerFixture


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_MONITOR_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_DISCOVERY_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_ISOLATED')=='1',
                     'Requires isolated PostgreSQL dedicated monitor and discovery roles')
class AlertDeliveryPostgresTests(OwnerFixture,unittest.TestCase):
    setUpClass=classmethod(support.DiscoveryPersistenceTests.setUpClass.__func__)
    _campaign=support.DiscoveryPersistenceTests._campaign
    _object=support.DiscoveryPersistenceTests._object
    _publish=support.DiscoveryPersistenceTests._publish

    def setUp(self):
        support.DiscoveryPersistenceTests.setUp(self)
        self.monitor_dsn=os.environ['HOSTING_TEST_POSTGRES_MONITOR_DSN']
        self.connect=lambda:self.psycopg.connect(self.monitor_dsn)
        self.history=FreshnessHistoryRepository(DiscoveryRepository(self.connect))
        self.delivery=AlertDeliveryRepository(self.history)
        self.audit=AuditContext('enrolled-monitor-service','alert-integration')
        self.revoked=False
        self._publish(self._campaign('first'),'PARTIAL',(self._object('vm-1','First'),),('VISIBLE_INVENTORY_ONLY',))
        self.check=self.history.capture(self.ctx,self.scope,self.environment_id,'check-1',
                                       audit=self.audit,authorize=self.authorize)
        self.intent=alert_projection(self.check)
        self.start_owner(lambda:datetime.now(timezone.utc))

    def authorize(self,scope,at):
        self.assertEqual(scope,self.scope)
        if self.revoked:raise PermissionError('monitor service revoked')

    def dispatch(self,**options):
        return self.delivery.dispatch(self.ctx,self.scope,self.environment_id,'check-1',owner=self.owner,
                                     audit=self.audit,authorize=self.authorize,**options)

    def counts(self):
        with self.history._repository._session(self.ctx) as con:
            return con.execute('SELECT count(*) FROM hosting_controlplane.discovery_alert_deliveries').fetchone()[0]

    def test_real_dedicated_role_has_only_monitoring_appends_and_forced_tenant_rls(self):
        require_monitor_role(self.connect,'hosting_discovery_monitor')
        with self.assertRaises(RuntimeError):
            require_monitor_role(lambda:self.psycopg.connect(self.runtime_dsn),'hosting_runtime')
        self.dispatch()
        with self.history._repository._session(self.ctx) as con:
            with self.assertRaises(self.psycopg.Error),con.transaction():
                con.execute('UPDATE hosting_controlplane.discovery_alert_deliveries SET event=%s',('ACKNOWLEDGED',))
            with self.assertRaises(self.psycopg.Error),con.transaction():
                con.execute('DELETE FROM hosting_controlplane.discovery_alert_deliveries')
            with self.assertRaises(self.psycopg.Error),con.transaction():
                con.execute('SELECT * FROM hosting_controlplane.enterprise_records')
        other=TenantContext(self.ctx.organization_id,'other')
        with self.history._repository._session(other) as con:
            self.assertEqual(con.execute('SELECT count(*) FROM hosting_controlplane.discovery_alert_deliveries').fetchone(),(0,))

    def test_real_committed_start_receipt_audit_and_old_check_acknowledgement(self):
        observed=[]
        self.on_request=lambda:observed.append(self.counts())
        value=self.dispatch()
        self.assertEqual(value['status'],'DELIVERY_ACCEPTED')
        self.assertEqual(observed,[1]);self.assertEqual(self.counts(),2)
        self.ack=True;receipt=self.dispatch(refresh=True)
        self.assertEqual(receipt['status'],'ACKNOWLEDGED');self.assertEqual(self.counts(),3)
        with self.history._repository._session(self.ctx) as con:
            events=con.execute("SELECT record_digest FROM hosting_controlplane.audit_events "
                "WHERE record_kind='DiscoveryAlertDelivery' ORDER BY audit_sequence").fetchall()
        self.assertEqual(events[-1][0],receipt['event']['recordDigest'])
        self.assertEqual(len(events),3);self.assertEqual(len(self.owner_calls),2)
        self.assertFalse(self.dispatch()['notificationAttempted']);self.assertEqual(len(self.owner_calls),2)

    def test_lost_reply_and_reopened_repository_require_explicit_same_original_retry(self):
        self.loss=True;self.assertEqual(self.dispatch()['status'],'DELIVERY_UNKNOWN')
        self.assertEqual(self.counts(),2);self.loss=False
        self.delivery=AlertDeliveryRepository(self.history)
        self.assertEqual(self.dispatch()['status'],'DELIVERY_UNKNOWN');self.assertEqual(len(self.owner_calls),1)
        self.assertEqual(self.dispatch(retry_unknown=True)['status'],'DELIVERY_ACCEPTED')
        self.assertEqual(self.counts(),4);self.assertEqual(len(self.intents),1)

    def test_concurrent_process_capable_session_lock_does_not_allow_overlapping_delivery(self):
        barrier=threading.Barrier(2);self.delay=.2
        def run(_):
            barrier.wait(timeout=5)
            try:return self.dispatch()['status']
            except AlertDeliveryHeld:return 'ALREADY_ACTIVE'
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(run,n) for n in range(2)]
            result=[future.result(timeout=20) for future in futures]
        self.assertEqual(sorted(result),['ALREADY_ACTIVE','DELIVERY_ACCEPTED'])
        self.assertEqual(len(self.owner_calls),1);self.assertEqual(self.counts(),2)

    def test_revocation_during_post_preserves_unknown_start_with_no_receipt_or_retry(self):
        self.on_request=lambda:setattr(self,'revoked',True)
        with self.assertRaises(PermissionError):self.dispatch()
        self.assertEqual(self.counts(),1)
        self.revoked=False;self.on_request=lambda:None
        self.assertEqual(self.dispatch()['status'],'DELIVERY_UNKNOWN');self.assertEqual(len(self.owner_calls),1)

    def test_database_rejects_changed_check_digest_sequence_or_post_ack_restart(self):
        self.dispatch();self.ack=True;self.dispatch(refresh=True)
        with self.assertRaises(self.psycopg.Error):
            self.delivery._append(self.ctx,self.scope,self.environment_id,self.intent,self.owner.target.owner_id,
                'DELIVERY_STARTED',2,None,audit=self.audit,authorize=self.authorize)
        self.assertEqual(self.counts(),3)
        altered={**self.intent,'checkRecordDigest':'f'*64}
        with self.assertRaises(self.psycopg.Error):
            self.delivery._append(self.ctx,self.scope,self.environment_id,altered,self.owner.target.owner_id,
                'DELIVERY_STARTED',2,None,audit=self.audit,authorize=self.authorize)
        self.assertEqual(self.counts(),3)


if __name__=='__main__':unittest.main()
