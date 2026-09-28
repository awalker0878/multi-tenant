"""A brownfield review proposal must never accept missing or owned resources."""
from __future__ import annotations

import unittest
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.discovery.adoption import (
    AdoptionSelection, NativeOwner, WorkloadReview,
    propose_brownfield_adoption,
)
from provisioner.controlplane.discovery.model import (
    DiscoveryFact, DiscoveryObject, DiscoveryResult, NativeIdentity,
)
from provisioner.controlplane.persistence.store import canonical_record_digest
from tests.provisioning.controlplane.test_discovery_model import START
from tests.provisioning.schema.test_enterprise_records import workload


SCOPE = PlanScope('org-01', 'tenant-01', 'cluster-east', 'wsd-01',
                  'vcenter-01', 'dc1', 'vmware')


def identity(binding):
    return NativeIdentity(binding['endpointId'], binding['nativeScopeId'],
                          binding['platformFamily'], binding['resourceKind'],
                          binding['nativeId'])


def scenario():
    record = workload()
    selections = []
    objects = []

    def add(machine_id, component_id, binding, facts):
        native = identity(binding)
        selections.append(AdoptionSelection(machine_id, component_id, native))
        objects.append(DiscoveryObject(native, tuple(
            DiscoveryFact.known(name, value) for name, value in facts.items())))

    for machine in record['spec']['machines']:
        machine_id = machine['machineId']
        add(machine_id, machine_id, machine['bindings'][0]['binding'],
            {'cpuCount': 4, 'memoryMiB': 8192, 'firmware': 'uefi'})
        for disk in machine['disks']:
            add(machine_id, disk['diskId'], disk['bindings'][0]['binding'],
                {'sizeBytes': 1000000, 'format': 'vmdk'})
        for nic in machine['nics']:
            add(machine_id, nic['nicId'], nic['bindings'][0]['binding'],
                {'network': 'tenant-net'})
    for dataset in record['spec']['datasets']:
        dataset['sizeBytes'] = {'state': 'KNOWN', 'value': 1000000}
        dataset['unknownFields'] = []
        add(dataset['machineId'], dataset['datasetId'],
            dataset['sourceBindings'][0], {'sizeBytes': 1000000})
    result = DiscoveryResult('campaign-01', 'b' * 64, SCOPE,
                             START + timedelta(minutes=2), 'COMPLETE',
                             tuple(objects), (), ())
    review = WorkloadReview('org-01', 'tenant-01', 'wsd-01',
                            'workload-01', 1, canonical_record_digest(record),
                            SCOPE,
                            'verified-owner-01', START,
                            START + timedelta(minutes=30))
    return record, review, tuple(selections), result


def propose(record, review, selections, result, *, owner_lookup=lambda _native: None,
            current_digest=None, checked_at=None):
    return propose_brownfield_adoption(
        result, record, review, selections,
        current_result_digest=result.digest if current_digest is None
        else current_digest,
        checked_at=checked_at or START + timedelta(minutes=3),
        max_observation_age=timedelta(minutes=15),
        owner_lookup=owner_lookup)


class BrownfieldAdoptionTests(unittest.TestCase):
    def test_complete_unowned_review_produces_immutable_no_change_proposal(self):
        record, review, selections, result = scenario()
        queried = []
        proposal = propose(record, review, selections, result,
                           owner_lookup=lambda native: queried.append(native.key()))
        self.assertEqual(proposal.status, 'REVIEWABLE')
        self.assertEqual(proposal.action, 'NO_CHANGE_REVIEW')
        self.assertEqual(proposal.holds, ())
        self.assertEqual(len(queried), len(selections))
        self.assertEqual(proposal.discovery_digest, result.digest)
        self.assertEqual(len(proposal.digest), 64)
        with self.assertRaises(FrozenInstanceError):
            proposal.action = 'IMPORT'
        self.assertEqual(proposal.digest, propose(record, review,
                                                  tuple(reversed(selections)),
                                                  result).digest)

    def test_ownership_conflicts_duplicate_mapping_and_lookup_failure_hold(self):
        record, review, selections, result = scenario()
        owned = selections[0].native
        proposal = propose(record, review, selections, result,
                           owner_lookup=lambda native: NativeOwner(
                               'org-01', 'tenant-01', 'wsd-01', 'other-workload')
                           if native == owned else None)
        self.assertIn('NATIVE_OWNERSHIP_CONFLICT',
                      {hold.code for hold in proposal.holds})
        duplicate = propose(record, review, selections + (selections[0],), result)
        self.assertIn('DUPLICATE_SELECTION',
                      {hold.code for hold in duplicate.holds})
        def unavailable(_identity):
            raise RuntimeError('database unavailable')
        lookup = propose(record, review, selections, result,
                         owner_lookup=unavailable)
        self.assertIn('OWNERSHIP_LOOKUP_UNAVAILABLE',
                      {hold.code for hold in lookup.holds})

    def test_cross_scope_missing_and_unknown_required_fact_hold(self):
        record, review, selections, result = scenario()
        foreign = replace(selections[0], native=replace(
            selections[0].native, native_scope_id='other-project'))
        queried = []
        cross = propose(record, review, (foreign,) + selections[1:], result,
                        owner_lookup=lambda native: queried.append(native.key()))
        self.assertIn('CROSS_SCOPE_BINDING', {hold.code for hold in cross.holds})
        self.assertNotIn(foreign.native.key(), queried)
        missing = propose(record, review, selections[:-1], result)
        self.assertIn('COMPONENT_NOT_SELECTED',
                      {hold.code for hold in missing.holds})
        vm = result.objects[0]
        unknown_vm = replace(vm, facts=(
            DiscoveryFact.unknown('cpuCount', 'NOT_RETURNED'),)
        )
        # An unknown fact makes the discovery generation partial; it cannot
        # become complete by labeling the result COMPLETE.
        partial = replace(result, completeness='PARTIAL',
                          objects=(unknown_vm,) + result.objects[1:])
        unknown = propose(record, review, selections, partial)
        self.assertIn('REQUIRED_FACT_UNKNOWN',
                      {hold.code for hold in unknown.holds})
        self.assertIn('DISCOVERY_INCOMPLETE',
                      {hold.code for hold in unknown.holds})
        changed_vm = replace(vm, facts=(
            DiscoveryFact.known('cpuCount', 8),
            DiscoveryFact.known('memoryMiB', 8192),
            DiscoveryFact.known('firmware', 'uefi')))
        mismatch = propose(record, review, selections, replace(
            result, objects=(changed_vm,) + result.objects[1:]))
        self.assertIn('REVIEWED_FACT_MISMATCH',
                      {hold.code for hold in mismatch.holds})

    def test_stale_not_latest_or_wrong_wsd_never_reviewable(self):
        record, review, selections, result = scenario()
        stale = propose(record, review, selections, result,
                        checked_at=START + timedelta(minutes=20))
        self.assertIn('DISCOVERY_STALE', {hold.code for hold in stale.holds})
        current = propose(record, review, selections, result,
                          current_digest='c' * 64)
        self.assertIn('DISCOVERY_NOT_CURRENT',
                      {hold.code for hold in current.holds})
        wrong = replace(result, scope=replace(SCOPE,
                                             security_domain_id='wsd-02'))
        cross = propose(record, review, selections, wrong)
        self.assertIn('CROSS_SCOPE_DISCOVERY',
                      {hold.code for hold in cross.holds})
        with self.assertRaises(ValueError):
            propose(deepcopy(record), replace(review,
                                              workload_digest='d' * 64),
                    selections, result)


if __name__ == '__main__':
    unittest.main()
