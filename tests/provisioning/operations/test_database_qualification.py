"""Synthetic metadata; exact database method proof remains separate from actions.

The test isolates qualification from the declared implementation map so it can
exercise this boundary while the complete database driver is separately held.
It neither contacts an engine nor issues a qualification or credential.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from provisioner.controlplane.authority.service import AuthorityDenied
from provisioner.qualification.action_gate import (
    SelectedQualificationGate, action_variant, bundle_digest,
    database_method_assertions, database_method_variant)
from tests.provisioning.operations.campaign_fixtures import fixture
from tests.provisioning.operations.test_action_gate import Cursor


class DatabaseQualificationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        _, self.bundle, self.selection = fixture(action='RESTORE_DATA')
        self.selection.update(driver='openstack-linux-application-database/1',
                              applicationDatabaseSelectionDigest='e' * 64)
        self.admitted = SimpleNamespace(organization_id='org-fixture', tenant_id='tenant-fixture')
        declared = patch('provisioner.qualification.action_gate.require_implemented_action_selection')
        declared.start(); self.addCleanup(declared.stop)
        for campaign, dossier in zip(self.bundle['campaign']['records'], self.bundle['qualification']['records']):
            for attempt in campaign['attempts']:
                if attempt['assertion_id'] == 'ACTION_RESTORE_DATA':
                    attempt['variant_ref'] = action_variant(self.selection, 'RESTORE_DATA')
            label = 'source' if dossier is self.bundle['qualification']['records'][0] else 'destination'
            for assertion, kind in database_method_assertions().items():
                ref = 'controlled-database-evidence:' + label + ':' + assertion
                sha = hashlib.sha256(ref.encode()).hexdigest()
                attempt = deepcopy(campaign['attempts'][-1])
                attempt.update(attempt_id=label + '-' + assertion, assertion_id=assertion,
                    observation_class=kind, variant_ref=database_method_variant(self.selection),
                    evidence_ref=ref, artifact_sha256=sha,
                    positive_control_attempt_ref=label + '-DISCOVERY_INDEPENDENT'
                        if kind == 'NEGATIVE_CONTROL' else None)
                campaign['required_assertions'].append(assertion)
                campaign['attempts'].append(attempt)
                dossier['evidence'].append(dict(ref=ref, sha256=sha,
                    observed_at=attempt['observed_at'], expires_at=attempt['fresh_until'], test_set='CT-FIXTURE'))
        self.gate = SelectedQualificationGate(**{
            'qualification_path': self.root / 'qualification.json', 'provenance_path': self.root / 'provenance.json',
            'campaign_path': self.root / 'campaign.json', 'target_selection_path': self.root / 'targetSelection.json',
            'capacity_path': self.root / 'capacity.json'})
        self.retain()

    def retain(self):
        dossier = self.bundle['qualification']['records'][1]
        self.bundle['capacity']['records'][0]['qualification_binding']['qualification_record_sha256'] = hashlib.sha256(
            json.dumps(dossier, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
        self.selection['qualificationDigest'] = bundle_digest(self.bundle)
        for key, value in self.bundle.items():
            file = self.root / (key + '.json'); file.write_text(json.dumps(value)); file.chmod(0o600)

    def require(self):
        self.gate.require_action(Cursor(), self.admitted, self.selection, 'RESTORE_DATA')

    def test_both_current_action_dossiers_and_all_exact_descriptor_method_proofs_required(self):
        self.require()
        self.assertEqual(len(database_method_assertions()), 7)
        self.assertNotEqual(database_method_variant(self.selection), action_variant(self.selection, 'RESTORE_DATA'))

    def test_destination_action_cannot_grant_source_publication_slot_effects(self):
        source = self.bundle['campaign']['records'][0]
        refs = {attempt['evidence_ref'] for attempt in source['attempts'] if attempt['assertion_id'] == 'ACTION_RESTORE_DATA'}
        source['attempts'] = [attempt for attempt in source['attempts'] if attempt['assertion_id'] != 'ACTION_RESTORE_DATA']
        source['required_assertions'].remove('ACTION_RESTORE_DATA')
        dossier = self.bundle['qualification']['records'][0]
        dossier['evidence'] = [item for item in dossier['evidence'] if item['ref'] not in refs]
        self.retain()
        with self.assertRaisesRegex(AuthorityDenied, 'direction/action/profile/code'): self.require()

    def test_source_capture_and_snapshot_capabilities_are_separately_required(self):
        self.bundle['qualification']['records'][0]['qualified_capabilities'].remove('capture_export')
        self.retain()
        with self.assertRaisesRegex(AuthorityDenied, 'action capabilities'): self.require()

    def test_generic_action_or_rebuild_variant_cannot_substitute_database_method_proof(self):
        for campaign in self.bundle['campaign']['records']:
            for attempt in campaign['attempts']:
                if attempt['assertion_id'] in database_method_assertions():
                    attempt['variant_ref'] = action_variant(self.selection, 'RESTORE_DATA')
        self.retain()
        with self.assertRaisesRegex(AuthorityDenied, 'database method/descriptor'): self.require()

    def test_changed_descriptor_wrong_observation_class_or_missing_method_assertion_holds(self):
        self.selection['applicationDatabaseSelectionDigest'] = 'f' * 64
        # Rebind only the generic action. The old method proof must still hold.
        for campaign in self.bundle['campaign']['records']:
            for attempt in campaign['attempts']:
                if attempt['assertion_id'] == 'ACTION_RESTORE_DATA':
                    attempt['variant_ref'] = action_variant(self.selection, 'RESTORE_DATA')
        self.retain()
        with self.assertRaisesRegex(AuthorityDenied, 'database method/descriptor'): self.require()
        self.selection['applicationDatabaseSelectionDigest'] = 'e' * 64
        for campaign in self.bundle['campaign']['records']:
            for attempt in campaign['attempts']:
                if attempt['assertion_id'] == 'ACTION_RESTORE_DATA':
                    attempt['variant_ref'] = action_variant(self.selection, 'RESTORE_DATA')
        source = self.bundle['campaign']['records'][0]
        proof = next(attempt for attempt in source['attempts']
                     if attempt['assertion_id'] == 'DATABASE_ENGINE_AND_VERSION_BOUND')
        proof['observation_class'] = 'SERVICE_OPERATION'
        self.retain()
        with self.assertRaises(AuthorityDenied): self.require()
        source['attempts'].remove(proof)
        source['required_assertions'].remove(proof['assertion_id'])
        dossier = self.bundle['qualification']['records'][0]
        dossier['evidence'] = [item for item in dossier['evidence'] if item['ref'] != proof['evidence_ref']]
        self.retain()
        with self.assertRaisesRegex(AuthorityDenied, 'database method/descriptor'): self.require()


if __name__ == '__main__':
    unittest.main()
