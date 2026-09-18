"""Source-backed ADR lifecycle and deterministic rendering; no approval is issued.

Records are maintained in Git. Validation checks evidence presence and consistency,
not signer authenticity. Synthetic lifecycle examples belong only in tests.
"""
from __future__ import annotations
from datetime import date
from pathlib import Path
import re

STATES = {'Proposed', 'Accepted', 'Superseded', 'Rejected'}


def substantive(value):
    return isinstance(value, str) and len(value.strip()) >= 3 and value.strip().lower() not in {
        'none', 'tbd', 'unknown', 'not recorded', 'not supplied', 'to be assigned', 'example-only'}


def validate(records):
    """Validate the single maintained record format without inventing authority.

    Proposed records cannot carry a completed lifecycle decision. Historical field
    aliases are rejected rather than silently translated into acceptance metadata.
    The directed superseded_by link must resolve and terminate at an Accepted ADR;
    its inverse is derived, not maintained as a second conflicting list.
    """
    errors=[]; byid={}
    if not isinstance(records,list) or not records:
        return ['ADR records must be a nonempty list']
    allowed={'accountable_role','scope','deciding_authority','decision_date',
             'decision_record','evidence_refs','decision_rationale','superseded_by'}
    for a in records:
        if not isinstance(a,dict) or not isinstance(a.get('id'),str) or not re.fullmatch(r'ADR-\d{4}',a['id']):
            errors.append('Invalid ADR record identity');continue
        key=a['id']
        if key in byid:errors.append(key+': duplicate ADR identifier')
        byid[key]=a
    for key,a in byid.items():
        state=a.get('status');meta=a.get('governance')
        if not isinstance(state,str) or state not in STATES:
            errors.append(key+': unknown lifecycle state');continue
        if not isinstance(meta,dict):errors.append(key+': governance object required');continue
        if set(meta)!=allowed:errors.append(key+': missing or unrecognized governance fields')
        for name in ('accountable_role','scope'):
            if not substantive(meta.get(name)):errors.append(key+': missing '+name)
        evidence=meta.get('evidence_refs')
        if not isinstance(evidence,list) or not all(substantive(x) for x in evidence):
            errors.append(key+': evidence references must be a list of non-placeholder strings')
        elif len(evidence)!=len(set(evidence)):
            errors.append(key+': duplicate evidence reference')
        if state=='Proposed':
            if any(meta.get(name) is not None for name in
                   ('deciding_authority','decision_record','decision_date','decision_rationale')) or evidence!=[]:
                errors.append(key+': Proposed record cannot contain a recorded lifecycle decision')
        else:
            for name in ('deciding_authority','decision_record','decision_date','decision_rationale'):
                if not substantive(meta.get(name)):errors.append(key+': missing '+name)
            try:
                value=date.fromisoformat(meta.get('decision_date',''))
                if value>date.today():errors.append(key+': decision date in the future')
            except (ValueError,TypeError):errors.append(key+': invalid decision date')
            if not evidence:errors.append(key+': evidence references required')
        successor=meta.get('superseded_by')
        if successor is not None and (not isinstance(successor,str) or not re.fullmatch(r'ADR-\d{4}',successor)):
            errors.append(key+': invalid successor type');continue
        if state=='Superseded':
            if successor==key or successor not in byid:errors.append(key+': invalid successor')
            elif byid[successor].get('status') not in ('Accepted','Superseded'):errors.append(key+': successor not accepted')
        elif successor is not None:errors.append(key+': only a superseded record can name a successor')
    # Shape errors are reported above. Walk only well-typed edges, with a finite bound.
    for key in byid:
        chain=set();at=key
        while isinstance(at,str) and at in byid:
            if at in chain:errors.append(key+': supersession cycle');break
            chain.add(at);meta=byid[at].get('governance')
            at=meta.get('superseded_by') if isinstance(meta,dict) else None
    return errors


def normalize_page(text):
    return re.sub(r' {2,}\n','<br>\n',text).rstrip()+'\n'


def render(a, builder):
    p=builder.adrpath(a);g=a['governance']
    refs=' · '.join(builder.slink(p,s,n) for s,n in a['source_sections'])
    originals=', '.join('`'+x+'`' for x in a['source_decision_ids']) or 'Chapter-derived; no standalone source ID asserted.'
    requirements=' · '.join(builder.link(p,'docs/assurance/requirements.md',x,x) for x in a['requirements'])
    code='\n'.join('- '+builder.link(p,x,x) for x in a['implementation_paths'])
    evidence='; '.join(g.get('evidence_refs',[])) or 'Not supplied'
    extensions=''
    for extension in a.get('proposed_extensions',[]):
        erefs=' · '.join(builder.slink(p,s,n) for s,n in extension['source_sections'])
        extensions+='\n## Proposed clarification — '+extension['title']+'\n\n'+extension['text']+'\n\nSource basis: '+erefs+'. This clarification is not an accepted historical decision.\n'
    return normalize_page(f'''# {a['id']} — {a['title']}

**Status:** {a['status']}<br>
**Accountable role:** {g['accountable_role']}<br>
**Scope:** {g['scope']}<br>
**Original decision identifiers:** {originals}<br>
**Source chapters:** {refs}

{a['derivation']} The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

## Context

{a['context']}

## Decision recorded in the source

{a['decision']}

## Alternatives and limits recorded in the source

{a['alternatives']}

## Consequences

{a['consequences']}

## Engineering and implementation obligations

{a['engineering_obligations']}

## Requirement and code traceability

{requirements}

Related implementation areas are traceability targets, not proof of complete implementation:

{code}

Review {builder.link(p,'docs/implementation/assertion-allocation.md','the assertion allocation')} for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

{a['open_work']}

**Deciding authority:** {g.get('deciding_authority') or 'Not recorded'}<br>
**Decision date:** {g.get('decision_date') or 'Not recorded'}<br>
**Decision record:** {g.get('decision_record') or 'Not supplied'}<br>
**Evidence references:** {evidence}<br>
**Decision rationale:** {g.get('decision_rationale') or 'No lifecycle decision recorded'}<br>
**Superseded by:** {g.get('superseded_by') or 'None'}

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.
{extensions}
---

{builder.link(p,'docs/adr/README.md','Decision register')} · {builder.link(p,'docs/current/README.md','Maintained design workspace')}
''')
