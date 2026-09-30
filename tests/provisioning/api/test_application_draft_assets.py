"""Serve the composed draft UI under existing origin/CSP and test its real scripts."""
from pathlib import Path
import shutil
import subprocess
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from provisioner.controlplane.api.portal import mount_portal
from tests.provisioning.api.test_portal import configured, ORIGIN

ROOT = Path(__file__).resolve().parents[3]


class ApplicationDraftAssetTests(unittest.TestCase):
    def test_draft_script_is_packaged_and_served_under_existing_origin_and_csp(self):
        app = FastAPI()
        mount_portal(app, configured())
        client = TestClient(app, base_url=ORIGIN)
        response = client.get('/portal/application_drafts.js')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertIn("frame-ancestors 'none'", response.headers['content-security-policy'])
        self.assertIn('const ApplicationDraftWorkspace', response.text)
        self.assertEqual(response.text, (ROOT / 'provisioner/controlplane/api/portal/application_drafts.js').read_text())
        self.assertEqual(TestClient(app, base_url='https://other.invalid').get(
            '/portal/application_drafts.js').status_code, 421)
        disabled = FastAPI()
        mount_portal(disabled, None)
        self.assertEqual(TestClient(disabled).get('/portal/application_drafts.js').status_code, 404)

    def test_page_composes_the_draft_client_before_shell_and_declares_read_only_boundaries(self):
        app = FastAPI()
        mount_portal(app, configured())
        page = TestClient(app, base_url=ORIGIN).get('/portal/').text
        self.assertLess(page.index('src="application_drafts.js"'), page.index('src="app.js"'))
        for name in ('draft-heading', 'draft-name', 'draft-owner', 'draft-order', 'draft-confirm',
                     'draft-members', 'draft-datasets', 'draft-dependencies', 'draft-status'):
            self.assertIn('id="'+name+'"', page)
        self.assertIn('role="status"', page)
        self.assertIn('Membership, datasets and dependency evidence remain read-only', page)
        self.assertIn('Create drafts or change membership and dependency evidence through the existing operator CLI', page)
        script = (ROOT / 'provisioner/controlplane/api/portal/application_drafts.js').read_text()
        for forbidden in ('localStorage', 'sessionStorage', 'innerHTML', 'document.cookie'):
            self.assertNotIn(forbidden, script)

    @unittest.skipUnless(shutil.which('node'), 'Node is required for browser-client contract tests')
    def test_draft_javascript_contracts_and_real_shell_composition(self):
        result = subprocess.run([shutil.which('node'), '--test',
            str(ROOT / 'tests/provisioning/api/test_application_draft_ui.js')],
            cwd=ROOT, text=True, capture_output=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout[-15000:]+result.stderr[-3000:])
        self.assertIn('# fail 0', result.stdout)
        self.assertIn('# skipped 0', result.stdout)


if __name__ == '__main__':
    unittest.main()
