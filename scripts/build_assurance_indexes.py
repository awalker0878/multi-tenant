#!/usr/bin/env python3
"""Render every retained test family and the explicit assertion allocation.

These are specifications and owner-review mappings, never executed-test counts.
No source requirement, inherited status or original procedure is overwritten.
"""
from pathlib import Path
import csv,json,re
from collections import Counter
from build_documentation import Builder
ROOT=Path(__file__).resolve().parents[1]


def read_csv(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def build(root=ROOT):
    b=Builder(root);base=root/'reference/Portable_Hosting_Delivery_Kits_v1_1'
    ra_path=base/'05_Reference_v1_4/registers/realization_verification_addenda.json'
    ra=json.loads(ra_path.read_text());ct=read_csv(base/'04_Shared/tests.csv')
    qpath=base/'04_Shared/development/qualification_observation_cards.csv';cards=read_csv(qpath)
    wpath=base/'05_Reference_v1_4/registers/v1_4_verification_assertions.csv';worked=read_csv(wpath)
    path='docs/assurance/realization-addenda.md';lines=['# Native realization addenda — RA-01 to RA-12','','These are the retained supplemental procedures, not a new set of executed tests. Each elaborates the CT references shown and retains its original not-run state. Select by actual stack, offered service and accepted test safety envelope.','',b.link(path,str(ra_path.relative_to(root)),'Unchanged source JSON'),'']
    for row in ra:
        lines += [f'<a id="{row["id"]}"></a>',f'## {row["id"]} — {row["title"]}','',f'**State:** {row["executionStatus"]}. **Base procedures:** '+', '.join(row['baseTests'])+'.','',row['procedure'],'','**Expected:** '+row['expected'],'','**Safety:** '+row['safety'],'','**Parent architecture:** '+' · '.join(b.slink(path,'RA',n) for n in row['chapters']), '']
    b.write(path,'\n'.join(lines))
    path='docs/assurance/verification-families.md'
    lines=['# Verification-family selection index','','A procedure ID is not an executed result. CT, RA, W14 and Q11 overlap deliberately; do not sum their counts as unique assurance coverage. All retained execution states below are unexecuted. Actual test records require version, target, preconditions, healthy controls, observations, evidence and reviewer.','','| Family | Retained entries | Purpose and applicability | Read |','|---|---:|---|---|',f'| CT | {len(ct)} | Baseline requirements; select by service, architecture and lifecycle stage | [Full specifications](test-specifications.md) |',f'| RA | {len(ra)} | Native realization elaborations of named CTs; selected platform/backend and change scope | [Full addenda](realization-addenda.md) |',f'| W14 | {len(worked)} | Connected internal reference design; fixture-specific architecture assertions | '+b.slink(path,'WD',13,'Worked assertions')+' |',f'| Q11 | {len(cards)} | Operational observation/control cards elaborating existing test IDs | '+b.slink(path,'QCP',3,'Campaign cards')+' |','','## Explicit supplemental mappings','','| ID | Source / existing test references | Selection / status |','|---|---|---|']
    mappings=[]
    for row in ra:
        refs=row['baseTests'];lines.append('| '+b.link(path,'docs/assurance/realization-addenda.md',row['id'],row['id'])+' | '+', '.join(refs)+' | Selected native realization; '+row['executionStatus']+' |')
        mappings.append({'id':row['id'],'family':'RA','source_path':str(ra_path.relative_to(root)),'base_tests':refs,'execution_status':row['executionStatus'],'applicability':'Selected native realization and covered failure; owner-approved scope required'})
    for row in cards:
        refs=[x.strip() for x in row['existing_test_ids'].split(';')];lines.append('| '+row['id']+' | '+', '.join(refs)+' | '+row['title']+'; '+row['execution_status']+' |')
        mappings.append({'id':row['id'],'family':'Q11','source_path':str(qpath.relative_to(root)),'base_tests':refs,'execution_status':row['execution_status'],'applicability':row['scope_note']})
    for row in worked:
        ident=row['assertion'].split(' / ',1)[0]
        # Preserve original columns and wording verbatim in the source; the navigation does not invent equivalence.
        mappings.append({'id':ident,'family':'W14','source_path':str(wpath.relative_to(root)),'original_record':row,'execution_status':'not-run','applicability':'Connected W14 design; applicability and current native observation must be assessed'})
    lines += ['',b.link(path,str(wpath.relative_to(root)),'Original W14 assertion register')+' · '+b.link(path,str(qpath.relative_to(root)),'Original Q11 observation register'),'','## Acceptance boundary','','A mandatory assertion that is blocked, not run or unjustifiably not applicable cannot pass a gate. First-stack acceptance does not wait for already-qualified multiple stacks; cross-stack outcome comparison and actual data/service exit are later separate claims. Reuse evidence only when target generation, topology, versions and dependency conditions remain valid.','', '[Assertion-to-owner allocation](../implementation/assertion-allocation.md) · [Historical finding dispositions](historical-dispositions.md)']
    b.write(path,'\n'.join(lines))
    out=root/'sources/assurance';out.mkdir(exist_ok=True)
    (out/'verification_families.json').write_text(json.dumps({'families':{'CT':len(ct),'RA':len(ra),'W14':len(worked),'Q11':len(cards)},'supplemental_mappings':mappings,'execution':'SPECIFICATIONS_NOT_EXECUTED','counts_are_not_additive_unique_tests':True},indent=2)+'\n')
    allocation=json.loads((out/'implementation_assertions.json').read_text());counts=Counter(row['requirement_id'].split('-')[0] for row in allocation)
    path='docs/implementation/assertion-allocation.md'
    lines=['# Assertion-level implementation and enforcement allocation','','**State: proposed engineering allocation; native verification and owner adoption are not claimed.** Each row retains its exact source requirement and identifies a narrower checkable facet, enforcement owner/location, related candidate artifact or external operating record, verification method and remaining dependency. A module link does not satisfy a requirement by itself.','','All 194 requirements are represented. Compound requirements have explicit facets as well as an umbrella obligation that preserves anything not covered by a facet. The umbrella is not marked passed; the owner must finish scope analysis for each actual offered service. Not applicable requires an explicit rationale and authority, not a convenience flag.','','| Family | Allocation rows | Read |','|---|---:|---|']
    for family,count in sorted(counts.items()):lines.append(f'| {family} | {count} | [{family} allocation](allocation/{family.lower()}.md) |')
    lines+=['','[Machine-readable allocation](../../sources/assurance/implementation_assertions.json) · [Editable CSV](../../sources/assurance/implementation_assertions.csv) · [Verification families](../assurance/verification-families.md)','','No actual site, supported vendor tuple, native approval or complete implementation is invented. The enforced-state evidence class remains **NATIVE_NOT_RUN** even where a candidate function is exercised in a local fixture.']
    lines+=['','The JSON/CSV allocation is a proposed starting record for owner review. The one-time initializer refuses to overwrite an existing allocation. Maintain accepted owner, applicability and evidence assignments through a reviewed record change; `build_assurance_indexes.py` only republishes those records. Native evidence transitions require extending the acceptance checker deliberately and supplying actual evidence, not deleting its not-run guard.']
    b.write(path,'\n'.join(lines))
    for family in sorted(counts):
        p=f'docs/implementation/allocation/{family.lower()}.md';text=['# '+family+' — assertion allocation','','[Allocation index](../assertion-allocation.md) · [Unchanged requirement catalogue](../../assurance/requirements.md)','','These are source-grounded proposed allocations, not native compliance results.'];last=None
        for row in (r for r in allocation if r['requirement_id'].split('-')[0]==family):
            if last!=row['requirement_id']:
                text += ['','## '+row['requirement_id'],'',row['source_requirement'],''];last=row['requirement_id']
            text += ['','### '+row['assertion_id'],'','**Assertion:** '+row['assertion'],'','**Owner / location:** '+row['implementation_owner']+' / '+row['enforcement_location'], '', '**Disposition:** '+row['implementation_disposition']+'. **Evidence class:** '+row['evidence_class'], '', '**Artifact or required operating record:** '+row['required_artifact_or_record'], '', '**Available related source:** '+' · '.join(b.link(p,x,x) for x in row['candidate_artifacts']), '', '**Verification:** '+row['verification_method']+' Baseline procedures: '+', '.join(row['reference_tests']), '', '**Remaining dependency:** '+row['remaining_dependency'], '', '**Review state:** '+row['owner_review']]
        b.write(p,'\n'.join(text))
    return {'allocation_rows':len(allocation),'requirement_count':len({x['requirement_id'] for x in allocation}),'family_counts':dict(counts),'verification_counts':{'CT':len(ct),'RA':len(ra),'W14':len(worked),'Q11':len(cards)}}
if __name__=='__main__':print(json.dumps(build(),indent=2))
