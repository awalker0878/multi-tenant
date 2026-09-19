#!/usr/bin/env python3
"""Validate exported qualification-campaign evidence without issuing qualification.

This checker validates the shape, scope binding, attempt chronology, positive-control
dependencies, evidence freshness and residual-gap state of an externally executed
native qualification campaign. It does not contact a target, run a native test, accept
evidence on behalf of an authority, publish a PlatformProfile qualification, apply
infrastructure, or authorize production.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import check_target_selection_assurance as target

INDEX = ROOT / 'sources/capabilities/qualification_campaign_evidence_index.json'
FORMAT = 'portable-hosting-qualification-campaign-evidence-index/1'
STATUS = 'EXPORTED_CAMPAIGN_EVIDENCE_NOT_QUALIFICATION_OR_PRODUCTION_AUTHORITY'
STATES = {'CURRENT_EVIDENCE_COMPLETE', 'REVIEW_DUE', 'GAPS_OPEN', 'UNCERTAIN'}
RESULTS = {'PASSED', 'FAILED', 'BLOCKED', 'NOT_RUN'}
OBSERVATION_CLASSES = {
    'POSITIVE_CONTROL', 'NEGATIVE_CONTROL', 'PATH_POLICY', 'SERVICE_OPERATION',
    'CAPACITY_LOAD', 'FAILURE_RECOVERY', 'LIFECYCLE', 'OTHER'
}
ADDRESS_FAMILIES = {'IPV4', 'IPV6'}
GAP_STATES = {'OPEN', 'ACCEPTED'}
SHA256 = re.compile(r'^[0-9a-f]{64}$')

INDEX_KEYS = {'format', 'status', 'reviewed_source_revision', 'records'}
RECORD_KEYS = {
    'campaign_id', 'generation', 'state', 'selection_id', 'scope', 'authorization',
    'governance', 'required_assertions', 'not_applicable', 'attempts',
    'residual_gaps', 'source_refs'
}
SCOPE_KEYS = {
    'site_ref', 'cell_ref', 'campaign_scope_ref', 'platform_family',
    'product_tuple_id', 'service_scope_ref', 'topology_generation_ref',
    'address_families', 'failure_scope_ref', 'started_at', 'review_by'
}
AUTHORIZATION_KEYS = {
    'change_authority_ref', 'target_contact_authority_ref',
    'target_contact_valid_until', 'stop_authority_ref',
    'qualification_campaign_ref', 'native_api_scope_ref', 'observer_scope_ref',
    'writer_scope_ref', 'credential_custody_ref', 'evidence_workspace_ref',
    'data_restriction_ref', 'permitted_operations_ref',
    'prohibited_operations_ref', 'cleanup_ref', 'contact_window_ref'
}
GOVERNANCE_KEYS = {
    'applicability_ref', 'run_sheet_ref', 'authorized_fault_scope_ref',
    'evidence_workspace_ref', 'artifact_manifest_ref', 'reviewer_ref',
    'qualification_decision_status', 'production_authority_status'
}
NA_KEYS = {'assertion_id', 'decision_ref', 'reason_ref', 'reviewer_ref', 'review_by'}
ATTEMPT_KEYS = {
    'attempt_id', 'assertion_id', 'procedure_ref', 'variant_ref',
    'observation_class', 'result', 'positive_control_attempt_ref',
    'evidence_ref', 'artifact_sha256', 'observed_at', 'fresh_until', 'reviewer_ref'
}
GAP_KEYS = {'gap_id', 'status', 'owner_ref', 'treatment_ref', 'decision_ref', 'review_by'}


def load(path: Path = INDEX):
    with path.open('rb') as stream:
        raw = stream.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError('Qualification-campaign evidence index exceeds bounded size')

    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError('Duplicate JSON property')
            out[key] = value
        return out

    def reject(_):
        raise ValueError('Non-finite JSON number')

    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=reject)
    if not isinstance(value, dict):
        raise ValueError('Qualification-campaign evidence index must be an object')
    return value


def validate_record(record, as_of, root=ROOT):
    if not isinstance(record, dict) or set(record) != RECORD_KEYS:
        raise ValueError('Qualification-campaign record has unexpected or missing fields')
    target.identifier(record['campaign_id'], 'campaign_id')
    target.identifier(record['selection_id'], 'selection_id')
    target.positive_int(record['generation'], 'generation')
    if record['state'] not in STATES:
        raise ValueError('Unknown qualification-campaign evidence state')

    scope = record['scope']
    if not isinstance(scope, dict) or set(scope) != SCOPE_KEYS:
        raise ValueError('Qualification-campaign scope shape invalid')
    for key in (
        'site_ref', 'cell_ref', 'campaign_scope_ref', 'service_scope_ref',
        'topology_generation_ref', 'failure_scope_ref'
    ):
        target.opaque_ref(scope[key], f'scope.{key}')
    if scope['platform_family'] not in target.PLATFORMS:
        raise ValueError('Unknown campaign platform family')
    target.identifier(scope['product_tuple_id'], 'scope.product_tuple_id')
    families = target.unique_strings(scope['address_families'], 'scope.address_families', maximum=2)
    if not set(families) <= ADDRESS_FAMILIES:
        raise ValueError('Unknown campaign address family')
    started = target.instant(scope['started_at'], 'scope.started_at')
    review_by = target.instant(scope['review_by'], 'scope.review_by')
    if started > as_of or review_by <= started:
        raise ValueError('Qualification-campaign scope chronology invalid')

    authorization = record['authorization']
    if not isinstance(authorization, dict) or set(authorization) != AUTHORIZATION_KEYS:
        raise ValueError('Qualification-campaign authorization shape invalid')
    for key in AUTHORIZATION_KEYS - {'target_contact_valid_until'}:
        target.opaque_ref(authorization[key], f'authorization.{key}')
    authorized_until = target.instant(
        authorization['target_contact_valid_until'],
        'authorization.target_contact_valid_until'
    )
    if authorized_until <= started:
        raise ValueError('Qualification campaign starts after its authorized target-contact window')

    governance = record['governance']
    if not isinstance(governance, dict) or set(governance) != GOVERNANCE_KEYS:
        raise ValueError('Qualification-campaign governance shape invalid')
    for key in GOVERNANCE_KEYS - {'qualification_decision_status', 'production_authority_status'}:
        target.opaque_ref(governance[key], f'governance.{key}')
    if governance['qualification_decision_status'] != 'NOT_ISSUED':
        raise ValueError('Campaign evidence cannot carry a qualification decision')
    if governance['production_authority_status'] != 'NOT_ISSUED':
        raise ValueError('Campaign evidence cannot carry production authority')
    if governance['evidence_workspace_ref'] != authorization['evidence_workspace_ref']:
        raise ValueError('Campaign evidence workspace differs from the authorized target-selection workspace')

    required = target.unique_strings(record['required_assertions'], 'required_assertions', maximum=512)
    for assertion_id in required:
        target.identifier(assertion_id, 'required_assertion')
    required_set = set(required)

    not_applicable = record['not_applicable']
    if not isinstance(not_applicable, list) or len(not_applicable) > 512:
        raise ValueError('not_applicable must be a bounded list')
    na_by_assertion = {}
    na_reviews = []
    for item in not_applicable:
        if not isinstance(item, dict) or set(item) != NA_KEYS:
            raise ValueError('Not-applicable decision shape invalid')
        assertion_id = target.identifier(item['assertion_id'], 'not_applicable.assertion_id')
        if assertion_id not in required_set:
            raise ValueError('Not-applicable decision references an assertion outside campaign scope')
        if assertion_id in na_by_assertion:
            raise ValueError('Duplicate not-applicable decision for one assertion')
        for key in ('decision_ref', 'reason_ref', 'reviewer_ref'):
            target.opaque_ref(item[key], f'not_applicable.{key}')
        review = target.instant(item['review_by'], 'not_applicable.review_by')
        if review <= started:
            raise ValueError('Not-applicable review must follow campaign start')
        na_by_assertion[assertion_id] = item
        na_reviews.append(review)

    attempts = record['attempts']
    if not isinstance(attempts, list) or len(attempts) > 4096:
        raise ValueError('Campaign attempts must be a bounded list')
    by_id = {}
    assertion_times = set()
    for raw in attempts:
        if not isinstance(raw, dict) or set(raw) != ATTEMPT_KEYS:
            raise ValueError('Campaign attempt shape invalid')
        attempt_id = target.identifier(raw['attempt_id'], 'attempt_id')
        if attempt_id in by_id:
            raise ValueError('Duplicate campaign attempt ID')
        assertion_id = target.identifier(raw['assertion_id'], 'attempt.assertion_id')
        if assertion_id not in required_set:
            raise ValueError('Attempt references an assertion outside campaign scope')
        if assertion_id in na_by_assertion:
            raise ValueError('An assertion cannot be both attempted and not applicable')
        for key in ('procedure_ref', 'variant_ref', 'evidence_ref', 'reviewer_ref'):
            target.opaque_ref(raw[key], f'attempt.{key}')
        if raw['observation_class'] not in OBSERVATION_CLASSES:
            raise ValueError('Unknown observation class')
        if raw['result'] not in RESULTS:
            raise ValueError('Unknown campaign attempt result')
        if not isinstance(raw['artifact_sha256'], str) or not SHA256.fullmatch(raw['artifact_sha256']):
            raise ValueError('Campaign attempt requires lowercase SHA-256')
        observed = target.instant(raw['observed_at'], 'attempt.observed_at')
        fresh_until = target.instant(raw['fresh_until'], 'attempt.fresh_until')
        if observed < started or observed > as_of or fresh_until <= observed:
            raise ValueError('Campaign attempt chronology invalid')
        if observed > authorized_until:
            raise ValueError('Campaign attempt occurred after authorized target-contact expiry')
        key = (assertion_id, observed)
        if key in assertion_times:
            raise ValueError('One assertion cannot have ambiguous attempts at the same observation time')
        assertion_times.add(key)
        control_ref = raw['positive_control_attempt_ref']
        if raw['observation_class'] == 'POSITIVE_CONTROL':
            if control_ref is not None:
                raise ValueError('Positive-control attempt cannot reference another positive control')
        elif raw['observation_class'] == 'NEGATIVE_CONTROL':
            if control_ref is None:
                raise ValueError('Negative-control attempt requires an explicit healthy positive control')
            target.identifier(control_ref, 'positive_control_attempt_ref')
        elif control_ref is not None:
            target.identifier(control_ref, 'positive_control_attempt_ref')
        by_id[attempt_id] = {
            **raw,
            '_observed': observed,
            '_fresh_until': fresh_until,
        }

    for item in by_id.values():
        control_ref = item['positive_control_attempt_ref']
        if control_ref is None:
            continue
        if control_ref == item['attempt_id'] or control_ref not in by_id:
            raise ValueError('Positive-control reference must identify a different retained attempt')
        control = by_id[control_ref]
        if control['observation_class'] != 'POSITIVE_CONTROL' or control['result'] != 'PASSED':
            raise ValueError('Referenced positive control must be a PASSED POSITIVE_CONTROL attempt')
        if control['_observed'] > item['_observed'] or control['_fresh_until'] < item['_observed']:
            raise ValueError('Referenced positive control was not healthy when the dependent attempt ran')

    latest = {}
    for item in by_id.values():
        current = latest.get(item['assertion_id'])
        if current is None or item['_observed'] > current['_observed']:
            latest[item['assertion_id']] = item

    gaps = record['residual_gaps']
    if not isinstance(gaps, list) or len(gaps) > 1024:
        raise ValueError('Residual campaign gaps must be a bounded list')
    gap_ids = set()
    open_gaps = []
    gap_reviews = []
    for gap in gaps:
        if not isinstance(gap, dict) or set(gap) != GAP_KEYS:
            raise ValueError('Residual campaign gap shape invalid')
        gap_id = target.identifier(gap['gap_id'], 'gap_id')
        if gap_id in gap_ids:
            raise ValueError('Duplicate residual campaign gap ID')
        gap_ids.add(gap_id)
        if gap['status'] not in GAP_STATES:
            raise ValueError('Unknown residual campaign gap state')
        target.opaque_ref(gap['owner_ref'], 'gap.owner_ref')
        target.opaque_ref(gap['treatment_ref'], 'gap.treatment_ref')
        gap_review = target.instant(gap['review_by'], 'gap.review_by')
        gap_reviews.append(gap_review)
        if gap['status'] == 'OPEN':
            if gap['decision_ref'] is not None:
                raise ValueError('OPEN campaign gap cannot carry an acceptance decision')
            open_gaps.append(gap_id)
        else:
            target.opaque_ref(gap['decision_ref'], 'gap.decision_ref')

    refs = target.unique_strings(record['source_refs'], 'source_refs')
    for ref in refs:
        target.repository_ref(ref, root)

    attempted_scope = required_set - set(na_by_assertion)
    missing = sorted(assertion_id for assertion_id in attempted_scope if assertion_id not in latest)
    nonpassing = sorted(
        assertion_id for assertion_id in attempted_scope
        if assertion_id in latest and latest[assertion_id]['result'] != 'PASSED'
    )
    stale = sorted(
        assertion_id for assertion_id in attempted_scope
        if assertion_id in latest and latest[assertion_id]['result'] == 'PASSED'
        and as_of >= latest[assertion_id]['_fresh_until']
    )
    review_due = (
        as_of >= review_by
        or any(as_of >= value for value in na_reviews)
        or any(as_of >= value for value in gap_reviews)
        or bool(stale)
    )
    complete = not missing and not nonpassing and not stale
    state = record['state']
    if state == 'CURRENT_EVIDENCE_COMPLETE':
        if review_due or open_gaps or not complete:
            raise ValueError('CURRENT_EVIDENCE_COMPLETE campaign is stale, incomplete or has OPEN gaps')
    elif state == 'REVIEW_DUE':
        if not review_due or open_gaps:
            raise ValueError('REVIEW_DUE requires due evidence/review and no OPEN residual gaps')
    elif state == 'GAPS_OPEN':
        if review_due or not open_gaps:
            raise ValueError('GAPS_OPEN requires current review and at least one OPEN residual gap')
    elif state == 'UNCERTAIN':
        pass

    return {
        'campaign_id': record['campaign_id'],
        'generation': record['generation'],
        'state': state,
        'selection_id': record['selection_id'],
        'site_ref': scope['site_ref'],
        'cell_ref': scope['cell_ref'],
        'campaign_scope_ref': scope['campaign_scope_ref'],
        'platform_family': scope['platform_family'],
        'product_tuple_id': scope['product_tuple_id'],
        'service_scope_ref': scope['service_scope_ref'],
        'started_at': started.isoformat(),
        'authorization': dict(authorization),
        'topology_generation_ref': scope['topology_generation_ref'],
        'address_families': sorted(families),
        'required_assertions': sorted(required),
        'not_applicable_assertions': sorted(na_by_assertion),
        'latest_passing_assertions': sorted(
            assertion_id for assertion_id in attempted_scope
            if assertion_id in latest and latest[assertion_id]['result'] == 'PASSED'
            and as_of < latest[assertion_id]['_fresh_until']
        ),
        'latest_passing_evidence': [
            {
                'assertion_id': assertion_id,
                'attempt_id': latest[assertion_id]['attempt_id'],
                'evidence_ref': latest[assertion_id]['evidence_ref'],
                'artifact_sha256': latest[assertion_id]['artifact_sha256'],
                'observed_at': latest[assertion_id]['_observed'].isoformat(),
                'fresh_until': latest[assertion_id]['_fresh_until'].isoformat(),
            }
            for assertion_id in sorted(attempted_scope)
            if assertion_id in latest and latest[assertion_id]['result'] == 'PASSED'
            and as_of < latest[assertion_id]['_fresh_until']
        ],
        'missing_assertions': missing,
        'nonpassing_assertions': nonpassing,
        'stale_assertions': stale,
        'attempt_count': len(attempts),
        'review_by': review_by.isoformat(),
        'open_gap_ids': sorted(open_gaps),
    }


def validate(index, as_of=None, root=ROOT, target_selection_index=None):
    if as_of is None:
        as_of = datetime.now(timezone.utc)
    if not isinstance(as_of, datetime) or as_of.tzinfo is None:
        raise ValueError('Timezone-aware as_of required')
    as_of = as_of.astimezone(timezone.utc)
    if set(index) != INDEX_KEYS:
        raise ValueError('Unexpected qualification-campaign evidence-index fields')
    if index['format'] != FORMAT or index['status'] != STATUS:
        raise ValueError('Unsupported qualification-campaign evidence format or authority boundary')
    revision = index['reviewed_source_revision']
    if not isinstance(revision, str) or not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Reviewed source revision must be an exact Git SHA')
    records = index['records']
    if not isinstance(records, list) or len(records) > 128:
        raise ValueError('Qualification-campaign records must be a bounded list')

    if target_selection_index is None:
        target_selection_index = target.load()
    target_summary = target.validate(target_selection_index, as_of=as_of, root=root)
    usable_targets = {
        item['selection_id']: item for item in target_summary['records']
        if item['state'] in {'CURRENT_SELECTED', 'CONTACT_AUTHORITY_DUE'}
    }

    campaign_ids = set()
    selection_ids = set()
    out = []
    for raw in records:
        item = validate_record(raw, as_of=as_of, root=root)
        if item['campaign_id'] in campaign_ids:
            raise ValueError('Duplicate qualification-campaign ID')
        if item['selection_id'] in selection_ids:
            raise ValueError('Only one active campaign evidence record is allowed per target selection')
        selected = usable_targets.get(item['selection_id'])
        if selected is None:
            raise ValueError('Qualification campaign requires a current reviewed target selection; review-due, gapped or uncertain target state is ineligible')
        for field in ('site_ref', 'cell_ref', 'campaign_scope_ref', 'platform_family', 'product_tuple_id'):
            if item[field] != selected[field]:
                raise ValueError(f'Qualification campaign does not match selected target field: {field}')
        expected_authorization = {
            'change_authority_ref': selected['change_authority_ref'],
            'target_contact_authority_ref': selected['target_contact_authority_ref'],
            'stop_authority_ref': selected['stop_authority_ref'],
            'qualification_campaign_ref': selected['qualification_campaign_ref'],
            'native_api_scope_ref': selected['native_api_scope_ref'],
            'observer_scope_ref': selected['observer_scope_ref'],
            'writer_scope_ref': selected['writer_scope_ref'],
            'credential_custody_ref': selected['credential_custody_ref'],
            'evidence_workspace_ref': selected['evidence_workspace_ref'],
            'data_restriction_ref': selected['data_restriction_ref'],
            'permitted_operations_ref': selected['permitted_operations_ref'],
            'prohibited_operations_ref': selected['prohibited_operations_ref'],
            'cleanup_ref': selected['cleanup_ref'],
            'contact_window_ref': selected['contact_window_ref'],
        }
        for field, value in expected_authorization.items():
            if item['authorization'][field] != value:
                raise ValueError(f'Qualification campaign authorization differs from target selection: {field}')
        campaign_authorized_until = target.instant(
            item['authorization']['target_contact_valid_until'],
            'campaign target_contact_valid_until'
        )
        selected_at = target.instant(selected['selected_at'], 'selected_at')
        selected_contact_until = target.instant(
            selected['target_contact_valid_until'], 'target_contact_valid_until'
        )
        if target.instant(item['started_at'], 'campaign started_at') < selected_at:
            raise ValueError('Qualification campaign starts before the target selection became effective')
        if campaign_authorized_until > selected_contact_until:
            raise ValueError('Qualification campaign claims a longer contact window than the target selection')
        item['target_selection_state'] = selected['state']
        campaign_ids.add(item['campaign_id'])
        selection_ids.add(item['selection_id'])
        out.append(item)

    return {
        'records': out,
        'record_count': len(out),
        'current_evidence_complete_count': sum(x['state'] == 'CURRENT_EVIDENCE_COMPLETE' for x in out),
        'review_due_count': sum(x['state'] == 'REVIEW_DUE' for x in out),
        'gaps_open_count': sum(x['state'] == 'GAPS_OPEN' for x in out),
        'uncertain_count': sum(x['state'] == 'UNCERTAIN' for x in out),
        'retained_attempt_count': sum(x['attempt_count'] for x in out),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index', type=Path, default=INDEX)
    parser.add_argument('--as-of', help='ISO-8601 review instant; defaults to current UTC')
    args = parser.parse_args()
    try:
        as_of = target.instant(args.as_of, 'as_of') if args.as_of else datetime.now(timezone.utc)
        summary = validate(load(args.index), as_of=as_of)
        print(json.dumps({
            'status': 'PASSED_QUALIFICATION_CAMPAIGN_EVIDENCE',
            'as_of': as_of.isoformat(),
            **{key: value for key, value in summary.items() if key != 'records'},
            'may_contact_target': False,
            'may_retrieve_credentials': False,
            'may_run_native_tests': False,
            'may_issue_qualification': False,
            'may_update_platform_registry': False,
            'may_apply': False,
            'may_activate': False,
            'limits': [
                'Campaign evidence is bound to the exact reviewed target selection and restricted authorization used when observations were collected; this checker does not contact it.',
                'A complete evidence packet is review input, not an independent qualification decision.',
                'The active PlatformProfile qualification index remains separately governed.',
                'Production activation requires separate operating and activation authority.'
            ]
        }, indent=2))
        return 0
    except (ValueError, OSError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({
            'status': 'FAILED_QUALIFICATION_CAMPAIGN_EVIDENCE',
            'reason': str(exc),
            'may_contact_target': False,
            'may_retrieve_credentials': False,
            'may_run_native_tests': False,
            'may_issue_qualification': False,
            'may_update_platform_registry': False,
            'may_apply': False,
            'may_activate': False
        }, indent=2))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
