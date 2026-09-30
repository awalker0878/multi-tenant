"""Each metadata read must remain a value snapshot across live callbacks."""
from dataclasses import replace
from datetime import timedelta
import unittest

from provisioner.controlplane.discovery.freshness import DiscoveryFreshnessService, FreshnessChanged
from provisioner.controlplane.discovery.persistence import DiscoveryRepository, StoredGeneration
from provisioner.controlplane.persistence.store import TenantContext
from tests.provisioning.api.test_http import NOW, SOURCE_SCOPE

CTX = TenantContext(SOURCE_SCOPE.organization_id, SOURCE_SCOPE.tenant_id)


def row():
    return StoredGeneration('env-01', 7, 'campaign-01', SOURCE_SCOPE, 'a'*64,
                            'b'*64, NOW-timedelta(seconds=60), 'COMPLETE', (), (), 3)


class MetadataRows(DiscoveryRepository):
    def __init__(self, values):
        self.values, self.reads, self.after_read = values, 0, None

    def latest_generation(self, *args):
        value = self.values[min(self.reads, len(self.values)-1)]
        self.reads += 1
        if self.after_read is not None:
            self.after_read(self.reads)
        return value


class FreshnessSnapshotTests(unittest.TestCase):
    def test_mutation_between_reads_cannot_make_a_shared_row_compare_equal_to_itself(self):
        original = row()
        repository = MetadataRows((original,))
        calls = 0
        def authorize(scope, at):
            nonlocal calls
            calls += 1
            if calls == 2:
                object.__setattr__(original, 'result_digest', 'c'*64)
        with self.assertRaises(FreshnessChanged):
            DiscoveryFreshnessService(repository, clock=lambda: NOW).inspect(
                CTX, SOURCE_SCOPE, 'env-01', authorize=authorize)
        self.assertEqual(repository.reads, 2)

    def test_second_read_snapshot_does_not_change_during_the_final_authorizer(self):
        first, second = row(), row()
        repository = MetadataRows((first, second))
        calls = 0
        def authorize(scope, at):
            nonlocal calls
            calls += 1
            if calls == 3:
                object.__setattr__(second, 'generation', 8)
        result = DiscoveryFreshnessService(repository, clock=lambda: NOW).inspect(
            CTX, SOURCE_SCOPE, 'env-01', authorize=authorize)
        self.assertEqual(result['observation']['generation'], 7)
        self.assertEqual(second.generation, 8)
        self.assertFalse(result['executionAuthorized'])

    def test_final_clock_callback_cannot_substitute_the_validated_capture(self):
        original = row()
        repository = MetadataRows((original,))
        calls = 0
        def clock():
            nonlocal calls
            calls += 1
            if calls == 4:
                object.__setattr__(original, 'captured_at', NOW-timedelta(days=2))
            return NOW
        result = DiscoveryFreshnessService(repository, clock=clock).inspect(
            CTX, SOURCE_SCOPE, 'env-01', authorize=lambda *args: None)
        self.assertEqual(result['ageMicroseconds'], 60000000)
        self.assertEqual(result['freshness'], 'FRESH')

    def test_revocation_still_precedes_the_changed_generation_response(self):
        repository = MetadataRows((row(), replace(row(), generation=8)))
        calls = 0
        def authorize(scope, at):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise PermissionError('Revoked')
        with self.assertRaises(PermissionError):
            DiscoveryFreshnessService(repository, clock=lambda: NOW).inspect(
                CTX, SOURCE_SCOPE, 'env-01', authorize=authorize)
        self.assertEqual(repository.reads, 2)
