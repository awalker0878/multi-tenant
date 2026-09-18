"""Independent publication fidelity, explicit amendments, and ADR governance.

A valid record is documentation evidence, not authentication of an authority.
This module neither imports the DOCX converter's text extractor nor contacts a target.
"""
from __future__ import annotations
import csv, hashlib, html, json, re
from datetime import date
from pathlib import Path
from xml.etree import ElementTree as ET

W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
STATUSES={'Proposed','Accepted','Rejected','Superseded'}
FIELDS=('context','decision','alternatives','consequences','engineering_obligations','open_work')

def sha(value):return hashlib.sha256(value.encode() if isinstance(value,str) else value).hexdigest()
def visible_word(node, code=False):
    pieces=[]
    for n in node.iter():
        if n.tag==W+'t':pieces.append(n.text or '')
        elif n.tag==W+'tab':pieces.append('\t' if code else ' ')
        elif n.tag in (W+'br',W+'cr') and n.get(W+'type') not in ('page','column'):pieces.append('\n')
        elif n.tag==W+'noBreakHyphen':pieces.append('‑')
    text=''.join(pieces).replace('\r\n','\n').replace('\r','\n')
    if code:return text
    return re.sub(r'\s+',' ',text.replace('\u00ad','').replace('\u200b','').replace('\xa0',' ')).strip()

def region(text,source_id,block):
    begin=f'<!-- SOURCE-BLOCK {source_id}:{block} BEGIN -->'
    end=f'<!-- SOURCE-BLOCK {source_id}:{block} END -->'
    if text.count(begin)!=1 or text.count(end)!=1 or text.index(begin)>text.index(end):
        raise ValueError('Missing, repeated or reversed source-block boundary')
    return text.split(begin,1)[1].split(end,1)[0].strip('\n')

def normalize_visible(text):
    return re.sub(r'\s+',' ',text.replace('\u00ad','').replace('\u200b','').replace('\xa0',' ')).strip()

def block_checks(node,source_id,block,page,parse,amendment=None):
    """Compare code exactly and every table cell in its original row/column."""
    checks=[]
    def add(label,ok):checks.append((f'{label}: {source_id}/{block}',bool(ok)))
    try:body=region(page,source_id,block)
    except ValueError:add('source block boundaries',False);return checks
    if amendment is not None:
        add('explicit maintained amendment',sha(body)==amendment['replacement_sha256'])
        return checks
    soup=parse(body)
    if node.tag==W+'tbl':
        table=soup.find('table');word_rows=node.findall(W+'tr')
        actual_rows=table.find_all('tr') if table else []
        add('ordered table rows',len(word_rows)==len(actual_rows))
        for i,(wr,ar) in enumerate(zip(word_rows,actual_rows)):
            expected=wr.findall(W+'tc');actual=ar.find_all(['td','th'],recursive=False)
            add(f'row {i} cell count',len(expected)==len(actual))
            for j,(wc,ac) in enumerate(zip(expected,actual)):
                # Word paragraph boundaries and HTML <br> are semantic whitespace;
                # inline emphasis and link elements do not add artificial spaces.
                for br in ac.find_all('br'):br.replace_with(' ')
                want=normalize_visible(' '.join(visible_word(p) for p in wc.iter(W+'p')))
                got=normalize_visible(ac.get_text())
                add(f'ordered cell {i}/{j}',want==got)
    elif node.tag==W+'p':
        style=node.find(W+'pPr/'+W+'pStyle');name=style.get(W+'val','') if style is not None else ''
        if 'code' in name.lower():
            code=soup.find('pre');got=code.get_text() if code else None
            expected=visible_word(node,True)
            # The code fence contributes one terminal line break; internal newlines,
            # tabs and spaces must match exactly, including a literal backslash.
            add('exact code structure',got==expected+'\n')
    return checks

def valid_date(value):
    if not isinstance(value,str):return False
    try:return date.fromisoformat(value).isoformat()==value
    except ValueError:return False

def lifecycle_errors(records):
    errors=[];ids={a.get('id') for a in records}
    if len(ids)!=len(records):errors.append('Duplicate ADR ID')
    byid={a['id']:a for a in records}
    for a in records:
        ident=a.get('id');g=a.get('governance',{});status=a.get('status')
        if status not in STATUSES:errors.append(f'{ident}: invalid status')
        for field in ('accountable_role','scope'):
            if not isinstance(g.get(field),str) or not g[field].strip():errors.append(f'{ident}: {field} required')
        if not valid_date(g.get('recorded_date')):errors.append(f'{ident}: recorded date required')
        if not isinstance(g.get('evidence'),list) or any(not isinstance(x,str) or not x.strip() for x in g.get('evidence',[])):errors.append(f'{ident}: evidence must be a reference list')
        if status in ('Accepted','Rejected','Superseded'):
            if not valid_date(g.get('decision_date')):errors.append(f'{ident}: actual decision date required')
            if not isinstance(g.get('accepting_authority'),str) or not g['accepting_authority'].strip():errors.append(f'{ident}: actual deciding authority required')
            if not g.get('evidence'):errors.append(f'{ident}: decision evidence required')
        if status in ('Rejected','Superseded') and not g.get('rationale'):errors.append(f'{ident}: disposition rationale required')
        if status=='Proposed' and (g.get('accepting_authority') or g.get('decision_date')):errors.append(f'{ident}: proposed record cannot claim acceptance')
        for key,reciprocal in [('supersedes','superseded_by'),('superseded_by','supersedes')]:
            values=g.get(key)
            if not isinstance(values,list) or len(values)!=len(set(values)):errors.append(f'{ident}: invalid {key}');continue
            for peer in values:
                if peer not in ids or peer==ident:errors.append(f'{ident}: invalid supersession target {peer}')
                elif ident not in byid[peer].get('governance',{}).get(reciprocal,[]):errors.append(f'{ident}: missing reciprocal supersession with {peer}')
                elif key=='superseded_by' and byid[peer].get('status') not in ('Accepted','Superseded'):errors.append(f'{ident}: successor is not an adopted decision')
        if status=='Superseded' and not g.get('superseded_by'):errors.append(f'{ident}: successor required')
        if status!='Superseded' and g.get('superseded_by'):errors.append(f'{ident}: non-superseded record names successor')
    # A supersession cycle would have no coherent current decision.
    def visit(i,path):
        if i in path:errors.append('Supersession cycle: '+i);return
        for n in byid[i].get('governance',{}).get('supersedes',[]):
            if n in byid:visit(n,path|{i})
    for i in ids:visit(i,set())
    return errors

def adr_text(builder,a):
    p=builder.adrpath(a);g=a['governance']
    refs=' · '.join(builder.slink(p,s,n) for s,n in a['source_sections'])
    ids=', '.join('`'+x+'`' for x in a['source_decision_ids']) or 'Chapter-derived; no invented source decision identifier.'
    reqs=' · '.join(builder.link(p,'docs/assurance/requirements.md',x,x) for x in a['requirements'])
    code='\n'.join('- '+builder.link(p,x,x) for x in a['implementation_paths'])
    evidence=' · '.join(g['evidence']) or 'Not supplied; no acceptance claim.'
    ext='\n> **Editorial extension:** this record includes a separately identified audit-remediation proposal grounded in its linked sources; no original approval is inferred.\n' if a.get('editorial_extensions') else ''
    return f'''# {a['id']} — {a['title']}

**Status:** {a['status']}<br>
**Accountable role:** {g['accountable_role']}<br>
**Scope:** {g['scope']}<br>
**Record date:** {g['recorded_date']} (not an approval date)<br>
**Original decision identifiers:** {ids}<br>
**Source chapters:** {refs}

{a['derivation']}{ext}

## Context

{a['context']}

## Decision

{a['decision']}

## Alternatives and source limitations

{a['alternatives']}

## Consequences

{a['consequences']}

## Engineering and implementation obligations

{a['engineering_obligations']}

## Requirement and code traceability

{reqs}

These are related implementation areas, not assertion-level evidence of native qualification:

{code}

{builder.link(p,'docs/assurance/implementation-allocation.md','Requirement/assertion allocation')} records partial, external and unimplemented controls separately.

## Open work

{a['open_work']}

## Decision lifecycle and authority

- Deciding authority: {g['accepting_authority'] or 'Not recorded.'}
- Decision date: {g['decision_date'] or 'Not recorded.'}
- Decision evidence: {evidence}
- Disposition rationale: {g['rationale'] or 'No rejection or supersession recorded.'}
- Supersedes: {', '.join(g['supersedes']) or 'None.'}
- Superseded by: {', '.join(g['superseded_by']) or 'None.'}

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

{builder.link(p,'docs/adr/README.md','Decision register')} · {builder.link(p,'docs/DOCUMENTATION_MIGRATION.md','Maintenance rules')}
'''.rstrip()+'\n'

def render_adrs(builder):
    errors=lifecycle_errors(builder.adrs)
    if errors:raise ValueError('; '.join(errors))
    cross=[];backlinks={}
    for a in builder.adrs:
        p=builder.adrpath(a);builder.write(p,adr_text(builder,a))
        for s,n in a['source_sections']:
            target=builder.section(s,n);backlinks.setdefault(target,[]).append(a)
            cross.append({'adr':a['id'],'title':a['title'],'status':a['status'],'originalDecisionIds':'; '.join(a['source_decision_ids']), 'sourceId':s,'sourceSection':str(n),'markdownSource':target,'adrPath':p})
    begin='<!-- BEGIN GENERATED DECISION LINKS -->';end='<!-- END GENERATED DECISION LINKS -->'
    for target,items in backlinks.items():
        p=builder.root/target;text=re.sub(re.escape(begin)+r'.*?'+re.escape(end),'',p.read_text(),flags=re.S).rstrip()
        block='\n\n'+begin+'\n\n## Related decision records\n\n'+'\n'.join('- '+builder.link(target,builder.adrpath(a),a['id']+' — '+a['title']) for a in items)+'\n\n'+end+'\n'
        p.write_text(text+block)
    with (builder.root/'sources/documentation/adr_crosswalk.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(cross[0]));writer.writeheader();writer.writerows(cross)
    p='docs/adr/README.md'
    lines=['# Architecture decision register','',
      'Source-derived records remain Proposed until actual adoption is recorded. The structured registry is the canonical ADR authoring record; pages, indexes and crosswalks are rendered from it. No status is invented by generation or by a passing test.','',
      '| Record | Original identifier | Status | Accountable role |','|---|---|---|---|',
      '| '+builder.link(p,'docs/adr/0001-architecture-first-repository.md','ADR-0001 — Repository structure')+' | Repository convention | Proposed | Repository owner |',
      '| '+builder.link(p,'docs/adr/0002-markdown-first-source-backed-documentation.md','ADR-0002 — Markdown maintenance')+' | Editorial proposal | Proposed | Documentation owner |']
    for a in builder.adrs:lines.append('| '+builder.link(p,builder.adrpath(a),a['id']+' — '+a['title'])+' | '+(', '.join(a['source_decision_ids']) or 'Chapter-derived')+' | '+a['status']+' | '+a['governance']['accountable_role']+' |')
    lines+=['','## Authoring and acceptance','',
      'Edit `sources/documentation/adr_records.json`, then run `python scripts/build_documentation.py`. Accepted, Rejected and Superseded records require an actual deciding authority, date and evidence; rejection/supersession also needs rationale. Supersession references are reciprocal and cycle-free. Proposed records cannot claim acceptance. A status transition must be backed by the stated actual evidence; no record is automatically promoted.', '',
      builder.link(p,'docs/adr/template.md','ADR template')+' · '+builder.link(p,'docs/assurance/implementation-allocation.md','Assertion-level allocation')]
    builder.write(p,'\n'.join(lines))

def amendment_records(root,specs,ledger,adr_ids,requirement_ids):
    path=root/'sources/documentation/amendments.json';rows=json.loads(path.read_text()) if path.exists() else []
    if not isinstance(rows,list):raise ValueError('Amendments must be a list')
    byblock={(r['source_id'],r['block']):r for r in ledger};out={}
    fields={'id','source_id','block','original_text_sha256','replacement_markdown','replacement_sha256','reason','accountable_role','recorded_date','status','requirements','adrs','decision_date','authority','evidence'}
    for a in rows:
        if set(a)!=fields:raise ValueError('Missing or unknown amendment fields')
        key=(a['source_id'],a['block']);record=byblock.get(key)
        if key in out or record is None or record['status']!='converted':raise ValueError('Invalid/duplicate amended block')
        if record['source_text_sha256']!=a['original_text_sha256']:raise ValueError('Amendment original identity mismatch')
        text=a['replacement_markdown']
        if not isinstance(text,str) or not text.strip() or '<!-- SOURCE-BLOCK' in text or sha(text.strip('\n'))!=a['replacement_sha256']:raise ValueError('Invalid amendment replacement')
        if not all(isinstance(a[k],str) and a[k].strip() for k in ('id','reason','accountable_role')) or not valid_date(a['recorded_date']):raise ValueError('Amendment provenance required')
        if a['status'] not in ('Proposed','Accepted'):raise ValueError('Invalid active amendment status')
        if a['status']=='Accepted' and (not a['authority'] or not a['evidence'] or not valid_date(a['decision_date'])):raise ValueError('Accepted amendment requires actual authority/date/evidence')
        if a['status']=='Proposed' and (a['authority'] or a['decision_date']):raise ValueError('Proposed amendment cannot claim acceptance')
        if not set(a['requirements'])<=requirement_ids or not set(a['adrs'])<=adr_ids:raise ValueError('Unknown amendment trace references')
        out[key]=a
    return out
