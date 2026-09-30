"""Application comparison browser assets and the unchanged API trust boundary."""
from pathlib import Path
import shutil
import subprocess
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from provisioner.controlplane.api.portal import mount_portal
from tests.provisioning.api.test_portal import configured, ORIGIN

ROOT = Path(__file__).resolve().parents[3]
PORTAL = ROOT / 'provisioner/controlplane/api/portal'


class ApplicationComparisonAssetTests(unittest.TestCase):
    def test_comparison_script_is_same_origin_no_store_and_disabled_without_identity(self):
        app = FastAPI()
        mount_portal(app, configured())
        reply = TestClient(app, base_url=ORIGIN).get('/portal/application_comparison.js')
        self.assertEqual(reply.status_code, 200)
        self.assertEqual(reply.headers['cache-control'], 'no-store')
        self.assertIn("script-src 'self'", reply.headers['content-security-policy'])
        self.assertEqual(reply.text, (PORTAL / 'application_comparison.js').read_text())
        self.assertEqual(TestClient(app, base_url='https://other.invalid').get(
            '/portal/application_comparison.js').status_code, 421)
        disabled = FastAPI()
        mount_portal(disabled, None)
        self.assertEqual(TestClient(disabled).get('/portal/application_comparison.js').status_code, 404)

    def test_page_composes_clients_and_exposes_only_read_only_comparison(self):
        page = (PORTAL / 'index.html').read_text()
        self.assertLess(page.index('src="application_drafts.js"'), page.index('src="application_comparison.js"'))
        self.assertLess(page.index('src="application_comparison.js"'), page.index('src="app.js"'))
        for name in ('application-comparison-heading', 'app-compare-source', 'app-compare-members',
                     'app-compare-settings', 'app-compare-submit', 'app-compare-cancel',
                     'app-compare-status', 'app-compare-results'):
            self.assertIn('id="' + name + '"', page)
        self.assertIn('No capacity is reserved', page)
        script = (PORTAL / 'application_comparison.js').read_text()
        for forbidden in ('localStorage', 'sessionStorage', 'innerHTML', 'document.cookie',
                          '/v1/jobs', '/approvals', "method: 'PUT'"):
            self.assertNotIn(forbidden, script)

    @unittest.skipUnless(shutil.which('node'), 'Node is required for browser contracts')
    def test_browser_request_response_race_and_composition_contracts(self):
        result = subprocess.run([shutil.which('node'), '--test',
            str(ROOT / 'tests/provisioning/api/test_application_comparison_ui.js')],
            cwd=ROOT, text=True, capture_output=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout[-18000:] + result.stderr[-3000:])
        self.assertIn('# fail 0', result.stdout)
        self.assertIn('# skipped 0', result.stdout)
