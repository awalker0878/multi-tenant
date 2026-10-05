"""Validate an operating-input record; never infer deployment authorization."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

FIELDS = {
    'OP01': {'IP02.component_environment_bom', 'IP02.deployment_network_constraints'},
    'OP02': {'IP02.registry_mirror_verification', 'IP02.identity_key_evidence_custody'},
    'OP03': {'IP02.identity_key_evidence_custody', 'IP06.trust_restore_model'},
    'OP04': {'IP01.criterion_reviewers', 'IP07.reviewer_implementer_conflicts'},
    'OP05': {'IP06.evidence_alert_recipients', 'IP06.measurement_conditions'},
    'OP06': {'IP01.retained_records_inventory', 'IP06.trust_restore_model', 'IP06.control_plane_targets'},
    'OP07': {'IP02.support_update_ownership', 'IP02.browser_assistive_matrix', 'IP06.support_access'},
}
EXPECTED = set(FIELDS)


def assess(record, carried, now=None):
    now = now or datetime.now(timezone.utc)
    items = record['inputs']
    if record['schema_version'] != 1 or len(items) != len(EXPECTED) or {i['id'] for i in items} != EXPECTED:
        raise ValueError('invalid_operating_input_inventory')
    missing = []
    for item in items:
        if (len(item['carried_fields']) != len(FIELDS[item['id']])
                or set(item['carried_fields']) != FIELDS[item['id']]):
            raise ValueError('operating_input_scope_changed')
        for field in item['carried_fields']:
            group, name = field.split('.')
            if name not in carried['groups'][group]['fields']:
                raise ValueError('unknown_carried_field')
        if item['status'] == 'UNKNOWN':
            if (item['value'] is not None or item['owner_identity'] is not None or item['evidence']
                    or item['review'] != {'disposition': 'NOT_REVIEWED', 'reviewed_by': None, 'reviewed_at': None}):
                raise ValueError('unknown_input_cannot_be_accepted')
            missing.append(item['id']);continue
        if (item['status'] != 'OBSERVED' or not item['value']
                or not isinstance(item['owner_identity'], str) or not item['owner_identity'].strip()
                or not isinstance(item['evidence'], list) or not item['evidence']):
            raise ValueError('incomplete_observed_input')
        seen = set()
        for evidence in item['evidence']:
            if (not re.fullmatch(r'[0-9a-f]{64}', evidence['sha256'])
                    or not re.fullmatch(r'[A-Za-z0-9._-]{1,128}', evidence['revision'])
                    or evidence['revision'].lower() in {'main', 'master', 'head', 'latest', 'unknown'}):
                raise ValueError('unbound_operating_evidence')
            uri = evidence['uri']
            if (not uri.startswith(('git://awalker0878/multi-tenant/', 'evidence://'))
                    or re.search(r'[\s\\?#@]', uri) or '..' in uri.split('/')):
                raise ValueError('use_sanitized_immutable_evidence_reference')
            if uri.startswith('git://') and (not re.fullmatch(r'[0-9a-f]{40}', evidence['revision'])
                    or not uri.startswith('git://awalker0878/multi-tenant/' + evidence['revision'] + '/')):
                raise ValueError('git_evidence_revision_mismatch')
            if uri.endswith('/') or uri in seen:
                raise ValueError('empty_or_duplicate_evidence_reference')
            seen.add(uri)
        review = item['review']
        if review['disposition'] not in {'NOT_REVIEWED', 'ACCEPTED', 'REJECTED'}:
            raise ValueError('invalid_operating_review_disposition')
        if review['disposition'] == 'NOT_REVIEWED':
            if review['reviewed_by'] is not None or review['reviewed_at'] is not None:
                raise ValueError('unreviewed_input_has_review')
            missing.append(item['id']);continue
        reviewed = datetime.fromisoformat(review['reviewed_at'])
        if (not isinstance(review['reviewed_by'], str) or not review['reviewed_by'].strip()
                or reviewed.tzinfo is None or reviewed.utcoffset().total_seconds() != 0 or reviewed > now):
            raise ValueError('unattributed_operating_review')
        if review['disposition'] == 'REJECTED':
            missing.append(item['id'])
    result = 'HELD' if missing else 'RECORD_COMPLETE_REQUIRES_INDEPENDENT_VERIFICATION'
    if record['status'] != result:
        raise ValueError('operating_readiness_overclaim')
    return {'result': result, 'missing_or_unreviewed': missing, 'promotion_authorized': False,
            'limitations': 'Checks recorded identity and completeness only; does not fetch custody evidence or authenticate review.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-complete', action='store_true',
                        help='Exit unsuccessfully while any input is missing or unreviewed; never authorizes promotion.')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    result = assess(json.loads((root / 'release/operating-inputs.json').read_text()),
                    json.loads((root / 'docs/qualification/feasibility/p00-input-record.json').read_text()))
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if args.require_complete and result['result'] == 'HELD' else 0)
