"""Validate maintained-design metadata and parent links, not frozen source wording."""
from pathlib import Path
from datetime import date
import json,re


def check(root):
    errors=[];path=root/'sources/documentation/current_design_records.json'
    records=json.loads(path.read_text());seen=set()
    for record in records:
        ident=record.get('id');rel=record.get('path','');p=root/rel
        if not ident or ident in seen:errors.append('Missing or duplicate maintained design ID')
        seen.add(ident)
        if not rel.startswith('docs/current/') or not p.resolve().is_relative_to((root/'docs/current').resolve()):errors.append(str(ident)+': outside maintained workspace')
        if not p.is_file():errors.append(str(ident)+': design file absent');continue
        for key in ('owner_role','version','status','scope','source_relation'):
            if not isinstance(record.get(key),str) or not record[key].strip():errors.append(str(ident)+': missing '+key)
        if record.get('status') not in ('Draft','Proposed','Accepted','Superseded','Rejected'):errors.append(str(ident)+': invalid state')
        if record.get('status')=='Accepted' and (not record.get('decision_authority') or not record.get('acceptance_evidence')):errors.append(str(ident)+': acceptance not recorded')
        if not record.get('parent_sections') or any(not (root/p).is_file() for p in record['parent_sections']):errors.append(str(ident)+': missing parent source')
        history=record.get('change_history')
        if not isinstance(history,list) or not history:errors.append(str(ident)+': change history required')
        else:
            for h in history:
                if not all(h.get(k) for k in ('version','date','summary')):errors.append(str(ident)+': incomplete change history')
                try:date.fromisoformat(h.get('date',''))
                except (TypeError,ValueError):errors.append(str(ident)+': invalid record date')
        text=p.read_text()
        header=f"**Version:** {record.get('version')} · **Status:** {record.get('status')} · **Accountable role:** {record.get('owner_role')}."
        metadata_lines=[line for line in text.splitlines() if line.startswith('**Version:**')]
        if metadata_lines!=[header]:errors.append(str(ident)+': rendered status/version/owner differs from maintained record')
        if record.get('status') in ('Draft','Proposed') and (record.get('decision_authority') is not None or record.get('acceptance_evidence') is not None):
            errors.append(str(ident)+': unaccepted design must not assert acceptance authority/evidence')
        if isinstance(history,list) and history and isinstance(history[-1],dict) and history[-1].get('version')!=record.get('version'):
            errors.append(str(ident)+': current version differs from latest change history')
        for heading in ('## Scope and authority','## Design content','## Engineering and implementation handoff','## Acceptance and open work'):
            if heading not in text:errors.append(str(ident)+': missing '+heading)
    return {'records':len(records),'errors':errors,'scope':'Maintained design structure and source links; editorial changes do not need to repeat frozen text. Approval authenticity remains external.'}
