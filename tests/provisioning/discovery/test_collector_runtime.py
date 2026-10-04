"""Installed-command composition with real native TLS, signatures and mTLS ingest.

The in-memory repository below verifies the actual retained evidence but is not
PostgreSQL. Dedicated database tests exercise the same command separately.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import io
import json
import os
import socket
import subprocess
import sys
import threading
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization

from provisioner.controlplane.discovery import collector_runtime, ingest
from provisioner.controlplane.discovery.collector_settings import DiscoveryCollectorSettings
from provisioner.controlplane.discovery.model import _json
from provisioner.controlplane.discovery.publication import PrivateDiscoveryOutbox
from provisioner.controlplane.persistence.store import TenantContext
from provisioner.controlplane.worker.pki import MutualTlsWorkerVerifier
from tests.provisioning.discovery import test_ahv_https as ahv_fixture
from tests.provisioning.discovery import test_vmware_https as vmware_fixture


def encoded_key(key):
    return base64.b64encode(key.public_key().public_bytes_raw()).decode('ascii')


def write_json(path, document):
    path.write_text(json.dumps(document))
    path.chmod(0o600)


def common_document(root, campaign_document, root_key, witness_key):
    """Write public selectors, not invented native credentials or authority."""
    write_json(root/'campaign.json', campaign_document)
    outbox = root/'outbox'
    outbox.mkdir(mode=0o700)
    return {'format': 'hosting-discovery-collector/1', 'campaignFile': str(root/'campaign.json'),
        'outboxRoot': str(outbox),
        'trust': {'policyFile': str(root/'trust.json'), 'rootKey': encoded_key(root_key), 'minimumRevision': 1},
        'witness': {'policyFile': str(root/'witness.json'), 'rootKey': encoded_key(witness_key), 'minimumRevision': 1}}


def publication_target(pki, port):
    root = pki.root
    (root/'collector.key').chmod(0o600)
    digest = lambda name: hashlib.sha256((root/name).read_bytes()).hexdigest()
    return {'origin': f'https://localhost:{port}', 'connectIp': '127.0.0.1',
        'trustDomain': 'workers.example', 'caBundle': str(root/'ca.pem'), 'caDigest': digest('ca.pem'),
        'crlBundle': str(root/'crl.pem'), 'crlDigest': digest('crl.pem'),
        'clientCertificate': str(root/'collector.pem'), 'certificateDigest': digest('collector.pem'),
        'clientKey': str(root/'collector.key'), 'timeoutSeconds': 3}


class RuntimeFixture:
    def configure(self, native=None, selection=None, ca=None):
        self.native = native or ahv_fixture.AhvHttpsTests()
        self.native.setUp()
        self.addCleanup(self.native.doCleanups)
        n = self.native
        signature = n.verifier.campaign_signature
        document = {'environmentId': n.environment, 'campaign': ingest.campaign_document(n.campaign),
                    'campaignSignature': {'keyId': signature.key_id, 'signature': signature.signature}}
        self.config = common_document(n.root, document, n.root_key, n.native_key)
        self.config['native'] = {'profile': n.campaign.collector_id, 'credentialFile': str(n.credential_path),
            'authorityKey': encoded_key(n.native_key), 'minimumRevision': 1,
            'selection': selection or {}, 'caBundles': ca or {'native': str(n.root/'ca.pem')},
            'timeoutSeconds': 3, 'maxResponseBytes': 4*1024*1024}
        self.signer_path = n.root/'result-signing.pem'
        self.signer_path.write_bytes(n.collector_key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        self.signer_path.chmod(0o600)
        self.config['signer'] = {'keyFile': str(self.signer_path), 'keyId': 'collector'}
        self.config_path = n.root/'collector.json'
        self.save()

    def save(self):
        write_json(self.config_path, self.config)

    def stage(self):
        return collector_runtime.execute(self.config_path, 'stage', clock=lambda: self.native.now)

    def outbox(self):
        scope = self.native.campaign.scope
        return PrivateDiscoveryOutbox(self.config['outboxRoot'], TenantContext(scope.organization_id, scope.tenant_id))

    def command(self, action):
        # A fresh interpreter uses real protected files; no in-process dependency injection.
        return subprocess.run([sys.executable, '-m', 'provisioner.controlplane.discovery.collector_runtime',
            action, '--config', str(self.config_path)], capture_output=True, text=True, timeout=15)

    def start_ingest(self):
        n = self.native
        n.pki.issue('server')
        scope = n.campaign.scope
        uri = (f'spiffe://workers.example/org/{scope.organization_id}/tenant/{scope.tenant_id}'
               f'/site/{scope.site_id}/worker/{n.campaign.collector_id}')
        n.pki.issue('collector', client=True, uri=uri)
        tls = MutualTlsWorkerVerifier(server_certificate=n.root/'server.pem', server_key=n.root/'server.key',
            trust_bundle=n.root/'ca.pem', crl_bundle=n.root/'crl.pem', trust_domain='workers.example')
        self.evidence = n.root/'ingest-evidence'
        self.evidence.mkdir(mode=0o700)
        self.results, self.requests = {}, []
        case = self

        class RecordingRepository:
            def __init__(self, connect, *, ingest_role=None, ingest_verifier=None):
                case.assertEqual(ingest_role, 'discovery_ingest')
                self.verifier = ingest_verifier
            def register_verified_campaign(self, context, environment, campaign):
                self.verifier.verify_campaign(campaign, environment, datetime.now(timezone.utc))
            def publish_verified_result(self, context, environment, result):
                proof = self.verifier.verify_result(n.campaign, result, environment, datetime.now(timezone.utc))
                record = json.loads(next(case.evidence.rglob(proof.verification_reference.split(':')[1])).read_bytes())
                raw = next(case.evidence.rglob(record['requestDigest'])).read_bytes()
                case.assertEqual(hashlib.sha256(raw).hexdigest(), record['requestDigest'])
                case.requests.append(raw)
                previous = case.results.setdefault(result.campaign_id, result.digest)
                case.assertEqual(previous, result.digest)
                return SimpleNamespace(environment_id=environment, generation=1,
                                       result_digest=result.digest, completeness=result.completeness)

        replacement = patch.object(ingest, 'DiscoveryRepository', RecordingRepository)
        replacement.start()
        self.addCleanup(replacement.stop)
        service = ingest.DiscoveryIngestService(connect=lambda: None, ingest_role='discovery_ingest',
            tls_verifier=tls, signature_verifier=n.verifier.verifier,
            evidence_sink=ingest.PrivateDiscoveryEvidenceSink(self.evidence))
        self.server = ingest.DiscoveryIngestServer(('127.0.0.1', 0), service)
        thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': 0.01}, daemon=True)
        thread.start()
        def stop():
            self.server.shutdown()
            self.server.server_close()
            thread.join(timeout=5)
        self.addCleanup(stop)
        self.config['publisher'] = publication_target(n.pki, self.server.server_port)
        self.save()


class CollectorRuntimeTests(RuntimeFixture, unittest.TestCase):
    def setUp(self):
        self.configure()

    def test_ahv_command_collects_signs_and_stages_without_publication(self):
        result = self.command('stage')
        self.assertEqual(result.returncode, 0, result.stderr+result.stdout)
        outcome = json.loads(result.stdout)
        self.assertEqual(outcome['status'], 'STAGED')
        self.assertEqual(outcome['completeness'], 'PARTIAL')
        self.assertEqual(outcome['objectCount'], 2)
        self.assertIs(outcome['publicationAttempted'], False)
        self.assertIs(outcome['executionAuthorized'], False)
        self.assertEqual(len(self.native.calls), 2)
        original = self.outbox().for_campaign(self.native.campaign, self.native.environment)
        self.assertEqual(original.digest, outcome['requestDigest'])
        self.assertNotIn(self.native.token, result.stdout+result.stderr)
        self.assertNotIn('PRIVATE KEY', result.stdout+result.stderr)

    def test_restart_stage_uses_original_without_native_or_signer_sections(self):
        first = self.stage()
        self.native.credential_path.unlink()
        self.signer_path.unlink()
        del self.config['native'], self.config['signer']
        self.save()
        result = self.command('stage')
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        again = json.loads(result.stdout)
        self.assertEqual(again['requestDigest'], first['requestDigest'])
        self.assertFalse(again['collectionRequested'])
        self.assertEqual(len(self.native.calls), 2)

    def test_publish_without_original_never_collects_or_signs(self):
        self.start_ingest()
        result = self.command('publish')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['status'], 'HELD')
        self.assertEqual(self.native.calls, [])
        self.assertEqual(self.requests, [])

    def test_native_to_installed_command_to_mtls_ingest_preserves_original_bytes(self):
        self.start_ingest()
        staged = self.command('stage')
        self.assertEqual(staged.returncode, 0, staged.stdout+staged.stderr)
        digest = json.loads(staged.stdout)['requestDigest']
        original = self.outbox().load(digest)
        self.signer_path.unlink()
        self.native.credential_path.unlink()
        del self.config['native'], self.config['signer']
        self.save()
        published = self.command('publish')
        self.assertEqual(published.returncode, 0, published.stdout+published.stderr)
        outcome = json.loads(published.stdout)
        self.assertEqual(outcome['status'], 'PUBLISHED')
        self.assertEqual(outcome['generation'], 1)
        self.assertIs(outcome['collectionRequested'], False)
        self.assertIs(outcome['executionAuthorized'], False)
        self.assertEqual(outcome['requestDigest'], digest)
        self.assertEqual(self.requests, [original.body])
        self.assertEqual(len(self.native.calls), 2)

    def test_lost_ack_has_distinct_exit_and_original_retry_never_rescans(self):
        self.start_ingest()
        staged = self.stage()
        reply = ingest._DiscoveryHandler._reply
        def lose(handler, status, document):
            if document.get('status') == 'RESULT_PUBLISHED':
                handler.connection.shutdown(socket.SHUT_RDWR)
                handler.close_connection = True
                return
            reply(handler, status, document)
        with patch.object(ingest._DiscoveryHandler, '_reply', lose):
            first = self.command('publish')
        self.assertEqual(first.returncode, 3, first.stdout+first.stderr)
        outcome = json.loads(first.stdout)
        self.assertEqual(outcome['status'], 'DELIVERY_UNKNOWN')
        self.assertEqual(outcome['phase'], 'RESULT')
        self.assertEqual(outcome['requestDigest'], staged['requestDigest'])
        self.assertTrue(outcome['reconciliationRequired'])
        self.assertEqual(len(self.requests), 1)
        again = self.command('publish')
        self.assertEqual(again.returncode, 0, again.stdout+again.stderr)
        self.assertEqual(self.requests[0], self.requests[1])
        self.assertEqual(len(self.native.calls), 2)
        self.assertEqual(len(self.results), 1)

    def test_revoked_resume_cannot_stage_publish_or_fall_back(self):
        self.start_ingest()
        self.stage()
        self.native.revoke_witness()
        for action in ('stage', 'publish'):
            result = self.command(action)
            self.assertEqual(result.returncode, 2, result.stdout+result.stderr)
        self.assertEqual(len(self.native.calls), 2)
        self.assertEqual(self.requests, [])

    def test_expired_or_regressed_campaign_never_contacts_native(self):
        for at in (self.native.campaign.expires_at, self.native.campaign.issued_at-timedelta(seconds=1)):
            with self.subTest(at=at), self.assertRaises(Exception):
                collector_runtime.execute(self.config_path, 'stage', clock=lambda: at)
        self.assertEqual(self.native.calls, [])

    def test_altered_unsigned_campaign_is_not_authority(self):
        path = Path(self.config['campaignFile'])
        document = json.loads(path.read_text())
        document['environmentId'] = 'foreign-environment'
        write_json(path, document)
        result = self.command('stage')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.native.calls, [])

    def test_changed_config_profile_and_unregistered_dynamic_import_are_held(self):
        for profile in ('site-worker-01', 'os.system', 'vcenter-rest-vm-info-8.0.3.0-visible-only-2'):
            with self.subTest(profile=profile):
                self.config['native']['profile'] = profile
                self.save()
                self.assertEqual(self.command('stage').returncode, 2)
        self.assertEqual(self.native.calls, [])

    def test_native_selection_or_trust_keys_cannot_override_admitted_cluster(self):
        original = copy.deepcopy(self.config)
        for field, value in (('selection', {'clusterId': 'foreign'}), ('caBundles', {'foreign': '/missing'})):
            self.config = copy.deepcopy(original)
            self.config['native'][field] = value
            self.save()
            self.assertEqual(self.command('stage').returncode, 2)
        self.assertEqual(self.native.calls, [])

    def test_incomplete_initial_configuration_cannot_invoke_a_native_client(self):
        del self.config['signer']
        self.save()
        self.assertEqual(self.command('stage').returncode, 2)
        self.assertEqual(self.native.calls, [])

    def test_missing_original_payload_holds_instead_of_recollecting(self):
        staged = self.stage()
        next(Path(self.config['outboxRoot']).rglob(staged['requestDigest'])).unlink()
        result = self.command('stage')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(len(self.native.calls), 2)

    def test_invalid_cli_arguments_never_echo_inline_secrets(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = collector_runtime.main(['stage', '--token', 'do-not-echo-this-secret'])
        self.assertEqual(code, 2)
        self.assertNotIn('do-not-echo', output.getvalue())
        self.assertEqual(json.loads(output.getvalue())['status'], 'HELD')
        self.assertEqual(self.native.calls, [])

    def test_interrupt_does_not_claim_noncommitment(self):
        output = io.StringIO()
        with patch.object(collector_runtime, 'execute', side_effect=KeyboardInterrupt), redirect_stdout(output):
            code = collector_runtime.main(['publish', '--config', str(self.config_path)])
        self.assertEqual(code, 130)
        outcome = json.loads(output.getvalue())
        self.assertEqual(outcome['status'], 'INTERRUPTED')
        self.assertTrue(outcome['reconciliationRequired'])
        self.assertIs(outcome['executionAuthorized'], False)


class CollectorConfigurationTests(RuntimeFixture, unittest.TestCase):
    def setUp(self):
        self.configure()

    def test_unknown_keys_duplicate_json_and_unsupported_format_are_rejected(self):
        for raw in (_json({**self.config, 'token': 'never-inline'}),
                    '{"format":"one","format":"two"}',
                    _json({**self.config, 'format': 'hosting-discovery-collector/0'}),
                    '{"unused":1e999}', '[]'):
            with self.subTest(raw=raw[:20]):
                self.config_path.write_text(raw)
                self.assertEqual(self.command('stage').returncode, 2)
        self.assertEqual(self.native.calls, [])

    def test_private_regular_configuration_file_is_mandatory(self):
        self.config_path.chmod(0o644)
        self.assertEqual(self.command('stage').returncode, 2)
        self.config_path.chmod(0o600)
        saved = self.config_path.with_suffix('.saved')
        self.config_path.rename(saved)
        self.config_path.symlink_to(saved)
        self.assertEqual(self.command('stage').returncode, 2)
        self.config_path.unlink()
        os.mkfifo(self.config_path, 0o600)
        self.assertEqual(self.command('stage').returncode, 2)
        self.config_path.unlink()
        self.assertEqual(self.command('stage').returncode, 2)
        self.assertEqual(self.native.calls, [])

    def test_oversized_config_and_noncanonical_paths_are_rejected(self):
        self.config_path.write_bytes(b' '*65537)
        self.assertEqual(self.command('stage').returncode, 2)
        for path in ('relative.json', '/etc/../file', '/etc//file', '/etc/file/', '/etc/./file', '/etc/fi\nle'):
            self.config['campaignFile'] = path
            self.save()
            self.assertEqual(self.command('stage').returncode, 2)
        self.assertEqual(self.native.calls, [])

    def test_authority_roots_are_distinct_and_revision_floors_typed(self):
        original = copy.deepcopy(self.config)
        for section in ('trust', 'witness', 'native'):
            for value in (True, 0, -1, '1', 2**63):
                with self.subTest(section=section, value=value):
                    self.config = copy.deepcopy(original)
                    self.config[section]['minimumRevision'] = value
                    self.save()
                    with self.assertRaises(ValueError): DiscoveryCollectorSettings.from_file(self.config_path)
        self.config = copy.deepcopy(original)
        self.config['witness']['rootKey'] = self.config['trust']['rootKey']
        self.save()
        with self.assertRaises(ValueError): DiscoveryCollectorSettings.from_file(self.config_path)
        self.assertEqual(self.native.calls, [])

    def test_native_limits_and_material_keys_are_not_coerced(self):
        original = copy.deepcopy(self.config)
        cases = (('timeoutSeconds', True), ('timeoutSeconds', 0), ('timeoutSeconds', 16),
                 ('maxResponseBytes', True), ('maxResponseBytes', 4*1024*1024+1),
                 ('authorityKey', self.config['trust']['rootKey']), ('authorityKey', 'invalid'))
        for field, value in cases:
            with self.subTest(field=field):
                self.config = copy.deepcopy(original)
                self.config['native'][field] = value
                self.save()
                with self.assertRaises(ValueError): DiscoveryCollectorSettings.from_file(self.config_path)
        self.assertEqual(self.native.calls, [])

    def test_snapshot_settings_are_immutable_and_do_not_show_native_material(self):
        settings = DiscoveryCollectorSettings.from_file(self.config_path)
        self.config['native']['selection']['new'] = 'not-installed'
        self.assertNotIn('not-installed', settings.native_json)
        self.assertNotIn('credentialFile', repr(settings))
        with self.assertRaises(AttributeError): settings.native_json = '{}'


class CollectorOtherPlatformTests(RuntimeFixture, unittest.TestCase):
    def test_vmware_runtime_composes_exact_folder_selection_and_signing(self):
        selection = vmware_fixture.SELECTION
        self.configure(vmware_fixture.VmwareHttpsTests(),
            selection={'folderIds': list(selection.folder_ids), 'coverageDigest': selection.coverage_digest})
        result = self.command('stage')
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertEqual(json.loads(result.stdout)['completeness'], 'PARTIAL')
        self.assertEqual(len(self.native.calls), 2)
        self.assertEqual(self.native.calls[0][1], vmware_fixture.LIST)

    def test_openstack_runtime_composes_all_four_services_and_signing(self):
        from tests.provisioning.discovery import test_openstack_https as fixture
        native = fixture.OpenStackHttpsTests()
        self.configure(native)
        self.config['native']['selection'] = {s: native.endpoints.for_service(s) for s in fixture.API_VERSIONS}
        self.config['native']['caBundles'] = {s: str(native.root/'ca.pem') for s in fixture.API_VERSIONS}
        self.save()
        result = self.command('stage')
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertEqual(json.loads(result.stdout)['completeness'], 'PARTIAL')
        self.assertEqual(len(native.calls), 7)
        self.assertEqual([x[0] for x in native.calls], ['compute','volume','network']*2 + ['image'])
        original = self.outbox().for_campaign(native.campaign, native.environment)
        self.assertNotIn(native.token.encode(), original.body)


if __name__ == '__main__':
    unittest.main()
