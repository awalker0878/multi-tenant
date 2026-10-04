"""Actual HTTPS owner, real JWT verification, independent rota and fsynced inbox.

The IAM directory is a revocable protocol fixture; its real PostgreSQL ingestion
and enrollment are separate campaigns. No on-call commissioning is fabricated.
"""
import base64
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from datetime import datetime,timezone,timedelta
import hashlib
import http.client
import json
from pathlib import Path
import ssl
from threading import Thread
import unittest

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from provisioner.controlplane.authority.model import RoleGrant
from provisioner.controlplane.authority.oidc import DirectoryIdentity,OIDCIdentityProvider
from provisioner.controlplane.authority.service import DISCOVERY_MONITOR
from provisioner.controlplane.discovery.alert_ownership import SignedFileAlertOwnership
from provisioner.controlplane.discovery.alert_receiver import AlertReceiver,AlertReceiverServer,PrivateAlertInbox
from provisioner.controlplane.discovery.alert_transport import AlertOwnerTarget,HttpsAlertOwner,verify_receipt,intent_digest,AlertDeliveryHeld
from provisioner.controlplane.discovery.freshness_history import FreshnessHistoryRepository
from provisioner.controlplane.discovery.freshness_monitor import alert_projection
from provisioner.controlplane.discovery.model import _json
from provisioner.controlplane.persistence.store import TenantContext,AuditContext
from tests.provisioning.api.test_http import SOURCE_SCOPE
from tests.provisioning.discovery import test_alert_delivery as custody
from tests.provisioning.authority.test_oidc import ISSUER,AUDIENCE,JWKS_URI
from tests.provisioning.worker.tls_fixtures import TestPki


def encoded(raw):return base64.b64encode(raw).decode('ascii')


class Directory:
    def __init__(self,rows):self.rows=rows;self.calls=[]
    def resolve(self,issuer,subject,session):
        self.calls.append((issuer,subject,session));return self.rows.get(subject)


class AlertReceiverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.jwt_key=rsa.generate_private_key(public_exponent=65537,key_size=2048)

    def setUp(self):
        self.pki=TestPki();self.addCleanup(self.pki.close);self.pki.issue('receiver')
        self.now=datetime.now(timezone.utc);self.key=Ed25519PrivateKey.generate();self.assignment_key=Ed25519PrivateKey.generate()
        self.db=custody.Database();self.db.now=self.now
        self.history=FreshnessHistoryRepository(custody.Discovery(self.db))
        check=self.history.capture(TenantContext(SOURCE_SCOPE.organization_id,SOURCE_SCOPE.tenant_id),SOURCE_SCOPE,
            'env-01','check-1',audit=AuditContext('monitor-service','check-1'),authorize=lambda scope,at:None)
        self.intent=alert_projection(check)
        grant=RoleGrant(DISCOVERY_MONITOR,SOURCE_SCOPE,self.now+timedelta(minutes=20))
        self.directory=Directory({
            'monitor-service':DirectoryIdentity('monitor-service','monitor-session',SOURCE_SCOPE.organization_id,SOURCE_SCOPE.tenant_id,'SERVICE',True,(grant,)),
            'oncall-human':DirectoryIdentity('oncall-human','human-session',SOURCE_SCOPE.organization_id,SOURCE_SCOPE.tenant_id,'HUMAN',True,()),
            'other-human':DirectoryIdentity('other-human','other-session',SOURCE_SCOPE.organization_id,SOURCE_SCOPE.tenant_id,'HUMAN',True,())})
        jwk=json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(self.jwt_key.public_key()));jwk.update(kid='receiver-jwt',alg='RS256',use='sig',key_ops=['verify'])
        self.identities=OIDCIdentityProvider(issuer=ISSUER,audience=AUDIENCE,jwks_uri=JWKS_URI,directory=self.directory,
            step_up_acr=frozenset({'unused'}),fetch_jwks=lambda url:{'keys':[jwk]})
        self.policy={'format':'hosting-discovery-alert-ownership/1','revision':1,'ownerId':'oncall-owner',
            'issuedAt':(self.now-timedelta(minutes=1)).isoformat(),'expiresAt':(self.now+timedelta(minutes=20)).isoformat(),
            'assignments':[{'assignmentId':'scope-oncall-1','environmentId':'env-01','scope':dict(vars(SOURCE_SCOPE)),
                            'monitorSubject':'monitor-service','onCallSubject':'oncall-human'}]}
        self.policy_path=self.pki.root/'ownership.json';self.write_policy()
        self.ownership=SignedFileAlertOwnership(self.policy_path,public_key=self.assignment_key.public_key().public_bytes_raw(),
            minimum_revision=1,owner_id='oncall-owner')
        self.inbox_path=self.pki.root/'inbox';self.inbox_path.mkdir(mode=0o700)
        self.inbox=PrivateAlertInbox(self.inbox_path);self.denied=False
        def recheck():
            if self.denied:raise PermissionError('service deployment lost current enrollment')
        self.recheck=recheck
        self.receiver=self.receiver_instance()
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(self.pki.root/'receiver.pem',self.pki.root/'receiver.key')
        self.server=AlertReceiverServer(('127.0.0.1',0),self.receiver,tls_context=context,max_connections=4)
        self.thread=Thread(target=self.server.serve_forever,kwargs={'poll_interval':.01},daemon=True);self.thread.start()
        def close():self.server.shutdown();self.server.server_close();self.thread.join(3)
        self.addCleanup(close)
        self.token_path=self.pki.root/'monitor-token';self.token_path.write_text(self.token('monitor-service'));self.token_path.chmod(0o600)
        self.target=AlertOwnerTarget.parse({'ownerId':'oncall-owner','origin':f'https://localhost:{self.server.server_port}',
            'connectIp':'127.0.0.1','caBundle':str(self.pki.root/'ca.pem'),'caDigest':hashlib.sha256((self.pki.root/'ca.pem').read_bytes()).hexdigest(),
            'credentialFile':str(self.token_path),'receiptPublicKey':encoded(self.key.public_key().public_bytes_raw()),'timeoutSeconds':2,
            'ownershipPublicKey':encoded(self.assignment_key.public_key().public_bytes_raw()),'minimumOwnershipRevision':1})
        self.client=HttpsAlertOwner(self.target)

    def receiver_instance(self):
        return AlertReceiver(owner_id='oncall-owner',inbox=PrivateAlertInbox(self.inbox_path),ownership=self.ownership,
            identities=self.identities,signing_key=self.key,recheck=self.recheck,clock=lambda:self.now)

    def token(self,subject,**changes):
        row=self.directory.rows[subject];at=int(datetime.now(timezone.utc).timestamp())
        claims={'iss':ISSUER,'aud':AUDIENCE,'sub':subject,'sid':row.session_id,'iat':at,'nbf':at,'exp':at+600,
                'roles':['EXECUTION_OPERATOR'],'identityKind':'HUMAN'}
        claims.update(changes)
        return jwt.encode(claims,self.jwt_key,algorithm='RS256',headers={'kid':'receiver-jwt','typ':'at+jwt'})

    def write_policy(self):
        self.policy_path.write_text(_json({'policy':self.policy,'signature':encoded(self.assignment_key.sign(_json(self.policy).encode('ascii')))}))
        self.policy_path.chmod(0o600)

    def deliver(self):return self.client.deliver(self.intent,lambda at:None,lambda:self.now)
    def refresh(self):return self.client.refresh(self.intent,lambda at:None,lambda:self.now)
    def acknowledge(self,subject='oncall-human',**changes):
        body={'alertId':self.intent['alertId'],'alertDigest':intent_digest(self.intent),'checkRecordDigest':self.intent['checkRecordDigest'],**changes}
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT);context.load_verify_locations(self.pki.root/'ca.pem')
        connection=http.client.HTTPSConnection('localhost',self.server.server_port,context=context,timeout=2)
        try:
            connection.request('POST','/v1/discovery/alerts/'+self.intent['alertId']+'/acknowledge',body=_json(body),
                headers={'Authorization':'Bearer '+self.token(subject),'Content-Type':'application/json','Connection':'close'})
            response=connection.getresponse();return response.status,json.loads(response.read())
        finally:connection.close()

    def test_actual_https_acceptance_restart_and_independent_scoped_oncall_acknowledgement(self):
        value=self.deliver();self.assertEqual(value['receipt']['status'],'DELIVERY_ACCEPTED')
        self.assertEqual(value['receipt']['onCallSubject'],'oncall-human');self.assertEqual(len(self.directory.calls),4)
        original=self.inbox.get(self.intent['alertId']);self.server.receiver=self.receiver_instance()
        self.assertEqual(self.deliver()['receipt']['acceptedAt'],original['acceptedAt'])
        status,ack=self.acknowledge();self.assertEqual(status,200);self.assertFalse(ack['executionAuthorized'])
        value=self.refresh();self.assertEqual(value['receipt']['status'],'ACKNOWLEDGED')
        self.assertEqual(value['receipt']['acknowledgedBy'],'oncall-human')
        verify_receipt(value,self.intent,self.target,self.now)
        self.assertEqual(len(list(self.inbox_path.glob('*.accepted.json'))),1)
        self.assertEqual(len(list(self.inbox_path.glob('*.ack-*.json'))),1)

    def test_wrong_human_service_claims_revoked_session_and_original_digest_cannot_acknowledge(self):
        self.deliver()
        for subject in ('other-human','monitor-service'):
            with self.subTest(subject=subject):self.assertEqual(self.acknowledge(subject)[0],403)
        self.assertEqual(self.acknowledge(alertDigest='a'*64)[0],409)
        self.directory.rows['oncall-human']=replace(self.directory.rows['oncall-human'],active=False)
        self.assertEqual(self.acknowledge()[0],403);self.assertFalse(list(self.inbox_path.glob('*.ack-*.json')))

    def test_receiver_cannot_invent_ownership_or_ack_actor_with_its_receipt_key(self):
        value=self.deliver();forged=deepcopy(value)
        forged['receipt']['onCallSubject']='other-human'
        forged['signature']=encoded(self.key.sign(_json(forged['receipt']).encode('ascii')))
        with self.assertRaises(AlertDeliveryHeld):verify_receipt(forged,self.intent,self.target,self.now)
        forged=deepcopy(value);forged['ownership']['policy']['assignments'][0]['onCallSubject']='other-human'
        with self.assertRaises(Exception):verify_receipt(forged,self.intent,self.target,self.now)

    def test_current_rota_revision_scope_and_receiver_enrollment_are_rechecked(self):
        self.deliver();self.policy['assignments'][0]['onCallSubject']='other-human';self.write_policy()
        with self.assertRaises(Exception):self.refresh()
        self.policy['revision']=2;self.write_policy()
        self.assertEqual(self.acknowledge()[0],403);self.assertEqual(self.acknowledge('other-human')[0],200)
        self.assertEqual(self.refresh()['receipt']['acknowledgedBy'],'other-human')
        # Reconstruct the owner with its original configured revision floor.
        # Actual retained original policies must still refuse a signed rollback.
        current=deepcopy(self.policy)
        self.ownership=SignedFileAlertOwnership(self.policy_path,
            public_key=self.assignment_key.public_key().public_bytes_raw(),minimum_revision=1,owner_id='oncall-owner')
        self.server.receiver=self.receiver_instance()
        self.policy['revision']=1;self.policy['assignments'][0]['onCallSubject']='oncall-human';self.write_policy()
        with self.assertRaises(Exception):self.refresh()
        self.policy=current;self.write_policy()
        self.ownership=SignedFileAlertOwnership(self.policy_path,
            public_key=self.assignment_key.public_key().public_bytes_raw(),minimum_revision=1,owner_id='oncall-owner')
        self.server.receiver=self.receiver_instance()
        self.assertEqual(self.refresh()['receipt']['acknowledgedBy'],'other-human')
        self.policy['assignments'][0]['scope']['tenant_id']='foreign';self.policy['revision']=3;self.write_policy()
        with self.assertRaises(Exception):self.refresh()
        self.denied=True
        with self.assertRaises(Exception):self.deliver()

    def test_expired_ownership_or_noncurrent_monitor_never_accepts_and_legacy_receipt_is_insufficient(self):
        self.directory.rows['monitor-service']=replace(self.directory.rows['monitor-service'],active=False)
        with self.assertRaises(Exception):self.deliver()
        self.assertIsNone(self.inbox.get(self.intent['alertId']))
        legacy=custody.signed_receipt(self.intent,self.key,self.now)
        with self.assertRaises(Exception):verify_receipt(legacy,self.intent,self.target,self.now)

    def test_duplicate_concurrent_delivery_is_one_original_and_inbox_tampering_holds(self):
        with ThreadPoolExecutor(max_workers=3) as pool:values=list(pool.map(lambda _:self.deliver(),range(3)))
        self.assertEqual(len({value['receipt']['acceptedAt'] for value in values}),1)
        path=next(self.inbox_path.glob('*.accepted.json'));raw=path.read_text();path.write_text(raw.replace('monitor-service','other-monitor'))
        with self.assertRaises(Exception):self.refresh()
        path.write_text(raw);self.inbox_path.rename(self.pki.root/'old-inbox');self.inbox_path.mkdir(mode=0o700)
        with self.assertRaises(Exception):self.refresh()


if __name__=='__main__':unittest.main()
