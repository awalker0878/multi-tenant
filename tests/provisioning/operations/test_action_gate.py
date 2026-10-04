from copy import deepcopy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from provisioner.controlplane.authority.service import AuthorityDenied
from provisioner.qualification.action_gate import SelectedQualificationGate, bundle_digest
from tests.provisioning.operations.campaign_fixtures import AS_OF, fixture


class Cursor:
    def __init__(self, tenant='tenant-fixture'):
        self.tenant = tenant
    def execute(self, *args):
        pass
    def fetchone(self):
        return 'org-fixture', self.tenant, AS_OF


class ActionGateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        _, self.bundle, self.selection = fixture(action='VM_CREATE')
        self.admitted = SimpleNamespace(organization_id='org-fixture', tenant_id='tenant-fixture')
        self.write_bundle()
        self.gate = SelectedQualificationGate(qualification_path=self.root / 'qualification.json',
            provenance_path=self.root / 'provenance.json', campaign_path=self.root / 'campaign.json',
            target_selection_path=self.root / 'targetSelection.json', capacity_path=self.root / 'capacity.json')

    def tearDown(self):
        self.temporary.cleanup()

    def write_bundle(self):
        for key, value in self.bundle.items():
            path = self.root / (key + '.json')
            path.write_text(json.dumps(value))
            path.chmod(0o600)

    def test_exact_current_action_and_commissioned_site_profile_passes_synthetic_chain(self):
        self.gate.require_action(Cursor(), self.admitted, self.selection, 'VM_CREATE')

    def test_reloads_revocation_and_changed_bundle_immediately_before_effect(self):
        self.gate.require_action(Cursor(), self.admitted, self.selection, 'VM_CREATE')
        self.bundle['qualification']['records'] = []
        self.write_bundle()
        with self.assertRaisesRegex(AuthorityDenied, 'withdrawn'):
            self.gate.require_action(Cursor(), self.admitted, self.selection, 'VM_CREATE')

    def test_wrong_tenant_action_profile_code_or_native_scope_never_passes(self):
        with self.assertRaises(AuthorityDenied):
            self.gate.require_action(Cursor('foreign-tenant'), self.admitted, self.selection, 'VM_CREATE')
        with self.assertRaises(AuthorityDenied):
            self.gate.require_action(Cursor(), self.admitted, self.selection, 'RESTORE_DATA')
        for field, value in (('guestProfile', 'WINDOWS'), ('sourceCommit', 'e' * 40)):
            changed = {**self.selection, field: value}
            with self.assertRaises(AuthorityDenied):
                self.gate.require_action(Cursor(), self.admitted, changed, 'VM_CREATE')
        changed = deepcopy(self.selection)
        changed['destination']['endpointId'] = 'foreign-endpoint'
        with self.assertRaises(AuthorityDenied):
            self.gate.require_action(Cursor(), self.admitted, changed, 'VM_CREATE')

    def test_uncommissioned_site_and_stale_dossier_block_even_rebound_digest(self):
        self.bundle['capacity']['records'] = []
        self.selection['qualificationDigest'] = bundle_digest(self.bundle)
        self.write_bundle()
        with self.assertRaisesRegex(AuthorityDenied, 'commissioned'):
            self.gate.require_action(Cursor(), self.admitted, self.selection, 'VM_CREATE')
        _, self.bundle, self.selection = fixture(action='VM_CREATE')
        self.bundle['qualification']['records'][0]['approval']['expires_at'] = '2026-10-01T00:00:00Z'
        self.selection['qualificationDigest'] = bundle_digest(self.bundle)
        self.write_bundle()
        with self.assertRaises(AuthorityDenied):
            self.gate.require_action(Cursor(), self.admitted, self.selection, 'VM_CREATE')

    def test_writable_custody_index_cannot_be_trusted(self):
        (self.root / 'campaign.json').chmod(0o666)
        with self.assertRaisesRegex(AuthorityDenied, 'protected'):
            self.gate.require_action(Cursor(), self.admitted, self.selection, 'VM_CREATE')


if __name__ == '__main__':
    unittest.main()
