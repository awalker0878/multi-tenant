"""Fresh collector command processes publish original bytes to real PostgreSQL.

Only the native observation and IAM evidence are synthetic; signatures, mTLS,
append-only persistence, role separation and retry idempotency are exercised.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import unittest
from unittest.mock import patch

from provisioner.controlplane.discovery import ingest
from provisioner.controlplane.discovery.publication import DiscoverySubmission, PrivateDiscoveryOutbox
from tests.provisioning.controlplane import test_discovery_ingest_postgres as existing
from tests.provisioning.discovery import test_collector_runtime as config_fixture


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_DISCOVERY_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_RUNTIME_DSN'),
                     'Requires dedicated disposable PostgreSQL discovery roles')
class CollectorCommandPostgresTests(unittest.TestCase):
    def setUp(self):
        self.f = existing.DiscoveryIngestPostgresTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        f = self.f
        config = config_fixture.common_document(f.root, f.document(), f.root_key, f.witness_key)
        config['publisher'] = config_fixture.publication_target(f.pki, f.server.server_port)
        self.config_path = f.root/'collector.json'
        config_fixture.write_json(self.config_path, config)
        doc = f.document(result=True)
        self.original = DiscoverySubmission(f.environment, f.campaign, ingest._signature(doc['campaignSignature']),
                                             f.result, ingest._signature(doc['resultSignature']))
        PrivateDiscoveryOutbox(config['outboxRoot'], f.context).retain(self.original)

    def command(self):
        return subprocess.run([sys.executable, '-m', 'provisioner.controlplane.discovery.collector_runtime',
            'publish', '--config', str(self.config_path)], capture_output=True, text=True, timeout=15)

    def assert_one_original(self):
        rows = self.f.reader.list_generations(self.f.context, self.f.scope, self.f.environment)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].result_digest, self.original.result.digest)
        self.assertEqual(next(self.f.evidence.rglob(self.original.digest)).read_bytes(), self.original.body)

    def test_two_fresh_commands_publish_one_generation_without_native_configuration(self):
        for _ in range(2):
            result = self.command()
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            outcome = json.loads(result.stdout)
            self.assertEqual(outcome['generation'], 1)
            self.assertEqual(outcome['requestDigest'], self.original.digest)
            self.assertIs(outcome['collectionRequested'], False)
            self.assertIs(outcome['executionAuthorized'], False)
        self.assert_one_original()

    def test_lost_ack_exit_and_new_process_retry_preserve_database_identity(self):
        reply = ingest._DiscoveryHandler._reply
        def lose(handler, status, document):
            if document.get('status') == 'RESULT_PUBLISHED':
                handler.connection.shutdown(socket.SHUT_RDWR)
                handler.close_connection = True
                return
            reply(handler, status, document)
        with patch.object(ingest._DiscoveryHandler, '_reply', lose):
            result = self.command()
        self.assertEqual(result.returncode, 3, result.stdout+result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'DELIVERY_UNKNOWN')
        self.assert_one_original()
        retry = self.command()
        self.assertEqual(retry.returncode, 0, retry.stdout+retry.stderr)
        self.assert_one_original()


if __name__ == '__main__':
    unittest.main()
