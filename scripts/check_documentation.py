#!/usr/bin/env python3
"""Read-only local Word-to-Markdown coverage and decision-link verification.

Does not regenerate documents, crawl external sites, initialize providers or contact
infrastructure. A pass is publishing consistency, not architectural authorization.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import mistune
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from convert_word_docs import Source, q, plain, clean_text, digest
from documentation_controls import block_checks, lifecycle_errors, adr_text, amendment_records
from build_documentation import Builder

MD=mistune.create_markdown(escape=False,plugins=['table','strikethrough','task_lists'])
def normalized(s):return re.sub(r'\s+','',clean_text(s))
def heading_anchor(s):return re.sub(r'[^\w\- ]','',s.lower()).replace(' ','-')
def parse(text):return BeautifulSoup(MD(text),'html.parser')

def run(root=ROOT):
    checks=[];errors=[];metrics=Counter()
    def check(name,passed,detail=None):
        checks.append({'name':name,'passed':bool(passed),**({'detail':detail} if detail else {})})
        if not passed:errors.append({'check':name,**({'detail':detail} if detail else {})})
    inv=json.loads((root/'sources/documentation/source_inventory.json').read_text())
    manifest=json.loads((root/'sources/documentation/conversion_manifest.json').read_text())['documents']
    ledger=json.loads((root/'sources/documentation/block_coverage.json').read_text())
    bysource={d['id']:d for d in manifest};specs={d['id']:d for d in inv['documents']}
    check('one manifest per source',set(bysource)==set(specs) and len(bysource)==len(manifest))
    actualdocx={str(p.relative_to(root)) for p in root.rglob('*.docx') if not any(x in p.parts for x in ('build','.git','.venv','evidence'))}
    check('all repository Word files converted',actualdocx=={d['source'] for d in manifest})
    records=json.loads((root/'sources/documentation/adr_records.json').read_text())
    reqs=list(csv.DictReader((root/'reference/Portable_Hosting_Delivery_Kits_v1_1/04_Shared/requirements.csv').open(encoding='utf-8-sig',newline='')))
    reqids={r['requirementId'] for r in reqs}
    try:
        amendments=amendment_records(root,specs,ledger,{a['id'] for a in records},reqids)
        check('maintained amendment records valid',True)
    except (ValueError,KeyError,TypeError) as exc:
        amendments={};check('maintained amendment records valid',False,str(exc))
    cache={};ids={}
    def soup(path):
        if path not in cache:
            cache[path]=parse(path.read_text(encoding='utf-8'))
        return cache[path]
    def anchors(path):
        if path not in ids:
            doc=soup(path);vals=[t.get('id') for t in doc.find_all(id=True)]
            check('unique explicit anchors: '+str(path.relative_to(root)),len(vals)==len(set(vals)))
            explicit=set(vals);counts=Counter()
            for h in doc.find_all(re.compile(r'^h[1-6]$')):
                base=heading_anchor(h.get_text());idx=counts[base];counts[base]+=1
                explicit.add(base+('-'+str(idx) if idx else ''))
            ids[path]=explicit
        return ids[path]
    for d in manifest:
        path=root/d['source'];s=Source(root,specs[d['id']]);metrics['source_documents']+=1
        check('source bytes: '+d['id'],digest(path.read_bytes())==d['source_sha256'])
        check('source bookmark count: '+d['id'],len(d['bookmarks'])==len(s.bookmarks))
        check('no unresolved conversion links: '+d['id'],not d['warnings'],d['warnings'] or None)
        rows=[x for x in ledger if x['source_id']==d['id']]
        check('each source block has one disposition: '+d['id'],[x['block'] for x in rows]==list(range(len(s.blocks))))
        check('source table count: '+d['id'],sum(x['kind']=='table' for x in rows)==d['tables'])
        check('source form count: '+d['id'],len(s.forms)==len(d['form_fields']))
        destinations=[root/d['index']]+[root/c['path'] for c in d['chapters']]
        check('all chapter files exist: '+d['id'],all(p.is_file() for p in destinations))
        alltext=''.join(soup(p).get_text() for p in destinations if p.is_file())
        allnorm=normalized(alltext)
        for f in s.forms:
            metrics['form_prompts']+=1
            check('form prompt retained: '+d['id']+' '+f.get('tag',''),normalized(f['text']) in allnorm)
        for row in rows:
            b=s.blocks[row['block']];p=root/row['destination'];metrics['body_blocks']+=1
            check(f'block digest: {d["id"]}/{row["block"]}',digest(plain(b).encode())==row['source_text_sha256'])
            if row['status']=='publication-navigation-replaced':
                check(f'navigation-only exclusion: {d["id"]}/{row["block"]}',row['block'] in s.omitted)
                metrics['navigation_blocks_replaced']+=1;continue
            amendment=amendments.get((d['id'],row['block']))
            for name,passed in block_checks(b,d['id'],row['block'],p.read_text(),parse,amendment):
                check(name,passed)
            if amendment:
                metrics['explicitly_amended_blocks']+=1
                continue
            textnorm=normalized(soup(p).get_text())
            # Compare each actual paragraph independently, including every table cell.
            paras=[b] if b.tag==q('w:p') else list(b.iter(q('w:p')))
            for j,para in enumerate(paras):
                expected=normalized(plain(para))
                if expected:
                    metrics['source_paragraphs_compared']+=1
                    check(f'paragraph text: {d["id"]}/{row["block"]}/{j}',expected in textnorm,
                          None if expected in textnorm else {'destination':str(p.relative_to(root)),'expected_start':plain(para)[:180]})
            if b.tag==q('w:tbl'):
                metrics['tables']+=1
                marker=soup(p).find(id=f'source-table-{row["block"]}')
                table=marker.find_next('table') if marker else None
                check(f'table exists: {d["id"]}/{row["block"]}',table is not None)
                if table:
                    rowshtml=table.find_all('tr');cells=table.find_all(['td','th'])
                    check(f'table shape: {d["id"]}/{row["block"]}',len(rowshtml)==row['rows'] and len(cells)==row['cells'],
                        None if len(rowshtml)==row['rows'] and len(cells)==row['cells'] else {'actual':[len(rowshtml),len(cells)],'expected':[row['rows'],row['cells']]})
        for im in d['images']:
            metrics['figure_occurrences']+=1
            target=root/im['destination']
            check('image digest: '+d['id']+' '+im['source_part'],target.is_file() and digest(target.read_bytes())==im['sha256'])
            src=unquote(str(target.relative_to(root)))
            found=any((root/im['from']).parent.joinpath(unquote(urlsplit(i.get('src','')).path)).resolve()==target.resolve() for i in soup(root/im['from']).find_all('img'))
            check('image embedded in source chapter: '+d['id']+' '+im['source_part'],found)
        for name,mark in d['bookmarks'].items():
            metrics['source_bookmarks']+=1
            check('bookmark retained: '+d['id']+' '+name,mark['anchor'] in anchors(root/mark['path']))
        for p in destinations:
            if d['historical']:check('historical banner: '+str(p.relative_to(root)),'Historical only.' in p.read_text())
    # Parse Markdown rather than scanning raw syntax: code samples are not links.
    paths=list((root/'docs').rglob('*.md'))+[root/'README.md']
    for p in paths:
        for tag in soup(p).find_all(['a','img']):
            value=tag.get('href') if tag.name=='a' else tag.get('src')
            if not value:continue
            parts=urlsplit(value)
            if parts.scheme or value.startswith('//'):
                metrics['external_links_retained_not_contacted']+=1;continue
            target=(p.parent/unquote(parts.path)).resolve() if parts.path else p.resolve()
            metrics['local_links']+=1
            safe=target.is_relative_to(root.resolve())
            check('local link: '+str(p.relative_to(root))+' -> '+value,safe and target.exists())
            if not safe or not target.is_file():continue
            if parts.fragment and target.suffix.lower()=='.md':
                metrics['fragment_links']+=1
                check('fragment link: '+str(p.relative_to(root))+' -> '+value,unquote(parts.fragment) in anchors(target))
    records=json.loads((root/'sources/documentation/adr_records.json').read_text())
    reqs=list(csv.DictReader((root/'reference/Portable_Hosting_Delivery_Kits_v1_1/04_Shared/requirements.csv').open(encoding='utf-8-sig',newline='')))
    reqids={r['requirementId'] for r in reqs}
    allsourceids={x for a in records for x in a['source_decision_ids']}
    required={f'AD-{i:02d}' for i in range(1,16)}|{f'RD14-{i:02d}' for i in range(1,6)}|{'DEV-ADR-01'}
    check('all explicit architecture decision IDs mapped',required<=allsourceids)
    lifecycle=lifecycle_errors(records)
    check('ADR lifecycle records consistent',not lifecycle,lifecycle or None)
    builder=Builder(root)
    for a in records:
        p=root/builder.adrpath(a)
        check('ADR rendered content and status match record: '+a['id'],p.is_file() and p.read_text()==adr_text(builder,a))
    cross=list(csv.DictReader((root/'sources/documentation/adr_crosswalk.csv').open(newline='')))
    byadr={a['id']:a for a in records}
    check('ADR crosswalk status agrees',all(r['adr'] in byadr and r['status']==byadr[r['adr']]['status'] for r in cross))
    index=(root/'docs/adr/README.md').read_text()
    for a in records:
        line=next((line for line in index.splitlines() if a['id']+' — '+a['title'] in line),'')
        check('ADR index status agrees: '+a['id'],f'| {a["status"]} |' in line)
    check('unique source-derived ADR IDs',len({a['id'] for a in records})==len(records))
    for a in records:
        check('ADR requirements resolve: '+a['id'],set(a['requirements'])<=reqids)
        check('ADR implementation targets exist: '+a['id'],all((root/p).exists() for p in a['implementation_paths']))
    requirementtext=normalized(soup(root/'docs/assurance/requirements.md').get_text())
    for row in reqs:check('requirement wording retained: '+row['requirementId'],normalized(row['text']) in requirementtext)
    tests=list(csv.DictReader((root/'reference/Portable_Hosting_Delivery_Kits_v1_1/04_Shared/tests.csv').open(encoding='utf-8-sig',newline='')))
    testtext=normalized(soup(root/'docs/assurance/test-specifications.md').get_text())
    for row in tests:
        check('test status retained: '+row['id'],row['executionStatus']=='not-run')
        for field in ('preconditions','procedure','expected','evidence','cadence'):
            check('test wording: '+row['id']+' '+field,normalized(row[field]) in testtext)
    metrics['source_derived_adrs']=len(records)
    metrics['markdown_pages_checked']=len(paths)
    metrics['checks']=len(checks)
    metrics['passed']=sum(c['passed'] for c in checks)
    metrics['failed']=len(errors)
    out={'kind':'SOURCE_TO_GIT_DOCUMENTATION_CHECK','status':'PASSED' if not errors else 'FAILED',
      'metrics':dict(metrics),'failures':errors,'external_sources':'RETAINED_NOT_REVALIDATED',
      'terraform_ansible_engine':'NOT_RUN_BY_THIS_CHECK','native_infrastructure':'NOT_CONTACTED',
      'architecture_approval':'NOT_ISSUED','checks':checks}
    report=root/'build/reports/documentation_validation.json';report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);args=p.parse_args()
    report=run(args.root.resolve());print(json.dumps({k:v for k,v in report.items() if k!='checks'},indent=2))
    return bool(report['failures'])
if __name__=='__main__':raise SystemExit(main())
