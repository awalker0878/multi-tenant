"""Installed monitor composition with real JWT/signatures/TLS and SQL-protocol fixtures."""
import base64
from copy import deepcopy
from datetime import datetime,timezone,timedelta
import io
import hashlib
import json
from dataclasses import replace
from contextlib import redirect_stdout
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from provisioner.controlplane.authority import directory as iam
from provisioner.controlplane.authority.model import RoleGrant
from provisioner.controlplane.authority.oidc import DirectoryIdentity,OIDCIdentityProvider
from provisioner.controlplane.authority.service import AuthenticationFailed,DISCOVERY_MONITOR
from provisioner.controlplane.discovery import monitor_runtime as module
from provisioner.controlplane.discovery import service_enrollment as service
from provisioner.controlplane.discovery.alert_delivery import AlertDeliveryRepository
from provisioner.controlplane.discovery.freshness_history import FreshnessHistoryRepository
from provisioner.controlplane.discovery.model import _json
from provisioner.controlplane.persistence.store import TenantContext
from tests.provisioning.api.test_http import SOURCE_SCOPE
from tests.provisioning.discovery.test_alert_delivery import Database,Discovery,OwnerFixture
from tests.provisioning.authority.test_oidc import Directory,ISSUER,AUDIENCE,JWKS_URI
from tests.provisioning.discovery.test_collector_runtime import write_json


def scope_document(scope):
    return {'organizationId':scope.organization_id,'tenantId':scope.tenant_id,'locationId':scope.site_id,
        'securityDomainId':scope.security_domain_id,'endpointId':scope.endpoint_id,
        'nativeScopeId':scope.native_scope_id,'platformFamily':scope.platform_family}


class MonitorRuntimeTests(OwnerFixture,unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.jwt_key=rsa.generate_private_key(public_exponent=65537,key_size=2048)

    def setUp(self):
        self.db=Database();self.db.now=datetime.now(timezone.utc)
        self.discovery=Discovery(self.db);self.history=FreshnessHistoryRepository(self.discovery)
        self.start_owner(lambda:self.db.now)
        self.subject='freshness-service'
        self.grant=RoleGrant(DISCOVERY_MONITOR,SOURCE_SCOPE,self.db.now+timedelta(minutes=20))
        self.directory=Directory(DirectoryIdentity(self.subject,'monitor-session',SOURCE_SCOPE.organization_id,
            SOURCE_SCOPE.tenant_id,'SERVICE',True,(self.grant,)))
        jwk=json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(self.jwt_key.public_key()))
        jwk.update(kid='monitor-key',alg='RS256',use='sig',key_ops=['verify'])
        self.identities=OIDCIdentityProvider(issuer=ISSUER,audience=AUDIENCE,jwks_uri=JWKS_URI,
            directory=self.directory,step_up_acr=frozenset({'unused'}),fetch_jwks=lambda url:{'keys':[jwk]})
        self.token_path=self.pki.root/'monitor-token';self.write_token()
        self.config_doc={'format':'hosting-discovery-monitor/1','subject':self.subject,
            'organizationId':SOURCE_SCOPE.organization_id,'tenantId':SOURCE_SCOPE.tenant_id,
            'tokenFile':str(self.token_path),'targets':[{'environmentId':'env-01','scope':scope_document(SOURCE_SCOPE)}],
            'policy':{'intervalSeconds':300,'maxTargets':4,'maxCycles':4},
            'freshnessPolicy':{'refreshAfterSeconds':3600,'maxAgeSeconds':86400},'alertOwner':self.owner_doc}
        self.path=self.pki.root/'monitor.json';write_json(self.path,self.config_doc)
        self.settings=module.MonitorSettings.from_file(self.path)
        self.row=SimpleNamespace(scope=SOURCE_SCOPE)
        self.environments=SimpleNamespace(get=lambda ctx,environment:self.row)
        self.evidence_denied=False;self.evidence_checks=[]
        def evidence(ctx):
            self.evidence_checks.append(ctx)
            if self.evidence_denied:raise PermissionError('independent custody unavailable')
        self.evidence=SimpleNamespace(require=evidence)
        self.runtime=module.MonitorRuntime(self.settings,identities=self.identities,environments=self.environments,
            history=self.history,delivery=AlertDeliveryRepository(self.history),evidence_gate=self.evidence,
            clock=lambda:self.db.now)

    def write_token(self,**updates):
        now=int(datetime.now(timezone.utc).timestamp())
        doc={'iss':ISSUER,'aud':AUDIENCE,'sub':self.subject,'sid':'monitor-session',
             'iat':now,'nbf':now,'exp':now+600,'roles':['EXECUTION_OPERATOR'],'identityKind':'HUMAN'}
        doc.update(updates)
        self.token_path.write_text(jwt.encode(doc,self.jwt_key,algorithm='RS256',headers={'kid':'monitor-key','typ':'at+jwt'}))
        self.token_path.chmod(0o600)

    def test_one_cycle_uses_current_oidc_directory_checks_existing_history_and_real_owner(self):
        result=self.runtime.cycle()
        self.assertEqual(result['status'],'MONITOR_EVALUATED')
        self.assertEqual(result['items'][0]['delivery']['status'],'DELIVERY_ACCEPTED')
        self.assertGreater(len(self.directory.lookups),5)
        self.assertGreater(len(self.evidence_checks),5)
        self.assertEqual(len(self.owner_calls),1);self.assertEqual(len(self.db.rows),1)
        again=self.runtime.cycle()
        self.assertEqual(again['items'][0]['checkId'],result['items'][0]['checkId'])
        self.assertFalse(again['items'][0]['notificationAttempted'])
        self.assertEqual(len(self.owner_calls),1)
        self.assertFalse(result['collectionRequested']);self.assertFalse(result['executionAuthorized'])

    def test_live_service_revocation_holds_history_without_sending(self):
        self.directory.enrollment=replace(self.directory.enrollment,active=False)
        result=self.runtime.cycle()
        self.assertEqual(result['status'],'MONITOR_HELD')
        self.assertEqual(result['items'][0]['status'],'CHECK_HELD')
        self.assertEqual(self.db.rows,[]);self.assertEqual(self.owner_calls,[])

    def test_human_worker_and_misassigned_service_roles_never_gain_monitor_authority(self):
        original=self.directory.enrollment
        for kind,role in [('HUMAN','DISCOVERY_MONITOR'),('WORKER','WORKER'),('SERVICE','EXECUTION_OPERATOR')]:
            self.directory.enrollment=replace(original,kind=kind,grants=(replace(self.grant,role=role),))
            with self.subTest(kind=kind,role=role):
                self.assertEqual(self.runtime.cycle()['items'][0]['status'],'CHECK_HELD')
        self.assertEqual(self.owner_calls,[]);self.assertEqual(self.db.rows,[])

    def test_token_and_configuration_rotation_are_rechecked_before_effect(self):
        self.write_token(sid='wrong-session')
        self.assertEqual(self.runtime.cycle()['status'],'MONITOR_HELD')
        self.write_token();self.config_doc['policy']['intervalSeconds']=600;write_json(self.path,self.config_doc)
        self.assertEqual(self.runtime.cycle()['status'],'MONITOR_HELD')
        self.assertEqual(self.owner_calls,[])

    def test_installed_composition_requires_actual_service_manifest_and_independent_oncall_owner(self):
        with self.assertRaisesRegex(ValueError,'service/interpreter/store enrollment'):
            module.create_runtime(self.settings,{})
        # Local protocol fixture for the installed distribution/interpreter only;
        # store identity and manifest custody below use the actual filesystem.
        with patch.object(service,'package_facts',return_value={'unitProtocolFixture':True}),patch.object(
                service,'interpreter_facts',return_value={'unitProtocolFixture':True}):
            manifest=self.pki.root/'monitor-service.json'
            raw=_json(service.capture_service_facts(self.subject,{'monitor-config':self.path.parent})).encode('ascii')
            manifest.write_bytes(raw);manifest.chmod(0o600)
            self.config_doc['serviceEnrollment']={'file':str(manifest),'digest':hashlib.sha256(raw).hexdigest()}
            write_json(self.path,self.config_doc);settings=module.MonitorSettings.from_file(self.path)
            with self.assertRaisesRegex(ValueError,'scoped alert/on-call ownership'):
                module.create_runtime(settings,{})
            settings.recheck();manifest.write_bytes(raw+b'\n')
            with self.assertRaises(PermissionError):settings.recheck()

    def test_exact_retained_check_ack_refresh_does_not_create_current_slot_or_resample(self):
        value=self.runtime.cycle();check=value['items'][0]['checkId']
        self.db.now+=timedelta(minutes=5);self.ack=True
        result=self.runtime.reconcile('env-01',check,refresh=True)
        self.assertEqual(result['status'],'ACKNOWLEDGED');self.assertEqual(len(self.db.rows),1)
        self.assertEqual(self.owner_calls[-1][0],'GET')
        with self.assertRaises(PermissionError):self.runtime.reconcile('unenrolled',check,refresh=True)

    def test_environment_scope_or_independent_custody_change_holds_before_monitoring(self):
        self.row=SimpleNamespace(scope=replace(SOURCE_SCOPE,endpoint_id='different'))
        self.assertEqual(self.runtime.cycle()['status'],'MONITOR_HELD')
        self.row=SimpleNamespace(scope=SOURCE_SCOPE);self.evidence_denied=True
        self.assertEqual(self.runtime.cycle()['status'],'MONITOR_HELD')
        self.assertEqual(self.db.rows,[]);self.assertEqual(self.owner_calls,[])

    def test_settings_are_exact_private_tenant_bounded_and_do_not_emit_credentials(self):
        original=deepcopy(self.config_doc)
        changes=[lambda d:d.update(subject='bad id'),lambda d:d.update(extra='secret'),
            lambda d:d['targets'].append(d['targets'][0]),
            lambda d:d['targets'][0]['scope'].update(tenantId='foreign'),
            lambda d:d['policy'].update(maxCycles=True),
            lambda d:d['alertOwner'].update(origin='http://localhost'),lambda d:d.update(tokenFile='relative')]
        for change in changes:
            doc=deepcopy(original);change(doc);write_json(self.path,doc)
            with self.subTest(doc=doc),self.assertRaises((ValueError,TypeError)):module.MonitorSettings.from_file(self.path)
        write_json(self.path,original);self.path.chmod(0o644)
        with self.assertRaises(Exception):module.MonitorSettings.from_file(self.path)
        self.assertNotIn(self.token,repr(self.settings))

    def test_installed_entrypoint_emits_sanitized_holds_and_original_only_reconciliation(self):
        output=io.StringIO()
        with redirect_stdout(output),patch.object(module,'create_runtime',return_value=self.runtime):
            code=module.main(['cycle','--config',str(self.path)])
        self.assertEqual(code,0);check=json.loads(output.getvalue())['items'][0]['checkId']
        self.ack=True;output=io.StringIO()
        with redirect_stdout(output),patch.object(module,'create_runtime',return_value=self.runtime):
            code=module.main(['refresh-acknowledgements','--config',str(self.path),'--environment-id','env-01','--check-id',check])
        self.assertEqual(code,0);self.assertEqual(json.loads(output.getvalue())['status'],'ACKNOWLEDGED')
        output=io.StringIO()
        with redirect_stdout(output),patch.object(module,'create_runtime',side_effect=RuntimeError('secret-dsn-token')):
            code=module.main(['cycle','--config',str(self.path)])
        self.assertEqual(code,2);self.assertNotIn('secret-dsn-token',output.getvalue())


class ServiceIAMContractTests(unittest.TestCase):
    def snapshot(self,kind,role):
        now=datetime.now(timezone.utc)
        return {'format':'hosting-directory-snapshot/1','issuer':ISSUER,'audience':AUDIENCE,'subject':'service',
            'organizationId':SOURCE_SCOPE.organization_id,'tenantId':SOURCE_SCOPE.tenant_id,'identityKind':kind,
            'active':True,'generation':1,'issuedAt':int(now.timestamp()),
            'grants':[{'role':role,'scope':scope_document(SOURCE_SCOPE),'expiresAt':int(now.timestamp())+600}],
            'sessions':[{'sessionId':'session-1','expiresAt':int(now.timestamp())+600}]},now

    def test_monitor_service_and_existing_human_worker_roles_are_strictly_separated(self):
        for kind,role in [('SERVICE','DISCOVERY_MONITOR'),('WORKER','WORKER'),('HUMAN','EXECUTION_OPERATOR')]:
            doc,now=self.snapshot(kind,role)
            values,_=iam._snapshot(doc,issuer=ISSUER,audience=AUDIENCE,now=now)
            self.assertEqual(values[0].role,role)
        for kind,role in [('SERVICE','WORKER'),('SERVICE','EXECUTION_OPERATOR'),('SERVICE','SOURCE_OWNER'),
                          ('HUMAN','DISCOVERY_MONITOR'),('WORKER','DISCOVERY_MONITOR')]:
            doc,now=self.snapshot(kind,role)
            with self.subTest(kind=kind,role=role),self.assertRaises(iam.DirectorySyncRefused):
                iam._snapshot(doc,issuer=ISSUER,audience=AUDIENCE,now=now)


if __name__=='__main__':unittest.main()
