"""Real HTTPS signed owner receipts with transaction-protocol storage fixtures."""
import base64
from copy import deepcopy
from dataclasses import replace
from datetime import datetime,timezone,timedelta
import hashlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import socket
import ssl
import threading
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from provisioner.controlplane.discovery import alert_delivery as module
from provisioner.controlplane.discovery.alert_transport import (
    AlertDeliveryHeld,AlertDeliveryUnknown,AlertOwnerTarget,HttpsAlertOwner,intent_digest,verify_receipt)
from provisioner.controlplane.discovery.freshness_history import FreshnessHistoryRepository
from provisioner.controlplane.discovery.freshness_monitor import alert_projection
from provisioner.controlplane.discovery.model import _json
from provisioner.controlplane.persistence.store import AuditContext,TenantContext
from tests.provisioning.api.test_http import NOW,SOURCE_SCOPE
from tests.provisioning.discovery import test_freshness_history as storage
from tests.provisioning.worker.tls_fixtures import TestPki


def signed_receipt(intent,key,at,*,status='DELIVERY_ACCEPTED'):
    receipt={'format':'hosting-discovery-alert-owner-receipt/1','ownerId':'oncall-owner',
        'receiptId':'receipt-1','alertId':intent['alertId'],'alertDigest':intent_digest(intent),
        'checkRecordDigest':intent['checkRecordDigest'],'status':status,
        'acceptedAt':intent['detectedAt'],'observedAt':at.isoformat(),
        'expiresAt':(at+timedelta(minutes=2)).isoformat(),
        'acknowledgedBy':'oncall-operator' if status=='ACKNOWLEDGED' else None,
        'acknowledgedAt':at.isoformat() if status=='ACKNOWLEDGED' else None}
    return {'receipt':receipt,'signature':base64.b64encode(key.sign(_json(receipt).encode('ascii'))).decode('ascii')}


class Database(storage.Database):
    def __init__(self):
        super().__init__();self.alert_rows=[];self.dispatch_lock=None;self.before_alert_insert=lambda:None


class Connection(storage.Connection):
    def __enter__(self):
        super().__enter__();self.alert_rows=deepcopy(self.db.alert_rows)
        self.rows_dirty=self.alerts_dirty=self.events_dirty=False
        return self
    def __exit__(self,kind,value,tb):
        if kind is None:
            if self.rows_dirty:self.db.rows=self.rows
            if self.alerts_dirty:self.db.alert_rows=self.alert_rows
            if self.events_dirty:self.db.events=self.events
        if self.db.dispatch_lock is self:self.db.dispatch_lock=None
    def execute(self,sql,parameters=()):
        if sql==module._LOCK_SQL:
            if self.db.dispatch_lock is not None:return storage.Rows([(False,)])
            self.db.dispatch_lock=self;return storage.Rows([(True,)])
        if sql==module._UNLOCK_SQL:
            self.db.dispatch_lock=None;return storage.Rows([(True,)])
        if sql.startswith('SELECT pg_advisory_xact_lock('):return storage.Rows()
        if sql.startswith('SELECT ') and module._TABLE in sql:
            return storage.Rows([r[8:] for r in self.alert_rows if r[:8]==parameters[:8] and r[8]==parameters[8]])
        if sql.startswith('INSERT INTO '+module._TABLE):
            self.db.before_alert_insert();self.alert_rows.append(parameters);self.alerts_dirty=True
            return storage.Rows()
        if sql.startswith('INSERT INTO '+storage.module._TABLE):self.rows_dirty=True
        if sql.startswith('INSERT INTO hosting_controlplane.audit_events'):self.events_dirty=True
        return super().execute(sql,parameters)


class Discovery(storage.Discovery):
    def __init__(self,db):
        super().__init__(db);self._connect=lambda:Connection(db)


class OwnerFixture:
    def start_owner(self,clock):
        self.pki=TestPki();self.addCleanup(self.pki.close);self.pki.issue('alert-owner')
        self.key=Ed25519PrivateKey.generate();self.owner_calls=[];self.intents={}
        self.ack=False;self.loss=False;self.on_request=lambda:None;self.alter=lambda value:value
        self.owner_status=200;self.delay=0
        self.token='synthetic-alert-owner-service-token';path=self.pki.root/'owner-token'
        path.write_text(self.token);path.chmod(0o600)
        case=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):self.receive()
            def do_GET(self):self.receive()
            def receive(self):
                try:
                    case.owner_calls.append((self.command,self.path,dict(self.headers)))
                    case.assertEqual(self.headers['Authorization'],'Bearer '+case.token)
                    if self.command=='POST':
                        intent=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                        original=case.intents.setdefault(intent['alertId'],intent)
                        case.assertEqual(intent,original)
                        case.assertEqual(self.path,'/v1/discovery/alerts')
                    else:intent=case.intents[self.path.split('/')[-2]]
                    case.on_request()
                    if case.loss:
                        self.connection.shutdown(socket.SHUT_RDWR);self.connection.close();return
                    body=_json(case.alter(signed_receipt(intent,case.key,clock(),
                        status='ACKNOWLEDGED' if case.ack else 'DELIVERY_ACCEPTED'))).encode('ascii')
                    if case.delay:threading.Event().wait(case.delay)
                    self.send_response(case.owner_status);self.send_header('Content-Type','application/json')
                    self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
                except (OSError,ssl.SSLError):pass
        self.owner_server=ThreadingHTTPServer(('127.0.0.1',0),Handler);self.owner_server.daemon_threads=True
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(self.pki.root/'alert-owner.pem',self.pki.root/'alert-owner.key')
        self.owner_server.socket=context.wrap_socket(self.owner_server.socket,server_side=True)
        thread=threading.Thread(target=self.owner_server.serve_forever,kwargs={'poll_interval':.01},daemon=True);thread.start()
        def stop():self.owner_server.shutdown();self.owner_server.server_close();thread.join(3)
        self.addCleanup(stop)
        self.owner_doc={'ownerId':'oncall-owner','origin':f'https://localhost:{self.owner_server.server_port}',
            'connectIp':'127.0.0.1','caBundle':str(self.pki.root/'ca.pem'),
            'caDigest':hashlib.sha256((self.pki.root/'ca.pem').read_bytes()).hexdigest(),
            'credentialFile':str(path),'receiptPublicKey':base64.b64encode(self.key.public_key().public_bytes_raw()).decode(),
            'timeoutSeconds':2}
        self.owner=HttpsAlertOwner(AlertOwnerTarget.parse(self.owner_doc))


class AlertDeliveryTests(OwnerFixture,unittest.TestCase):
    def setUp(self):
        self.db=Database();self.discovery=Discovery(self.db)
        self.history=FreshnessHistoryRepository(self.discovery);self.delivery=module.AlertDeliveryRepository(self.history)
        self.ctx=TenantContext(SOURCE_SCOPE.organization_id,SOURCE_SCOPE.tenant_id)
        self.denied=False;self.authorizations=[]
        self.audit=AuditContext('freshness-service','check-1')
        self.check=self.history.capture(self.ctx,SOURCE_SCOPE,'env-01','check-1',audit=self.audit,authorize=self.authorize)
        self.intent=alert_projection(self.check);self.start_owner(lambda:self.db.now)

    def authorize(self,scope,at):
        self.assertEqual(scope,SOURCE_SCOPE);self.authorizations.append(at)
        if self.denied:raise PermissionError('revoked service role')

    def dispatch(self,**kwargs):
        return self.delivery.dispatch(self.ctx,SOURCE_SCOPE,'env-01','check-1',owner=self.owner,
                                      audit=self.audit,authorize=self.authorize,**kwargs)

    def test_signed_owner_acceptance_is_retained_before_idempotent_restart(self):
        value=self.dispatch()
        self.assertEqual(value['status'],'DELIVERY_ACCEPTED')
        self.assertEqual([r[13] for r in self.db.alert_rows],['DELIVERY_STARTED','DELIVERY_ACCEPTED'])
        self.assertFalse(value['historicalOnly']);self.assertTrue(value['notificationAttempted'])
        self.assertEqual(len(self.owner_calls),1)
        other=module.AlertDeliveryRepository(self.history)
        retry=other.dispatch(self.ctx,SOURCE_SCOPE,'env-01','check-1',owner=self.owner,
                            audit=self.audit,authorize=self.authorize)
        self.assertTrue(retry['historicalOnly']);self.assertFalse(retry['notificationAttempted'])
        self.assertEqual(len(self.owner_calls),1)

    def test_refresh_verifies_external_attributed_acknowledgement_of_exact_old_check(self):
        self.dispatch();self.db.now+=timedelta(minutes=10);self.ack=True
        value=self.dispatch(refresh=True)
        self.assertEqual(value['status'],'ACKNOWLEDGED')
        self.assertFalse(value['notificationAttempted']);self.assertFalse(value['historicalOnly'])
        self.assertEqual(value['currentOwnerReceipt']['receipt']['acknowledgedBy'],'oncall-operator')
        self.assertEqual(self.owner_calls[-1][0],'GET')
        self.assertEqual(len(self.db.rows),1)
        self.assertEqual(len(self.db.alert_rows),3)

    def test_lost_reply_is_unknown_and_only_explicit_replay_delivers_same_intent(self):
        self.loss=True;value=self.dispatch()
        self.assertEqual(value['status'],'DELIVERY_UNKNOWN');self.assertEqual(len(self.owner_calls),1)
        self.loss=False
        self.assertEqual(self.dispatch()['status'],'DELIVERY_UNKNOWN');self.assertEqual(len(self.owner_calls),1)
        value=self.dispatch(retry_unknown=True)
        self.assertEqual(value['status'],'DELIVERY_ACCEPTED');self.assertEqual(len(self.owner_calls),2)
        self.assertEqual(len(self.intents),1);self.assertEqual(len(self.db.rows),1)

    def test_revocation_after_post_keeps_start_and_does_not_relabel_delivery_as_accepted(self):
        self.on_request=lambda:setattr(self,'denied',True)
        with self.assertRaises(PermissionError):self.dispatch()
        self.assertEqual(len(self.db.alert_rows),1)
        self.assertEqual(self.db.alert_rows[0][13],'DELIVERY_STARTED')
        self.denied=False;self.on_request=lambda:None
        self.assertEqual(self.dispatch()['status'],'DELIVERY_UNKNOWN')
        self.assertEqual(len(self.owner_calls),1)

    def test_dispatch_lock_prevents_competing_delivery_and_start_precedes_effect(self):
        observed=[]
        def during_request():
            observed.append(self.db.alert_rows[0][13])
            with self.assertRaises(AlertDeliveryHeld):self.dispatch(retry_unknown=True)
        self.on_request=during_request
        self.assertEqual(self.dispatch()['status'],'DELIVERY_ACCEPTED')
        self.assertEqual(observed,['DELIVERY_STARTED']);self.assertEqual(len(self.owner_calls),1)

    def test_corrupt_signed_receipt_or_wrong_scope_retains_uncertainty(self):
        self.alter=lambda value:{**value,'signature':base64.b64encode(b'x'*64).decode()}
        self.assertEqual(self.dispatch()['status'],'DELIVERY_UNKNOWN')
        self.assertEqual(len(self.db.rows),1)
        other=replace(SOURCE_SCOPE,tenant_id='foreign')
        with self.assertRaises((AssertionError,ValueError)):
            self.delivery.dispatch(self.ctx,other,'env-01','check-1',owner=self.owner,audit=self.audit,authorize=self.authorize)

    def test_retry_budget_and_restored_event_integrity_hold_without_more_sends(self):
        self.loss=True
        self.dispatch();self.dispatch(retry_unknown=True);self.dispatch(retry_unknown=True)
        with self.assertRaises(AlertDeliveryHeld):self.dispatch(retry_unknown=True)
        self.assertEqual(len(self.owner_calls),3)
        row=list(self.db.alert_rows[0]);row[-1]='f'*64;self.db.alert_rows[0]=tuple(row)
        with self.assertRaises(AlertDeliveryHeld):self.dispatch(retry_unknown=True)
        self.assertEqual(len(self.owner_calls),3)

    def test_endpoint_trust_or_current_receipt_mutation_never_marks_an_acknowledgement(self):
        self.dispatch();self.ack=True
        self.alter=lambda value:{**value,'receipt':{**value['receipt'],'acknowledgedBy':None}}
        with self.assertRaises(AlertDeliveryHeld):self.dispatch(refresh=True)
        self.assertEqual(len(self.db.alert_rows),2)


if __name__=='__main__':unittest.main()
