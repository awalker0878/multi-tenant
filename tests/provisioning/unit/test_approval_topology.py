"""The reviewed delivery topology: one canonical source, bound into the approval.

F02 of `docs/deepseek-refactor-post-audit-corrective-action.md`. The manifest used to
bind a digest of the owner-operation *summary* (`provisioner.execution.delivery.
graph_digest`) while the executable topology lived in a separate declaration
(`provisioner.execution.handoff.STEPS`) that `hosting apply` built only *after* the
approval digest had already been checked. A change to a step dependency, a step kind,
the operation-to-step mapping or a reviewed step parameter could therefore change what
would execute without changing the identity an external approval cites.

What is proved here is the corrected invariant: the reviewed topology is one canonical
declaration in `handoff.py`, its digest is bound into the reviewed manifest, and the
execution-time `hosting-delivery/1` graph must project back onto exactly that approved
topology or the handoff is refused.
"""
from __future__ import annotations

import unittest
from dataclasses import replace
from unittest import mock

from provisioner.domain import errors
from provisioner.domain.errors import ProvisioningError
from provisioner.domain.request import digest as canonical_digest
from provisioner.execution import authority as authority_module
from provisioner.execution import delivery
from provisioner.execution import handoff
from provisioner.execution import manifest as plan_manifest
from provisioner.execution import service

from tests.provisioning import support

COMMIT = 'a' * 40
CLEAN_CHECKOUT = {'status': 'HASHES_MATCH', 'commit': 'c' * 40, 'issues': []}


def _renamed(step_id: str, **changes) -> tuple:
    """The reviewed sequence with exactly one step replaced."""
    return tuple(replace(step, **changes) if step.id == step_id else step
                 for step in handoff.STEPS)


class TopologyIntentTest(unittest.TestCase):
    """One canonical reviewed topology, and the manifest binds its identity."""

    def setUp(self):
        self.plan = support.reference_plan()

    def test_manifest_binds_ordered_handoff_steps(self):
        intent = handoff.topology_intent(self.plan)
        self.assertEqual(intent['format'], handoff.TOPOLOGY_FORMAT)
        self.assertEqual([step['id'] for step in intent['steps']],
                         [step.id for step in handoff.STEPS])
        self.assertEqual([step['kind'] for step in intent['steps']],
                         [step.kind for step in handoff.STEPS])
        self.assertEqual([step['needs'] for step in intent['steps']],
                         [list(step.needs) for step in handoff.STEPS])
        self.assertEqual(self.plan.manifest['delivery']['topology_digest'],
                         handoff.topology_digest(self.plan))
        self.assertEqual(handoff.topology_digest(self.plan), canonical_digest(intent))

    def test_the_manifest_binds_no_parallel_delivery_identity(self):
        """The owner-operation summary digest must not survive as a second identity."""
        self.assertFalse(hasattr(delivery, 'graph_digest'))
        self.assertFalse(hasattr(plan_manifest, 'DELIVERY_KEYS'))
        self.assertFalse(hasattr(plan_manifest, 'DELIVERY_OPERATION_KEYS'))

    def test_manifest_binds_handoff_dependencies(self):
        """A changed step dependency must change the approved identity."""
        changed = _renamed('workload-plan', needs=('admission',))
        self.assertNotEqual(changed, handoff.STEPS)
        with mock.patch.object(handoff, 'STEPS', changed):
            rebuilt = plan_manifest.build(self.plan)
        self.assertNotEqual(rebuilt['delivery']['topology_digest'],
                            self.plan.manifest['delivery']['topology_digest'])
        self.assertNotEqual(canonical_digest(rebuilt), self.plan.manifest_digest)
        # The topology is the only delivery term, so nothing else may move.
        self.assertEqual({key: value for key, value in rebuilt.items() if key != 'delivery'},
                         {key: value for key, value in self.plan.manifest.items()
                          if key != 'delivery'})

    def test_manifest_binds_handoff_step_kinds(self):
        """A changed step kind must change the approved identity."""
        changed = _renamed('capacity-reservation', kind='ipam')
        self.assertNotEqual(changed, handoff.STEPS)
        with mock.patch.object(handoff, 'STEPS', changed):
            rebuilt = plan_manifest.build(self.plan)
        self.assertNotEqual(rebuilt['delivery']['topology_digest'],
                            self.plan.manifest['delivery']['topology_digest'])
        self.assertNotEqual(canonical_digest(rebuilt), self.plan.manifest_digest)

    def test_manifest_binds_operation_step_mapping(self):
        """A changed operation-to-step mapping must change the approved identity."""
        self.assertEqual(handoff.topology_intent(self.plan)['operationBindings']
                         ['native-qualification'], 'pre-activation-campaign')
        changed = {**handoff.OPERATION_STEPS, 'native-qualification': 'activation'}
        with mock.patch.object(handoff, 'OPERATION_STEPS', changed):
            rebuilt = plan_manifest.build(self.plan)
        self.assertNotEqual(rebuilt['delivery']['topology_digest'],
                            self.plan.manifest['delivery']['topology_digest'])
        self.assertNotEqual(canonical_digest(rebuilt), self.plan.manifest_digest)

    def test_manifest_binds_reviewed_step_parameters(self):
        """A changed reviewed parameter value must change the approved identity."""
        cases = (('edge-policy', 'mode', 'active'),
                 ('capacity-reservation', 'action', 'confirm'))
        for step_id, name, value in cases:
            with self.subTest(step=step_id, parameter=name):
                self.assertNotEqual(handoff.REVIEWED_PARAMETERS[step_id][name], value)
                changed = {**handoff.REVIEWED_PARAMETERS,
                           step_id: {**handoff.REVIEWED_PARAMETERS[step_id], name: value}}
                with mock.patch.object(handoff, 'REVIEWED_PARAMETERS', changed):
                    rebuilt = plan_manifest.build(self.plan)
                self.assertNotEqual(rebuilt['delivery']['topology_digest'],
                                    self.plan.manifest['delivery']['topology_digest'])
                self.assertNotEqual(canonical_digest(rebuilt), self.plan.manifest_digest)

    def test_the_topology_intent_carries_no_execution_time_binding(self):
        """A commit, an operation id or a generation is never an approved decision."""
        intent = handoff.topology_intent(self.plan)
        self.assertEqual(sorted(intent), sorted(handoff.TOPOLOGY_KEYS))
        for derived in ('plan_digest', 'operation_id', 'source_commit', 'generation',
                        'identity', 'scope'):
            with self.subTest(derived=derived):
                self.assertNotIn(derived, intent)
        self.assertNotEqual(self.plan.manifest['delivery']['topology_digest'],
                            self.plan.operation_id)


class ApprovedTopologyProjectionTest(unittest.TestCase):
    """The graph an operator can hand to the runner is the approved topology."""

    def test_the_execution_graph_matches_the_approved_topology(self):
        for name in support.REFERENCE_REQUESTS:
            plan = support.reference_plan(name)
            runtime = handoff.build(plan, COMMIT)
            with self.subTest(request=name):
                self.assertEqual(canonical_digest(handoff.approval_projection(plan, runtime)),
                                 plan.manifest['delivery']['topology_digest'])

    def test_every_platform_projects_onto_its_approved_topology(self):
        for platform in support.PLATFORMS:
            plan = support.platform_plan(platform)
            runtime = handoff.build(plan, COMMIT)
            with self.subTest(platform=platform):
                self.assertEqual(canonical_digest(handoff.approval_projection(plan, runtime)),
                                 plan.manifest['delivery']['topology_digest'])

    def test_the_projection_compares_the_complete_topology_not_a_summary(self):
        plan = support.reference_plan()
        runtime = handoff.build(plan, COMMIT)
        baseline = handoff.approval_projection(plan, runtime)
        self.assertEqual(sorted(baseline), sorted(handoff.TOPOLOGY_KEYS))
        self.assertEqual(baseline['steps'], runtime['steps'])
        for index, mutation in ((0, {'kind': 'capacity'}),
                                        (1, {'needs': []}),
                                (2, {'id': 'renamed'})):
            steps = [dict(step) for step in runtime['steps']]
            steps[index] = {**steps[index], **mutation}
            with self.subTest(mutation=mutation):
                self.assertNotEqual(
                    canonical_digest(handoff.approval_projection(
                        plan, {**runtime, 'steps': steps})),
                    plan.manifest['delivery']['topology_digest'])


class TopologyDriftTest(unittest.TestCase):
    """A topology that is not the approved one is refused, never executed."""

    def setUp(self):
        self.plan = support.reference_plan()

    def test_the_handoff_refuses_a_topology_the_manifest_does_not_bind(self):
        changed = _renamed('workload-plan', needs=('admission',))
        with mock.patch.object(handoff, 'STEPS', changed):
            with self.assertRaises(ProvisioningError) as raised:
                handoff.build(self.plan, COMMIT)
        self.assertEqual(raised.exception.code, 'APPROVAL_TOPOLOGY_MISMATCH')
        self.assertEqual(errors.CODES['APPROVAL_TOPOLOGY_MISMATCH'][0], 'execution')
        self.assertEqual(raised.exception.details['approved_topology_digest'],
                         self.plan.manifest['delivery']['topology_digest'])
        self.assertNotEqual(raised.exception.details['compiled_topology_digest'],
                            raised.exception.details['approved_topology_digest'])

    def test_a_plan_whose_manifest_binds_this_topology_still_compiles(self):
        """The refusal is a mismatch, not a blanket refusal to compile."""
        changed = _renamed('workload-plan', needs=('admission',))
        with mock.patch.object(handoff, 'STEPS', changed):
            rebound = replace(self.plan, manifest=plan_manifest.build(self.plan))
            self.assertEqual(handoff.build(rebound, COMMIT)['steps'],
                             [step.to_dict() for step in changed])

    def test_apply_refuses_when_runtime_topology_differs_from_approved_topology(self):
        from provisioner.cli import apply as apply_module
        context = service.build_context(support.REQUEST)
        plan = service.plan_for(context)
        approval = authority_module.Approval(plan_digest=plan.digest,
                                             approved_by='reviewer-01',
                                             authority_ref='CHG-0001')
        changed = _renamed('workload-plan', needs=('admission',))
        with mock.patch.object(apply_module, 'plan_for', return_value=plan), \
                mock.patch.object(apply_module.repository, 'source_commit',
                                  return_value=CLEAN_CHECKOUT), \
                mock.patch.object(handoff, 'STEPS', changed):
            code, payload = apply_module.run(context, approved_plan=plan.digest,
                                             approvals=(approval,),
                                             source_commit=CLEAN_CHECKOUT['commit'])
        self.assertEqual(code, 2)
        self.assertEqual(payload['errors'][0]['code'], 'APPROVAL_TOPOLOGY_MISMATCH')
        self.assertNotIn('delivery', payload)
        self.assertFalse(payload['native_contact'])