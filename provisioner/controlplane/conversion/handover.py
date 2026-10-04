"""Scoped original-native reconciliation and one controlled owner-epoch advance."""
from __future__ import annotations

from datetime import timedelta

from provisioner.controlplane.authority.service import AuthorityDenied
from provisioner.controlplane.jobs.repository import _json, _tenant
from provisioner.controlplane.persistence import TenantContext
from provisioner.controlplane.persistence.store import NativeBinding
from provisioner.execution import readback_core as c
from provisioner.execution.neutron_observe import strict_loads
from provisioner.execution.run_files import digest, encoded, require
from .importer import RetainedStateImporter, native_statement
from .proofs import require_independent


def require_write_admission(cursor, context: TenantContext, *,
                            security_domain_id: str, workload_id: str) -> None:
    """Additional observation-only interlock; never authors modern authority."""
    _tenant(cursor, context)
    cursor.execute('SELECT hosting_controlplane.retained_conversion_write_is_admitted(%s,%s,%s,%s)',
        (context.organization_id,context.tenant_id,security_domain_id,workload_id))
    if cursor.fetchone() != (True,):
        raise AuthorityDenied('Retained scope is observation-only or its exact accepted handover is unavailable')


class RetainedStateHandover:
    def __init__(self, importer: RetainedStateImporter):
        if not isinstance(importer, RetainedStateImporter):
            raise TypeError('The actual canonical retained-state importer is required')
        self.importer = importer

    @staticmethod
    def _state(cursor, context, batch):
        cursor.execute('SELECT state,encode(sha256(convert_to(state::text,\'UTF8\')),\'hex\') FROM '
            'hosting_controlplane.retained_conversion_state(%s,%s,%s) AS state',
            (context.organization_id,context.tenant_id,batch))
        row = cursor.fetchone()
        require(row is not None, 'Retained conversion state is unavailable')
        return _json(row[0]), row[1]

    def inspect(self, context: TenantContext, batch_id: str) -> dict:
        c.identifier(batch_id)
        self.importer.evidence.require(context)
        with self.importer._connect() as connection, connection.cursor() as cursor:
            _tenant(cursor, context)
            state, state_digest = self._state(cursor,context,batch_id)
            cursor.execute('SELECT hosting_controlplane.retained_conversion_write_is_admitted(%s,%s,%s,%s)',
                (context.organization_id,context.tenant_id,*self._scope(cursor,context,batch_id)[1:3]))
            armed = cursor.fetchone() == (True,)
        return {'format':'hosting-retained-conversion-inspection/1','state':state,
                'reconciliationDigest':state_digest,'serviceMode':'WRITE_ADMITTED' if armed else 'OBSERVATION_ONLY',
                'retryAuthorized':False}

    @staticmethod
    def _scope(cursor,context,batch):
        cursor.execute('SELECT scope,security_domain_id,workload_id,manifest_digest,archive_inventory_digest,'
            'source_boundary,source_counts FROM hosting_controlplane.retained_conversion_batches '
            'WHERE organization_id=%s AND tenant_id=%s AND batch_id=%s',
            (context.organization_id,context.tenant_id,batch))
        row=cursor.fetchone()
        require(row is not None,'Retained conversion batch is not visible')
        return (_json(row[0]),*row[1:5],_json(row[5]),_json(row[6]))

    def accept_handover(self, context: TenantContext, batch_id: str, *, proof_events: dict[str,str]) -> dict:
        c.identifier(batch_id)
        c.exact_keys(proof_events,{'NATIVE','EXCLUSION','OWNER','SECURITY','CUSTODY'})
        self.importer.evidence.require(context)
        with self.importer._connect() as connection, connection.cursor() as cursor:
            _tenant(cursor,context)
            scope,wsd,workload,batch_digest,archive_digest,boundary,counts=self._scope(cursor,context,batch_id)
            state,state_digest=self._state(cursor,context,batch_id)
            cursor.execute('SELECT native_proof,exclusion_proof,owner_proof,security_proof,custody_proof,'
                'reconciliation_digest FROM hosting_controlplane.retained_conversion_handovers '
                'WHERE organization_id=%s AND tenant_id=%s AND batch_id=%s',
                (context.organization_id,context.tenant_id,batch_id))
            previous=cursor.fetchone()
            if previous is not None:
                require(tuple(previous[:5])==tuple(proof_events[purpose] for purpose in
                    ('NATIVE','EXCLUSION','OWNER','SECURITY','CUSTODY')),
                    'This exact source batch already has another immutable handover')
                state_digest=previous[5]
            proofs={purpose:self.importer.proofs.verify(cursor,context,scope,event_key=event,batch_id=batch_id,
                manifest_digest=batch_digest,purpose=purpose) for purpose,event in proof_events.items()}
            require_independent(list(proofs.values()))
            raw_manifest=self.importer.originals.read(batch_digest)
            value=strict_loads(raw_manifest)
            inventory=value['inventory']
            require(inventory['scope']==scope and inventory['batchId']==batch_id and digest(raw_manifest)==batch_digest,
                    'Original manifest identity/scope changed')
            cursor.execute('SELECT source_path,original_digest,byte_count FROM hosting_controlplane.retained_conversion_files '
                'WHERE organization_id=%s AND tenant_id=%s AND batch_id=%s ORDER BY source_path',
                (context.organization_id,context.tenant_id,batch_id))
            files=cursor.fetchall()
            require(len(files)==counts['files'] and {row[0]:row[1] for row in files}==inventory['sourceFileSha256'],
                    'Original/archive/imported file counts differ')
            archived=[]
            for name,expected,size in files:
                original=self.importer.originals.read(expected)
                require(len(original)==size,'Original retained byte extent differs')
                archived.append({'path':name,'sha256':expected,'bytes':size})
            require(digest(encoded({'manifestSha256':batch_digest,'files':archived}))==archive_digest,
                    'Original protected archive inventory differs')
            custody=proofs['CUSTODY'].statement
            require(custody=={'originalManifestSha256':batch_digest,'archiveInventoryDigest':archive_digest,
                'sourceBoundary':boundary,'sourceCounts':counts},'Current independent custody/high-water acceptance differs')
            cursor.execute('SELECT operation_id,generation,original_outcome FROM hosting_controlplane.retained_conversion_recovery '
                'WHERE organization_id=%s AND tenant_id=%s AND batch_id=%s ORDER BY operation_id,generation',
                (context.organization_id,context.tenant_id,batch_id))
            recoveries=[{'operationId':row[0],'generation':row[1],'outcome':row[2]} for row in cursor.fetchall()]
            native_digest=inventory['sourceFileSha256'][inventory['evidence']['nativeInventory']]
            original_native=strict_loads(self.importer.originals.read(native_digest))
            bindings=[row['binding'] for row in original_native['bindings']]
            native_statement(proofs['NATIVE'].statement,bindings,recoveries,native_digest=native_digest,
                             state_digest=state_digest,handover=True)
            original_freeze=strict_loads(self.importer.originals.read(
                inventory['sourceFileSha256'][inventory['evidence']['oldWriterFreeze']]))
            exclusion=proofs['EXCLUSION'].statement
            c.exact_keys(exclusion,{'oldWriters','allExcluded','queuedRequestsExcluded','nativeTasksQuiesced',
                                   'retainedFreezeDigest','reconciliationDigest'})
            require(exclusion['oldWriters']==original_freeze['oldWriters'] and exclusion['allExcluded'] is True
                and exclusion['queuedRequestsExcluded'] is True and exclusion['nativeTasksQuiesced'] is True
                and exclusion['reconciliationDigest']==state_digest and exclusion['retainedFreezeDigest']==
                inventory['sourceFileSha256'][inventory['evidence']['oldWriterFreeze']],
                'Actual current original-writer/task exclusion is held')
            old_writers={row['writerId'] for row in original_freeze['oldWriters']}
            require(not old_writers & {proof.subject_id for proof in proofs.values()},
                    'Old writers cannot independently accept their own exclusion/handover')
            epochs=[{'binding':row['binding'],'sourceEpoch':row['sourceEpoch'],'targetEpoch':row['targetEpoch']}
                    for row in state['nativeEpochs']]
            accepted=proofs['OWNER'].statement
            c.exact_keys(accepted,{'reconciliationDigest','nativeEpochs','writeAdmissionUntil'})
            require(accepted==proofs['SECURITY'].statement and accepted['reconciliationDigest']==state_digest
                    and accepted['nativeEpochs']==epochs,'Distinct owners have not accepted the same exact scope/epoch handover')
            cursor.execute('SELECT clock_timestamp()')
            now=cursor.fetchone()[0]
            deadline=c.timestamp(accepted['writeAdmissionUntil'])
            require(now<deadline<=now+timedelta(hours=1),'Explicit bounded current scope-specific write acceptance required')
            handover_id='handover:'+digest(encoded({'batchId':batch_id,'proofs':proof_events,'reconciliationDigest':state_digest}))
            cursor.execute('SELECT hosting_controlplane.accept_retained_conversion_handover(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                (context.organization_id,context.tenant_id,batch_id,handover_id,proof_events['NATIVE'],
                 proof_events['EXCLUSION'],proof_events['OWNER'],proof_events['SECURITY'],proof_events['CUSTODY'],state_digest))
            changed=cursor.fetchone()==(True,)
            require_write_admission(cursor,context,security_domain_id=wsd,workload_id=workload)
        return {'format':'hosting-retained-conversion-handover/1','batchId':batch_id,'handoverId':handover_id,
                'advanced':changed,'nativeEpochs':epochs,'serviceMode':'WRITE_ADMITTED','retryAuthorized':False}
