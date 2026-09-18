#!/usr/bin/env python3
"""Render proposed implementation/disposition records and full verification families.

Original procedures are not promoted to executed tests. No native control is marked
satisfied by a code link, an editorial assertion split or an ADR review.
"""
from __future__ import annotations
import csv,json,os,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def link(origin,target,label):return f'[{label}]({os.path.relpath(target,Path(origin).parent).replace(os.sep,"/")})'
def write(root,path,text):
 p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text.rstrip()+'\n')
def build(root=ROOT):
 path='docs/assurance/implementation-allocation.md';rows=json.loads((root/'sources/assurance/implementation_allocation.json').read_text());groups={}
 for a in rows:groups.setdefault(a['requirement_id'],[]).append(a)
 lines=['# Proposed assertion-level implementation allocation','',
 '**State: proposed engineering allocation. No native requirement is marked satisfied.** Each original requirement is retained verbatim and compound obligations are separated into exact source-focus spans. A span inherits its complete requirement; this is not a new normative rewrite or a claim that every possible interpretation is exhausted.','',
 'The allocation distinguishes concrete enforcement locations, responsible source roles, partial candidate code, external services, manual/governance decisions and unimplemented work. Every focus needs a site-specific configuration record and actual evidence. Unresolved mandatory responsibility blocks Service Ready.', '',
 link(path,'sources/assurance/implementation_allocation.csv','Editable allocation CSV')+' · '+link(path,'sources/assurance/implementation_allocation.json','Canonical records')+' · '+link(path,'docs/assurance/verification-families.md','Verification families'),'',
 f'Coverage: {len(groups)} original requirements; {len(rows)} proposed assertion focuses. These are allocation records, not counts of implemented controls or tests.','',
 '## Requirement navigation','', ' · '.join(link(path,path,ident)+'#' if False else f'[{ident}](#{ident})' for ident in groups),'']
 for ident,items in groups.items():
  first=items[0];lines += [f'<a id="{ident}"></a>',f'## {ident}','',first['source_requirement'],'',
   '**Source role:** '+first['responsible_role']+'. **Original design references:** '+first['source_sections']+'.','',
   '**Enforcement location:** '+first['enforcement_location']+'.','',
   '**Delivery disposition:** `'+first['implementation_disposition']+'`.','',
   '**Related code/procedure:** '+' · '.join(link(path,p,p) for p in first['artifacts'])+'. These artifacts do not individually or collectively establish the entire requirement.','',
   '**Current evidence limit:** '+first['evidence_level']+'. Actual native evidence is not supplied.','',
   '**Outstanding dependency:** '+first['remaining_dependency'],'',
   '| Assertion | Exact source focus | Required site-specific completion |','| --- | --- | --- |']
  for a in items:lines += ['| '+a['assertion_id']+' | '+a['assertion_focus'].replace('|','&#124;')+' | Identify accepted setting/native authority, apply referenced test at this focus, and retain actual reviewed evidence. |']
  lines += ['','**Verification:** '+' · '.join(f'[{t}](test-specifications.md#{t})' for t in first['verification_procedures'])+'. '+first['verification_method'],'',
   '**Applicability and acceptance:** '+first['applicability']+'. The accountable project role records applicability, configuration and evidence; this reusable allocation does not invent those decisions.','']
 write(root,path,'\n'.join(lines))
 path='docs/assurance/historical-findings.md';rows=json.loads((root/'sources/assurance/historical_findings.json').read_text())
 lines=['# Individual disposition of the historical F01–F24 audit','',
 '**Status: individually triaged, not closed.** These are proposed current-scope dispositions based on the supplied completion audit and original finding. A retired contract bug is not repaired by converting prose. Native obligations that remain applicable are not waived. No closure authority is invented.','',link(path,'sources/assurance/historical_findings.json','Canonical disposition records'),'']
 for a in rows:
  lines += [f'<a id="{a["original_finding"]}"></a>',f'## {a["title"]}','',link(path,a['source_path'],'Original historical finding'),'',
   '**Proposed current applicability:** '+a['proposed_current_disposition']+'.','',a['audit_assessment'],'',
   '**Accountable role to assign:** '+a['accountable_role']+'.','',
   '**Current implementation/evidence allocation:** '+link(path,a['current_scope_reference'],'Assertion-level allocation')+'.','',
   '**Remaining closure evidence:** '+a['required_closure_evidence'],'',
   '**Closure:** '+a['closure_status']+'; authority '+a['closure_authority']+'. This record does not renew an old acceptance state.','']
 write(root,path,'\n'.join(lines))
 families=json.loads((root/'sources/assurance/verification_families.json').read_text());path='docs/assurance/verification-families.md'
 lines=['# Unified verification-family index','',
 'Specification IDs are not passing results. CT procedures, RA realization addenda, W14 worked assertions and Q11 observation cards overlap by design. Do not add their counts as unique executed coverage. All imported execution statuses remain not-run; actual later fixture/native evidence is separately scoped.', '',
 '| Family | Purpose | Records | Applicable use |','| --- | --- | ---: | --- |',
 '| CT | Inherited baseline procedures | 80 | Apply by service, family, topology and accepted test scope |',
 '| RA | Native realization elaborations of CT procedures | 12 | Exact selected platform/upstream/backend and claimed capability |',
 '| W14 | Worked-design acceptance assertions mapped to CT | 12 | Check whether the illustrative plan is fully realized in the accepted target |',
 '| Q11 | Observation/healthy-control cards elaborating existing procedures | 12 | Collect meaningful bounded observations, not command success alone |','',
 '[Complete CT procedures](test-specifications.md) · [Full RA addenda](realization-addenda.md) · [W14 assertions](worked-assertions.md) · [Q11 cards](observation-cards.md)','',
 '## Selection and evidence','',
 'First-platform qualification uses applicable single-stack tests. A second stack needs its own qualification; portability and usable data/application exit require the separately scoped comparison and migration evidence. Intrusive failure scenarios need an authorized envelope and restoration plan; routine tenant provisioning does not automatically rerun destructive shared-foundation failures.', '',
 'Record applicability per assertion, target resources, exact versions/topology, approved procedure, positive/negative controls, actual outcome, retained artifacts and reviewer. Unknown/missing evidence is not a pass. A justified not-applicable case is an explicit owner decision; the directory structure does not make it so.','']
 for fam,data in families.items():lines += [link(path,data['source'],fam+' original source records')]
 write(root,path,'\n'.join(lines))
 for fam,filename,title in [('RA','realization-addenda.md','RA realization addenda'),('W14','worked-assertions.md','W14 worked-design assertions'),('Q11','observation-cards.md','Q11 qualification observation cards')]:
  path='docs/assurance/'+filename;data=families[fam];lines=['# '+title,'','Original fields are rendered below without rewriting their procedure, scope or not-run status. These are not newly executed results. [Family index](verification-families.md).','',link(path,data['source'],'Original records'),'']
  for row in data['records']:
   ident=row.get('id',row.get('assertion','')).split(' / ')[0]
   lines += [f'<a id="{ident}"></a>',f'## {ident}'+(' — '+row['title'] if row.get('title') else ''),'']
   for key,value in row.items():
    if isinstance(value,list):value='; '.join(map(str,value))
    lines += ['**'+key+':** '+(str(value) if value not in ('',None) else '[Unfilled original response field]'),'']
   tests=sorted(set(re.findall(r'CT-\d{3}',json.dumps(row))))
   if tests:lines+=['Related baseline procedures: '+' · '.join(f'[{t}](test-specifications.md#{t})' for t in tests),'']
  write(root,path,'\n'.join(lines))
 # Navigation is generated elsewhere; append idempotent links after its generation.
 for name in ('docs/README.md','docs/assurance/README.md','docs/assurance/audit-map.md','docs/implementation/code-map.md','docs/assurance/test-specifications.md'):
  p=root/name
  if not p.exists():continue
  marker='<!-- BEGIN ASSURANCE ALLOCATION LINKS -->';end='<!-- END ASSURANCE ALLOCATION LINKS -->'
  text=re.sub(re.escape(marker)+r'.*?'+re.escape(end),'',p.read_text(),flags=re.S).rstrip()
  text+='\n\n'+marker+'\n\n'+ ' · '.join(link(name,target,label) for target,label in [('docs/assurance/implementation-allocation.md','Assertion-level allocation'),('docs/assurance/verification-families.md','All verification families'),('docs/assurance/historical-findings.md','Historical finding dispositions'),('docs/assurance/completion-audit.md','Completion-audit corrections')])+'\n\n'+end+'\n';p.write_text(text)
 print('Rendered assertion allocation, historical dispositions and complete verification families')
if __name__=='__main__':build()
