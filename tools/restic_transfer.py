"""Exact cross-scope file restore bindings, authenticated by the worker runtime.

The transfer envelope and ordinary restore authority are evidence, not credentials.
Only a runtime-created TransferGuard can authorize a foreign destination. It calls
the existing authority service before each repository command, preserving live
identity, approval, plan revision and owner-lease checks. The original capture
receipt and file manifest always retain their source scope.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
import re

from provisioner.controlplane.authority import AuthorityService, PlanScope, WorkerGrant
from provisioner.domain.enterprise_records import validate_record
from tools.run_files import digest, encoded, require

FORMAT = 'hosting-restic-transfer/1'
RECEIPT_FORMAT = 'hosting-restic-transfer-receipt/2'
_SCOPE_KEYS = {'environment_key', 'site_key', 'platform', 'tenant_key', 'wsd_key'}
_KEYS = {'format', 'migration_plan', 'transfer', 'source_execution_scope',
         'destination_execution_scope', 'source_config_sha256', 'repository_id',
         'snapshot_id', 'file_manifest_sha256', 'target_member', 'target'}


def _sha(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value)


def _scope(value):
    require(isinstance(value, dict) and set(value) == _SCOPE_KEYS
            and all(isinstance(v, str) and re.fullmatch(r'[a-z][a-z0-9-]{1,40}', v)
                    for v in value.values())
            and value['platform'] in {'vmware', 'nutanix', 'openstack'},
            'Exact transfer execution scope required')


def validate(envelope, config, receipt, expected, target):
    """Validate data bindings only; success never grants access to a repository."""
    require(isinstance(envelope, dict) and set(envelope) == _KEYS
            and envelope['format'] == FORMAT, 'Exact restic transfer envelope required')
    plan, transfer = envelope['migration_plan'], envelope['transfer']
    require(isinstance(plan, dict) and plan.get('kind') == 'MigrationPlan'
            and not validate_record(plan), 'Exact canonical migration plan required')
    require(isinstance(transfer, dict) and transfer.get('kind') == 'TransferManifest'
            and not validate_record(transfer, plan=plan),
            'Canonical transfer does not bind the selected migration plan')
    spec = transfer['spec']
    source, destination = envelope['source_execution_scope'], envelope['destination_execution_scope']
    _scope(source); _scope(destination)
    require(source == config['scope'] and source == receipt['scope']
            and source == expected['scope'], 'Original capture scope must survive transfer')
    require(source['platform'] == spec['sourceScope']['platformFamily']
            and destination['platform'] == spec['destinationScope']['platformFamily']
            and source['tenant_key'] == destination['tenant_key'],
            'Transfer scope mapping changes platform family or tenant')
    # The envelope maps existing delivery keys to canonical native scopes. Their
    # names need not be identical; the complete mapping is independently pinned
    # by the runtime's immutable manifest digest, never inferred from aliases.
    require(envelope['source_config_sha256'] == digest(encoded(config))
            and spec['sourceReceipt']['receiptDigest'] == digest(encoded(receipt))
            and envelope['file_manifest_sha256'] == digest(encoded(expected))
            and receipt['manifest_sha256'] == envelope['file_manifest_sha256']
            and envelope['repository_id'] == config['repository_id'] == receipt['repository_id']
            and envelope['snapshot_id'] == receipt['snapshot_id']
            and _sha(envelope['snapshot_id']),
            'Transfer capture, repository, manifest or snapshot binding changed')
    require(isinstance(envelope['target_member'], str)
            and re.fullmatch(r'[a-z][a-z0-9-]{1,40}', envelope['target_member']),
            'Exact target member required')
    root = Path(envelope['target'])
    require(root.is_absolute() and root != Path('/') and '..' not in root.parts
            and str(root) == envelope['target'] == str(Path(target).absolute()),
            'Transfer must bind one canonical isolated restore root')
    require(spec['sourceFormat'] == spec['targetFormat'],
            'File restore cannot claim format conversion')
    if spec['expectedBytes']['state'] == 'KNOWN':
        require(spec['expectedBytes']['value'] == sum(row['size'] for row in expected['files'].values()),
                'Dataset byte count differs from captured file manifest')
    return envelope


def grant_digest(grant: WorkerGrant) -> str:
    """Stable public grant identity; hashing is not grant authentication."""
    require(isinstance(grant, WorkerGrant), 'Authoritative worker grant required')
    body = asdict(grant)
    for name, value in body.items():
        if isinstance(value, datetime):
            body[name] = value.isoformat()
    return digest(encoded(body))


@dataclass(frozen=True)
class TransferGuard:
    """Trusted runtime wiring, never constructed from packet/request JSON.

    expected_manifest_sha256 is read from the reviewed job's immutable transfer
    mapping. source/destination aliases, dataset and target root are covered by
    that digest. The authority service independently reads its current plan,
    approvals and worker lease. A manifest alone cannot create this decision.
    """
    authority: AuthorityService
    credential: object
    expected_manifest_sha256: str
    grant_id: str
    step_id: str
    operation_id: str

    def __post_init__(self):
        require(isinstance(self.authority, AuthorityService)
                and _sha(self.expected_manifest_sha256)
                and all(isinstance(value, str) and value for value in
                        (self.grant_id, self.step_id, self.operation_id)),
                'Trusted worker authority and immutable transfer binding required')

    def check(self, envelope):
        return self.check_window(envelope)[0]

    def check_window(self, envelope):
        require(digest(encoded(envelope)) == self.expected_manifest_sha256,
                'Transfer differs from the immutable runtime mapping')
        transfer = envelope['transfer']
        meta, spec = transfer['metadata'], transfer['spec']
        destination = PlanScope.from_record(spec['destinationScope'])
        grant, deadline = self.authority.require_worker_step_window(
            self.credential, self.grant_id, step_id=self.step_id,
            operation_id=self.operation_id, operation_kind='RESTORE_DATA',
            operation_scope=destination)
        require((grant.organization_id, grant.tenant_id, grant.plan_id,
                 grant.plan_revision, grant.plan_digest, grant.source, grant.destination) ==
                (meta['organizationId'], meta['tenantId'], meta['planId'],
                 meta['planRevision'], meta['planDigest'],
                 PlanScope.from_record(spec['sourceScope']), destination)
                and spec['grant']['grantId'] == grant.grant_id
                and spec['grant']['grantDigest'] == grant_digest(grant),
                'Transfer grant does not bind the original source and destination')
        return grant, deadline


def destination_receipt(envelope, source_receipt, restore_receipt):
    """A separate target receipt; neither source evidence artifact is rewritten."""
    spec = envelope['transfer']['spec']
    require(restore_receipt.get('format') == 'hosting-restic-restore-receipt/1'
            and isinstance(restore_receipt.get('target_machine_id'), str)
            and re.fullmatch(r'[0-9a-f]{32}', restore_receipt['target_machine_id'])
            and restore_receipt.get('restore_root') == envelope['target'],
            'Destination receipt requires observed restore machine and exact root')
    return {'format': RECEIPT_FORMAT,
            'status': 'RESTORED_FILE_BYTES_VERIFIED_NOT_APPLICATION_ACCEPTED',
            'scope': envelope['destination_execution_scope'],
            'member': envelope['target_member'],
            'source_scope': source_receipt['scope'],
            'source_member': source_receipt['member'],
            'source_receipt_sha256': digest(encoded(source_receipt)),
            'restore_receipt_sha256': digest(encoded(restore_receipt)),
            'transfer_manifest_sha256': digest(encoded(envelope)),
            'migration_plan_digest': envelope['transfer']['metadata']['planDigest'],
            'dataset_id': spec['datasetId'], 'target_ref': spec['targetRef'],
            'snapshot_id': envelope['snapshot_id'], 'repository_id': envelope['repository_id'],
            'file_manifest_sha256': envelope['file_manifest_sha256'],
            'restore_root': restore_receipt['restore_root'],
            'target_machine_id': restore_receipt['target_machine_id'],
            'file_count': restore_receipt['file_count'],
            'completed_at': restore_receipt['completed_at'],
            'application_acceptance': False, 'production_activation': False,
            'native_qualification': False}


class GuardedRestic:
    """Recheck revocation and lease before and after every repository operation."""
    def __init__(self, client, guard, envelope):
        self.client, self.guard, self.envelope = client, guard, envelope

    def _check(self):
        import time
        from tools.run_files import utcnow
        _grant, deadline = self.guard.check_window(self.envelope)
        self.client.deadline = min(self.client.deadline, time.monotonic() +
                                   (deadline - utcnow()).total_seconds())

    def repository(self):
        self._check()
        result = self.client.repository()
        self._check()
        return result

    def command(self, arguments):
        self._check()
        result = self.client.command(arguments)
        self._check()
        return result


def execute_authorized_transfer(*, authority_service, worker_credential,
                                expected_manifest_sha256, grant_id, step_id,
                                operation_id, transfer, config, credentials,
                                binary, operation, receipt, expected, target,
                                restore_authority, ca_file=None):
    """Trusted worker entrypoint, invoked after the existing native intent gate.

    The runtime supplies authority_service and the immutable job mapping digest;
    neither is taken from the transfer packet. It must acquire scoped ephemeral
    repository credentials using its normal credential broker. This function
    does not grant source fencing, activate production, or qualify a site route.
    """
    from tools.restic_run import execute
    guard = TransferGuard(authority_service, worker_credential,
                          expected_manifest_sha256, grant_id, step_id, operation_id)
    return execute('restore', config, credentials, binary, operation,
                   ca_file=ca_file, receipt=receipt, expected=expected, target=target,
                   authority=restore_authority, transfer=transfer, transfer_guard=guard)
