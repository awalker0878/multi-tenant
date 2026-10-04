"""Append-only, tenant-scoped alert attempts over existing freshness custody.

A start commits before sending. A session lock excludes concurrent dispatch even
across processes. Interrupted starts remain UNKNOWN and require explicit replay
of the same intent; the owner must implement exact alert-ID idempotency. Signed
external receipts distinguish owner delivery acceptance from acknowledgement.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json

from provisioner.controlplane.persistence.store import AuditContext
from .alert_transport import AlertDeliveryHeld, HttpsAlertOwner, intent_digest, verify_receipt
from .freshness_history import FreshnessHistoryRepository, _sha
from .freshness_monitor import alert_projection
from .model import _json, _utc
from .persistence import DiscoveryRepository
from .trust import _keys

_TABLE='hosting_controlplane.discovery_alert_deliveries'
_COLUMNS=('alert_id,check_id,check_record_digest,owner_id,sequence,event,attempt_number,'
          'intent_json,intent_digest,receipt_json,recorded_by,recorded_at,previous_record_digest,record_digest')
_SCOPE_SQL=('organization_id=%s AND tenant_id=%s AND environment_id=%s AND site_id=%s '
            'AND security_domain_id=%s AND endpoint_id=%s AND native_scope_id=%s AND platform_family=%s')
_LOCK_SQL="SELECT pg_try_advisory_lock(hashtextextended(jsonb_build_array('discovery-alert-dispatch',%s::text,%s::text,%s::text,%s::text)::text,0))"
_UNLOCK_SQL=_LOCK_SQL.replace('pg_try_advisory_lock','pg_advisory_unlock')


def _digest(value):return hashlib.sha256(_json(value).encode('ascii')).hexdigest()


class AlertDeliveryRepository:
    def __init__(self,history:FreshnessHistoryRepository):
        if not isinstance(history,FreshnessHistoryRepository):raise TypeError('Existing freshness history owner is required')
        self._history=history
        self._repository=history._repository

    @contextmanager
    def _session(self,ctx,scope,environment_id,authorize):
        # Reuse exact tenant, role, clock and current-authority semantics.
        with self._history._session(ctx,scope,environment_id,authorize) as pair:yield pair

    @staticmethod
    def _document(row,scope,environment_id):
        keys=('alertId','checkId','checkRecordDigest','ownerId','sequence','event','attemptNumber',
              'intentJson','intentDigest','receiptJson','recordedBy','recordedAt','previousRecordDigest','recordDigest')
        doc=dict(zip(keys,row))
        at=doc['recordedAt']
        if (type(doc['sequence']) is not int or not 1<=doc['sequence']<=7
                or type(doc['attemptNumber']) is not int or not 1<=doc['attemptNumber']<=3
                or not _utc(at) or not all(_sha(doc[key]) for key in ('alertId','checkRecordDigest','intentDigest','recordDigest'))
                or doc['event'] not in ('DELIVERY_STARTED','DELIVERY_UNKNOWN','DELIVERY_ACCEPTED','ACKNOWLEDGED')):
            raise AlertDeliveryHeld('Retained alert event identity is invalid')
        intent=json.loads(doc.pop('intentJson'))
        raw_receipt=doc.pop('receiptJson')
        receipt=None if raw_receipt is None else json.loads(raw_receipt)
        if (intent_digest(intent)!=doc['intentDigest'] or intent.get('alertId')!=doc['alertId']
                or intent.get('checkId')!=doc['checkId'] or intent.get('checkRecordDigest')!=doc['checkRecordDigest']
                or intent.get('scope')!=vars(scope) or intent.get('environmentId')!=environment_id
                or (receipt is not None)!=(doc['event'] in ('DELIVERY_ACCEPTED','ACKNOWLEDGED'))):
            raise AlertDeliveryHeld('Retained alert event differs from its intent')
        doc.update(format='hosting-discovery-alert-delivery-event/1',environmentId=environment_id,
                   scope=dict(vars(scope)),intent=intent,receipt=receipt,recordedAt=at.isoformat())
        body={key:value for key,value in doc.items() if key!='recordDigest'}
        if _digest(body)!=doc['recordDigest']:raise AlertDeliveryHeld('Retained alert event content has changed')
        AuditContext(doc['recordedBy'],doc['alertId'])
        return doc

    def _load(self,con,args,scope,environment_id,alert_id):
        rows=con.execute('SELECT '+_COLUMNS+' FROM '+_TABLE+' WHERE '+_SCOPE_SQL+
            ' AND alert_id=%s ORDER BY sequence LIMIT 8',(*args,alert_id)).fetchall()
        values=[self._document(row,scope,environment_id) for row in rows]
        previous=None
        for index,value in enumerate(values,1):
            if (index>7 or value['sequence']!=index
                    or value['previousRecordDigest']!=(None if previous is None else previous['recordDigest'])
                    or previous is not None and value['recordedAt']<previous['recordedAt']):
                raise AlertDeliveryHeld('Alert delivery history is incomplete or reordered')
            if previous is None:
                valid=value['event']=='DELIVERY_STARTED' and value['attemptNumber']==1
            else:
                valid=(all(value[k]==previous[k] for k in
                           ('alertId','checkId','checkRecordDigest','ownerId','intentDigest','recordedBy'))
                    and ((value['event']=='DELIVERY_STARTED'
                          and previous['event'] in ('DELIVERY_STARTED','DELIVERY_UNKNOWN')
                          and value['attemptNumber']==previous['attemptNumber']+1)
                        or (value['event'] in ('DELIVERY_UNKNOWN','DELIVERY_ACCEPTED','ACKNOWLEDGED')
                            and previous['event']=='DELIVERY_STARTED' and value['attemptNumber']==previous['attemptNumber'])
                        or (value['event']=='ACKNOWLEDGED' and previous['event']=='DELIVERY_ACCEPTED'
                            and value['attemptNumber']==previous['attemptNumber'])))
            if not valid:raise AlertDeliveryHeld('Alert delivery history has an invalid transition')
            previous=value
        return previous

    def inspect(self,ctx,scope,environment_id,intent,*,authorize):
        with self._session(ctx,scope,environment_id,authorize) as (con,_):
            return self._load(con,DiscoveryRepository._scope_args(ctx,scope,environment_id),scope,environment_id,intent['alertId'])

    def _append(self,ctx,scope,environment_id,intent,owner_id,event,attempt,receipt,*,audit,authorize):
        args=DiscoveryRepository._scope_args(ctx,scope,environment_id)
        with self._session(ctx,scope,environment_id,authorize) as (con,now):
            con.execute("SELECT pg_advisory_xact_lock(hashtextextended(jsonb_build_array('discovery-alert-event',%s::text,%s::text,%s::text,%s::text)::text,0))",
                        (*args[:3],intent['alertId']))
            authorize(scope,now())
            previous=self._load(con,args,scope,environment_id,intent['alertId'])
            at=now()
            doc={'format':'hosting-discovery-alert-delivery-event/1','environmentId':environment_id,
                'scope':dict(vars(scope)),'alertId':intent['alertId'],'checkId':intent['checkId'],
                'checkRecordDigest':intent['checkRecordDigest'],'ownerId':owner_id,
                'sequence':1 if previous is None else previous['sequence']+1,'event':event,
                'attemptNumber':attempt,'intent':intent,'intentDigest':intent_digest(intent),'receipt':receipt,
                'recordedBy':audit.actor_id,'recordedAt':at.isoformat(),
                'previousRecordDigest':None if previous is None else previous['recordDigest']}
            doc['recordDigest']=_digest(doc)
            values=(doc['alertId'],doc['checkId'],doc['checkRecordDigest'],doc['ownerId'],doc['sequence'],
                doc['event'],doc['attemptNumber'],_json(intent),doc['intentDigest'],
                None if receipt is None else _json(receipt),audit.actor_id,at,doc['previousRecordDigest'],doc['recordDigest'])
            self._document(values,scope,environment_id)
            authorize(scope,now())
            con.execute('INSERT INTO '+_TABLE+' (organization_id,tenant_id,environment_id,site_id,security_domain_id,'
                'endpoint_id,native_scope_id,platform_family,'+_COLUMNS+') VALUES ('+','.join(['%s']*22)+')',(*args,*values))
            con.execute('INSERT INTO hosting_controlplane.audit_events '
                '(organization_id,tenant_id,actor_id,correlation_id,action,record_kind,record_id,revision,record_digest,details) '
                'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)',
                (ctx.organization_id,ctx.tenant_id,audit.actor_id,audit.correlation_id,'RECORD_CREATE',
                 'DiscoveryAlertDelivery',doc['alertId'],doc['sequence'],doc['recordDigest'],
                 _json({'event':event,'ownerId':owner_id,'intentDigest':doc['intentDigest']})))
            return doc

    def dispatch(self,ctx,scope,environment_id,check_id,*,owner:HttpsAlertOwner,audit:AuditContext,
                 authorize,retry_unknown=False,refresh=False):
        if not isinstance(owner,HttpsAlertOwner) or not isinstance(audit,AuditContext):
            raise TypeError('Explicit alert owner, authenticated actor and current authority are required')
        if type(retry_unknown) is not bool or type(refresh) is not bool or retry_unknown and refresh:
            raise ValueError('Select a delivery retry or acknowledgement refresh')
        check=self._history.get(ctx,scope,environment_id,check_id,authorize=authorize)
        if check is None:raise AlertDeliveryHeld('Retained freshness check is unavailable')
        intent=alert_projection(check)
        if intent is None:return {'status':'NO_ALERT','notificationAttempted':False,'executionAuthorized':False}
        args=DiscoveryRepository._scope_args(ctx,scope,environment_id)
        # This lock's connection survives the separate committed start/receipt
        # transactions. Another process cannot replay while the first is sending.
        with self._session(ctx,scope,environment_id,authorize) as (lock_con,now):
            lock_args=(*args[:3],intent['alertId'])
            if lock_con.execute(_LOCK_SQL,lock_args).fetchone()!=(True,):
                raise AlertDeliveryHeld('Alert dispatch is already active')
            try:
                prior=self.inspect(ctx,scope,environment_id,intent,authorize=authorize)
                if prior is not None and (prior['ownerId']!=owner.target.owner_id or prior['recordedBy']!=audit.actor_id):
                    raise AlertDeliveryHeld('Retained dispatch belongs to another owner or service')
                def clock():return now()
                def current(at):authorize(scope,at)
                if refresh:
                    if prior is None or prior['event'] not in ('DELIVERY_ACCEPTED','ACKNOWLEDGED'):
                        raise AlertDeliveryHeld('Acknowledgement refresh requires an accepted delivery')
                    receipt=owner.refresh(intent,current,clock)
                    verify_receipt(receipt,intent,owner.target,now())
                    if receipt['receipt']['status']=='ACKNOWLEDGED' and prior['event']!='ACKNOWLEDGED':
                        prior=self._append(ctx,scope,environment_id,intent,owner.target.owner_id,
                            'ACKNOWLEDGED',prior['attemptNumber'],receipt,audit=audit,authorize=authorize)
                    return self._outcome(prior,False,current_receipt=receipt)
                if prior is not None and prior['event'] in ('DELIVERY_ACCEPTED','ACKNOWLEDGED'):
                    return self._outcome(prior,False)
                if prior is not None and not retry_unknown:
                    return self._outcome(prior,False)
                attempt=1 if prior is None else prior['attemptNumber']+1
                if attempt>3:raise AlertDeliveryHeld('Original alert retry budget is exhausted')
                started=self._append(ctx,scope,environment_id,intent,owner.target.owner_id,
                    'DELIVERY_STARTED',attempt,None,audit=audit,authorize=authorize)
                try:
                    receipt=owner.deliver(intent,current,clock)
                    verify_receipt(receipt,intent,owner.target,now())
                    retained=self._append(ctx,scope,environment_id,intent,owner.target.owner_id,
                        receipt['receipt']['status'],attempt,receipt,audit=audit,authorize=authorize)
                    return self._outcome(retained,True,current_receipt=receipt)
                except Exception:
                    try:
                        started=self._append(ctx,scope,environment_id,intent,owner.target.owner_id,
                            'DELIVERY_UNKNOWN',attempt,None,audit=audit,authorize=authorize)
                    except Exception:pass  # The committed START is itself an unresolved attempt.
                    return self._outcome(started,True)
            finally:
                lock_con.execute(_UNLOCK_SQL,lock_args)

    @staticmethod
    def _outcome(value,attempted,*,current_receipt=None):
        unknown=value['event'] in ('DELIVERY_STARTED','DELIVERY_UNKNOWN')
        return {'format':'hosting-discovery-alert-delivery-outcome/1',
            'status':'DELIVERY_UNKNOWN' if unknown else value['event'],'event':value,
            'notificationAttempted':attempted,'reconciliationRequired':unknown,
            'historicalOnly':current_receipt is None,'currentOwnerReceipt':current_receipt,
            'collectionRequested':False,'executionAuthorized':False}
