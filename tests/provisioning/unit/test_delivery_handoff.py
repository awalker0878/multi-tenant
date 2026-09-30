"""The reviewed delivery handoff: the plan compiled into the existing runner's graph.

The portable package plans and refuses. What has to be provable here is that the
refusal is *useful*: the reviewed plan compiles into the exact `hosting-delivery/2`
graph the repository's persistent delivery runner already validates, that every
reviewed owner operation is discharged by a declared typed step, that one clean
source commit and one generation are bound, and that nothing in this repository
became a second runner, a second journal or a second recovery model.

`tools/delivery_run.py` is the owner of the graph contract and imports `fcntl` at
module scope through the delivery journal, so it is imported here behind a no-op
stub for the duration of the import — the pure `validate()` contract does not need
file locking. The mirrored declarations are compared against the owner's source and
against `tools.delivery_steps.KINDS`, so a kind, a parameter or a grammar the runner
adds cannot drift unnoticed.
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from provisioner.cli import apply as apply_module
from provisioner.domain import generation
from provisioner.domain.errors import ProvisioningError
from provisioner.execution import authority as authority_module
from provisioner.execution import handoff
from provisioner.execution import service
from provisioner.placement import eligibility

from tests.provisioning import support

REQUEST = str(support.REQUEST)
MODULE = 'provisioner.cli'
DELIVERY_RUNNER = support.ROOT / 'tools' / 'delivery_run.py'
DELIVERY_STEPS = support.ROOT / 'tools' / 'delivery_steps.py'
COMMIT = 'a' * 40


def checkout_commit() -> str:
    """The commit the checkout reports, so a handoff can bind it explicitly."""
    return support.source_commit()


def _run(*arguments: str) -> tuple[int, dict]:
    completed = subprocess.run([sys.executable, '-m', MODULE, *arguments],
                               cwd=str(support.ROOT), capture_output=True, text=True,
                               encoding='utf-8')
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        raise AssertionError(
            f'CLI did not emit JSON (exit {completed.returncode}): '
            f'{completed.stdout!r} {completed.stderr!r}')
    return completed.returncode, payload


def _delivery_runner():
    """`tools.delivery_run`, importable on a platform without POSIX file locking."""
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


def _delivery_steps():
    from tools import delivery_steps
    return delivery_steps


def _literal_set(pattern: str) -> set:
    """The set literal `tools/delivery_steps.py` accepts at one predicate.

    The runner owns these sets. Reading them out of its source keeps the mirror
    honest without restating the contract a second time.
    """
    source = DELIVERY_STEPS.read_text(encoding='utf-8')
    match = re.search(pattern, source)
    assert match is not None, f'the runner no longer declares {pattern!r}'
    return set(re.findall(r"'([^']+)'", match.group(1)))


def _module_literal(relative: str, name: str) -> set:
    """A module-level set constant, read from the module's source.

    `tools.netbox_ipam` and `tools.netbox_dns` import `fcntl` at module scope, so
    their declarations are read the same way the runner's are.
    """
    source = (support.ROOT / relative).read_text(encoding='utf-8')
    match = re.search(rf"^{name} = (\{{[^}}]*\}})", source, flags=re.MULTILINE)
    assert match is not None, f'{relative} no longer declares {name}'
    return set(re.findall(r"'([^']+)'", match.group(1)))


class MirroredContractTest(unittest.TestCase):
    """Every mirror is compared with the owner, so neither can drift alone."""

    def test_every_mirrored_kind_is_a_declared_kind(self):
        self.assertEqual(handoff.KINDS, set(_delivery_steps().KINDS))

    def test_every_mirrored_parameter_set_matches_the_declared_set(self):
        declared = _delivery_steps().KINDS
        for kind, entry in sorted(declared.items()):
            with self.subTest(kind=kind):
                self.assertEqual(handoff._declared_parameters(kind), set(entry[0]))

    def test_the_identifier_grammar_is_the_declared_grammar(self):
        from tools import readback_core
        self.assertEqual(handoff.IDENTIFIER.pattern, readback_core.ID.pattern)

    def test_the_graph_and_step_keys_are_the_ones_the_runner_requires(self):
        tree = ast.parse(DELIVERY_RUNNER.read_text(encoding='utf-8'))
        declared = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Set):
                values = {element.value for element in node.elts
                          if isinstance(element, ast.Constant)}
                if values and all(isinstance(value, str) for value in values):
                    declared.append(values)
        graph_keys = [values for values in declared if 'source_commit' in values]
        step_keys = [values for values in declared if 'kind' in values]
        self.assertTrue(graph_keys, 'the runner no longer declares the graph keys')
        self.assertTrue(step_keys, 'the runner no longer declares the step keys')
        self.assertEqual(set(handoff.HANDOFF_KEYS), graph_keys[0])
        self.assertEqual(set(handoff.STEP_KEYS), step_keys[0])
        source = DELIVERY_RUNNER.read_text(encoding='utf-8')
        self.assertIn(f"== '{handoff.HANDOFF_FORMAT}'", source)

    def test_the_platform_set_is_the_declared_platform_set(self):
        source = DELIVERY_RUNNER.read_text(encoding='utf-8')
        match = re.search(r"plan\['scope'\]\['platform'\] in (\{[^}]*\})", source)
        self.assertIsNotNone(match)
        self.assertEqual(set(re.findall(r"'([^']+)'", match.group(1))), set(eligibility.PLATFORMS))

    def test_every_mirrored_action_set_is_the_declared_action_set(self):
        self.assertEqual(handoff.IPAM_ACTIONS,
                         _module_literal('tools/netbox_ipam.py', 'ACTIONS'))
        self.assertEqual(handoff.DNS_ACTIONS,
                         _module_literal('tools/netbox_dns.py', 'ACTIONS'))
        self.assertEqual(handoff.CAPACITY_ACTIONS,
                         _literal_set(r"values\['action'\] in (\{[^}]*\}),"
                                      r"'Unknown capacity transition'"))
        self.assertEqual(handoff.RESTIC_ACTIONS,
                         _literal_set(r"values\['action'\] in (\{[^}]*\}),"
                                      r"'Unknown backup transition'"))

    def test_every_mirrored_purpose_mode_and_stage_is_declared(self):
        self.assertEqual(handoff.ACCEPTANCE_PURPOSES,
                         _literal_set(r"values\['purpose'\] in (\{[^}]*\})"))
        self.assertEqual(handoff.TRANSITION_STAGES,
                         _literal_set(r"values\['stage'\] in (\{[^}]*\})"))
        self.assertEqual(handoff.GUEST_MODES,
                         _literal_set(r"values\['mode'\] in (\{[^}]*\}) and type"))
        self.assertEqual(handoff.EDGE_MODES,
                         _literal_set(r"if kind=='edge_policy': "
                                      r"require\(values\['mode'\] in (\{[^}]*\})"))


class SequenceTest(unittest.TestCase):
    """The reviewed sequence: declared kinds, topological order, total coverage."""

    def setUp(self):
        self.plan = support.reference_plan()
        self.graph = handoff.build(self.plan, COMMIT)

    def test_every_step_is_a_declared_kind_in_a_topological_order(self):
        seen: set[str] = set()
        for step in handoff.STEPS:
            with self.subTest(step=step.id):
                self.assertIn(step.kind, handoff.KINDS)
                self.assertNotIn(step.id, seen)
                self.assertTrue(set(step.needs) <= seen, 'a dependency is declared later')
                if seen:
                    self.assertTrue(step.needs, 'a subsequent step retains a dependency')
            seen.add(step.id)

    def test_the_sequence_starts_with_one_admission_gate(self):
        self.assertEqual(handoff.STEPS[0].id, 'admission')
        self.assertEqual(handoff.STEPS[0].kind, 'acceptance')
        self.assertEqual(handoff.STEPS[0].needs, ())
        self.assertEqual(handoff.predecessors('admission'), ())

    def test_every_reviewed_owner_operation_is_discharged(self):
        operations = handoff.operation_names(self.plan)
        self.assertEqual(len(operations), 10)
        self.assertEqual(handoff.uncovered(operations), [])

    def test_every_mapped_step_exists_and_carries_the_right_kind(self):
        kinds = {'state-backend': 'terraform_plan',
                 'capacity-reservation': 'capacity',
                 'address-allocation': 'ipam',
                 'dns-registration': 'dns',
                 'security-edge-route': 'edge_policy',
                 'shared-service-handoff': 'acceptance',
                 'backup-retention': 'restic',
                 'native-qualification': 'target_campaign',
                 'production-authorization': 'acceptance',
                 'guest-configuration': 'guest_apply'}
        self.assertEqual(sorted(handoff.OPERATION_STEPS), sorted(kinds))
        for operation, step_id in sorted(handoff.OPERATION_STEPS.items()):
            with self.subTest(operation=operation):
                self.assertEqual(handoff.step_of(step_id).kind, kinds[operation])

    def test_an_operation_without_a_step_is_refused_before_a_graph_exists(self):
        self.assertEqual(handoff.uncovered(['capacity-reservation', 'invented']), ['invented'])
        plan = support.reference_plan()
        broken = plan.delivery['operations'] + [dict(plan.delivery['operations'][0],
                                                     name='invented')]
        object.__setattr__(plan, 'delivery', {**plan.delivery, 'operations': broken})
        with self.assertRaises(ProvisioningError) as raised:
            handoff.build(plan, COMMIT)
        self.assertEqual(raised.exception.code, 'COMPILATION_FAILED')
        self.assertEqual(raised.exception.details['uncovered'], ['invented'])

    def test_the_two_load_bearing_orderings_are_declared(self):
        ancestors = lambda step: {s.id for s in handoff.STEPS
                                  if _is_ancestor(step, s.id)} | {step}
        self.assertIn('capacity-reservation', ancestors('workload-apply'))
        self.assertIn('capacity-reservation', ancestors('workload-plan'))
        for step_id in ('workload-apply', 'workload-plan', 'bootstrap'):
            with self.subTest(step=step_id):
                self.assertIn('edge-policy', ancestors(step_id))
        self.assertEqual(handoff.predecessors('post-activation-campaign'), ('activation',))
        self.assertEqual(set(handoff.predecessors('activation')),
                         {'pre-activation-campaign', 'bootstrap-acceptance'})

    def test_reviewed_parameters_are_declared_for_their_kind(self):
        for step_id, parameters in sorted(handoff.REVIEWED_PARAMETERS.items()):
            with self.subTest(step=step_id):
                step = handoff.step_of(step_id)
                self.assertTrue(set(parameters) <= handoff._declared_parameters(step.kind))

    def test_every_declared_parameter_of_every_step_is_accounted_for(self):
        for step in handoff.STEPS:
            declared = handoff._declared_parameters(step.kind)
            named = (set(handoff.REVIEWED_PARAMETERS.get(step.id, ()))
                     | set(handoff.COMPILED_PARAMETERS.get(step.id, ()))
                     | set(handoff.OPERATOR_PARAMETERS.get(step.id, ())))
            with self.subTest(step=step.id):
                self.assertTrue(declared <= named, f'{step.kind} parameters are unnamed')

    def test_no_parameter_is_claimed_by_two_provenances(self):
        sets = {name: {value for values in getattr(handoff, name).values()
                       for value in values}
                for name in ('REVIEWED_PARAMETERS', 'COMPILED_PARAMETERS',
                             'OPERATOR_PARAMETERS')}
        for left, right in (('REVIEWED_PARAMETERS', 'COMPILED_PARAMETERS'),
                            ('REVIEWED_PARAMETERS', 'OPERATOR_PARAMETERS'),
                            ('COMPILED_PARAMETERS', 'OPERATOR_PARAMETERS')):
            with self.subTest(pair=f'{left}/{right}'):
                self.assertFalse(sets[left] & sets[right], 'a parameter is claimed twice')

    def test_every_reviewed_value_is_a_declared_value_for_its_kind(self):
        legal = {('acceptance', 'purpose'): handoff.ACCEPTANCE_PURPOSES,
                 ('capacity', 'action'): handoff.CAPACITY_ACTIONS,
                 ('ipam', 'action'): handoff.IPAM_ACTIONS,
                 ('dns', 'action'): handoff.DNS_ACTIONS,
                 ('restic', 'action'): handoff.RESTIC_ACTIONS,
                 ('edge_policy', 'mode'): handoff.EDGE_MODES,
                 ('platform_transition', 'stage'): handoff.TRANSITION_STAGES,
                 ('guest_plan', 'mode'): handoff.GUEST_MODES}
        for step_id, values in sorted(handoff.REVIEWED_PARAMETERS.items()):
            step = handoff.step_of(step_id)
            for name, value in sorted(values.items()):
                allowed = legal.get((step.kind, name))
                if allowed is None:
                    continue
                with self.subTest(step=step_id, parameter=name):
                    self.assertIn(value, allowed)

    def test_every_reviewed_dependency_is_a_direct_dependency_of_the_right_kind(self):
        expected = {'dns_step': 'dns', 'prior_step': 'terraform_apply',
                    'workload_step': 'terraform_apply'}
        for step_id, values in sorted(handoff.REVIEWED_PARAMETERS.items()):
            step = handoff.step_of(step_id)
            for name, value in sorted(values.items()):
                if name == 'prepared_step':
                    with self.subTest(step=step_id, parameter=name):
                        self.assertIn(value, handoff.predecessors(step_id))
                        self.assertIn(handoff.step_of(value).kind,
                                      ('terraform_plan', 'guest_plan'))
                elif name in expected:
                    with self.subTest(step=step_id, parameter=name):
                        self.assertIn(value, handoff.predecessors(step_id))
                        self.assertEqual(handoff.step_of(value).kind, expected[name])
                elif name == 'domain_steps':
                    with self.subTest(step=step_id, parameter=name):
                        self.assertTrue(value)
                        self.assertEqual(len(set(value)), len(value))
                        for selected in value:
                            self.assertIn(selected, handoff.predecessors(step_id))
                            self.assertEqual(handoff.step_of(selected).kind,
                                             'terraform_apply')

    def test_the_compiled_parameters_are_supplied_once_the_phase_compiled(self):
        supplied = handoff.reviewed_parameters(self.plan)
        catalogs = handoff.catalog_ids(self.plan)
        self.assertEqual(set(catalogs), {'domains'})
        self.assertEqual(supplied['domain-plan'], {'catalog_id': catalogs['domains']})

    def test_a_held_phase_supplies_no_compiled_parameter(self):
        """The workloads phase is held pending native outputs, so none is invented."""
        held = [phase['phase'] for phase in self.plan.phases
                if phase['status'].startswith('HELD')]
        self.assertEqual(held, ['workloads'])
        supplied = handoff.reviewed_parameters(self.plan)
        self.assertNotIn('workload-plan', supplied)
        self.assertNotIn('selected_input', supplied['workload-inputs'])


def _is_ancestor(step_id: str, candidate: str) -> bool:
    """Whether `candidate` is a transitive predecessor of `step_id`."""
    pending = list(handoff.predecessors(step_id))
    seen: set[str] = set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        if current == candidate:
            return True
        seen.add(current)
        pending.extend(handoff.predecessors(current))
    return False


class GraphTest(unittest.TestCase):
    """The compiled graph is the declared contract, bound to the reviewed plan."""

    def setUp(self):
        self.plan = support.reference_plan()
        self.graph = handoff.build(self.plan, COMMIT)

    def test_the_existing_runner_accepts_the_compiled_graph(self):
        runner = _delivery_runner()
        self.assertIsNone(runner.validate(self.graph))

    def test_the_graph_is_deterministic(self):
        self.assertEqual(handoff.build(self.plan, COMMIT), self.graph)
        self.assertEqual(json.dumps(handoff.build(self.plan, COMMIT), sort_keys=True),
                         json.dumps(self.graph, sort_keys=True))

    def test_the_graph_carries_exactly_the_declared_keys(self):
        self.assertEqual(sorted(self.graph), sorted(handoff.HANDOFF_KEYS))
        self.assertEqual(self.graph['format'], handoff.HANDOFF_FORMAT)
        for step in self.graph['steps']:
            with self.subTest(step=step['id']):
                self.assertEqual(sorted(step), sorted(handoff.STEP_KEYS))

    def test_the_commit_generation_scope_and_operation_identity_are_bound(self):
        self.assertEqual(self.graph['source_commit'], COMMIT)
        self.assertEqual(self.graph['generation'], self.plan.generation)
        self.assertEqual(self.graph['scope'], self.plan.identity.scope)
        self.assertEqual(self.graph['operation_id'], self.plan.operation_id)
        self.assertEqual(set(self.graph['scope']), set(generation.SCOPE_KEYS))
        self.assertEqual(self.graph['operation_id'],
                         f'{self.plan.identity.wsd_key}-g{self.plan.generation}'
                         f'-{self.plan.digest[:12]}')

    def test_the_graph_carries_reviewed_values_but_no_private_runtime_inputs(self):
        """Approval-relevant values are bound; secrets, binaries and receipts are not."""
        text = json.dumps(self.graph, sort_keys=True)
        for term in ('terraform_sha256', 'nft_sha256', 'ssh_sha256', 'password',
                     'token', 'private_key', 'restic_sha256'):
            with self.subTest(term=term):
                self.assertNotIn(term, text)
        self.assertEqual(self.graph['operation_bindings'],
                         dict(sorted(handoff.OPERATION_STEPS.items())))
        self.assertEqual(self.graph['reviewed_parameters'],
                         handoff.reviewed_parameters(self.plan))
        self.assertEqual(self.graph['compiled_catalog_ids'],
                         dict(sorted(handoff.catalog_ids(self.plan).items())))
        for step in self.graph['steps']:
            with self.subTest(step=step['id']):
                self.assertEqual(sorted(step), ['id', 'kind', 'needs'])

    def test_every_platform_compiles_to_its_own_bound_scope(self):
        for platform in eligibility.PLATFORMS:
            with self.subTest(platform=platform):
                plan = support.platform_plan(platform)
                graph = handoff.build(plan, COMMIT)
                self.assertEqual(graph['scope']['platform'], platform)
                self.assertEqual(graph['scope'], plan.identity.scope)
                self.assertEqual(graph['operation_id'], plan.operation_id)
                self.assertEqual(graph['steps'], [step.to_dict() for step in handoff.sequence(plan)])
                if platform == 'vmware':
                    self.assertTrue(any(step['kind'] == 'vsphere_power' for step in graph['steps']))
                    self.assertFalse(any(step['id'] == 'workload-bootstrap' for step in graph['steps']))

    def test_the_review_projection_names_the_coverage(self):
        review = handoff.review(self.graph)
        self.assertEqual(review['format'], handoff.HANDOFF_FORMAT)
        self.assertEqual(review['steps'], len(handoff.STEPS))
        self.assertEqual(review['source_commit'], COMMIT)
        self.assertEqual(review['generation'], self.plan.generation)
        self.assertEqual(review['operation_id'], self.plan.operation_id)
        self.assertEqual(sorted(review['operations']), sorted(handoff.OPERATION_STEPS))
        self.assertTrue(review['limits'])

    def test_a_malformed_graph_is_refused_by_the_mirror(self):
        cases = [('format', 'hosting-delivery/3'),
                 ('source_commit', 'a' * 39),
                 ('operation_id', 'wsd:01'),
                 ('generation', 0),
                 ('generation', True)]
        for key, value in cases:
            with self.subTest(key=key, value=value):
                graph = {**self.graph, key: value}
                with self.assertRaises(ProvisioningError):
                    handoff.validate(graph)

    def test_a_missing_or_extra_key_is_refused_by_the_mirror(self):
        with self.assertRaises(ProvisioningError):
            handoff.validate({key: value for key, value in self.graph.items()
                              if key != 'steps'})
        with self.assertRaises(ProvisioningError):
            handoff.validate({**self.graph, 'extra': True})

    def test_a_broken_step_graph_is_refused_by_the_mirror(self):
        first = self.graph['steps'][0]
        cases = {'duplicate': [first, first],
                 'missing-dependency': [first, {'id': 'second', 'kind': 'acceptance',
                                                'needs': ['absent']}],
                 'unordered': [{'id': 'first', 'kind': 'acceptance', 'needs': ['second']},
                               {'id': 'second', 'kind': 'acceptance', 'needs': []}],
                 'no-dependency': [first, {'id': 'second', 'kind': 'acceptance', 'needs': []}],
                 'unknown-kind': [first, {'id': 'second', 'kind': 'invented',
                                          'needs': ['first']}]}
        for name, steps in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(ProvisioningError):
                    handoff.validate({**self.graph, 'steps': steps})

    def test_the_mirror_and_the_runner_agree_on_the_same_graphs(self):
        runner = _delivery_runner()
        cases = [self.graph,
                 {**self.graph, 'generation': 0},
                 {**self.graph, 'source_commit': 'z' * 40},
                 {**self.graph, 'operation_id': 'wsd:01'},
                 {**self.graph, 'scope': {**self.graph['scope'], 'platform': 'kvm'}},
                 {**self.graph, 'steps': self.graph['steps'][:1] + [
                     {'id': 'again', 'kind': 'acceptance', 'needs': []}]}]
        for index, graph in enumerate(cases):
            with self.subTest(case=index):
                mirror_refused = _refused(lambda: handoff.validate(graph))
                runner_refused = _refused(lambda: runner.validate(graph))
                self.assertEqual(mirror_refused, runner_refused,
                                 f'the mirror and the runner disagree on case {index}')


def _refused(call) -> bool:
    try:
        call()
    except Exception:
        return True
    return False


class GenerationBindingTest(unittest.TestCase):
    """A superseded or unfinished claim is refused before a graph exists."""

    def setUp(self):
        self.plan = support.reference_plan()

    def test_the_first_generation_of_an_identity_compiles(self):
        ledger = generation.InMemoryLedger()
        graph = handoff.build(self.plan, COMMIT, ledger)
        self.assertEqual(graph['generation'], 1)

    def test_the_same_generation_with_the_same_plan_is_a_replay(self):
        ledger = generation.InMemoryLedger([generation.record_for(self.plan)])
        graph = handoff.build(self.plan, COMMIT, ledger)
        self.assertEqual(graph, handoff.build(self.plan, COMMIT))

    def test_a_stale_generation_is_refused_before_the_graph_exists(self):
        newer = support.reference_plan(generation=2)
        ledger = generation.InMemoryLedger([generation.record_for(newer)])
        with self.assertRaises(ProvisioningError) as raised:
            handoff.build(self.plan, COMMIT, ledger)
        self.assertEqual(raised.exception.code, 'STALE_GENERATION')
        self.assertEqual(raised.exception.details['held'], 2)
        self.assertEqual(raised.exception.details['proposed'], 1)

    def test_changed_reviewed_state_at_the_same_generation_is_refused(self):
        ledger = generation.InMemoryLedger([generation.record_for(self.plan)])
        other = support.reference_plan(compile_environment=False)
        self.assertEqual(other.identity.key, self.plan.identity.key)
        self.assertNotEqual(other.digest, self.plan.digest)
        with self.assertRaises(ProvisioningError) as raised:
            handoff.build(other, COMMIT, ledger)
        self.assertEqual(raised.exception.code, 'GENERATION_CONFLICT')
        self.assertEqual(raised.exception.details['generation'], 1)

    def test_the_repository_passes_no_ledger_of_its_own(self):
        """The repository holds no authoritative record, so it compiles without one."""
        code, payload = _run('apply', REQUEST, '--approved-plan', 'f' * 64)
        self.assertEqual(code, 2)
        self.assertEqual(payload['errors'][0]['code'], 'ARTIFACT_INTEGRITY_FAILED')


class ApplyBoundaryTest(unittest.TestCase):
    """Every refusal precedes the handoff; nothing reaches a runner or an owner."""

    def _approved(self) -> tuple[dict, str, str]:
        code, plan = _run('plan', REQUEST)
        self.assertEqual(code, 0)
        directory = tempfile.mkdtemp()
        record = Path(directory) / 'approvals.json'
        record.write_text(json.dumps(
            {'format': 'hosting-plan-approval-set/1',
             'approvals': [{'plan_digest': plan['digest'], 'approved_by': 'reviewer-01',
                            'authority_ref': 'CHG-0001'}]}), encoding='utf-8')
        return plan, str(record), directory

    def test_the_handoff_is_compiled_and_execution_is_still_refused(self):
        plan, record, _ = self._approved()
        code, payload = _run('apply', REQUEST, '--approved-plan', plan['digest'],
                             '--approvals', record, '--source-commit', checkout_commit())
        self.assertEqual(code, 2)
        self.assertEqual(payload['status'], 'EXECUTION_REFUSED_HANDOFF_READY')
        self.assertEqual(payload['errors'][0]['code'], 'EXECUTION_REFUSED')
        self.assertFalse(payload['native_contact'])
        self.assertEqual(payload['delivery']['format'], 'hosting-delivery/2')
        self.assertEqual(payload['delivery']['source_commit'], checkout_commit())
        self.assertEqual(payload['delivery']['operation_id'], plan['operation_id'])
        self.assertEqual(payload['delivery']['generation'], plan['generation'])
        self.assertEqual(payload['delivery']['scope'],
                         {name: plan['identity'][name] for name in generation.SCOPE_KEYS})
        self.assertIsNone(_delivery_runner().validate(payload['delivery']))
        self.assertEqual(payload['delivery_review']['steps'], len(handoff.STEPS))

    def test_a_digest_mismatch_is_refused_before_the_handoff(self):
        code, payload = _run('apply', REQUEST, '--approved-plan', 'f' * 64)
        self.assertEqual(code, 2)
        self.assertEqual(payload['errors'][0]['code'], 'ARTIFACT_INTEGRITY_FAILED')
        self.assertNotIn('delivery', payload)

    def test_a_missing_digest_is_refused_before_the_handoff(self):
        code, payload = _run('apply', REQUEST)
        self.assertEqual(code, 2)
        self.assertEqual(payload['errors'][0]['code'], 'AUTHORITY_REQUIRED')
        self.assertNotIn('delivery', payload)

    def test_a_missing_approval_is_refused_before_the_handoff(self):
        code, plan = _run('plan', REQUEST)
        self.assertEqual(code, 0)
        code, payload = _run('apply', REQUEST, '--approved-plan', plan['digest'])
        self.assertEqual(code, 2)
        self.assertEqual(payload['errors'][0]['code'], 'AUTHORITY_REQUIRED')
        self.assertNotIn('delivery', payload)

    def _in_process(self, source: dict, requested: str | None = None) -> tuple[int, dict]:
        """Run the apply core against one exact repository source reading.

        The checkout's own state is not a property this suite controls, so the
        source binding is exercised against a declared reading instead of the
        ambient worktree.
        """
        context = service.build_context(support.REQUEST)
        plan = service.plan_for(context)
        approval = authority_module.Approval(plan_digest=plan.digest,
                                             approved_by='reviewer-01',
                                             authority_ref='CHG-0001')
        with mock.patch.object(apply_module.source_module.repository, 'source_commit',
                               return_value=source):
            return apply_module.run(context, approved_plan=plan.digest,
                                    approvals=(approval,), source_commit=requested)

    def test_a_checkout_that_is_not_clean_without_a_declared_commit_is_refused(self):
        source = {'status': 'FAILED_INTEGRITY_CHECK', 'commit': 'c' * 40,
                  'issues': [{'kind': 'WORKTREE_DIFFERS_FROM_HEAD', 'file': 'x'}]}
        code, payload = self._in_process(source)
        self.assertEqual(code, 2)
        self.assertEqual(payload['errors'][0]['code'], 'ARTIFACT_INTEGRITY_FAILED')
        self.assertEqual(payload['errors'][0]['details']['status'],
                         'FAILED_INTEGRITY_CHECK')
        self.assertIn('instruction', payload['errors'][0]['details'])
        self.assertNotIn('delivery', payload)

    def test_a_clean_checkout_without_a_declared_commit_binds_the_checkout(self):
        source = {'status': 'HASHES_MATCH', 'commit': 'c' * 40, 'issues': []}
        code, payload = self._in_process(source)
        self.assertEqual(code, 2)
        self.assertEqual(payload['status'], apply_module.HANDOFF_STATUS)
        self.assertEqual(payload['delivery']['source_commit'], 'c' * 40)
        self.assertEqual(payload['source_checkout']['status'], 'HASHES_MATCH')

    def test_a_declared_commit_that_is_not_the_checkout_is_refused(self):
        plan, record, _ = self._approved()
        code, payload = _run('apply', REQUEST, '--approved-plan', plan['digest'],
                             '--approvals', record, '--source-commit', 'b' * 40)
        self.assertEqual(code, 2)
        self.assertEqual(payload['errors'][0]['code'], 'ARTIFACT_INTEGRITY_FAILED')
        self.assertEqual(payload['errors'][0]['details']['source_commit'], 'b' * 40)
        self.assertNotIn('delivery', payload)

    def test_a_declared_commit_must_be_the_declared_grammar(self):
        plan, record, _ = self._approved()
        code, payload = _run('apply', REQUEST, '--approved-plan', plan['digest'],
                             '--approvals', record, '--source-commit', 'not-a-commit')
        self.assertEqual(code, 2)
        self.assertEqual(payload['errors'][0]['code'], 'SCHEMA_VALIDATION_FAILED')
        self.assertNotIn('delivery', payload)


class NoBypassTest(unittest.TestCase):
    """Nothing here became a second runner, a second journal or an execution path."""

    PACKAGE = support.ROOT / 'provisioner'

    def test_the_compiler_reaches_no_repository_tooling(self):
        tree = ast.parse((self.PACKAGE / 'execution' / 'handoff.py').read_text(
            encoding='utf-8'))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        for name in sorted(imported):
            with self.subTest(module=name):
                self.assertFalse(name.startswith(('tools', 'scripts')),
                                 'only provisioner/repository.py may reach the tools')

    def test_only_the_repository_module_reaches_the_tools(self):
        for path in sorted(self.PACKAGE.rglob('*.py')):
            if path == self.PACKAGE / 'repository.py':
                continue
            text = path.read_text(encoding='utf-8')
            with self.subTest(module=str(path.relative_to(self.PACKAGE))):
                self.assertNotIn('import tools', text)
                self.assertNotIn('import scripts', text)

    def test_no_module_under_provisioner_owns_a_journal(self):
        for path in sorted(self.PACKAGE.rglob('*.py')):
            text = path.read_text(encoding='utf-8')
            with self.subTest(module=str(path.relative_to(self.PACKAGE))):
                self.assertNotIn('execution_journal', text)
                self.assertNotIn('flock', text)

    def test_the_repository_declares_no_execution_authority(self):
        self.assertEqual(authority_module.EXECUTION_AUTHORITY, 'EXTERNAL_ONLY')
        self.assertEqual(authority_module.to_dict()['authority'], 'EXTERNAL_ONLY')

    def test_the_runner_requires_an_explicit_execution_opt_in(self):
        source = DELIVERY_RUNNER.read_text(encoding='utf-8')
        self.assertIn('execute=False', source)
        self.assertIn('require(execute', source)

    def test_the_runner_still_owns_the_stale_generation_rule(self):
        """The repository binds the generation; the runner refuses a superseded one."""
        source = DELIVERY_RUNNER.read_text(encoding='utf-8')
        self.assertIn("plan['generation']>active['generation']", source)
        self.assertIn('Another delivery owns the held scope', source)

    def test_the_runner_still_owns_the_receipt_and_resume_model(self):
        source = DELIVERY_RUNNER.read_text(encoding='utf-8')
        for term in ('receipts', 'STEP_STARTED', 'resume_only', 'renewals'):
            with self.subTest(term=term):
                self.assertIn(term, source)

    def test_every_command_still_routes_through_the_shared_service(self):
        from tests.provisioning.unit import test_architecture as architecture
        for path in sorted((self.PACKAGE / 'cli').glob('*.py')):
            if path.name in architecture.TRANSPORT_MODULES | architecture.API_ONLY_COMMANDS:
                continue
            with self.subTest(command=path.name):
                self.assertIn('execution.service',
                              path.read_text(encoding='utf-8'))

    def test_operator_command_cannot_bypass_the_control_api(self):
        from tests.provisioning.unit import test_architecture as architecture
        for name in sorted(architecture.API_ONLY_COMMANDS):
            path = self.PACKAGE / 'cli' / name
            self.assertTrue(path.is_file())
            with self.subTest(module=name):
                self.assertEqual(architecture._api_client_import_violations(
                    path, 'provisioner.cli.' + path.stem), [])
        self.assertIn('httpx', architecture._absolute_imports(
            self.PACKAGE / 'cli' / 'operator.py'))


if __name__ == '__main__':
    unittest.main()
