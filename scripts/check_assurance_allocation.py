"""Structural assertions for explicitly proposed allocation and test-family coverage."""
import csv,json


def check(root):
    errors=[]
    shared=root/'reference/Portable_Hosting_Delivery_Kits_v1_1/04_Shared'
    with (shared/'requirements.csv').open(encoding='utf-8-sig',newline='') as f:requirements={r['requirementId']:r for r in csv.DictReader(f)}
    with (shared/'tests.csv').open(encoding='utf-8-sig',newline='') as f:ct={r['id'] for r in csv.DictReader(f)}
    rows=json.loads((root/'sources/assurance/implementation_assertions.json').read_text());seen=set();covered=set()
    for row in rows:
        ident=row.get('assertion_id');parent=row.get('requirement_id')
        if not ident or ident in seen:errors.append('Duplicate/missing assertion ID')
        seen.add(ident);covered.add(parent)
        if parent not in requirements or row.get('source_requirement')!=requirements[parent]['text']:errors.append(str(ident)+': source statement differs')
        for key in ('assertion','implementation_owner','enforcement_location','implementation_disposition','required_artifact_or_record','verification_method','evidence_class','remaining_dependency','owner_review'):
            if not isinstance(row.get(key),str) or len(row[key].strip())<4:errors.append(str(ident)+': incomplete '+key)
        if not row.get('candidate_artifacts') or any(not (root/p).exists() for p in row['candidate_artifacts']):errors.append(str(ident)+': unresolved source artifact')
        if not set(row.get('reference_tests',[]))<=ct:errors.append(str(ident)+': unresolved test IDs')
        if 'NATIVE_NOT_RUN' not in row.get('evidence_class',''):errors.append(str(ident)+': an unverified allocation must not claim native success')
    if covered!=set(requirements):errors.append('Not all requirements have an allocation')
    families=json.loads((root/'sources/assurance/verification_families.json').read_text())
    if families['families']!={'CT':80,'RA':12,'W14':12,'Q11':12}:errors.append('Verification family count mismatch')
    mappings=families['supplemental_mappings'];ids=[r['id'] for r in mappings]
    expected={f'RA-{i:02d}' for i in range(1,13)}|{f'Q11-{i:02d}' for i in range(1,13)}|{f'W14-{i:02d}' for i in range(1,13)}
    if len(ids)!=len(set(ids)) or set(ids)!=expected:errors.append('Supplemental family ID coverage mismatch')
    for entry in mappings:
        if not (root/entry['source_path']).is_file():errors.append('Missing test source')
        if entry['execution_status']!='not-run':errors.append('Unexecuted test specification promoted to result')
        if not set(entry.get('base_tests',[]))<=ct:errors.append('Unknown CT mapping')
    with (root/'sources/assurance/historical_audit_dispositions.csv').open(newline='') as f:history=list(csv.DictReader(f))
    if {x['original_finding'] for x in history}!={f'F{i:02d}' for i in range(1,25)}:errors.append('Historical finding coverage incomplete')
    for x in history:
        if x['closure_status']!='NOT_CLOSED_BY_THIS_AUDIT' or not (root/x['source_path']).is_file():errors.append('Historical closure incorrectly asserted or source absent')
    return {'allocation_rows':len(rows),'requirements':len(covered),'errors':errors}
