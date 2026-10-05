"""Validate an operating-input record; never infer deployment authorization."""
from datetime import datetime
import json
from pathlib import Path
import re

EXPECTED = {'OP01', 'OP02', 'OP03', 'OP04', 'OP05', 'OP06', 'OP07'}


def assess(record, carried):
    items = record['inputs']
    if record['schema_version'] != 1 or len(items) != len(EXPECTED) or {i['id'] for i in items} != EXPECTED:
        raise ValueError('invalid_operating_input_inventory')
    missing = []
    for item in items:
        for field in item['carried_fields']:
            group, name = field.split('.')
            if name not in carried['groups'][group]['fields']:
                raise ValueError('unknown_carried_field')
        if item['status'] == 'UNKNOWN':
            if item['value'] is not None or item['review']['disposition'] != 'NOT_REVIEWED':
                raise ValueError('unknown_input_cannot_be_accepted')
            missing.append(item['id']);continue
        if item['status'] != 'OBSERVED' or not item['value'] or not item['owner_identity'] or not item['evidence']:
            raise ValueError('incomplete_observed_input')
        for evidence in item['evidence']:
            if not re.fullmatch(r'[0-9a-f]{64}', evidence['sha256']) or not evidence['revision']:
                raise ValueError('unbound_operating_evidence')
            if not evidence['uri'].startswith(('git://awalker0878/multi-tenant/', 'evidence://')):
                raise ValueError('use_sanitized_immutable_evidence_reference')
        review = item['review']
        if review['disposition'] != 'ACCEPTED':
            missing.append(item['id']);continue
        if not review['reviewed_by'] or datetime.fromisoformat(review['reviewed_at']).tzinfo is None:
            raise ValueError('unattributed_operating_review')
    result = 'HELD' if missing else 'RECORD_COMPLETE_REQUIRES_INDEPENDENT_VERIFICATION'
    if record['status'] != result:
        raise ValueError('operating_readiness_overclaim')
    return {'result': result, 'missing_or_unreviewed': missing, 'promotion_authorized': False,
            'limitations': 'Checks recorded identity and completeness only; does not fetch custody evidence or authenticate review.'}


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[3]
    print(json.dumps(assess(json.loads((root / 'release/operating-inputs.json').read_text()),
                           json.loads((root / 'docs/qualification/feasibility/p00-input-record.json').read_text())), indent=2))
