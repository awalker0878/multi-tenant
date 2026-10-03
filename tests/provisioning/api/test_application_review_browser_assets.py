"""Packaged review UI and real Python -> browser contract; no native qualification."""
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
import json
import shutil
import subprocess
import tempfile
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from provisioner.controlplane.api.portal import mount_portal
from provisioner.controlplane.discovery.application_reviews import _view, REVIEW_STATUSES
from provisioner.controlplane.discovery.assessment_inputs import parse_evidence
from tests.provisioning.api.test_portal import configured, ORIGIN
from tests.provisioning.api.test_application_authoring_assets import _Markup
from tests.provisioning.discovery.test_application_review import stored_fixture, review_document, OwnerFixture, NOW
from tests.provisioning.discovery import test_grouping as grouping

ROOT = Path(__file__).resolve().parents[3]


def review_fixtures():
    """All eight real service states, with actual ephemeral signatures for decisions."""
    values = []
    for mode in ('UNREVIEWED', 'REVOKED', 'DRAFT', 'INVENTORY', 'PARTIAL', 'STALE', 'READY', 'UNKNOWN'):
        stored, result = stored_fixture()
        if mode in ('PARTIAL', 'STALE', 'UNKNOWN'):
            if mode == 'PARTIAL':
                result = replace(result, completeness='PARTIAL', collection_errors=('VISIBLE_INVENTORY_ONLY',))
            if mode == 'STALE':
                result = replace(result, captured_at=NOW-timedelta(hours=2))
            edges = ((replace(grouping.UNKNOWN, observed_at=result.captured_at),) if mode == 'UNKNOWN' else None)
            stored, result = stored_fixture(result=result, edges=edges)
        document = review_document(stored, decision='REVOKE' if mode == 'REVOKED' else 'ACCEPT_FOR_ASSESSMENT')
        evidence = parse_evidence(document)
        with tempfile.TemporaryDirectory() as directory:
            owner = OwnerFixture(Path(directory)/'policy.json', stored)
            owner.trust.verify(evidence, owner.sign(document), NOW)
        view = _view(stored, result, None if mode == 'UNREVIEWED' else evidence,
                     2 if mode == 'INVENTORY' else 1, 2 if mode == 'DRAFT' else 1, NOW)
        values.append({'record': stored.document(latest_generation=1), 'review': view})
    # Cross the actual authenticated HTTP serialization boundary as well.
    from tests.provisioning.api.test_application_assessment_http import ApplicationAssessmentHttpTests
    case = ApplicationAssessmentHttpTests(); case.setUp()
    try:
        path = '/v1/environments/source/application-drafts/app-1'
        record = case.client.get(path+'?revision=1', headers={'Authorization': 'Bearer operator'})
        review = case.client.get(path+'/review?revision=1', headers={'Authorization': 'Bearer operator'})
        assert record.status_code == review.status_code == 200, (record.text, review.text)
        assert review.headers['cache-control'] == 'no-store'
        api = {'record': record.json(), 'review': review.json()}
    finally:
        case.doCleanups()
    return {'variants': values, 'api': api}


class ApplicationReviewBrowserAssetsTests(unittest.TestCase):
    def test_review_controls_are_disabled_and_read_only_in_packaged_shell(self):
        app = FastAPI(); mount_portal(app, configured())
        client = TestClient(app, base_url=ORIGIN)
        response = client.get('/portal/')
        self.assertEqual(response.status_code, 200)
        markup = _Markup(); markup.feed(response.text)
        control = markup.controls['draft-review-check']
        self.assertEqual(control[0], 'button')
        self.assertEqual(control[1]['type'], 'button')
        self.assertIn('disabled', control[1])
        for identity in ('draft-review-heading', 'draft-review-status', 'draft-review-result'):
            self.assertIn(identity, markup.ids)
        self.assertIn('cannot sign, accept, revoke or submit', response.text)
        self.assertIn('id="draft-review-result" class="review-card" hidden', response.text)
        script = client.get('/portal/application_drafts.js')
        self.assertEqual(script.headers['cache-control'], 'no-store')
        self.assertIn("frame-ancestors 'none'", script.headers['content-security-policy'])
        self.assertEqual(script.text, (ROOT/'provisioner/controlplane/api/portal/application_drafts.js').read_text())

    def test_review_validator_has_one_active_browser_owner_without_an_alias(self):
        drafts = (ROOT/'provisioner/controlplane/api/portal/application_drafts.js').read_text()
        comparison = (ROOT/'provisioner/controlplane/api/portal/application_comparison.js').read_text()
        self.assertEqual(drafts.count('function validateReview('), 1)
        self.assertNotIn('function validateReview(', comparison)
        self.assertIn('draftContract.validateReview(v.applicationReview, record)', comparison)
        for forbidden in ('innerHTML', 'localStorage', 'sessionStorage', 'document.cookie'):
            self.assertNotIn(forbidden, drafts)

    def test_serialized_fixtures_cover_every_real_review_status_without_authority(self):
        data = review_fixtures()
        self.assertEqual({v['review']['status'] for v in data['variants']}, REVIEW_STATUSES)
        for row in data['variants'] + [data['api']]:
            self.assertEqual(row['record']['recordDigest'], row['review']['draftRecordDigest'])
            self.assertIs(row['review']['executionAuthorized'], False)
            self.assertIs(row['review']['ownershipAccepted'], False)
            self.assertIs(row['review']['dependencyEvidenceVerified'], False)
            self.assertEqual(row['record']['status'], 'UNREVIEWED')

    @unittest.skipUnless(shutil.which('node'), 'Node is required for browser review integration')
    def test_actual_review_client_and_python_api_service_contracts(self):
        run = subprocess.run([shutil.which('node'), '--test', '--test-reporter=tap',
            str(ROOT/'tests/provisioning/api/test_application_review_ui.js')], cwd=ROOT,
            text=True, capture_output=True, timeout=45)
        self.assertEqual(run.returncode, 0, run.stdout[-18000:]+run.stderr[-4000:])
        self.assertIn('# fail 0', run.stdout)
        self.assertIn('# skipped 0', run.stdout)


if __name__ == '__main__':
    unittest.main()
