"""Initial and saved-revision browser authoring uses real serialized summaries and the existing parser.

These are in-process API serialization/domain and Node DOM-contract tests, not a
browser deployment, database-role test, owner acceptance or native qualification.
"""
from dataclasses import replace
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from provisioner.controlplane.api.http import _generation_view, _observation_view
from provisioner.controlplane.discovery.application_drafts import (
    StoredApplicationDraft, _digest, _json, parse_content)
from provisioner.controlplane.discovery.grouping import proposal_document, proposal_digest, validate_draft
from provisioner.controlplane.discovery.persistence import StoredGeneration, StoredObservation
from tests.provisioning.discovery.test_application_draft_contract import content
from tests.provisioning.discovery.test_grouping import DRAFT, RESULT, KNOWN, UNKNOWN, NOW

ROOT = Path(__file__).resolve().parents[3]


def serialized_fixture():
    result = replace(RESULT, completeness='PARTIAL', collection_errors=('VISIBLE_INVENTORY_ONLY',))
    edges = (KNOWN, UNKNOWN)
    proposal = proposal_document(result, DRAFT, edges)
    stored = StoredApplicationDraft('environment-a', result.scope, DRAFT.application_group_id,
        1, 3, result.digest, _json(proposal), proposal_digest(result, DRAFT, edges),
        'synthetic-author', NOW, '')
    stored = replace(stored, record_digest=_digest(stored.binding()))
    generation = StoredGeneration('environment-a', 3, result.campaign_id, result.scope,
        result.authorization_digest, result.digest, result.captured_at, result.completeness,
        result.collection_errors, result.missing_privileges, len(result.objects))
    observations = []
    for obj in result.objects:
        facts = tuple({'name': f.name, 'state': f.state, 'value': f.value()} for f in obj.facts)
        row = StoredObservation(3, obj.identity, facts, _digest({'id': obj.identity.key(), 'facts': facts}))
        observations.append(_observation_view(row).model_dump(mode='json', by_alias=True))
    return {
        'listing': {'format': 'hosting-application-draft-list/1', 'environmentId': 'environment-a',
            'scope': vars(result.scope), 'latestGeneration': 3, 'consistency': 'LIVE_PAGE',
            'items': [], 'nextAfter': None, 'executionAuthorized': False},
        'source': _generation_view(generation).model_dump(mode='json', by_alias=True),
        'page': {'environmentId': 'environment-a', 'generation': 3,
                 'items': observations, 'nextAfter': None},
        'content': content(result=result, edges=edges),
        'saved': stored.document(latest_generation=3),
    }, result


class _Markup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.labels, self.controls = set(), set(), {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        identity = attrs.get('id')
        if identity:
            if identity in self.ids:
                raise AssertionError('Duplicate DOM identity: ' + identity)
            self.ids.add(identity)
        if tag == 'label' and attrs.get('for'):
            self.labels.add(attrs['for'])
        if tag in ('input', 'select', 'textarea', 'button') and identity:
            self.controls[identity] = (tag, attrs)


class ApplicationAuthoringAssetTests(unittest.TestCase):
    def test_creation_controls_are_labelled_and_initially_disabled_in_the_real_shell(self):
        markup = _Markup()
        markup.feed((ROOT / 'provisioner/controlplane/api/portal/index.html').read_text())
        fields = ('data-group', 'data-ids', 'edge-id', 'edge-from', 'edge-to', 'edge-relation',
                  'edge-state', 'edge-reason', 'edge-source', 'edge-reference', 'edge-time')
        for field in fields:
            with self.subTest(field=field):
                identity = 'draft-' + field
                self.assertIn(identity, markup.labels)
                self.assertIn('disabled', markup.controls[identity][1])
        for identity in ('draft-start', 'draft-edit-evidence', 'draft-objects', 'draft-add-group', 'draft-add-edge'):
            with self.subTest(identity=identity):
                self.assertEqual(markup.controls[identity][0], 'button')
                self.assertEqual(markup.controls[identity][1]['type'], 'button')
                self.assertIn('disabled', markup.controls[identity][1])

    @unittest.skipUnless(shutil.which('node'), 'Node is required for browser-client contract tests')
    def test_initial_and_saved_authoring_contracts_and_real_python_serialization_roundtrip(self):
        fixture, result = serialized_fixture()
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / 'fixture.json', Path(directory) / 'request.json'
            revision_output = Path(directory) / 'revision-request.json'
            source.write_text(json.dumps(fixture))
            env = {**os.environ, 'HOSTING_AUTHORING_FIXTURE': str(source),
                   'HOSTING_AUTHORING_REQUEST': str(output),
                   'HOSTING_REVISION_REQUEST': str(revision_output)}
            run = subprocess.run([shutil.which('node'), '--test',
                str(ROOT / 'tests/provisioning/api/test_application_authoring_ui.js')],
                cwd=ROOT, env=env, text=True, capture_output=True, timeout=45)
            self.assertEqual(run.returncode, 0, run.stdout[-16000:] + run.stderr[-3000:])
            self.assertIn('# fail 0', run.stdout)
            self.assertIn('# skipped 0', run.stdout)
            body = json.loads(output.read_text())
            revision_body = json.loads(revision_output.read_text())
        self.assertEqual(set(body), {'generation', 'resultDigest', 'expectedRevision', 'draft', 'dependencies'})
        self.assertEqual((body['generation'], body['resultDigest'], body['expectedRevision']), (3, result.digest, 0))
        draft, edges = parse_content({'draft': body['draft'], 'dependencies': body['dependencies']})
        self.assertEqual(draft, DRAFT)
        self.assertEqual(edges, (KNOWN, UNKNOWN))
        self.assertEqual(validate_draft(result, draft, edges, checked_at=NOW), (UNKNOWN,))
        self.assertEqual(proposal_digest(result, draft, edges), fixture['saved']['proposalDigest'])
        self.assertEqual(set(revision_body), set(body))
        self.assertEqual((revision_body['generation'], revision_body['resultDigest'],
                          revision_body['expectedRevision']), (3, result.digest, 1))
        revised, revised_edges = parse_content({key: revision_body[key] for key in ('draft', 'dependencies')})
        self.assertEqual(revised.members[0], DRAFT.members[0])
        self.assertEqual(revised.members[1].native_vm, DRAFT.members[1].native_vm)
        self.assertEqual(revised.members[1].workload_id, 'replacement-member')
        self.assertEqual(revised.dataset_ids, DRAFT.dataset_ids + ('additional-data',))
        self.assertEqual(revised.startup_order, ('db', 'replacement-member'))
        self.assertEqual(revised_edges, ())
        self.assertEqual(validate_draft(result, revised, revised_edges, checked_at=NOW), ())
        self.assertNotEqual(proposal_digest(result, revised, revised_edges), fixture['saved']['proposalDigest'])


if __name__ == '__main__':
    unittest.main()
