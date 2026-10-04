"""Read-only commissioning maps; synthetic bytes never establish native proof."""
from copy import deepcopy
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from provisioner.controlplane.workflow.installed_identity import InstalledApplicationIdentity
from provisioner.qualification.commissioning import build_dossier
from tests.provisioning.operations.campaign_fixtures import AS_OF, fixture


class CommissioningTests(unittest.TestCase):
    def setUp(self):
        self.spec, self.bundle, _ = fixture()
        installation = patch.object(InstalledApplicationIdentity, 'require_current',
            return_value=(self.spec.code_revision, self.spec.installed_artifact_sha256))
        self.current = installation.start()
        self.addCleanup(installation.stop)
        self.installed = InstalledApplicationIdentity(Path('/synthetic-not-installed.json'),
            Path('/synthetic-not-installed'), '0' * 64, self.spec.code_revision,
            self.spec.installed_artifact_sha256)

    def build(self, *, specifications=None, bundle=None):
        return build_dossier(installed_identity=self.installed,
            specifications=[self.spec] if specifications is None else specifications,
            bundle=self.bundle if bundle is None else bundle, as_of=AS_OF)

    def test_complete_metadata_retains_original_evidence_and_all_directed_holds(self):
        result = self.build()
        self.assertEqual(len(result['routeRows']), 216)
        self.assertEqual(result['selectedCampaigns'][0]['metadataAssessment']['status'],
                         'CURRENT_NATIVE_EVIDENCE_SELECTED')
        self.assertTrue(all(row['state'] == 'COMMISSIONING_HELD' and
                            row['originalNativeProofVerified'] is False for row in result['routeRows']))
        selected = result['selectedCampaigns'][0]
        self.assertEqual(len(selected['endpoints']), 2)
        self.assertEqual(selected['endpoints'][0]['exactTuple']['productTupleId'], 'source-tuple')
        self.assertEqual(len(selected['endpoints'][0]['originalEvidenceRequired']), len(self.spec.assertions()))
        rows = {row['routeId']: row for row in result['routeRows']}
        cold = rows['vmware-nsx:openstack:COLD_WHOLE_VM:ENCRYPTED_VTPM']
        self.assertIsNone(cold['implementedDriver'])
        self.assertIn('ENCRYPTED_OR_VTPM_DEVICE_REJECTED', cold['requiredAssertions'])
        reverse = rows['openstack:vmware-nsx:APPLICATION_REBUILD_RESTORE:linux-ubuntu-2404']
        self.assertIsNone(reverse['implementedDriver'])
        self.assertFalse(result['nativeContact'])
        self.assertFalse(result['jobDispatched'])
        self.assertFalse(result['activeIndexesChanged'])
        self.assertFalse(result['qualificationIssued'])
        self.assertEqual(len(result['minimumOperatingPrerequisites']), 9)
        self.assertEqual(len(result['pilotScenarios']), 6)
        self.assertEqual(len(result['explicitWaveAssertions']), 4)
        self.assertEqual(len(result['databaseMethodPrerequisites']['requiredAssertions']), 7)
        self.assertEqual(result['databaseMethodPrerequisites']['requiredEndpoints'], ['source', 'destination'])
        restore = next(item for item in result['actionCampaignRequirements'] if item['operationKind'] == 'RESTORE_DATA')
        self.assertEqual(restore['databaseDriverEndpoint'], 'both')
        self.assertTrue(any('oldest due job' in stage.get('dispatchBoundary', '')
                            for stage in result['acquisitionStages']))

    def test_empty_native_indexes_preserve_missing_tuple_slots_without_invented_campaigns(self):
        bundle = deepcopy(self.bundle)
        for index in bundle.values():
            index['records'] = []
        result = self.build(specifications=[], bundle=bundle)
        self.assertEqual(result['exactNativeTuples'], [])
        self.assertEqual(result['selectedCampaigns'], [])
        self.assertTrue(all(not row['sourceTupleIds'] and not row['destinationTupleIds']
                            for row in result['routeRows']))
        self.assertTrue(all(row['metadataState'] == 'UNSUPPORTED_HELD' for row in result['routeRows']))

    def test_foreign_final_bytes_duplicate_specs_and_installation_drift_are_not_mapped(self):
        for changed in (replace(self.spec, code_revision='d' * 40),
                        replace(self.spec, installed_artifact_sha256='e' * 64)):
            with self.subTest(spec=changed), self.assertRaises(ValueError):
                self.build(specifications=[changed])
        with self.assertRaises(ValueError):
            self.build(specifications=[self.spec, self.spec])
        self.current.side_effect = ValueError('Actual accepted installation changed')
        with self.assertRaises(ValueError):
            self.build()
        with self.assertRaises(ValueError):
            build_dossier(installed_identity=SimpleNamespace(require_current=lambda: True),
                bundle=self.bundle, specifications=[self.spec], as_of=AS_OF)

    def test_real_cli_without_commissioned_installation_remains_read_only_held(self):
        environment = dict(os.environ)
        environment.pop('HOSTING_APPLICATION_RUNTIME_CONFIG', None)
        environment.pop('HOSTING_APPLICATION_SOURCE_ROOT', None)
        result = subprocess.run([sys.executable, '-m', 'provisioner.qualification.commissioning'],
            env=environment, capture_output=True, check=False, timeout=30)
        self.assertEqual(result.returncode, 2)
        value = json.loads(result.stdout)
        self.assertEqual(value['status'], 'FINAL_CODE_COMMISSIONING_DOSSIER_HELD')
        self.assertFalse(value['nativeContact'])
        self.assertFalse(value['jobDispatched'])
        self.assertFalse(value['mutationAuthorized'])


if __name__ == '__main__':
    unittest.main()
