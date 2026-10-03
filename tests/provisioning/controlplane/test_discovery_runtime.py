"""Discovery deployment settings and database privilege gates fail closed."""
from base64 import b64encode
from copy import deepcopy
from dataclasses import replace
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from provisioner.controlplane.discovery.runtime import DiscoveryIngestSettings, require_ingest_role


class DiscoveryRuntimeTests(unittest.TestCase):
    def settings(self):
        values = {
            'POSTGRES_DSN': 'postgresql://discovery_ingest@db.example/hosting?sslmode=verify-full&connect_timeout=5&sslrootcert=/etc/ca.pem',
            'POSTGRES_ROLE': 'discovery_ingest', 'BIND_IP': '127.0.0.1', 'BIND_PORT': '8446',
            'TLS_CERT': '/etc/server.pem', 'TLS_KEY': '/etc/server.key',
            'TLS_CA': '/etc/ca.pem', 'TLS_CRL': '/etc/crl.pem', 'TRUST_DOMAIN': 'discovery.example',
            'TRUST_POLICY_FILE': '/etc/discovery-trust.json', 'TRUST_MIN_REVISION': '1',
            'CREDENTIAL_WITNESS_FILE': '/etc/credential-witness.json',
            'CREDENTIAL_WITNESS_MIN_REVISION': '2', 'EVIDENCE_ROOT': '/var/lib/discovery-evidence',
        }
        for field in ('TRUST_ROOT_KEY', 'CREDENTIAL_WITNESS_ROOT_KEY'):
            values[field] = b64encode(Ed25519PrivateKey.generate().public_key().public_bytes_raw()).decode()
        return {'HOSTING_DISCOVERY_' + key: value for key, value in values.items()}

    def test_distinct_pinned_keys_verified_tls_dsn_and_exact_bind(self):
        settings = DiscoveryIngestSettings.from_environment(self.settings())
        self.assertEqual(settings.bind_port, 8446)
        self.assertEqual(settings.max_connections, 16)
        self.assertNotIn(settings.postgres_dsn, repr(settings))

    def test_missing_insecure_or_unbounded_configuration_is_denied(self):
        base = self.settings()
        for key in base:
            values = dict(base)
            values.pop(key)
            with self.subTest(missing=key), self.assertRaises(ValueError):
                DiscoveryIngestSettings.from_environment(values)
        mutations = {
            'BIND_IP': '0.0.0.0', 'BIND_PORT': '0', 'TRUST_MIN_REVISION': '0',
            'CREDENTIAL_WITNESS_ROOT_KEY': base['HOSTING_DISCOVERY_TRUST_ROOT_KEY'],
            'EVIDENCE_ROOT': './relative', 'MAX_CONNECTIONS': '1000',
            'POSTGRES_ROLE': 'other_role',
            'POSTGRES_DSN': base['HOSTING_DISCOVERY_POSTGRES_DSN'].replace('verify-full', 'require'),
        }
        for key, value in mutations.items():
            with self.subTest(field=key), self.assertRaises(ValueError):
                DiscoveryIngestSettings.from_environment(base | {'HOSTING_DISCOVERY_' + key: value})

    def test_sql_role_accepts_only_exact_append_only_ingestion_privileges(self):
        approved = [('discovery_ingest', 'discovery_ingest', False, False, False, False, False),
                    (False,), (False,), (False, False), (False,), (True,), (True, True)]

        class Connection:
            autocommit = False
            def __init__(self, rows): self.rows = iter(rows)
            def __enter__(self): return self
            def __exit__(self, *_args): pass
            def execute(self, *_args): return self
            def fetchone(self): return next(self.rows)

        require_ingest_role(lambda: Connection(approved), 'discovery_ingest')
        failures = [('root', 'root', True, True, True, True, True), (True,), (True,),
                    (False, True), (True,), (False,), (True, False)]
        for index, rejected in enumerate(failures):
            rows = deepcopy(approved)
            rows[index] = rejected
            with self.subTest(gate=index), self.assertRaises(RuntimeError):
                require_ingest_role(lambda: Connection(rows), 'discovery_ingest')
        connection = Connection(approved)
        connection.autocommit = True
        with self.assertRaises(RuntimeError):
            require_ingest_role(lambda: connection, 'discovery_ingest')


if __name__ == '__main__':
    unittest.main()
