"""Bounded, publish-once rehearsal of explicitly inventoried retained state.

The output is a private quarantine archive and a reconciliation proposal. It is
not a database importer, a job, an owner lease or authorization to retry a native
operation. Current persistence/reconciliation owners retain those responsibilities.
The first supported Terraform projection is the OpenStack workload v1 contract;
other retained paths must be inventoried and remain held until separately designed.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path, PurePosixPath
import re
from datetime import datetime, timezone

from provisioner.controlplane.persistence.store import NativeBinding, canonical_record_digest
from provisioner.domain.enterprise_records import validate_record
from provisioner.execution import readback_core as c
from provisioner.execution.neutron_observe import strict_loads
from provisioner.execution.run_files import (digest, encoded, private_path, read_private,
                                           require, sync_directory, write_new)
from provisioner.execution.terraform_apply import ATTEMPT_FIELDS, completed_history
from provisioner.execution.terraform_run import backend_settings
from .contracts import RETAINED_OUTPUT_CONTRACTS

FORMAT = 'hosting-retained-state-rehearsal/1'
SCOPE_FIELDS = {'organizationId', 'tenantId', 'securityDomainId', 'workloadId',
                'endpointId', 'nativeScopeId', 'locationId', 'platformFamily',
                'environmentKey', 'siteKey'}
COUNTS = {'files', 'workloads', 'terraformRuns', 'terraformStarts',
          'terraformResults', 'deliveryEvents'}
BUNDLE_FIELDS = {'format', 'source_commit', 'catalog_id', 'root', 'scope', 'state_key',
                 'operation_id', 'generation', 'created_at', 'terraform_version',
                 'terraform_sha256', 'source_files', 'artifacts', 'review_status', 'status'}
BUNDLE_ARTIFACTS = {'inputs.json', 'backend.json', 'backend.hcl', 'environment.json',
                    'contact.json', 'references.json', 'terraform.rc', 'version.json',
                    'saved.tfplan', 'plan.json', 'review.json'}
MAX_FILES, MAX_FILE_BYTES, MAX_BATCH_BYTES = 10000, 8 * 1024 * 1024, 64 * 1024 * 1024


def _path(value: str) -> str:
    require(isinstance(value, str) and value and len(value) <= 1024,
            'Bounded relative source path required')
    path = PurePosixPath(value)
    require(not path.is_absolute() and '..' not in path.parts and '.' not in path.parts
            and str(path) == value, 'Canonical relative source path required')
    return value


def _positive(value) -> bool:
    return type(value) is int and 0 < value < 2**63


def _timestamp(value) -> datetime:
    result = c.timestamp(value)
    require(result.utcoffset().total_seconds() == 0, 'UTC retained-state timestamp required')
    return result


def _legacy(scope, *, phase=True):
    result = {'environment_key': scope['environmentKey'], 'site_key': scope['siteKey'],
              'platform': scope['platformFamily'], 'tenant_key': scope['tenantId'],
              'wsd_key': scope['securityDomainId']}
    if phase:
        result['phase'] = 'workloads'
    return result


def _binding(value, scope) -> NativeBinding:
    binding = NativeBinding.from_record(value)
    require((binding.platform_family, binding.endpoint_id, binding.native_scope_id) ==
            (scope['platformFamily'], scope['endpointId'], scope['nativeScopeId']),
            'Retained native binding belongs to another scope')
    return binding


class Snapshot:
    """One complete immutable byte inventory, read before conversion starts."""

    def __init__(self, root: Path, manifest: dict):
        self.root = private_path(root, directory=True)
        self.raw: dict[str, bytes] = {}
        sealed = manifest['sourceFileSha256']
        require(isinstance(sealed, dict) and 1 <= len(sealed) <= MAX_FILES,
                'Explicit nonempty retained-file inventory required')
        actual = set()
        for path in sorted(self.root.rglob('*')):
            require(not path.is_symlink(), 'Symlink in retained-state inventory')
            if path.is_file():
                actual.add(path.relative_to(self.root).as_posix())
                require(len(actual) <= MAX_FILES, 'Retained file enumeration exceeds bound')
        require(actual == set(sealed), 'Enumerated retained files differ from sealed inventory')
        total = 0
        for name, expected in sealed.items():
            _path(name)
            require(isinstance(expected, str) and c.HEX.fullmatch(expected),
                    'Exact retained-file digest required')
            path = self.root / name
            require(path.stat().st_size <= MAX_FILE_BYTES, 'Retained file exceeds byte bound')
            raw = read_private(path)
            total += len(raw)
            require(total <= MAX_BATCH_BYTES and digest(raw) == expected,
                    'Retained bytes changed or exceed batch bound')
            self.raw[name] = raw
        self.used: set[str] = set()

    def json(self, name):
        _path(name)
        require(name in self.raw, 'Required retained record is absent from inventory')
        self.used.add(name)
        result = strict_loads(self.raw[name])
        require(isinstance(result, dict), 'Retained record must be a JSON object')
        return result

    def files_under(self, directory):
        _path(directory)
        result = sorted(name for name in self.raw if name.startswith(directory + '/'))
        require(result, 'Declared retained directory has no inventoried files')
        return result

    def recheck(self):
        # Re-enumerate as well as rehash: newly published receipts are significant.
        actual = set()
        for path in self.root.rglob('*'):
            require(not path.is_symlink(), 'Symlink appeared in retained-state inventory')
            if path.is_file():
                actual.add(path.relative_to(self.root).as_posix())
                require(len(actual) <= MAX_FILES, 'Retained file enumeration exceeds bound')
        require(actual == set(self.raw) and all(read_private(self.root / name) == raw
                for name, raw in self.raw.items()), 'Retained inventory changed during rehearsal')


def _manifest(value, as_of):
    c.exact_keys(value, {'format', 'batchId', 'capturedAt', 'scope', 'sourceFileSha256',
                         'workloadFiles', 'terraformRuns', 'terraformLedgers',
                         'deliveryJournals', 'sourceCounts', 'evidence'})
    require(value['format'] == FORMAT, 'Unsupported retained-state rehearsal version')
    c.identifier(value['batchId'])
    require(_timestamp(value['capturedAt']) <= as_of, 'Future retained inventory')
    c.exact_keys(value['scope'], SCOPE_FIELDS)
    for field, item in value['scope'].items():
        if field == 'nativeScopeId':
            c.text(item, length=512)
        else:
            c.identifier(item)
    require(value['scope']['platformFamily'] in {'vmware', 'nutanix', 'openstack'},
            'Unsupported retained platform')
    groups = []
    for key in ('workloadFiles', 'terraformRuns', 'terraformLedgers', 'deliveryJournals'):
        names = value[key]
        require(isinstance(names, list) and len(names) <= MAX_FILES and
                len(set(names)) == len(names), 'Duplicate or unbounded retained group')
        groups.extend(_path(name) for name in names)
    require(len(groups) == len(set(groups)), 'Retained source belongs to more than one group')
    c.exact_keys(value['sourceCounts'], COUNTS)
    require(all(type(n) is int and 0 <= n <= MAX_FILES for n in value['sourceCounts'].values()),
            'Explicit bounded source counts required')
    c.exact_keys(value['evidence'], {'nativeInventory', 'oldWriterFreeze', 'newOwnerSnapshot'})
    for name in value['evidence'].values():
        if name is not None:
            _path(name)


def _evidence(snapshot, manifest, key, marker, fields, holds, as_of):
    name = manifest['evidence'][key]
    if name is None:
        holds.add('HOLD_MISSING_' + key.upper())
        return None
    value = snapshot.json(name)
    c.exact_keys(value, {'format', 'scope', *fields})
    require(value['format'] == marker and value['scope'] == manifest['scope'],
            'Retained reconciliation evidence version or scope differs')
    time_field = 'frozenAt' if key == 'oldWriterFreeze' else 'capturedAt'
    at = _timestamp(value[time_field])
    captured = _timestamp(manifest['capturedAt'])
    require(at <= as_of and (at <= captured if key == 'oldWriterFreeze' else at >= captured),
            'Evidence does not surround the retained-state boundary')
    c.text(value['observerId'])
    return value


def _workloads(snapshot, manifest, holds):
    scope, bindings, projections = manifest['scope'], {}, []
    seen = set()
    for name in manifest['workloadFiles']:
        record = snapshot.json(name)
        require(not validate_record(record) and record['kind'] == 'Workload',
                'Authentic canonical hosting.platform/v1 Workload required')
        meta = record['metadata']
        require((meta['organizationId'], meta['tenantId'], meta['workloadId'], meta['wsdId']) ==
                (scope['organizationId'], scope['tenantId'], scope['workloadId'],
                 scope['securityDomainId']), 'Canonical workload scope differs')
        identity = (meta['workloadId'], meta['revision'])
        require(identity not in seen, 'Duplicate retained workload revision')
        seen.add(identity)
        require(len(seen) == 1, 'This rehearsal accepts one current workload revision only')
        for machine in record['spec']['machines']:
            for resource in (machine, *machine['disks'], *machine['nics']):
                for history in resource['bindings']:
                    binding = _binding(history['binding'], scope)
                    if history['role'] == 'RETIRED':
                        holds.add('HOLD_RETIRED_BINDING_REQUIRES_DATA_DISPOSITION')
                    key = binding.key()
                    require(key not in bindings, 'Duplicate retained native identity')
                    bindings[key] = history['binding']
        for dataset in record['spec']['datasets']:
            for value in dataset['sourceBindings']:
                binding = _binding(value, scope)
                # Dataset lineage can name a volume already represented by a disk.
                bindings.setdefault(binding.key(), value)
        projections.append({'sourcePath': name, 'sourceDigest': digest(snapshot.raw[name]),
                            'canonicalRecordDigest': canonical_record_digest(record),
                            'record': record})
    if not projections:
        holds.add('HOLD_NO_CANONICAL_WORKLOAD_INVENTORY')
    if not bindings:
        holds.add('HOLD_NO_RETAINED_NATIVE_IDENTITY_INVENTORY')
    return bindings, projections


def _runs(snapshot, manifest, native, holds, as_of):
    scope, runs, bindings, stages, identities = manifest['scope'], {}, {}, [], set()
    for directory in manifest['terraformRuns']:
        bundle_name = directory + '/bundle.json'
        bundle = snapshot.json(bundle_name)
        c.exact_keys(bundle, BUNDLE_FIELDS)
        require(bundle['format'] == 'hosting-terraform-bundle/1' and
                bundle['status'] == 'AWAITING_EXACT_PLAN_REVIEW', 'Unknown retained Terraform bundle')
        require(bundle['scope'] == _legacy(scope), 'Retained Terraform bundle scope differs')
        require(re.fullmatch(r'[0-9a-f]{40}', bundle['source_commit']) and
                _positive(bundle['generation']) and _timestamp(bundle['created_at']) <= as_of,
                'Invalid retained Terraform bundle identity or chronology')
        c.identifier(bundle['operation_id'])
        identity = (bundle['operation_id'], bundle['generation'])
        require(identity not in identities, 'Duplicate retained bundle operation/generation')
        identities.add(identity)
        require(isinstance(bundle['artifacts'], dict) and BUNDLE_ARTIFACTS <= set(bundle['artifacts'])
                and set(bundle['artifacts']) <= BUNDLE_ARTIFACTS | {'ca.pem', 'transition.json'},
                'Unknown or incomplete retained Terraform artifact contract')
        require(isinstance(bundle['source_files'], dict) and bundle['source_files'],
                'Retained Terraform source manifest is empty')
        for prefix, artifacts in (('', bundle['artifacts']), ('source/', bundle['source_files'])):
            for file, expected in artifacts.items():
                _path(file)
                name = directory + '/' + prefix + file
                require(name in snapshot.raw and digest(snapshot.raw[name]) == expected,
                        'Retained Terraform artifact or source digest differs')
                snapshot.used.add(name)
        require(isinstance(bundle['terraform_sha256'], str) and c.HEX.fullmatch(bundle['terraform_sha256']),
                'Retained Terraform binary digest required')
        inputs = snapshot.json(directory + '/inputs.json')
        backend_settings(snapshot.json(directory + '/backend.json'), bundle['state_key'])
        require(all(inputs.get(key) == value for key, value in _legacy(scope, phase=False).items()
                    if key != 'platform'), 'Retained Terraform input scope differs')
        require(isinstance(inputs.get('members'), dict) and inputs['members'],
                'Retained Terraform member inventory is missing')
        key = digest(snapshot.raw[bundle_name])
        require(key not in runs, 'Duplicate retained Terraform bundle')
        runs[key] = {'bundle': bundle, 'directory': directory}
        contact = snapshot.json(directory + '/contact.json')
        c.exact_keys(contact, {'format', 'source_commit', 'scope', 'operation_id', 'generation',
                              'input_sha256', 'backend_sha256', 'environment_sha256',
                              'cloud_sha256', 'ca_sha256', 'valid_from', 'valid_until', 'change_ref'})
        require(contact['format'] == 'hosting-terraform-contact/2' and
                contact['scope'] == bundle['scope'] and contact['source_commit'] == bundle['source_commit']
                and contact['operation_id'] == bundle['operation_id'] and
                _positive(contact['generation']) and contact['generation'] == bundle['generation'],
                'Retained contact version or bundle identity differs')
        for field, artifact in (('input_sha256', 'inputs.json'), ('backend_sha256', 'backend.json'),
                                ('environment_sha256', 'environment.json')):
            require(contact[field] == digest(snapshot.raw[directory + '/' + artifact]),
                    'Retained contact artifact digest differs')
        require(_timestamp(contact['valid_from']) <= _timestamp(bundle['created_at']) <
                _timestamp(contact['valid_until']), 'Bundle was not created inside its retained contact window')
        if 'transition.json' in bundle['artifacts']:
            transition = snapshot.json(directory + '/transition.json')
            require(transition.get('format') in {'hosting-openstack-transition/1', 'hosting-platform-transition/1'},
                    'Unknown retained lifecycle transition version')
            require(transition.get('scope') == bundle['scope'] and transition.get('input_sha256') ==
                    digest(snapshot.raw[directory + '/inputs.json']), 'Retained lifecycle transition binding differs')
            holds.add('HOLD_RETAINED_TRANSITION_REQUIRES_OWNER_REVALIDATION')
        for optional in ('approval.json', 'result.json', 'apply.log', 'plan.log', 'init.log'):
            name = directory + '/' + optional
            if name in snapshot.raw:
                snapshot.used.add(name)
        approval_name = directory + '/approval.json'
        if approval_name in snapshot.raw:
            approval = snapshot.json(approval_name)
            c.exact_keys(approval, {'format', 'bundle_sha256', 'review_sha256', 'operation_id',
                                  'generation', 'valid_from', 'valid_until', 'change_ref'})
            require(approval['format'] == 'hosting-terraform-approval/1' and
                    approval['bundle_sha256'] == key and approval['operation_id'] == bundle['operation_id']
                    and _positive(approval['generation']) and approval['generation'] == bundle['generation'] and
                    approval['review_sha256'] == digest(snapshot.raw[directory + '/review.json']),
                    'Retained approval does not bind its exact old bundle')
        outputs_name = directory + '/outputs.json'
        if outputs_name not in snapshot.raw:
            holds.add('HOLD_MISSING_RETAINED_TERRAFORM_OUTPUTS')
            continue
        outputs = snapshot.json(outputs_name)
        require(outputs.get('scope', {}).get('value') == _legacy(scope) and
                outputs.get('delivery_state', {}).get('value') == 'PREPARED_NOT_QUALIFIED_NOT_SERVICE_READY',
                'Retained Terraform output scope or state differs')
        members = outputs.get('members', {}).get('value')
        require(isinstance(members, dict) and set(members) == set(inputs['members']),
                'Retained Terraform output members differ')
        output_contract = RETAINED_OUTPUT_CONTRACTS.get((bundle['format'],
            scope['platformFamily'], bundle['scope']['phase']))
        if output_contract is None:
            holds.add('HOLD_TERRAFORM_PROFILE_NOT_IMPLEMENTED')
            continue
        for member_id, output in members.items():
            require(isinstance(output, dict) and output.get('delivery_state') ==
                    'PREPARED_NOT_QUALIFIED_NOT_SERVICE_READY', 'Invalid retained member state')
            member_bindings = []
            for field, kind in output_contract.scalar_bindings:
                value = {'platformFamily': scope['platformFamily'], 'endpointId': scope['endpointId'],
                         'nativeScopeId': scope['nativeScopeId'], 'resourceKind': kind,
                         'nativeId': output.get(field)}
                binding = _binding(value, scope)
                require(binding.key() not in bindings, 'Duplicate Terraform native identity')
                bindings[binding.key()] = value
                member_bindings.append(binding.key())
            for field, kind in output_contract.array_bindings:
                require(isinstance(output.get(field), list), 'Explicit data-volume inventory required')
                for native_id in output[field]:
                    value = {'platformFamily': scope['platformFamily'], 'endpointId': scope['endpointId'],
                             'nativeScopeId': scope['nativeScopeId'], 'resourceKind': kind, 'nativeId': native_id}
                    binding = _binding(value, scope)
                    require(binding.key() not in bindings, 'Duplicate Terraform native identity')
                    bindings[binding.key()] = value
                    member_bindings.append(binding.key())
            explicit = [value['lifecycle_stage'] for value in (inputs['members'][member_id], output)
                        if 'lifecycle_stage' in value]
            require(all(stage in {'prepared', 'bootstrap'} for stage in explicit) and
                    len(set(explicit)) <= 1, 'Retained lifecycle stages conflict or are unsupported')
            observed = {native[key]['lifecycleStage'] for key in member_bindings if key in native}
            stage = explicit[0] if explicit else None
            if len(observed) != 1 or None in observed or set(member_bindings) - set(native):
                holds.add('HOLD_UNRESOLVED_NATIVE_LIFECYCLE_STAGE')
            elif stage is not None and observed != {stage}:
                holds.add('HOLD_LIFECYCLE_STAGE_NATIVE_MISMATCH')
            elif stage is None:
                stage = next(iter(observed))
            stages.append({'bundleDigest': key, 'memberId': member_id, 'lifecycleStage': stage,
                           'stageOrigin': 'EXPLICIT_LEGACY' if explicit else
                                          'NATIVE_OBSERVATION' if stage else 'UNRESOLVED',
                           'nativeEvidenceDigest': manifest['sourceFileSha256'].get(
                               manifest['evidence']['nativeInventory']),
                           'originalsChanged': False})
    return runs, bindings, stages


def _attempts(snapshot, manifest, runs, holds, as_of):
    projections, count_start, count_result, attempted = [], 0, 0, set()
    scope = _legacy(manifest['scope'])
    for directory in manifest['terraformLedgers']:
        starts, results = {}, {}
        for name in snapshot.files_under(directory):
            leaf = name[len(directory) + 1:]
            if leaf == 'writer.lock':
                snapshot.used.add(name)
                continue
            if leaf == 'head.json':
                continue
            require('/' not in leaf and (leaf.endswith('.started.json') or leaf.endswith('.result.json')),
                    'Unknown retained Terraform ledger record')
            value = snapshot.json(name)
            started = leaf.endswith('.started.json')
            fields = ATTEMPT_FIELDS if started else (ATTEMPT_FIELDS | (
                {'completed_at', 'outputs_sha256'} if value.get('status') ==
                'APPLIED_REQUIRES_NATIVE_ACCEPTANCE' else {'stopped_at'}))
            c.exact_keys(value, fields)
            require(value['format'] == 'hosting-terraform-attempt/1' and value['scope'] == scope
                    and _positive(value['generation']) and c.HEX.fullmatch(value['bundle_sha256']),
                    'Retained Terraform attempt contract or scope differs')
            c.identifier(value['operation_id']); c.text(value['change_ref'])
            require(_timestamp(value['started_at']) <= as_of, 'Future retained native attempt')
            identity = digest(encoded({'operation': value['operation_id'], 'generation': value['generation']}))
            require(leaf == identity + ('.started.json' if started else '.result.json'),
                    'Retained Terraform attempt filename differs')
            if started:
                require(value['status'] == 'STARTED_OUTCOME_UNKNOWN', 'Unknown retained start status')
                starts[identity] = value
                count_start += 1
            else:
                require(value['status'] in {'APPLIED_REQUIRES_NATIVE_ACCEPTANCE', 'HOLD_RECONCILIATION_REQUIRED'},
                        'Unknown retained result status')
                at = value['completed_at'] if 'completed_at' in value else value['stopped_at']
                require(_timestamp(value['started_at']) <= _timestamp(at) <= as_of,
                        'Retained Terraform result chronology differs')
                results[identity] = value
                count_result += 1
        if set(results) - set(starts):
            holds.add('HOLD_ORPHAN_TERRAFORM_RESULT')
        ordered = sorted(starts.values(), key=lambda row: _timestamp(row['started_at']))
        for identity, start in starts.items():
            identity_key = (start['operation_id'], start['generation'])
            require(identity_key not in attempted, 'Duplicate retained operation/generation across ledgers')
            attempted.add(identity_key)
            result, run = results.get(identity), runs.get(start['bundle_sha256'])
            if run is None:
                holds.add('HOLD_ATTEMPT_BUNDLE_UNAVAILABLE')
            else:
                bundle = run['bundle']
                require((bundle['operation_id'], bundle['generation']) == identity_key,
                        'Attempt points to a different native operation')
                require(_timestamp(bundle['created_at']) <= _timestamp(start['started_at']),
                        'Retained native attempt precedes its bundle')
            outcome = 'UNKNOWN'
            if result is not None:
                require(all(result[field] == start[field] for field in ATTEMPT_FIELDS - {'status'}),
                        'Retained completion identity changed')
                if result['status'] == 'APPLIED_REQUIRES_NATIVE_ACCEPTANCE':
                    require(isinstance(result['outputs_sha256'], str) and c.HEX.fullmatch(result['outputs_sha256']),
                            'Retained outcome output digest required')
                    if run is not None:
                        output_name = run['directory'] + '/outputs.json'
                        require(output_name in snapshot.raw and digest(snapshot.raw[output_name]) == result['outputs_sha256'],
                                'Retained result output bytes differ')
                        local_result_name = run['directory'] + '/result.json'
                        require(local_result_name in snapshot.raw and snapshot.json(local_result_name) == result,
                                'Bundle outcome differs from its immutable ledger')
                    outcome = 'LEGACY_APPLIED_REQUIRES_NATIVE_ACCEPTANCE'
            if outcome == 'UNKNOWN':
                holds.add('HOLD_UNCERTAIN_NATIVE_START_REQUIRES_CANONICAL_RECOVERY')
            projections.append({'operationId': start['operation_id'], 'generation': start['generation'],
                                'bundleDigest': start['bundle_sha256'], 'outcome': outcome,
                                'retryAuthorized': False})
        head_name = directory + '/head.json'
        if ordered:
            last = ordered[-1]
            identity = digest(encoded({'operation': last['operation_id'], 'generation': last['generation']}))
            require(head_name in snapshot.raw and snapshot.json(head_name) == results.get(identity, last),
                    'Retained Terraform head does not match latest attempt')
        elif head_name in snapshot.raw:
            holds.add('HOLD_ORPHAN_TERRAFORM_HEAD')
            snapshot.json(head_name)
        if starts and set(starts) == set(results) and all(row['status'] ==
                'APPLIED_REQUIRES_NATIVE_ACCEPTANCE' for row in results.values()):
            # Use the actual retained-ledger owner, including overlap/head checks.
            completed_history(snapshot.root / directory, scope)
        elif len(starts) > 1:
            holds.add('HOLD_MIXED_OR_UNCERTAIN_LEDGER_REQUIRES_RECONCILIATION')
    for run in runs.values():
        identity = (run['bundle']['operation_id'], run['bundle']['generation'])
        if identity not in attempted:
            holds.add('HOLD_RETAINED_RUN_WITHOUT_DURABLE_START')
    return projections, count_start, count_result


def _delivery(snapshot, manifest, holds):
    count = 0
    for directory in manifest['deliveryJournals']:
        # The retained journal and replay implementations remain the owners of
        # event-chain and predecessor/artifact semantics. No dispatcher is called.
        from provisioner.execution.execution_journal import Journal
        from provisioner.execution.delivery_run import replay
        for name in snapshot.files_under(directory):
            snapshot.used.add(name)
        scope = {'owner': 'delivery', **_legacy(manifest['scope'], phase=False)}
        journal = Journal(snapshot.root / directory, scope)
        count += len(journal.events)
        if not journal.events:
            holds.add('HOLD_EMPTY_DELIVERY_JOURNAL')
            continue
        plans = [row['data']['plan'] for row in journal.events if row['kind'] == 'DELIVERY_STARTED']
        require(plans, 'Retained delivery journal lacks a start')
        starts, receipts, _, closed, _ = replay(journal, plans[-1])
        if set(starts) - set(receipts):
            holds.add('HOLD_UNCERTAIN_DELIVERY_STEP_REQUIRES_CANONICAL_RECOVERY')
        if not closed:
            holds.add('HOLD_INCOMPLETE_DELIVERY')
    return count


def reconcile(snapshot, manifest, *, as_of):
    """Return a deterministic observation-only proposal over recognized records."""
    _manifest(manifest, as_of)
    holds, native = set(), {}
    inventory = _evidence(snapshot, manifest, 'nativeInventory', 'hosting-retained-native-inventory/1',
                          {'capturedAt', 'observerId', 'complete', 'bindings'}, holds, as_of)
    if inventory is not None:
        require(type(inventory['complete']) is bool and isinstance(inventory['bindings'], list),
                'Explicit native inventory completeness required')
        if not inventory['complete']:
            holds.add('HOLD_NATIVE_INVENTORY_INCOMPLETE')
        for row in inventory['bindings']:
            c.exact_keys(row, {'binding', 'lifecycleStage'})
            require(row['lifecycleStage'] in {None, 'prepared', 'bootstrap'}, 'Unknown observed lifecycle stage')
            key = _binding(row['binding'], manifest['scope']).key()
            require(key not in native, 'Duplicate independently observed native identity')
            native[key] = row
    freeze = _evidence(snapshot, manifest, 'oldWriterFreeze', 'hosting-retained-writer-freeze/1',
                       {'frozenAt', 'observerId', 'oldWriters'}, holds, as_of)
    maximum_old_epoch = 0
    if freeze is not None:
        require(isinstance(freeze['oldWriters'], list) and freeze['oldWriters'],
                'Explicit nonempty old-writer inventory required')
        writers = set()
        for row in freeze['oldWriters']:
            c.exact_keys(row, {'writerId', 'frozen', 'epoch', 'proofDigest'})
            c.identifier(row['writerId'])
            require(row['writerId'] not in writers and type(row['frozen']) is bool and
                    _positive(row['epoch']) and c.HEX.fullmatch(row['proofDigest']),
                    'Duplicate or invalid old-writer freeze evidence')
            writers.add(row['writerId'])
            if row['frozen'] is not True:
                holds.add('HOLD_OLD_WRITER_NOT_FROZEN')
            maximum_old_epoch = max(maximum_old_epoch, row['epoch'])
    ownership = _evidence(snapshot, manifest, 'newOwnerSnapshot', 'hosting-retained-owner-snapshot/1',
                          {'capturedAt', 'observerId', 'observationOnly', 'owners'}, holds, as_of)
    owners = {}
    if ownership is not None:
        require(ownership['observationOnly'] is True and isinstance(ownership['owners'], list),
                'New service must be observed without write authority')
        for row in ownership['owners']:
            c.exact_keys(row, {'binding', 'epoch', 'workerId'})
            key = _binding(row['binding'], manifest['scope']).key()
            require(key not in owners and _positive(row['epoch']) and row['workerId'] is None,
                    'Duplicate owner, invalid epoch or active writer in observation-only snapshot')
            owners[key] = row
            if row['epoch'] <= maximum_old_epoch:
                holds.add('HOLD_NEW_OWNER_EPOCH_NOT_ADVANCED')
    recorded, workloads = _workloads(snapshot, manifest, holds)
    runs, terraform, stages = _runs(snapshot, manifest, native, holds, as_of)
    attempts, starts, results = _attempts(snapshot, manifest, runs, holds, as_of)
    delivery_events = _delivery(snapshot, manifest, holds)
    for key in terraform:
        if key not in recorded:
            holds.add('HOLD_TERRAFORM_NATIVE_ID_NOT_IN_CANONICAL_WORKLOAD')
    expected = set(recorded) | set(terraform)
    if expected != set(native):
        holds.add('HOLD_NATIVE_ID_INVENTORY_MISMATCH')
    if expected != set(owners):
        holds.add('HOLD_OWNER_NATIVE_ID_INVENTORY_MISMATCH')
    if not manifest['terraformLedgers'] and manifest['terraformRuns']:
        holds.add('HOLD_TERRAFORM_LEDGER_INVENTORY_MISSING')
    counts = {'files': len(snapshot.raw), 'workloads': len(workloads), 'terraformRuns': len(runs),
              'terraformStarts': starts, 'terraformResults': results, 'deliveryEvents': delivery_events}
    if counts != manifest['sourceCounts']:
        holds.add('HOLD_SOURCE_COUNT_MISMATCH')
    if set(snapshot.raw) != snapshot.used:
        holds.add('HOLD_UNRECOGNIZED_RETAINED_FILES')
    report = {'format': 'hosting-retained-state-reconciliation/1', 'batchId': manifest['batchId'],
              'scope': manifest['scope'], 'asOf': as_of.isoformat(), 'manifestDigest': digest(encoded(manifest)),
              'status': 'REHEARSAL_HELD' if holds else 'REHEARSAL_RECONCILED_OBSERVATION_ONLY',
              'holds': sorted(holds), 'sourceCounts': manifest['sourceCounts'], 'observedCounts': counts,
              'archivedFileCount': len(snapshot.raw), 'projectedWorkloadCount': len(workloads),
              'retainedNativeIdCount': len(expected), 'observedNativeIdCount': len(native),
              'observedOwnerIdCount': len(owners), 'maximumOldWriterEpoch': maximum_old_epoch,
              'uncertainAttemptCount': sum(row['outcome'] == 'UNKNOWN' for row in attempts),
              'unrecognizedFileCount': len(set(snapshot.raw) - snapshot.used),
              'evidenceAuthenticated': False, 'databaseImported': False, 'serviceMode': 'OBSERVATION_ONLY',
              'writesAuthorized': False, 'retryAuthorized': False, 'oldWritersStoppedByTool': False,
              'releaseGatesRemaining': ['INDEPENDENT_EVIDENCE_AUTHENTICATION', 'ACTUAL_STATE_IMPORT',
                                       'CANONICAL_NATIVE_RECOVERY', 'OWNER_ACCEPTANCE',
                                       'POST_DELETION_QUALIFICATION']}
    projection = {'format': 'hosting-retained-state-projection/1', 'batchId': manifest['batchId'],
                  'manifestDigest': report['manifestDigest'], 'workloads': workloads,
                  'attempts': attempts, 'lifecycleStages': stages,
                  'authority': 'HISTORICAL_OBSERVATION_ONLY'}
    return report, projection


def _mkdir(directory):
    directory.mkdir(mode=0o700, exist_ok=True)
    private_path(directory, directory=True)


def _publish(path, raw):
    if path.exists():
        require(read_private(path) == raw, 'Previously published rehearsal bytes changed or conflict')
    else:
        write_new(path, raw)
        path.chmod(0o400)


def rehearse(manifest_path: Path, source_root: Path, destination: Path, *, as_of: datetime):
    """Archive once and compare, with crash recovery through exact-byte replay."""
    require(isinstance(as_of, datetime) and as_of.tzinfo is not None and as_of.utcoffset().total_seconds() == 0,
            'Explicit UTC rehearsal time required')
    manifest_raw = read_private(manifest_path)
    manifest = strict_loads(manifest_raw)
    _manifest(manifest, as_of)
    snapshot = Snapshot(source_root, manifest)
    report, projection = reconcile(snapshot, manifest, as_of=as_of)
    destination = private_path(destination, directory=True)
    require(not destination.is_relative_to(snapshot.root) and not snapshot.root.is_relative_to(destination),
            'Separate private source and rehearsal destination required')
    descriptor = os.open(destination / 'rehearsal.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        private_path(destination / 'rehearsal.lock')
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        batch = destination / manifest['batchId']
        _mkdir(batch)
        _publish(batch / 'manifest.json', manifest_raw)
        _mkdir(batch / 'originals')
        for name, raw in snapshot.raw.items():
            path = batch / 'originals' / name
            current = batch / 'originals'
            for segment in PurePosixPath(name).parts[:-1]:
                current = current / segment
                _mkdir(current)
            _publish(path, raw)
        snapshot.recheck()
        require(read_private(manifest_path) == manifest_raw, 'Manifest changed during rehearsal')
        _publish(batch / 'projection.json', encoded(projection))
        _publish(batch / 'reconciliation.json', encoded(report))
        sync_directory(batch)
        return report
    finally:
        os.close(descriptor)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--as-of', required=True)
    args = parser.parse_args(argv)
    try:
        report = rehearse(args.manifest, args.source_root, args.destination, as_of=_timestamp(args.as_of))
        # Paths, originals and projections can contain operational or credential
        # material. Console output only contains counts and fixed hold codes.
        print(json.dumps({key: report[key] for key in ('status', 'holds', 'observedCounts',
                          'uncertainAttemptCount', 'databaseImported', 'writesAuthorized')}))
        return 2 if report['holds'] else 0
    except (OSError, ValueError, KeyError, TypeError, OverflowError, RecursionError):
        print('{"status":"REHEARSAL_REJECTED","writesAuthorized":false,"privateArchiveMayExist":true}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
