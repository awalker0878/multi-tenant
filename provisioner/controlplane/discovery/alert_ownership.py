"""Independently signed, finite scope-specific on-call notification assignments.

An on-call assignment authorizes acknowledgement of discovery alerts only. It is
not an execution role, change approval, workload writer or native credential.
The assignment key must be independent of the receiver's receipt-signing key.
"""
from datetime import datetime,timedelta
import hashlib
from pathlib import Path
import re

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from provisioner.controlplane.authority.model import PlanScope
from .alert_transport import AlertDeliveryHeld
from .model import _id,_json,_scope,_utc
from .native_credentials import decode_json,read_protected
from .collector_settings import protected_path
from .review_files import read_private,publish_once
from .trust import _decode,_keys


def assignment_digest(document):return hashlib.sha256(_json(document).encode('ascii')).hexdigest()


def verify_ownership(document,*,public_key,minimum_revision,owner_id,intent,at):
    envelope=_keys(document,{'policy','signature'})
    policy=_keys(envelope['policy'],{'format','revision','ownerId','issuedAt','expiresAt','assignments'})
    issued,expires=(datetime.fromisoformat(policy[name]) for name in ('issuedAt','expiresAt'))
    if (not _utc(at) or not _utc(issued) or not _utc(expires) or not issued<=at<expires
            or expires-issued>timedelta(days=1) or policy['format']!='hosting-discovery-alert-ownership/1'
            or type(policy['revision']) is not int or not minimum_revision<=policy['revision']<2**63
            or policy['ownerId']!=owner_id or not isinstance(policy['assignments'],list)
            or not 1<=len(policy['assignments'])<=128):
        raise AlertDeliveryHeld('Current independent on-call ownership is unavailable')
    if not isinstance(public_key,bytes) or len(public_key)!=32:
        raise AlertDeliveryHeld('Independent ownership key is not enrolled')
    Ed25519PublicKey.from_public_bytes(public_key).verify(_decode(envelope['signature'],64),_json(policy).encode('ascii'))
    ids=set();routes=set();selected=[]
    for item in policy['assignments']:
        _keys(item,{'assignmentId','environmentId','scope','monitorSubject','onCallSubject'})
        scope_doc=_keys(item['scope'],{'organization_id','tenant_id','site_id','security_domain_id',
                                     'endpoint_id','native_scope_id','platform_family'})
        scope=PlanScope(**scope_doc)
        if not _scope(scope) or any(not _id(item[name]) for name in ('assignmentId','environmentId','monitorSubject','onCallSubject')):
            raise AlertDeliveryHeld('On-call assignment identity is invalid')
        route=(item['environmentId'],_json(item['scope']))
        if item['assignmentId'] in ids or route in routes:
            raise AlertDeliveryHeld('On-call assignment is ambiguous')
        ids.add(item['assignmentId']);routes.add(route)
        if (item['environmentId'],item['scope'])==(intent['environmentId'],intent['scope']):selected.append(item)
    if len(selected)!=1:raise AlertDeliveryHeld('Alert scope has no exact current on-call owner')
    return selected[0],policy,assignment_digest(policy)


class SignedFileAlertOwnership:
    def __init__(self,path,*,public_key,minimum_revision,owner_id):
        if type(minimum_revision) is not int or minimum_revision<1 or not _id(owner_id):
            raise ValueError('Pinned current alert ownership is required')
        self.path=protected_path(str(path));self.public_key=public_key
        self.minimum_revision=minimum_revision;self.owner_id=owner_id;self._seen_digest=None

    def current(self,intent,at):
        document=decode_json(read_protected(self.path,65536),65536)
        assignment,policy,digest=verify_ownership(document,public_key=self.public_key,
            minimum_revision=self.minimum_revision,owner_id=self.owner_id,intent=intent,at=at)
        if policy['revision']==self.minimum_revision and self._seen_digest is not None and digest!=self._seen_digest:
            raise AlertDeliveryHeld('On-call authority equivocated at the same revision')
        self.minimum_revision=policy['revision'];self._seen_digest=digest
        return document,assignment,policy,digest

    def retain_revision(self,directory,document):
        """Preserve the original policy and reject rollback after receiver restart.

        The receiver calls this while holding its existing inbox transaction.
        No new assignment signer, enrollment issuer or background writer exists.
        """
        directory=protected_path(str(directory));policy=document['policy'];revision=policy['revision']
        selected=[]
        for path in directory.iterdir():
            if not path.name.startswith('ownership-'):continue
            match=re.fullmatch('ownership-([0-9]{19})[.]json',path.name)
            if match is None:raise AlertDeliveryHeld('Retained ownership filename changed')
            selected.append((int(match[1]),path))
            if len(selected)>100000:raise AlertDeliveryHeld('Ownership retention ceiling reached')
        if selected:
            floor,path=max(selected)
            prior=_keys(decode_json(read_private(str(path),65536),65536),{'policy','signature'})
            if (prior['policy'].get('revision')!=floor or prior['policy'].get('ownerId')!=self.owner_id
                    or prior['policy'].get('format')!='hosting-discovery-alert-ownership/1'):
                raise AlertDeliveryHeld('Retained ownership identity changed')
            Ed25519PublicKey.from_public_bytes(self.public_key).verify(_decode(prior['signature'],64),_json(prior['policy']).encode('ascii'))
            if revision<floor or revision==floor and document!=prior:
                raise AlertDeliveryHeld('Current ownership rolled back or equivocated')
            if revision==floor:return
        path=directory/f'ownership-{revision:019d}.json'
        raw=_json(document).encode('ascii')
        def current():
            if decode_json(read_protected(self.path,65536),65536)!=document:
                raise AlertDeliveryHeld('Ownership changed before revision custody')
        publish_once(str(path),raw,current)
