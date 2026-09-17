"""Read-only publishing and example checks for the v1.1 document development.

No infrastructure, provider API, privileged credentials or real gate decisions are accessed.
An optional JSON report is the only output mutation. Exit 1 denotes failed local checks.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
from decimal import Decimal
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit
import zipfile
import xml.etree.ElementTree as ET

W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P='http://schemas.openxmlformats.org/package/2006/relationships'
NS={'w':W,'r':R}

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def rows(path: Path) -> list[dict]:
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

class HTMLLinks(HTMLParser):
    def __init__(self): super().__init__();self.links=[];self.ids=set()
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'href' in a:self.links.append(a['href'])
        if 'id' in a:self.ids.add(a['id'])

class Check:
    def __init__(self):self.items=[];self.metrics={}
    def add(self,name,ok,detail):
        self.items.append({'name':name,'passed':bool(ok),'detail':detail})

def validate(root: Path) -> dict:
    root=root.resolve();c=Check()
    specs=json.loads((root/'08_Development_Source/documents.json').read_text())
    sources=json.loads((root/'08_Development_Source/sources.json').read_text())
    baseline=json.loads((root/'04_Shared/development/baseline_fingerprints.json').read_text())
    def frozen(prefix=None,suffix=None,exclude=()):
        selected=[p for p in baseline if (prefix is None or p.startswith(prefix)) and (suffix is None or p.endswith(suffix)) and p not in exclude]
        changed=[p for p in selected if not (root/p).is_file() or digest(root/p)!=baseline[p]]
        return selected,changed
    sel,bad=frozen('05_Reference_v1_4/')
    c.add('Frozen architecture and reference registers byte-preserved',len(sel)>8 and not bad, {'files':len(sel),'changed':bad})
    sel,bad=frozen(suffix='.xlsx')
    c.add('Three working workbooks byte-preserved',len(sel)==3 and not bad, {'files':len(sel),'changed':bad,'note':'No formula recalculation or new spreadsheet assurance.'})
    sel,bad=frozen(suffix='.docx',exclude=('00_Delivery_Map.docx',))
    c.add('All prior non-map Word documents byte-preserved',len(sel)==16 and not bad, {'files':len(sel),'changed':bad})
    sel,bad=frozen('03_Implementation/runbooks/')
    c.add('Ten inherited Markdown runbooks byte-preserved',len(sel)==10 and not bad,{'files':len(sel),'changed':bad})
    sel,bad=frozen('04_Shared/')
    c.add('Existing shared catalogues and records byte-preserved',len(sel)>10 and not bad, {'files':len(sel),'changed':bad})
    retained=rows(root/'04_Shared/requirements.csv');tests=rows(root/'04_Shared/tests.csv');adds=rows(root/'04_Shared/addenda.csv');assertions=rows(root/'04_Shared/assertions.csv');deliverables=rows(root/'04_Shared/deliverables.csv')
    c.add('Baseline requirement and deliverable identities retained', len(retained)==194 and len({r['requirementId'] for r in retained})==194 and len(deliverables)==27, {'requirements':len(retained),'role_outputs':len(deliverables)})
    c.add('Reference verification remains unexecuted',len(tests)==80 and len(adds)==12 and len(assertions)==12 and all(r['executionStatus']=='not-run' for r in tests+adds) and all('NOT RUN' in r['mapped_procedures_and_status'] for r in assertions), {'CT':len(tests),'realization_addenda':len(adds),'W14_assertions':len(assertions)})
    history=root/'07_Quality/prior_v1_0'
    historical_pairs={'00_Delivery_Map.docx':'00_Delivery_Map.docx','README.md':'ROOT_README.md','START_HERE.html':'ROOT_START_HERE.html','RELEASE_MANIFEST.json':'RELEASE_MANIFEST.json','SHA256SUMS':'SHA256SUMS'}
    hb=[p for p,q in historical_pairs.items() if not (history/q).is_file() or digest(history/q)!=baseline[p]]
    c.add('Superseded root artifacts retained as historical snapshots',not hb,{'changed':hb})

    active=[p for p in root.rglob('*.docx') if '07_Quality' not in p.parts]
    trees={};bookmarks={};zip_errors=[]
    for path in active:
        try:
            with zipfile.ZipFile(path) as z:
                if z.testzip():zip_errors.append(str(path.relative_to(root)))
                tree=ET.fromstring(z.read('word/document.xml'))
                trees[path]=tree
                bookmarks[path]=set(x.get('{'+W+'}name') for x in tree.findall('.//w:bookmarkStart',NS))
        except (OSError,zipfile.BadZipFile,ET.ParseError) as e:zip_errors.append(str(path)+': '+str(e))
    c.add('Active DOCX packages readable and CRC-clean',len(active)==22 and not zip_errors,{'documents':len(active),'errors':zip_errors})
    c.metrics['active_word_documents']=len(active)

    def resolve_link(origin: Path,target: str,anchor: str|None=None):
        u=urlsplit(target)
        if u.scheme in ('http','https','mailto'):return None
        if u.scheme:return f'Unsupported local-link scheme: {target}'
        path=(origin.parent/unquote(u.path)).resolve() if u.path else origin
        frag=unquote(anchor or u.fragment)
        try:path.relative_to(root)
        except ValueError:return f'Escapes release: {target}'
        if not path.exists():return f'Missing file: {target}'
        if frag and path.suffix.lower()=='.docx':
            if frag not in bookmarks.get(path,set()):return f'Missing Word bookmark {frag} in {path.relative_to(root)}'
        elif frag and path.suffix.lower() in ('.html','.htm'):
            parser=HTMLLinks();parser.feed(path.read_text())
            if frag not in parser.ids:return f'Missing HTML anchor {frag} in {path.relative_to(root)}'
        return None

    link_bad=[];local_links=0;web_links=0;internal_links=0
    for path in active:
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if not name.startswith('word/') or not name.endswith('.xml') or '/_rels/' in name:continue
                try:t=ET.fromstring(z.read(name))
                except ET.ParseError:continue
                base=Path(name);relname=(base.parent/'_rels'/(base.name+'.rels')).as_posix();rels={}
                if relname in z.namelist():
                    rt=ET.fromstring(z.read(relname));rels={x.get('Id'):x.get('Target') for x in rt}
                for h in t.findall('.//w:hyperlink',NS):
                    rid=h.get('{'+R+'}id');anchor=h.get('{'+W+'}anchor')
                    if rid:
                        target=rels.get(rid)
                        if target is None:link_bad.append(f'{path.name}: missing relationship {rid}');continue
                        if urlsplit(target).scheme in ('http','https','mailto'):web_links+=1;continue
                        local_links+=1;err=resolve_link(path,target,anchor)
                    elif anchor:
                        internal_links+=1;err=None if anchor in bookmarks[path] else f'Missing internal bookmark {anchor}'
                    else:err='Hyperlink has no relationship or anchor'
                    if err:link_bad.append(f'{path.relative_to(root)}: {err}')
    c.add('All active Word local destinations and bookmarks resolve',not link_bad,{'cross_file_links':local_links,'internal_links':internal_links,'web_links_not_revalidated_by_this_checker':web_links,'errors':link_bad})
    c.metrics.update(word_local_links=local_links,word_internal_links=internal_links,word_external_web_links=web_links)
    new_tags=[];content_errors=[];heading_errors=[];table_errors=[];nav_errors=[];fresh_text={}
    for code,s in specs.items():
        path=(root/s['path']).resolve();tree=trees.get(path)
        if tree is None:content_errors.append(f'Missing {code}');continue
        text=' '.join(x.text or '' for x in tree.findall('.//w:t',NS));fresh_text[code]=text
        names=[x.get('{'+W+'}name') for x in tree.findall('.//w:bookmarkStart',NS)]
        wanted={f'{code}_{n:02d}' for n in range(1,len(s['sections'])+1)}
        if set(names)!=wanted or len(names)!=len(wanted):heading_errors.append(code+' bookmark/section mismatch')
        navs=[h.get('{'+W+'}anchor') for h in tree.findall('.//w:hyperlink',NS) if h.get('{'+W+'}anchor')]
        if not wanted.issubset(navs):nav_errors.append(code)
        expected=[s['title'],s['subtitle'],s['intro']]
        for n,sec in enumerate(s['sections'],1):
            expected += [f'{n}. {sec["title"]}']
            if sec.get('lead'):expected.append(sec['lead'])
            for b in sec['blocks']:
                if b['kind'] in ('p','h','note'):expected.append(b['text'])
                if b['kind']=='table':
                    expected += b['headers']
                    expected += [str(v) for row in b['rows'] for v in row if not isinstance(v,dict)]
        normalized=' '.join(text.split())
        for e in expected:
            if ' '.join(e.split()) not in normalized:content_errors.append(code+': '+e[:100])
        for table in tree.findall('.//w:tbl',NS):
            trs=table.findall('w:tr',NS)
            if not trs or trs[0].find('w:trPr/w:tblHeader',NS) is None:table_errors.append(code+': missing table header')
            for tr in trs[1:]:
                if tr.find('w:trPr/w:cantSplit',NS) is None:table_errors.append(code+': splittable row')
        new_tags += [x.get('{'+W+'}val') for x in tree.findall('.//w:sdtPr/w:tag',NS)]
    c.add('Six developed documents retain every authored content block',len(fresh_text)==6 and not content_errors, {'errors':content_errors})
    c.add('Developed section identities and navigation match',not heading_errors and not nav_errors,{'sections':sum(len(s['sections']) for s in specs.values()),'errors':heading_errors+nav_errors})
    c.add('New tables have repeated headers and protected rows',not table_errors,{'errors':table_errors})
    c.add('Thirty additional editable responses have unique tags',len(new_tags)==30 and len(set(new_tags))==30,{'fields':len(new_tags),'duplicate_tags':[k for k,v in Counter(new_tags).items() if v>1]})
    c.metrics['new_editable_response_fields']=len(new_tags)
    c.add('Retained Delivery Map section anchors preserved',all(f'DEL_{i:02d}' in bookmarks[(root/'00_Delivery_Map.docx').resolve()] for i in range(1,7)), 'Existing links to DEL_01–DEL_06 remain resolvable.')
    c.add('Developed documents distinguish proposals and actual evidence',all('Proposed engineering development' in t and 'site' in t.lower() for t in fresh_text.values()), 'Presence check for scope disclosures; not an automated semantic assessment.')
    c.add('No tool citation tokens in generated document text',not any(re.search(r'|turn\d+(?:file|view|search)\d+|sandbox:/mnt/data',t) for t in fresh_text.values()), 'Human document/source references are used.')

    dev=rows(root/'04_Shared/development/development_register.csv');cards=rows(root/'04_Shared/development/qualification_observation_cards.csv');index=rows(root/'04_Shared/development/document_section_index.csv');handoffs=rows(root/'04_Shared/development/service_handoff_development.csv')
    c.add('Development register contains distinct traceable treatments',len(dev)==24 and len({x['id'] for x in dev})==24 and all(x['actual_owner']==x['actual_evidence']=='' for x in dev), {'records':len(dev),'note':'Implementation remains open.'})
    bad=[];outputs={x['id'] for x in deliverables}
    for rec in dev:
        if rec['document_code'] not in specs:bad.append(rec['id']+' unknown document')
        err=resolve_link(root/'START_HERE.html',rec['document_path']+'#'+rec['bookmark'])
        if err:bad.append(rec['id']+': '+err)
        if not set(re.findall(r'(?:AK|EK|IK)-\d{2}',rec['role_outputs'])).issubset(outputs):bad.append(rec['id']+' unknown role output')
    c.add('Development records resolve to sections and stable role outputs',not bad,{'errors':bad})
    c.add('Section index matches the developed documents',len(index)==46 and all(not resolve_link(root/'START_HERE.html',x['document_path']+'#'+x['bookmark']) for x in index),{'sections':len(index)})
    tids={x['id'] for x in tests}
    cbad=[]
    for card in cards:
        if not set(re.findall(r'CT-\d{3}',card['existing_test_ids'])).issubset(tids):cbad.append(card['id'])
        if resolve_link(root/'START_HERE.html',card['document_path']+'#'+card['bookmark']):cbad.append(card['id']+' destination')
    c.add('Twelve observation cards map only to known CT procedures',len(cards)==12 and len({x['id'] for x in cards})==12 and not cbad,{'cards':len(cards),'errors':cbad})
    c.add('New observation cards do not contain fabricated results',all(x['execution_status']=='not-run' and not any(x[k] for k in ['actual_target','observed_result','evidence_reference','reviewer']) for x in cards),'Expected outcomes are separate from blank actual observations.')
    c.add('Shared-service handoff records are unapproved reference records',len(handoffs)==5 and all(not any(x[k] for k in ['actual_producer','actual_consumer','actual_evidence']) for x in handoffs),{'handoffs':len(handoffs)})
    srcrows=rows(root/'04_Shared/development/source_reviews.csv');ids={x['id'] for x in sources}
    referenced={sid for s in specs.values() for sec in s['sections'] for b in sec['blocks'] if b['kind']=='external' for sid in b['ids']}
    c.add('Source register and document mechanism references agree',srcrows==sources and len(ids)==8 and referenced==ids,{'source_ids':sorted(ids),'note':'Publishing check; live URLs are not fetched by this script.'})
    c.add('External source scope and review limitations are recorded',all(x.get('locator') and x.get('limitation') and x.get('reviewed') and urlsplit(x['url']).scheme=='https' for x in sources),'No source is represented as installed compatibility or formal authorization.')

    ex=json.loads((root/'04_Shared/development/engineering_examples.json').read_text())
    f=ex['fixture'];calc=lambda probes:{'vcpus':(f['permanent_endpoints']+probes)*f['vcpus_each'],'memory_gib':(f['permanent_endpoints']+probes)*f['memory_gib_each'],'virtual_disk_gib':(f['permanent_endpoints']+probes)*f['virtual_disk_gib_each']}
    c.add('Fixture arithmetic matches sequential and simultaneous examples',calc(f['sequential_probes'])==f['sequential_peak'] and calc(f['simultaneous_probes'])==f['simultaneous_peak'],{'sequential':calc(f['sequential_probes']),'simultaneous':calc(f['simultaneous_probes'])})
    m=ex['mtu'];common=sum(m[k] for k in ['inner_ip_bytes','inner_ethernet_bytes','vxlan_bytes','udp_bytes'])
    c.add('Basic VXLAN example arithmetic matches stated assumptions',common+m['outer_ipv4_bytes']==m['outer_ipv4_packet_bytes'] and common+m['outer_ipv6_bytes']==m['outer_ipv6_packet_bytes'],{'outer_ipv4_IP_packet_bytes':common+m['outer_ipv4_bytes'],'outer_ipv6_IP_packet_bytes':common+m['outer_ipv6_bytes'],'note':m['exclusions']})
    e=ex['edge_capacity'];avail=Decimal(e['surviving_capacity'])-Decimal(e['reserve'])-Decimal(e['existing_commitment']);margin=avail-Decimal(e['additional_request'])
    c.add('Survivor capacity example rejects the excess demand',avail==Decimal(e['available']) and margin==Decimal(e['margin_after_request']) and margin<0,{'available_Gbit_s':str(avail),'margin_Gbit_s':str(margin)})
    r=ex['recovery'];core=sum(r[k] for k in ['detect','decide','bootstrap','restore','validate','cutover']);par=core+max(r['network'],r['storage']);serial=core+r['network']+r['storage']
    c.add('Recovery dependency arithmetic distinguishes parallel and serial work',par==r['parallel_elapsed'] and serial==r['serial_elapsed'] and r['target']-par==r['parallel_margin'] and r['target']-serial==r['serial_margin'],{'parallel_minutes':par,'serial_minutes':serial,'note':'Local planning example, not measured performance.'})
    def mins(v):h,m=map(int,v.split(':'));return 60*h+m
    c.add('RPO example uses consistency point rather than job finish',mins(ex['rpo']['service_loss'])-mins(ex['rpo']['recoverable_consistency_point'])==ex['rpo']['data_age_minutes']==15,'Timestamps are illustrative, not actual telemetry.')
    routes=rows(root/'04_Shared/routes4.csv')
    required={('D01O','192.0.2.32/27','198.51.100.1'),('EC-01','192.0.2.32/27','198.51.100.6'),('D01R','192.0.2.0/27','198.51.100.5'),('EC-01','192.0.2.0/27','198.51.100.2')}
    actual={(x['owner'],x['destination'],x['next_hop']) for x in routes}
    c.add('Worked forward/reply route example matches frozen route schedule',required.issubset(actual), {'missing':list(required-actual),'note':'Reference parity, not route installation or data-plane testing.'})
    c.add('Initial readiness dependency remains explicit in entry map','G4 initial' in fresh_text['DEL'] and 'G3' in fresh_text['DEL'] and 'Initial G4' in fresh_text['OPS'], 'Disclosure-presence check only; actual gate decisions are not evaluated.')

    nav_bad=[];nav_count=0
    for path in root.rglob('*'):
        if not path.is_file() or path.suffix.lower() not in ('.md','.html'):continue
        if '07_Quality' in path.parts and 'prior_v1_0' in path.parts:continue
        if 'source' in path.parts:continue # historic build documentation, not release navigation
        text=path.read_text(encoding='utf-8-sig')
        if path.suffix=='.html':p=HTMLLinks();p.feed(text);links=p.links
        else:
            text=re.sub(r'```[\s\S]*?```','',text)
            links=[x.strip('<>') for x in re.findall(r'(?<!!)\[[^\]]+\]\(([^\s]+)(?:\s+"[^"]*")?\)',text)]
        for target in links:
            if urlsplit(target).scheme in ('http','https','mailto'):continue
            nav_count+=1;err=resolve_link(path,target)
            if err:nav_bad.append(str(path.relative_to(root))+': '+err)
    c.add('Active HTML and Markdown local navigation resolves',not nav_bad, {'links':nav_count,'errors':nav_bad})
    c.metrics['html_markdown_local_links']=nav_count

    vr_path=root/'07_Quality/v1_1/visual_review.json';vr=json.loads(vr_path.read_text()) if vr_path.is_file() else {}
    visualbad=[];pages=0
    for code,s in specs.items():
        entry=vr.get('documents',{}).get(code,{})
        if entry.get('document_sha256')!=digest(root/s['path']) or entry.get('pages_reviewed')!=entry.get('rendered_pages') or not entry.get('all_pages_visually_reviewed'):visualbad.append(code)
        pages+=entry.get('rendered_pages',0)
    c.add('Every current developed page has a matching visual review record',not visualbad and pages==52, {'rendered_and_reviewed_pages':pages,'unreviewed_or_changed':visualbad,'note':'Recorded human/assistant page-image review, not computed design assurance.'})
    c.metrics['new_modified_pages_reviewed']=pages
    ab=[]
    for code in specs:
        p=root/'07_Quality/v1_1'/f'a11y_{code}.json'
        if not p.exists():ab.append(code+' missing');continue
        report=json.loads(p.read_text())
        # The audit tool uses a summary of counts and a findings list.
        if report.get('issues') or report.get('findings'):ab.append(code+' findings present')
    c.add('Fresh automated accessibility scans report no findings',not ab,{'documents':len(specs),'issues':ab,'note':'Automated scan only, not accessibility certification.'})
    c.add('Required current release instructions and source exist',all((root/p).is_file() for p in ['START_HERE.html','README.md','08_Development_Source/README.md','08_Development_Source/author_content.py','08_Development_Source/build_documents.py','08_Development_Source/build_registers.py','07_Quality/v1_1/README.md']),'Current v1.1 build/check instructions are separate from historic v1.0 tooling.')
    return {'release':'Delivery kits v1.1','scope':'Offline document publishing, lineage and illustrative arithmetic; no infrastructure execution or authorization',
            'passed':sum(i['passed'] for i in c.items),'failed':sum(not i['passed'] for i in c.items),'metrics':c.metrics,'checks':c.items}

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);ap.add_argument('--output',type=Path)
    args=ap.parse_args()
    try:report=validate(args.root)
    except (OSError,KeyError,ValueError,ET.ParseError,zipfile.BadZipFile) as e:
        print(f'Cannot validate release: {e}',file=sys.stderr);return 2
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'passed':report['passed'],'failed':report['failed'],'metrics':report['metrics']},indent=2))
    for item in report['checks']:
        if not item['passed']:print('FAIL:',item['name'],json.dumps(item['detail'],ensure_ascii=False))
    return 1 if report['failed'] else 0

if __name__=='__main__':raise SystemExit(main())
