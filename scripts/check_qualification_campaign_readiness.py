#!/usr/bin/env python3
"""Evaluate whether a qualification-campaign evidence packet is review-ready.

A ready result means the exported packet is current and mechanically complete for the
exact selected target and campaign scope. It never grants target contact, native test,
qualification, registry publication, apply, or production activation authority.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import check_qualification_campaign_assurance as campaign

FORMAT = 'portable-hosting-qualification-campaign-readiness-intent/1'
STATUS = 'PLANNING_ONLY_NOT_AUTHORIZED'
READY = 'QUALIFICATION_CAMPAIGN_EVIDENCE_CURRENT_DECISION_NOT_ISSUED'
HOLD_NONE = 'HOLD_NO_CURRENT_QUALIFICATION_CAMPAIGN_EVIDENCE'
HOLD_REVIEW = 'HOLD_QUALIFICATION_CAMPAIGN_REVIEW_DUE'
HOLD_GAPS = 'HOLD_QUALIFICATION_CAMPAIGN_GAPS_OPEN'
HOLD_UNCERTAIN = 'HOLD_QUALIFICATION_CAMPAIGN_UNCERTAIN'
HOLD_SCOPE = 'HOLD_QUALIFICATION_CAMPAIGN_SCOPE_MISMATCH'
INTENT_KEYS = {
    'format', 'status', 'request_id', 'campaign_id', 'selection_id',
    'site_ref', 'cell_ref', 'campaign_scope_ref', 'platform_family',
    'product_tuple_id', 'service_scope_ref', 'topology_generation_ref',
    'qualification_decision', 'production_authority', 'source_refs'
}


def load(path):
    with Path(path).open('rb') as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError('Qualification-campaign readiness intent exceeds bounded size')
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('Qualification-campaign readiness intent must be an object')
    return value


def validate_intent(intent):
    if set(intent) != INTENT_KEYS or intent['format'] != FORMAT or intent['status'] != STATUS:
        raise ValueError('Unsupported qualification-campaign readiness intent')
    campaign.target.identifier(intent['request_id'], 'request_id')
    campaign.target.identifier(intent['campaign_id'], 'campaign_id')
    campaign.target.identifier(intent['selection_id'], 'selection_id')
    for key in (
        'site_ref', 'cell_ref', 'campaign_scope_ref', 'service_scope_ref',
        'topology_generation_ref'
    ):
        campaign.target.opaque_ref(intent[key], key)
    if intent['platform_family'] not in campaign.target.PLATFORMS:
        raise ValueError('Unknown campaign platform family')
    campaign.target.identifier(intent['product_tuple_id'], 'product_tuple_id')
    if intent['qualification_decision'] != 'NOT_ASSESSED':
        raise ValueError('Campaign readiness cannot carry a qualification decision')
    if intent['production_authority'] != 'NOT_ASSESSED':
        raise ValueError('Campaign readiness cannot carry production authority')
    for ref in campaign.target.unique_strings(intent['source_refs'], 'source_refs'):
        campaign.target.repository_ref(ref)


def evaluate(intent, index=None, target_selection_index=None, as_of=None):
    if as_of is None:
        as_of = datetime.now(timezone.utc)
    if not isinstance(as_of, datetime) or as_of.tzinfo is None:
        raise ValueError('Timezone-aware as_of required')
    as_of = as_of.astimezone(timezone.utc)
    validate_intent(intent)
    if index is None:
        index = campaign.load()
    summary = campaign.validate(
        index, as_of=as_of, target_selection_index=target_selection_index
    )
    records = [item for item in summary['records'] if item['campaign_id'] == intent['campaign_id']]
    record = records[0] if records else None

    if record is None:
        result = HOLD_NONE
    elif record['state'] == 'UNCERTAIN':
        result = HOLD_UNCERTAIN
    elif record['state'] == 'REVIEW_DUE':
        result = HOLD_REVIEW
    elif record['state'] == 'GAPS_OPEN':
        result = HOLD_GAPS
    elif any([
        record['selection_id'] != intent['selection_id'],
        record['site_ref'] != intent['site_ref'],
        record['cell_ref'] != intent['cell_ref'],
        record['campaign_scope_ref'] != intent['campaign_scope_ref'],
        record['platform_family'] != intent['platform_family'],
        record['product_tuple_id'] != intent['product_tuple_id'],
        record['service_scope_ref'] != intent['service_scope_ref'],
        record['topology_generation_ref'] != intent['topology_generation_ref'],
    ]):
        result = HOLD_SCOPE
    else:
        result = READY

    return {
        'kind': 'QUALIFICATION_CAMPAIGN_EVIDENCE_PREFLIGHT',
        'status': result,
        'request_id': intent['request_id'],
        'campaign_id': intent['campaign_id'],
        'selection_id': intent['selection_id'],
        'required_assertions': record['required_assertions'] if record else [],
        'not_applicable_assertions': record['not_applicable_assertions'] if record else [],
        'latest_passing_assertions': record['latest_passing_assertions'] if record else [],
        'missing_assertions': record['missing_assertions'] if record else [],
        'nonpassing_assertions': record['nonpassing_assertions'] if record else [],
        'stale_assertions': record['stale_assertions'] if record else [],
        'open_gap_ids': record['open_gap_ids'] if record else [],
        'may_contact_target': False,
        'may_retrieve_credentials': False,
        'may_run_native_tests': False,
        'may_issue_qualification': False,
        'may_update_platform_registry': False,
        'may_apply': False,
        'may_activate': False,
        'next_owner_action': {
            READY: 'Submit the controlled evidence packet to the accountable independent qualification authority; do not treat this preflight as approval.',
            HOLD_NONE: 'Execute the separately authorized native campaign and export its exact applicability, retained attempts, evidence, freshness and residual-gap record.',
            HOLD_REVIEW: 'Refresh due evidence, applicability decisions or campaign review before qualification review.',
            HOLD_GAPS: 'Resolve or formally disposition every OPEN campaign gap and retain the original failed/blocked attempts.',
            HOLD_UNCERTAIN: 'Reconcile campaign scope, attempts, evidence provenance or reviewer state before relying on the packet.',
            HOLD_SCOPE: 'Use evidence for the exact selected site/cell/campaign/platform/tuple/service/topology generation.'
        }[result],
        'limits': [
            'A ready result is mechanical evidence-packet readiness only.',
            'The independent qualification decision and active PlatformProfile record are separate controlled records.',
            'CI never contacts a native target, executes tests, publishes qualification, applies infrastructure or activates production.'
        ]
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('intent', type=Path)
    parser.add_argument('--as-of')
    parser.add_argument('--expected-status', choices=(
        READY, HOLD_NONE, HOLD_REVIEW, HOLD_GAPS, HOLD_UNCERTAIN, HOLD_SCOPE
    ))
    args = parser.parse_args()
    try:
        as_of = campaign.target.instant(args.as_of, 'as_of') if args.as_of else datetime.now(timezone.utc)
        result = evaluate(load(args.intent), as_of=as_of)
        print(json.dumps(result, indent=2))
        if args.expected_status is not None:
            return 0 if result['status'] == args.expected_status else 2
        return 0 if result['status'] == READY else 2
    except (ValueError, OSError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({
            'kind': 'QUALIFICATION_CAMPAIGN_EVIDENCE_PREFLIGHT',
            'status': 'INVALID_QUALIFICATION_CAMPAIGN_READINESS_INTENT',
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
