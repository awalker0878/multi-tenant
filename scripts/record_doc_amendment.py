#!/usr/bin/env python3
"""Record a proposed source-block revision after editing maintained Markdown.

No approval or external side effect. Full ledger validation precedes atomic local
write. Actual acceptance fields are entered through a separate reviewed record edit.
"""
from __future__ import annotations
import argparse,csv,json,os,tempfile
from datetime import date
from pathlib import Path
from documentation_controls import region,sha,amendment_records
ROOT=Path(__file__).resolve().parents[1]
def proposed(root,source_id,block,reason,role,requirements,adrs):
    ledger=json.loads((root/'sources/documentation/block_coverage.json').read_text())
    row=next((r for r in ledger if r['source_id']==source_id and r['block']==block and r['status']=='converted'),None)
    if not row:raise ValueError('Unknown converted source block')
    text=region((root/row['destination']).read_text(),source_id,block)
    if not reason.strip() or not role.strip() or not text.strip():raise ValueError('Reason, accountable role and content required')
    return {'id':f'AMEND-{source_id}-{block:04d}','source_id':source_id,'block':block,
        'original_text_sha256':row['source_text_sha256'],'replacement_markdown':text,
        'replacement_sha256':sha(text),'reason':reason,'accountable_role':role,
        'recorded_date':date.today().isoformat(),'status':'Proposed','requirements':requirements,'adrs':adrs,
        'decision_date':None,'authority':None,'evidence':[]}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source_id');p.add_argument('block',type=int)
    p.add_argument('--reason',required=True);p.add_argument('--role',required=True)
    p.add_argument('--requirement',action='append',default=[]);p.add_argument('--adr',action='append',default=[])
    p.add_argument('--write-record',action='store_true');a=p.parse_args()
    try:
        record=proposed(ROOT,a.source_id,a.block,a.reason,a.role,a.requirement,a.adr)
        path=ROOT/'sources/documentation/amendments.json';rows=json.loads(path.read_text())
        if any(r['source_id']==a.source_id and r['block']==a.block for r in rows):raise ValueError('Existing amendment requires explicit reviewed revision, not overwrite')
        adrs={r['id'] for r in json.loads((ROOT/'sources/documentation/adr_records.json').read_text())}
        reqs={r['requirementId'] for r in csv.DictReader((ROOT/'reference/Portable_Hosting_Delivery_Kits_v1_1/04_Shared/requirements.csv').open(encoding='utf-8-sig'))}
        if not set(a.adr)<=adrs or not set(a.requirement)<=reqs:raise ValueError('Unknown traceability identifier')
        print(json.dumps(record,indent=2))
        if a.write_record:
            fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.amend-')
            try:
                with os.fdopen(fd,'w') as out:json.dump(rows+[record],out,ensure_ascii=False,indent=2);out.write('\n')
                os.replace(tmp,path)
            finally:
                if os.path.exists(tmp):os.unlink(tmp)
            print('Proposed amendment recorded; run the checker and review its diff. No acceptance issued.')
        return 0
    except (ValueError,OSError,KeyError) as e:print('BLOCKED:',str(e));return 2
if __name__=='__main__':raise SystemExit(main())
