"""Role probes use the actual pinned psycopg formatter without a DB server.

The synthetic rows exercise refusals only as unit protocol facts. Real login,
privilege and forced-RLS semantics remain in the isolated PostgreSQL campaign.
"""
import unittest

try:
    from psycopg.adapt import Transformer
    from psycopg._queries import PostgresQuery
except ImportError:
    Transformer = PostgresQuery = None

if PostgresQuery is not None:
    from provisioner.controlplane.discovery.monitor_runtime import require_monitor_role
    from provisioner.controlplane.discovery.runtime import require_ingest_role


class FormattingConnection:
    autocommit = False

    def __init__(self, rows):
        self.rows = iter(rows)
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self, query, parameters=None):
        # Connection.execute uses this exact pinned driver conversion. A plain
        # execute mock concealed the literal-percent error in earlier checks.
        converted = PostgresQuery(Transformer())
        converted.convert(query, parameters)
        self.statements.append((query, parameters, converted.query, converted.params))
        self.row = next(self.rows)
        return self

    def fetchone(self):
        return self.row


@unittest.skipUnless(PostgresQuery is not None, 'Declared psycopg controlplane dependency is unavailable')
class SQLRoleFormattingTests(unittest.TestCase):
    monitor_role = 'hosting_discovery_monitor'
    ingest_role = 'hosting_discovery_ingest'

    def monitor_rows(self):
        return [(self.monitor_role, False, False), (False,), (False,),
                (True,), (True,), (True,)]

    def ingest_rows(self):
        return [(self.ingest_role, self.ingest_role, False, False, False, False, False),
                (False,), (False,), (False, False), (False,), (True,), (True, True)]

    def assert_namespace_filter_is_bound(self, connection):
        checks = [record for record in connection.statements
                  if 'has_table_privilege' in record[0] and 'NOT LIKE' in record[0]]
        self.assertEqual(len(checks), 1)
        query, parameters, wire_query, wire_parameters = checks[0]
        self.assertIn('n.nspname NOT LIKE %s', query)
        self.assertEqual(parameters[-1], 'pg_%')
        self.assertEqual(bytes(wire_parameters[-1]), b'pg_%')
        self.assertNotIn(b"NOT LIKE 'pg_%'", wire_query)
        # The parameter fix retains every original forbidden mutation and the
        # independently checked required table and forced-RLS probes.
        for privilege in ('UPDATE', 'DELETE', 'TRUNCATE', 'TRIGGER', 'REFERENCES', 'INSERT'):
            self.assertIn("'" + privilege + "'", query)
        self.assertTrue(any('c.relrowsecurity AND c.relforcerowsecurity' in record[0]
                            for record in connection.statements))

    def test_monitor_role_queries_convert_with_real_psycopg_and_preserve_namespace_pattern(self):
        connection = FormattingConnection(self.monitor_rows())
        require_monitor_role(lambda: connection, self.monitor_role)
        self.assert_namespace_filter_is_bound(connection)
        self.assertEqual(len(connection.statements), 6)

    def test_ingest_role_queries_convert_with_real_psycopg_and_preserve_namespace_pattern(self):
        connection = FormattingConnection(self.ingest_rows())
        require_ingest_role(lambda: connection, self.ingest_role)
        self.assert_namespace_filter_is_bound(connection)
        self.assertEqual(len(connection.statements), 7)

    def test_monitor_bypass_site_other_privileges_missing_reads_writes_or_rls_still_refuse(self):
        for index, refusal in ((0, (self.monitor_role, False, True)), (1, (True,)),
                               (2, (True,)), (3, (False,)), (4, (False,)), (5, (False,))):
            rows = self.monitor_rows()
            rows[index] = refusal
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                require_monitor_role(lambda: FormattingConnection(rows), self.monitor_role)

    def test_ingest_mutations_missing_required_tables_or_forced_rls_still_refuse(self):
        for index, refusal in ((4, (True,)), (5, (False,)), (6, (True, False))):
            rows = self.ingest_rows()
            rows[index] = refusal
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                require_ingest_role(lambda: FormattingConnection(rows), self.ingest_role)


if __name__ == '__main__':
    unittest.main()
