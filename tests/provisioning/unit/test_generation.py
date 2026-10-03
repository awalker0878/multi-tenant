"""Stable WSD identity and monotonic generation, made checkable.

The generation model is the join between the portable plan and the delivery runner
that already required a generation. What has to be provable here is not that a
counter exists, but that the same generation can be replayed safely, that changed
desired state is refused at the same generation, that a newer generation supersedes
a finished one, and that evidence from another generation never counts as current.
"""
from __future__ import annotations

import ast
import sys
import types
import unittest

from provisioner.cli import evidence as evidence_command
from provisioner.cli import verify as verify_command
from provisioner.conformance import checks as conformance_checks
from provisioner.conformance import report as conformance_report
from provisioner.domain import generation
from provisioner.domain.errors import ProvisioningError
from provisioner.observation import native

from tests.provisioning import support

SOURCE = support.ROOT / 'provisioner' / 'domain' / 'generation.py'
DELIVERY_RUNNER = support.ROOT / 'tools' / 'delivery_run.py'


def _declared_delivery_scope_keys() -> set:
    """The scope keys `tools/delivery_run.validate` requires, read from its source.

    The runner is the owner of the scope contract, so this reads the contract
    instead of restating it. `tools.delivery_run` imports `fcntl` at module scope
    through the delivery journal, so the source is the portable way to see it.
    """
    tree = ast.parse(DELIVERY_RUNNER.read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if isinstance(node, ast.Set):
            values = {element.value for element in node.elts
                      if isinstance(element, ast.Constant)}
            if {'tenant_key', 'wsd_key'} <= values:
                return values
    raise AssertionError('the delivery runner declares no scope contract')


def _delivery_runner():
    """`tools.delivery_run`, importable on a platform without POSIX file locking.

    The delivery *journal* genuinely needs `fcntl`; the pure `validate()` contract
    does not. Only that contract is exercised here, so a no-op stub is installed for
    the duration of the import and removed again: nothing outside this call can
    observe it, and on a platform that has `fcntl` nothing is stubbed at all.
    """
    try:
        import fcntl  # noqa: F401
    except ImportError:
        stub = types.ModuleType('fcntl')
        stub.LOCK_EX, stub.LOCK_NB = 2, 4
        stub.flock = lambda *arguments, **options: None
        sys.modules['fcntl'] = stub
        try:
            from tools import delivery_run
            return delivery_run
        finally:
            del sys.modules['fcntl']
    from tools import delivery_run
    return delivery_run


_UNSET = object()


def _delivery_document(plan, generation=_UNSET) -> dict:
    return {'format': 'hosting-delivery/2', 'source_commit': '0' * 40,
            'operation_id': plan.operation_id,
            'generation': plan.generation if generation is _UNSET else generation,
            'reviewed_plan_digest': '0' * 64,
            'scope': plan.identity.scope,
            'steps': [{'id': 'first-step', 'kind': 'guest_plan', 'needs': []}], 'operation_bindings': {}, 'reviewed_parameters': {}, 'compiled_catalog_ids': {}}


def observed(subject: str, native_id: str, generation_value):
    return native.observed(subject, native_id, {}, 'readback', generation_value)


class IdentityTest(unittest.TestCase):
    def test_the_identity_projects_the_resolved_desired_state(self):
        plan = support.reference_plan()
        identity = plan.identity
        self.assertEqual(identity.tenant_key, plan.desired_state.tenant)
        self.assertEqual(identity.wsd_key, plan.desired_state.wsd)
        self.assertEqual(identity.site_key, plan.desired_state.site_key)
        self.assertEqual(identity.platform, plan.desired_state.platform)
        self.assertEqual(identity.environment_key,
                         f'{plan.desired_state.site_key}-{plan.desired_state.lifecycle}')

    def test_the_identity_is_derived_rather_than_stored_a_second_time(self):
        plan = support.reference_plan()
        self.assertNotIn('identity', plan.desired_state.to_dict())
        self.assertEqual(plan.desired_state.identity.key, plan.identity.key)

    def test_the_identity_key_names_the_whole_scope(self):
        plan = support.reference_plan()
        self.assertEqual(plan.identity.key,
                         'tenant-01/wsd-01@site-01-production/site-01/openstack')

    def test_the_identity_scope_matches_the_delivery_contract(self):
        plan = support.reference_plan()
        self.assertEqual(set(plan.identity.scope), set(generation.SCOPE_KEYS))
        self.assertEqual(set(plan.identity.to_dict()),
                         {'format', 'key', 'digest', 'limits'} | set(generation.SCOPE_KEYS))

    def test_the_delivery_runner_declares_the_same_scope_contract(self):
        """The delivery runner owns the scope contract, so its source is read, not restated."""
        self.assertEqual(_declared_delivery_scope_keys(), set(generation.SCOPE_KEYS))

    def test_the_delivery_runner_accepts_the_scope_and_operation_identity(self):
        plan = support.reference_plan()
        _delivery_runner().validate(_delivery_document(plan))

    def test_the_scoped_identifier_rule_is_the_delivery_identifier_rule(self):
        from provisioner.execution import readback_core
        self.assertEqual(generation.SCOPE_IDENTIFIER.pattern, readback_core.ID.pattern)

    def test_an_identity_component_must_be_a_scoped_identifier(self):
        for name, value in (('tenant_key', 'tenant 01'), ('wsd_key', ''), ('site_key', 'a' * 129),
                            ('platform', None)):
            with self.subTest(component=name):
                components = {'tenant_key': 'tenant-01', 'wsd_key': 'wsd-01',
                              'environment_key': 'site-01-production', 'site_key': 'site-01',
                              'platform': 'openstack', name: value}
                with self.assertRaises(ProvisioningError) as raised:
                    generation.WsdIdentity(**components)
                self.assertEqual(raised.exception.code, 'SCHEMA_VALIDATION_FAILED')

    def test_the_identity_digest_covers_the_whole_scope(self):
        base = generation.WsdIdentity('tenant-01', 'wsd-01', 'site-01-production',
                                      'site-01', 'openstack')
        for name, value in (('tenant_key', 'tenant-02'), ('wsd_key', 'wsd-02'),
                            ('environment_key', 'site-01-development'), ('site_key', 'site-02'),
                            ('platform', 'nutanix')):
            with self.subTest(component=name):
                components = {'tenant_key': base.tenant_key, 'wsd_key': base.wsd_key,
                              'environment_key': base.environment_key,
                              'site_key': base.site_key, 'platform': base.platform, name: value}
                self.assertNotEqual(generation.WsdIdentity(**components).digest, base.digest)

    def test_the_identity_grants_nothing(self):
        identity = support.reference_plan().identity
        self.assertEqual(identity.to_dict()['limits'],
                         ['Identity names the reviewed scope; it grants no authority'])


class GenerationValueTest(unittest.TestCase):
    def test_the_first_generation_is_one(self):
        self.assertEqual(generation.to_dict()['first_generation'], 1)
        self.assertEqual(support.reference_plan().generation, 1)
        self.assertEqual(support.reference_plan().desired_state.generation, 1)

    def test_only_a_positive_integer_is_a_generation(self):
        self.assertEqual(generation.require_generation(1), 1)
        self.assertEqual(generation.require_generation(97), 97)
        for value in (0, -1, True, False, '1', 1.0, None):
            with self.subTest(value=value):
                with self.assertRaises(ProvisioningError) as raised:
                    generation.require_generation(value)
                self.assertEqual(raised.exception.code, 'SCHEMA_VALIDATION_FAILED')

    def test_the_delivery_runner_refuses_the_same_values(self):
        """The two models must agree on what a generation is, not merely coexist."""
        plan = support.reference_plan()
        for value in (0, -1, True, '1', None):
            with self.subTest(value=value):
                document = _delivery_document(plan, generation=value)
                with self.assertRaises(Exception):
                    _delivery_runner().validate(document)

    def test_a_claimed_generation_changes_the_desired_state_and_the_plan(self):
        first = support.reference_plan()
        later = support.reference_plan(generation=2)
        self.assertEqual(first.request.digest, later.request.digest)
        self.assertNotEqual(first.desired_state.digest, later.desired_state.digest)
        self.assertNotEqual(first.digest, later.digest)
        self.assertNotEqual(first.operation_id, later.operation_id)
        self.assertEqual(later.desired_state.to_dict()['generation'], 2)

    def test_the_repository_holds_no_local_counter(self):
        """A local counter is not authority, so the module must not be able to read one."""
        tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and not node.level:
                imported.add(node.module or '')
        self.assertEqual(imported & {'os', 'pathlib', 'json', 'sqlite3', 'tempfile',
                                     'shutil'}, set())
        self.assertEqual(generation.to_dict()['authority'], 'EXTERNAL_LEDGER_ONLY')


class GenerationBindingTest(unittest.TestCase):
    def test_the_generation_reaches_every_artifact(self):
        plan = support.reference_plan()
        self.assertEqual(plan.desired_state.to_dict()['generation'], plan.generation)
        self.assertEqual(plan.to_dict()['generation'], plan.generation)
        self.assertEqual(plan.delivery['generation'], plan.generation)
        self.assertEqual(plan.delivery['identity']['key'], plan.identity.key)
        self.assertEqual(plan.delivery['plan_digest'], plan.digest)
        self.assertEqual(plan.conformance['generation'], plan.generation)
        self.assertEqual(plan.conformance['identity'], plan.identity.key)
        self.assertEqual(plan.conformance['operation_id'], plan.operation_id)
        self.assertEqual(plan.to_dict()['generation_record']['generation'], plan.generation)
        self.assertEqual(plan.to_dict()['generation_record']['plan_digest'], plan.digest)
        self.assertEqual(plan.to_dict()['generation_record']['desired_state_digest'],
                         plan.desired_state.digest)

    def test_the_operation_identity_is_derived_from_the_plan(self):
        plan = support.reference_plan()
        self.assertEqual(plan.operation_id,
                         f'{plan.identity.wsd_key}-g{plan.generation}-{plan.digest[:12]}')
        record = generation.record_for(plan)
        self.assertEqual(record.operation_id, plan.operation_id)
        self.assertEqual(record.identity_key, plan.identity.key)
        self.assertEqual(record.identity_digest, plan.identity.digest)

    def test_every_owner_operation_is_generation_bound(self):
        from provisioner.execution import readback_core
        plan = support.reference_plan()
        operations = plan.delivery['operations']
        self.assertTrue(operations)
        for operation in operations:
            with self.subTest(operation=operation['name']):
                self.assertEqual(operation['generation'], plan.generation)
                self.assertEqual(operation['operation_id'],
                                 f'{plan.operation_id}-{operation["name"]}')
                readback_core.identifier(operation['operation_id'])
        self.assertEqual(len({o['operation_id'] for o in operations}), len(operations))

    def test_a_later_generation_names_different_operations(self):
        first = support.reference_plan()
        later = support.reference_plan(generation=2)
        self.assertEqual({o['name'] for o in first.delivery['operations']},
                         {o['name'] for o in later.delivery['operations']})
        self.assertFalse({o['operation_id'] for o in first.delivery['operations']}
                         & {o['operation_id'] for o in later.delivery['operations']})

    def test_every_repository_evidence_record_is_generation_bound(self):
        plan = support.reference_plan()
        rows = evidence_command.records(plan)
        self.assertTrue(rows)
        for row in rows:
            with self.subTest(kind=row['kind']):
                self.assertEqual(row['generation'], plan.generation)
        self.assertEqual({row['kind'] for row in rows} & {'generation'}, {'generation'})

    def test_the_generation_evidence_record_claims_nothing(self):
        plan = support.reference_plan()
        row = [r for r in evidence_command.records(plan) if r['kind'] == 'generation'][0]
        self.assertEqual(row['status'], 'CLAIMED_BY_CALLER')
        self.assertEqual(row['authority'], 'REPOSITORY_SIDE_ONLY')
        self.assertEqual(row['details']['generation'], plan.generation)
        self.assertEqual(row['details']['operation_id'], plan.operation_id)
        self.assertEqual(row['details']['authority'], 'EXTERNAL_LEDGER_ONLY')

    def test_the_verification_plan_is_generation_bound(self):
        plan = support.reference_plan()
        rows = verify_command.verification_plan(plan)
        self.assertTrue(rows)
        for row in rows:
            with self.subTest(subject=row['subject']):
                self.assertEqual(row['generation'], plan.generation)
                self.assertEqual(row['operation_id'], plan.operation_id)


class LedgerClaimTest(unittest.TestCase):
    def setUp(self):
        self.plan = support.reference_plan()
        self.identity = self.plan.identity
        self.record = generation.record_for(self.plan)

    def claim(self, ledger, record, **options):
        return generation.claim(ledger, record, **options)

    def test_the_first_claim_of_an_identity_is_generation_one(self):
        ledger = generation.InMemoryLedger()
        later = generation.record(self.identity, 2, 'a' * 64, 'b' * 64)
        with self.assertRaises(ProvisioningError) as raised:
            self.claim(ledger, later)
        self.assertEqual(raised.exception.code, 'GENERATION_CONFLICT')
        self.assertIsNone(ledger.current(self.identity.key))

    def test_the_same_generation_and_digest_is_a_replay(self):
        ledger = generation.InMemoryLedger()
        first = self.claim(ledger, self.record)
        self.assertEqual(first['status'], generation.CLAIMED)
        replay = self.claim(ledger, generation.record_for(support.reference_plan()))
        self.assertEqual(replay['status'], generation.REPLAYED)
        self.assertFalse(replay['duplicate_operations'])
        self.assertEqual(ledger.current(self.identity.key).generation, 1)
        self.assertEqual(replay['operation_id'], first['operation_id'])

    def test_changed_desired_state_at_the_same_generation_is_refused(self):
        ledger = generation.InMemoryLedger()
        self.claim(ledger, self.record)
        changed = generation.record(self.identity, 1, 'c' * 64, 'd' * 64)
        with self.assertRaises(ProvisioningError) as raised:
            self.claim(ledger, changed)
        self.assertEqual(raised.exception.code, 'GENERATION_CONFLICT')
        self.assertIn('new generation', raised.exception.message)
        self.assertEqual(ledger.current(self.identity.key).desired_state_digest,
                         self.record.desired_state_digest)

    def test_a_changed_plan_at_the_same_generation_is_refused(self):
        ledger = generation.InMemoryLedger()
        self.claim(ledger, self.record)
        same_state = generation.record(self.identity, 1, self.record.desired_state_digest,
                                       'e' * 64)
        with self.assertRaises(ProvisioningError) as raised:
            self.claim(ledger, same_state)
        self.assertEqual(raised.exception.code, 'GENERATION_CONFLICT')

    def test_a_newer_generation_supersedes_a_closed_record(self):
        closed = generation.record_for(self.plan)
        ledger = generation.InMemoryLedger([generation.GenerationRecord(
            **{**closed.__dict__, 'status': generation.CLOSED})])
        later = generation.record(self.identity, 2, 'f' * 64, 'a1' * 32)
        outcome = self.claim(ledger, later)
        self.assertEqual(outcome['status'], generation.CLAIMED)
        self.assertEqual(outcome['superseded']['generation'], 1)
        self.assertEqual(outcome['superseded']['status'], generation.CLOSED)
        self.assertEqual(ledger.current(self.identity.key).generation, 2)

    def test_a_newer_generation_is_refused_while_the_operation_is_unfinished(self):
        ledger = generation.InMemoryLedger()
        self.claim(ledger, self.record)
        later = generation.record(self.identity, 2, 'f' * 64, 'a1' * 32)
        with self.assertRaises(ProvisioningError) as raised:
            self.claim(ledger, later)
        self.assertEqual(raised.exception.code, 'GENERATION_CONFLICT')
        self.assertIn('reconciled or closed', raised.exception.message)
        self.assertEqual(ledger.current(self.identity.key).generation, 1)

    def test_reconciliation_can_authorize_superseding_an_unfinished_generation(self):
        ledger = generation.InMemoryLedger()
        self.claim(ledger, self.record)
        later = generation.record(self.identity, 2, 'f' * 64, 'a1' * 32)
        outcome = self.claim(ledger, later, allow_open_supersession=True)
        self.assertEqual(outcome['status'], generation.CLAIMED)
        self.assertEqual(ledger.current(self.identity.key).generation, 2)

    def test_a_lower_generation_is_stale(self):
        ledger = generation.InMemoryLedger()
        self.claim(ledger, self.record)
        self.claim(ledger, generation.record(self.identity, 2, 'f' * 64, 'a1' * 32),
                   allow_open_supersession=True)
        with self.assertRaises(ProvisioningError) as raised:
            self.claim(ledger, self.record)
        self.assertEqual(raised.exception.code, 'STALE_GENERATION')
        self.assertEqual(ledger.current(self.identity.key).generation, 2)

    def test_another_identity_is_tracked_independently(self):
        ledger = generation.InMemoryLedger()
        self.claim(ledger, self.record)
        foreign = generation.record(generation.WsdIdentity('tenant-02', 'wsd-01',
                                                           'site-01-production', 'site-01',
                                                           'openstack'),
                                    1, 'f' * 64, 'a1' * 32)
        outcome = self.claim(ledger, foreign)
        self.assertEqual(outcome['status'], generation.CLAIMED)
        self.assertEqual(ledger.current(foreign.identity_key).generation, 1)
        self.assertEqual(ledger.current(self.identity.key).generation, 1)
        self.assertNotEqual(foreign.identity_key, self.identity.key)

    def test_a_ledger_returning_another_identity_is_refused(self):
        """A record must never be read as belonging to an identity it does not describe."""
        foreign = generation.record(generation.WsdIdentity('tenant-02', 'wsd-01',
                                                           'site-01-production', 'site-01',
                                                           'openstack'),
                                    1, 'f' * 64, 'a1' * 32)

        class MismatchingLedger:
            def current(self, identity_key):
                return foreign

            def compare_and_set(self, expected, proposed):
                raise AssertionError('a mismatched record must never be committed')

        with self.assertRaises(ProvisioningError) as raised:
            generation.claim(MismatchingLedger(), self.record)
        self.assertEqual(raised.exception.code, 'GENERATION_IDENTITY_MISMATCH')
        self.assertIn('different WSD identity', raised.exception.message)

    def test_concurrent_claims_cannot_both_become_current(self):
        """Two claimants that both read an empty ledger: only the first one commits."""
        ledger = generation.InMemoryLedger()
        seen = ledger.current(self.identity.key)
        self.assertIsNone(seen)
        other = generation.record(self.identity, 1, 'f' * 64, 'a1' * 32)
        ledger.commit(seen, other)
        with self.assertRaises(ProvisioningError) as raised:
            ledger.compare_and_set(seen, self.record)
        self.assertEqual(raised.exception.code, 'GENERATION_CONFLICT')
        self.assertEqual(ledger.current(self.identity.key).plan_digest, other.plan_digest)

    def test_a_claim_is_not_an_authorization(self):
        ledger = generation.InMemoryLedger()
        outcome = self.claim(ledger, self.record)
        self.assertFalse(outcome['native_contact'])
        self.assertEqual(outcome['authority'], generation.InMemoryLedger.AUTHORITY)
        self.assertEqual(generation.InMemoryLedger.AUTHORITY, 'IN_MEMORY_NOT_AUTHORITATIVE')
        self.assertIn('authorizes nothing', ' '.join(outcome['limits']))
        self.assertIn('never production authority', ' '.join(generation.to_dict()['limits']))

    def test_the_record_digest_covers_the_whole_record(self):
        first = generation.record(self.identity, 1, 'a' * 64, 'b' * 64)
        self.assertEqual(first.digest, generation.record(self.identity, 1, 'a' * 64,
                                                         'b' * 64).digest)
        self.assertNotIn('digest', first.body())
        for change in ({'status': generation.CLOSED}, {'superseded_by': 2},
                       {'plan_digest': 'c' * 64}, {'generation': 2}):
            with self.subTest(change=change):
                self.assertNotEqual(generation.GenerationRecord(**{**first.__dict__,
                                                                   **change}).digest,
                                    first.digest)

    def test_an_unknown_record_status_is_refused(self):
        with self.assertRaises(ValueError):
            generation.GenerationRecord(**{**self.record.__dict__, 'status': 'MAYBE'})

    def test_the_ledger_reports_what_it_is(self):
        ledger = generation.InMemoryLedger()
        self.claim(ledger, self.record)
        document = ledger.to_dict()
        self.assertEqual(document['format'], generation.LEDGER_FORMAT)
        self.assertEqual(document['authority'], 'IN_MEMORY_NOT_AUTHORITATIVE')
        self.assertEqual(document['identities'], [self.identity.key])

    def test_the_claim_interface_is_a_protocol_not_an_implementation(self):
        self.assertIsInstance(generation.GenerationLedger, type)
        for name in ('current', 'compare_and_set'):
            with self.subTest(method=name):
                self.assertTrue(callable(getattr(generation.GenerationLedger, name)))


class ObservationBindingTest(unittest.TestCase):
    def test_an_observation_from_an_earlier_generation_is_stale(self):
        plan = support.reference_plan(generation=2)
        rows = (observed('domain', 'wsd-01-OZ', 1),)
        bound = native.binding(rows, plan.generation)
        self.assertEqual(bound['stale'], 1)
        self.assertEqual(bound['bound'], 0)
        self.assertEqual(bound['rows'][0]['binding'], native.BINDING_STALE)
        self.assertIn('generation 1', bound['rows'][0]['reason'])

    def test_an_observation_that_names_no_generation_is_unbound(self):
        rows = (observed('domain', 'wsd-01-OZ', None),)
        bound = native.binding(rows, 1)
        self.assertEqual(bound['unbound'], 1)
        self.assertEqual(bound['rows'][0]['binding'], native.BINDING_UNBOUND)

    def test_an_observation_of_the_current_generation_is_bound(self):
        rows = (observed('domain', 'wsd-01-OZ', 1), observed('domain', 'wsd-01-RZ', 1))
        bound = native.binding(rows, 1)
        self.assertEqual(bound['bound'], 2)
        self.assertEqual(bound['stale'], 0)
        self.assertEqual(bound['unbound'], 0)
        self.assertEqual(native.bound(rows, 1), rows)
        self.assertEqual(native.bound(rows, 2), ())

    def test_the_readback_document_reports_the_binding_when_a_generation_is_given(self):
        plan = support.reference_plan()
        rows = (observed('domain', 'wsd-01-OZ', plan.generation),)
        payload = native.to_dict(rows, plan.desired_state, plan.generation)
        self.assertEqual(payload['generation'], plan.generation)
        self.assertEqual(payload['binding']['bound'], 1)
        self.assertNotIn('binding', native.to_dict(rows, plan.desired_state))

    def test_a_stale_observation_does_not_satisfy_current_conformance(self):
        plan = support.reference_plan(generation=2)
        rows = (observed('domain', 'wsd-01-OZ', 1),)
        report = conformance_report.build(plan, rows)
        self.assertEqual(report['status'], conformance_report.FAILED)
        self.assertIn('generation', report['failed'])
        check = [c for c in report['checks'] if c['name'] == 'generation'][0]
        self.assertEqual(check['status'], conformance_checks.FAIL)
        self.assertEqual(check['evidence']['stale'], 1)
        self.assertEqual(check['evidence']['stale_subjects'],
                         [['domain', 'wsd-01-OZ', 1]])

    def test_an_unattributed_observation_does_not_satisfy_current_conformance(self):
        plan = support.reference_plan()
        rows = (observed('domain', 'wsd-01-OZ', None),)
        report = conformance_report.build(plan, rows)
        self.assertIn('generation', report['failed'])
        check = [c for c in report['checks'] if c['name'] == 'generation'][0]
        self.assertEqual(check['evidence']['unbound'], 1)

    def test_a_bound_observation_satisfies_the_generation_check(self):
        plan = support.reference_plan()
        rows = (observed('domain', 'wsd-01-OZ', plan.generation),)
        report = conformance_report.build(plan, rows)
        self.assertNotIn('generation', report['failed'])
        check = [c for c in report['checks'] if c['name'] == 'generation'][0]
        self.assertEqual(check['status'], conformance_checks.PASS)
        self.assertEqual(check['evidence']['bound'], 1)

    def test_the_generation_check_is_mandatory_and_repository_side(self):
        plan = support.reference_plan()
        report = conformance_report.build(plan)
        check = [c for c in report['checks'] if c['name'] == 'generation'][0]
        self.assertTrue(check['mandatory'])
        self.assertEqual(check['authority'], 'REPOSITORY')
        self.assertIn('generation', conformance_checks.MANDATORY)
        self.assertIn('generation', conformance_checks.REPOSITORY_CHECKS)
        self.assertNotIn('generation', conformance_checks.EXTERNAL_CHECKS)

    def test_the_native_observation_evidence_carries_the_binding(self):
        plan = support.reference_plan()
        rows = (observed('domain', 'wsd-01-OZ', 1),)
        report = conformance_report.build(plan, rows)
        check = [c for c in report['checks'] if c['name'] == 'native-observation'][0]
        self.assertEqual(check['status'], conformance_checks.PENDING)
        self.assertEqual(check['evidence']['generation'], plan.generation)
        self.assertEqual(check['evidence']['bound'], 1)
        self.assertEqual(check['evidence']['stale'], 0)

    def test_the_report_states_that_another_generations_evidence_never_satisfies_it(self):
        report = conformance_report.build(support.reference_plan())
        self.assertIn('another generation', ' '.join(report['limits']))


if __name__ == '__main__':
    unittest.main()