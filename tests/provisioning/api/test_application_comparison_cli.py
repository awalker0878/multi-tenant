"""Application comparison client fixtures confer no owner or native authority."""
from __future__ import annotations

import copy
import io
import json
import unittest
from unittest.mock import patch

import httpx

from provisioner.cli import assessments, operator

STAMP = '2026-09-30T06:00:00+00:00'
DIGEST = 'a' * 64


def command():
    return ['assessments', 'compare-application', '--source-environment', 'source',
        '--source-generation', '7', '--application-group', 'app-1', '--draft-revision', '1',
        '--draft-record-digest', DIGEST, '--member-profile', 'db', 'linux-uefi',
        '--member-profile', 'web', 'linux-uefi', '--destination', 'target-a', '7',
        '--destination', 'target-b', '7', '--capacity', 'target-a', 'pool', 'pool-1',
        '--capacity', 'target-b', 'pool', 'pool-1', '--method', 'COLD_VM_CONVERSION',
        '--network-mode', 'routed', '--data-mode', 'offline']


def selected(argv=None):
    args = operator.build_parser().parse_args(['--api-url', 'https://control.example',
        '--token-stdin', *(argv or command())])
    return operator._request(args)[3]


def report(document):
    def binding(env, family):
        return {'environmentId': env, 'generation': 7, 'endpointId': env + '-endpoint',
            'nativeScopeId': env + '-scope', 'platformFamily': family,
            'productTupleId': 'tuple-' + env, 'productTupleDigest': 'b' * 64,
            'observation': {'rawSnapshotDigest': 'c' * 64, 'assessmentSnapshotDigest': 'd' * 64,
                'normalizerVersion': 'hosting-assessment-normalizer/2', 'capturedAt': STAMP,
                'collectionCompleteness': 'COMPLETE', 'assessmentCompleteness': 'COMPLETE'},
            'superseded': False, 'latestObservation': {'generation': 7,
                'rawSnapshotDigest': 'c' * 64, 'capturedAt': STAMP,
                'collectionCompleteness': 'COMPLETE', 'collectionErrors': [], 'missingPrivileges': []}}
    scope = {'organization_id': 'org', 'tenant_id': 'tenant', 'site_id': 'source-site',
        'security_domain_id': 'wsd', 'endpoint_id': 'source-endpoint',
        'native_scope_id': 'source-scope', 'platform_family': 'vmware'}
    review = {'format': 'hosting-application-review-status/1', 'environmentId': 'source',
        'scope': scope, 'applicationGroupId': 'app-1', 'draftRevision': 1,
        'draftRecordDigest': DIGEST, 'proposalDigest': 'b' * 64, 'generation': 7,
        'resultDigest': 'c' * 64, 'latestGeneration': 7, 'latestDraftRevision': 1,
        'checkedAt': STAMP, 'status': 'REVIEWED_ASSESSMENT_ONLY', 'ownerDecision': 'ACCEPT_FOR_ASSESSMENT',
        'ownerId': 'owner', 'reviewReference': 'CHG-1', 'evidenceId': 'review-1', 'evidenceRevision': 1,
        'evidenceDigest': 'e' * 64, 'reviewedAt': '2026-09-30T05:59:00+00:00',
        'expiresAt': '2026-09-30T06:30:00+00:00', 'candidateDigest': 'f' * 64,
        'unknownDependencyCount': 0, 'dependencyEvidenceVerified': False,
        'ownershipAccepted': False, 'executionAuthorized': False}
    rows = []
    for name in ('target-a', 'target-b'):
        rows.append({'environmentId': name, 'status': 'CONDITIONAL',
            'capacityIdentity': [name + '-endpoint', name + '-scope', 'openstack', 'pool', 'pool-1'],
            'capacity': {'basis': 'SUM_OF_OBSERVED_LOGICAL_VM_REQUIREMENTS', 'memberCount': 2,
                'resources': {k: {'required': need, 'available': available} for k, need, available in
                    [('VM_COUNT', 2, 4), ('VCPU', 8, 16), ('MEMORY', 16000, 32000), ('STORAGE', 40000, 80000)]},
                'reservationHeld': False, 'transientAndRecoveryFootprintIncluded': False},
            'issues': [{'severity': 'CONDITION', 'code': code} for code in
                ('APPLICATION_POLICY_DATA_REVIEW_REQUIRED', 'APPLICATION_RESERVATION_NOT_HELD')],
            'members': [{'workloadId': name, 'nativeVm': ['source-endpoint', 'source-scope', 'vmware', 'vm', name],
                'guestProfile': 'linux-uefi', 'assessedAt': STAMP, 'status': 'ELIGIBLE',
                'issues': [], 'executionAuthorized': False} for name in ('db', 'web')],
            'executionAuthorized': False})
    return {'format': 'hosting-application-comparison/2', 'selectionDigest': assessments.selection_digest(document),
        'applicationReview': review, 'sourceInput': binding('source', 'vmware'),
        'destinationInputs': [binding(name, 'openstack') for name in ('target-a', 'target-b')],
        'assessments': rows, 'status': 'ASSESSED_NOT_AUTHORIZED', 'consistency': 'PINNED_INPUTS_LIVE_RECHECKS',
        'ownershipAccepted': False, 'executionAuthorized': False, 'dependencyEvidenceVerified': False,
        'reservationHeld': False, 'startupOrder': ['db', 'web'], 'datasetCount': 2, 'consistencyGroupCount': 1}


def held(document, status='UNREVIEWED'):
    value = report(document)
    for key in ('startupOrder', 'datasetCount', 'consistencyGroupCount'):
        del value[key]
    value.update(status='HELD_APPLICATION_REVIEW', sourceInput=None, destinationInputs=[], assessments=[])
    review = value['applicationReview']
    review['status'] = status
    review['candidateDigest'] = review['unknownDependencyCount'] = None
    if status == 'UNREVIEWED':
        for key in ('ownerDecision', 'ownerId', 'reviewReference', 'evidenceId', 'evidenceRevision',
                    'evidenceDigest', 'reviewedAt', 'expiresAt'):
            review[key] = None
    elif status == 'REVOKED':
        review['ownerDecision'] = 'REVOKE'
    return value


class ApplicationComparisonCliTests(unittest.TestCase):
    def setUp(self):
        self.document = selected()
        self.value, self.calls = report(self.document), []

    def invoke(self, argv=None, handler=None):
        def respond(request):
            self.calls.append(request)
            return httpx.Response(200, json=self.value)
        out, err = io.StringIO(), io.StringIO()
        code = operator.run(['--api-url', 'https://control.example', '--token-stdin', *(argv or command())],
            stdin=io.StringIO('synthetic-access-token\n'), stdout=out, stderr=err,
            transport=httpx.MockTransport(handler or respond))
        return code, out.getvalue(), err.getvalue()

    def invalid(self):
        code, out, err = self.invoke()
        self.assertEqual((code, out), (3, ''))
        self.assertEqual(json.loads(err), {'error': 'APPLICATION_COMPARISON_RESPONSE_INVALID'})

    def test_exact_read_only_request_and_complete_response(self):
        code, out, err = self.invoke()
        self.assertEqual((code, err), (0, ''))
        self.assertEqual(json.loads(out), self.value)
        self.assertEqual(len(self.calls), 1)
        request = self.calls[0]
        self.assertEqual((request.method, request.url.path), ('POST', '/v1/assessments/applications/compare'))
        self.assertEqual(json.loads(request.content), self.document)
        self.assertEqual(request.headers['cache-control'], 'no-store')
        self.assertEqual(request.headers['authorization'], 'Bearer synthetic-access-token')
        self.assertNotIn('synthetic-access-token', out + err + str(request.url))
        self.assertNotIn('idempotency-key', request.headers)

    def test_held_and_revoked_reports_remain_valid_non_authorizing_answers(self):
        for status in ('UNREVIEWED', 'REVOKED', 'HELD_INCOMPLETE_INVENTORY', 'HELD_STALE_INVENTORY'):
            self.value = held(self.document, status)
            with self.subTest(status=status):
                self.assertEqual(self.invoke()[0], 0)
                self.assertEqual(self.value['assessments'], [])

    def test_each_selection_dimension_changes_the_digest(self):
        variants = [dict(self.document, method='REBUILD_RESTORE'),
                    dict(self.document, networkMode='renumber'), dict(self.document, dataMode='online'),
                    dict(self.document, draftRevision=2), dict(self.document, draftRecordDigest='f'*64)]
        for field in ('source', 'memberProfiles', 'destinations'):
            value = copy.deepcopy(self.document)
            if field == 'source': value[field]['generation'] = 8
            elif field == 'memberProfiles': value[field][1]['guestProfile'] = 'windows'
            else: value[field][0]['capacityNativeId'] = 'another-pool'
            variants.append(value)
        for value in variants:
            with self.subTest(value=value):
                self.assertNotEqual(assessments.selection_digest(value), assessments.selection_digest(self.document))
                self.value['selectionDigest'] = assessments.selection_digest(value)
                self.invalid()

    def test_old_or_missing_interpretation_is_rejected_without_alias(self):
        for change in ({'format': 'hosting-application-comparison/1'}, {'selectionDigest': 'bad'}):
            self.value = {**report(self.document), **change}
            self.invalid()
        self.value = report(self.document); del self.value['selectionDigest']; self.invalid()

    def test_dropped_duplicate_foreign_or_reordered_destinations_are_not_accepted(self):
        for change in ('drop', 'duplicate', 'foreign', 'reorder', 'generation', 'capacity'):
            self.value = report(self.document)
            if change == 'drop': self.value['assessments'].pop()
            elif change == 'duplicate': self.value['destinationInputs'][1] = self.value['destinationInputs'][0]
            elif change == 'foreign': self.value['assessments'][0]['environmentId'] = 'foreign'
            elif change == 'reorder': self.value['destinationInputs'].reverse()
            elif change == 'generation': self.value['destinationInputs'][0]['generation'] = 8
            else: self.value['assessments'][0]['capacityIdentity'][-1] = 'other-pool'
            with self.subTest(change=change): self.invalid()

    def test_members_cannot_be_dropped_duplicated_or_substituted(self):
        for change in ('drop', 'duplicate', 'guest', 'scope', 'identity', 'member'):
            self.value = report(self.document); members = self.value['assessments'][0]['members']
            if change == 'drop': members.pop()
            elif change == 'duplicate': members[1] = members[0]
            elif change == 'guest': members[0]['guestProfile'] = 'windows'
            elif change == 'scope': members[0]['nativeVm'][0] = 'other-endpoint'
            elif change == 'identity': members[0]['nativeVm'][-1] = 'another-vm'
            else: members[0]['workloadId'] = 'other'
            with self.subTest(change=change): self.invalid()

    def test_review_and_source_bindings_cannot_be_replaced(self):
        for field, replacement in (('environmentId', 'other'), ('draftRevision', 2),
                ('draftRecordDigest', 'f'*64), ('generation', 8), ('resultDigest', 'f'*64),
                ('candidateDigest', None), ('evidenceDigest', 'bad')):
            self.value = report(self.document); self.value['applicationReview'][field] = replacement
            with self.subTest(field=field): self.invalid()

    def test_all_authority_flags_remain_false_at_every_level(self):
        for flag in ('executionAuthorized', 'ownershipAccepted', 'reservationHeld', 'dependencyEvidenceVerified'):
            self.value = report(self.document); self.value[flag] = True
            with self.subTest(flag=flag): self.invalid()
        for select, flag in ((lambda v: v['applicationReview'], 'ownershipAccepted'),
                (lambda v: v['assessments'][0], 'executionAuthorized'),
                (lambda v: v['assessments'][0]['members'][0], 'executionAuthorized'),
                (lambda v: v['assessments'][0]['capacity'], 'reservationHeld'),
                (lambda v: v['assessments'][0]['capacity'], 'transientAndRecoveryFootprintIncluded')):
            self.value = report(self.document); select(self.value)[flag] = True; self.invalid()

    def test_capacity_unknown_and_blocked_answers_are_not_promoted(self):
        row = self.value['assessments'][0]
        row['capacity']['resources']['VCPU']['available'] = 6
        row['issues'].append({'severity': 'BLOCKER', 'code': 'APPLICATION_VCPU_CAPACITY_INSUFFICIENT'})
        row['status'] = 'BLOCKED'
        self.assertEqual(self.invoke()[0], 0)
        row['status'] = 'CONDITIONAL'; self.invalid()
        self.value = report(self.document); row = self.value['assessments'][0]
        row['capacity']['resources']['MEMORY']['available'] = None
        row['issues'].append({'severity': 'UNKNOWN', 'code': 'APPLICATION_MEMORY_CAPACITY_UNKNOWN'})
        row['status'] = 'UNKNOWN'
        self.assertEqual(self.invoke()[0], 0)
        row['issues'].pop(); row['status'] = 'CONDITIONAL'; self.invalid()

    def test_capacity_numbers_cannot_be_boolean_negative_overflow_or_different_demands(self):
        for bad in (True, -1, 2**63, '8', 0, 9):
            self.value = report(self.document)
            self.value['assessments'][0]['capacity']['resources']['VCPU']['required'] = bad
            with self.subTest(bad=bad): self.invalid()
        self.value = report(self.document); self.value['assessments'][0]['capacity']['memberCount'] = True
        self.invalid()

    def test_missing_unknown_or_shortage_findings_are_invalid(self):
        for field, amount in (('required', None), ('available', None), ('available', 1)):
            self.value = report(self.document)
            self.value['assessments'][0]['capacity']['resources']['STORAGE'][field] = amount
            with self.subTest(field=field, amount=amount): self.invalid()

    def test_member_and_aggregate_status_must_preserve_blockers(self):
        row = self.value['assessments'][0]
        row['members'][0]['issues'] = [{'severity': 'BLOCKER', 'code': 'GUEST_INCOMPATIBLE'}]
        self.invalid()
        row['members'][0]['status'] = 'BLOCKED'; self.invalid()
        row['status'] = 'BLOCKED'; self.assertEqual(self.invoke()[0], 0)
        row['members'][0]['issues'][0]['severity'] = 'INFORMATION'; self.invalid()

    def test_no_pool_selection_stays_explicit(self):
        argv = command()
        for _ in range(2):
            index = argv.index('--capacity'); del argv[index:index+4]
        document = selected(argv); self.value = report(document)
        for row in self.value['assessments']:
            row['capacityIdentity'] = None
            row['status'] = 'UNKNOWN'
            for resource, quantities in row['capacity']['resources'].items():
                quantities['available'] = None
                row['issues'].append({'severity': 'UNKNOWN', 'code': f'APPLICATION_{resource}_CAPACITY_UNKNOWN'})
        self.assertEqual(self.invoke(argv)[0], 0)
        self.value['assessments'][0]['capacity']['resources']['VCPU']['available'] = 16
        self.assertEqual(self.invoke(argv)[0], 3)
        self.value['assessments'][0]['capacityIdentity'] = ['foreign']
        self.assertEqual(self.invoke(argv)[0], 3)

    def test_held_report_cannot_include_calculation_or_ready_candidate(self):
        self.value = held(self.document); self.value['assessments'] = report(self.document)['assessments']
        self.invalid()
        self.value = held(self.document); self.value['applicationReview'] = report(self.document)['applicationReview']
        self.invalid()
        self.value = report(self.document); self.value['applicationReview'] = held(self.document)['applicationReview']
        self.invalid()

    def test_unknown_dependencies_require_unknown_findings(self):
        review = self.value['applicationReview']
        review.update(status='REVIEWED_WITH_UNKNOWNS', unknownDependencyCount=1)
        self.invalid()
        for row in self.value['assessments']:
            row['issues'].append({'severity': 'UNKNOWN', 'code': 'APPLICATION_DEPENDENCIES_UNRESOLVED'})
            row['status'] = 'UNKNOWN'
        self.assertEqual(self.invoke()[0], 0)

    def test_latest_snapshot_and_normalizer_mismatch_are_not_current_evidence(self):
        for changes in ({'normalizerVersion': 'hosting-assessment-normalizer/1'},
                        {'rawSnapshotDigest': 'f'*64}, {'capturedAt': 'not-a-time'}):
            self.value = report(self.document)
            self.value['sourceInput']['observation'].update(changes); self.invalid()
        self.value = report(self.document); self.value['sourceInput']['superseded'] = True; self.invalid()

    def test_request_limits_and_exact_positive_integer_selections_fail_before_http(self):
        for field, bad in (('--source-generation', '0'), ('--source-generation', str(2**63)),
                ('--draft-revision', '-1'), ('--draft-record-digest', 'A'*64),
                ('--application-group', '../escape')):
            argv = command(); argv[argv.index(field)+1] = bad
            with self.subTest(field=field): self.assertEqual(self.invoke(argv)[:2], (3, ''))
        self.assertEqual(self.calls, [])
        args = operator.build_parser().parse_args(['--api-url','https://control.example','--token-stdin',*command()])
        for name in ('source_generation', 'draft_revision'):
            old = getattr(args,name); setattr(args,name,True)
            with self.assertRaises(ValueError): operator._request(args)
            setattr(args,name,old)

    def test_duplicate_members_targets_and_capacity_selectors_fail_before_http(self):
        variants = [command()+['--member-profile','db','linux'], command()+['--destination','target-a','7'],
            command()+['--destination','source','7'], command()+['--capacity','target-a','pool','other'],
            command()+['--capacity','foreign','pool','pool-1']]
        for argv in variants:
            with self.subTest(argv=argv): self.assertEqual(self.invoke(argv)[0],3)
        self.assertEqual(self.calls, [])

    def test_member_destination_product_is_bounded_without_truncation(self):
        args = operator.build_parser().parse_args(['--api-url','https://control.example','--token-stdin',*command()])
        args.member_profile = [[f'vm-{i}','linux'] for i in range(100)]
        self.assertEqual(len(operator._request(args)[3]['memberProfiles']),100)
        args.destination.append(['target-c','7'])
        with self.assertRaises(ValueError): operator._request(args)
        args.member_profile = [['single','linux']]
        with self.assertRaises(ValueError): operator._request(args)

    def test_missing_and_unexpected_success_fields_are_rejected(self):
        valid = report(self.document)
        for key in valid:
            self.value = {name: item for name,item in valid.items() if name != key}
            with self.subTest(key=key): self.invalid()
        self.value = {**valid, 'jobId': 'not-a-job'}; self.invalid()

    def test_non_200_success_and_malformed_json_cannot_be_reported_as_advice(self):
        for status, content in ((202,json.dumps(self.value).encode()), (204,b''),
                (200,b'{"x":1,"x":2}'),(200,b'{"x":1e999}'),(200,b'\xff')):
            def reply(request):
                self.calls.append(request);return httpx.Response(status,content=content)
            code,out,err=self.invoke(handler=reply)
            with self.subTest(status=status):
                self.assertEqual((code,out),(3,''))
                self.assertEqual(json.loads(err)['error'],'APPLICATION_COMPARISON_RESPONSE_INVALID')

    def test_api_errors_and_connection_loss_never_launch_or_retry(self):
        for status in (302,401,403,404,422,503):
            def reply(request):
                self.calls.append(request)
                return httpx.Response(status,json={'error':{'code':'APPLICATION_ASSESSMENT_UNAVAILABLE',
                    'message':'private internals'}},headers={'location':'https://other.invalid'})
            before=len(self.calls);code,out,err=self.invoke(handler=reply)
            with self.subTest(status=status):
                self.assertEqual((code,out),(2,''));self.assertEqual(len(self.calls),before+1)
                self.assertNotIn('private',err)
        def lost(request):
            self.calls.append(request);raise httpx.ReadTimeout('private token')
        before=len(self.calls);code,out,err=self.invoke(handler=lost)
        self.assertEqual((code,out),(3,''));self.assertEqual(len(self.calls),before+1)
        self.assertEqual(json.loads(err),{'error':'API_UNAVAILABLE'})

    def test_response_bound_and_interruption_discard_partial_output(self):
        with patch.object(assessments,'MAX_RESPONSE_BYTES',100):
            self.invalid()
        def interrupt(request):
            self.calls.append(request);raise KeyboardInterrupt()
        code,out,err=self.invoke(handler=interrupt)
        self.assertEqual((code,out),(130,''));self.assertEqual(json.loads(err),{'error':'INTERRUPTED'})

    def test_single_vm_command_retains_existing_request_contract(self):
        argv=['assessments','compare','--source-environment','source','--source-generation','7',
            '--destination','target-a','7','--destination','target-b','7',
            '--workload-native-id','vm/with:native-id','--guest-profile','linux-uefi',
            '--method','REBUILD_RESTORE','--network-mode','routed','--data-mode','offline']
        document=selected(argv)
        self.assertEqual(document['workloadNativeId'],'vm/with:native-id')
        self.assertNotIn('applicationGroupId',document)
        self.value={'format':'hosting-discovery-comparison/1','executionAuthorized':False}
        self.assertEqual(self.invoke(argv)[0],0)
        self.assertEqual(self.calls[-1].url.path,'/v1/assessments/compare')

    def test_client_does_not_import_controller_or_platforms(self):
        import ast
        from pathlib import Path
        tree=ast.parse(Path(assessments.__file__).read_text())
        imports=[node.module for node in ast.walk(tree) if isinstance(node,ast.ImportFrom)]
        self.assertFalse(any(name and name.startswith(('provisioner','tools','scripts')) for name in imports))
        self.assertFalse(any(isinstance(node,ast.ImportFrom) and node.level for node in ast.walk(tree)))


if __name__ == '__main__': unittest.main()
