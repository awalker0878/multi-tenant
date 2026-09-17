#!/usr/bin/env python3
"""Read-only checks for this delivery-kit release. Not an infrastructure audit."""
from __future__ import annotations
import argparse,csv,hashlib,json,re,sys,zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit,unquote
from xml.etree import ElementTree as E
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
R='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
PK='{http://schemas.openxmlformats.org/package/2006/relationships}'
M='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'

def load_csv(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def doc_info(path):
    with zipfile.ZipFile(path) as z:
        tree=E.fromstring(z.read('word/document.xml'))
        rels={x.get('Id'):x.get('Target') for x in E.fromstring(z.read('word/_rels/document.xml.rels'))}
    b=[x.get(W+'name') for x in tree.iter(W+'bookmarkStart')]
    tags=[x.get(W+'val') for x in tree.iter(W+'tag')]
    links=[]
    for h in tree.iter(W+'hyperlink'):
        rid=h.get(R+'id');target=rels.get(rid) if rid else None
        links.append((target,h.get(W+'anchor') or h.get(W+'docLocation')))
    tables=list(tree.iter(W+'tbl'))
    missing_headers=0
    for t in tables:
        row=t.find(W+'tr')
        if row is not None and row.find('.//'+W+'tblHeader') is None:missing_headers+=1
    return {'bookmarks':b,'tags':tags,'links':links,'tables':len(tables),'missing_headers':missing_headers}

class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.hrefs=[]; self.ids=set()
    def handle_starttag(self,tag,attrs):
        values=dict(attrs)
        if values.get('id'):self.ids.add(values['id'])
        if tag=='a' and values.get('href'):self.hrefs.append(values['href'])

def text_links(path):
    text=path.read_text(encoding='utf-8')
    if path.suffix.lower()=='.html':
        parser=Links();parser.feed(text);return parser.hrefs,parser.ids
    # The package uses simple inline Markdown links without nested parentheses.
    text=re.sub(r'```.*?```','',text,flags=re.S)
    refs=re.findall(r'(?<!!)\[[^\]\n]+\]\(([^)\n]+)\)',text)
    refs=[x.strip().split(' "',1)[0].strip('<>') for x in refs]
    ids=set()
    for heading in re.findall(r'^#{1,6}\s+(.+)$',text,re.M):
        slug=re.sub(r'[^\w\- ]','',heading.lower()).strip().replace(' ','-')
        ids.add(slug)
    return refs,ids

def check(root:Path,verify_manifest=True):
    root=root.resolve();checks=[];warnings=[];infos={};internal=0;cross=0;web=0
    def add(name,passed,detail=''):checks.append({'check':name,'passed':bool(passed),'detail':detail})
    required=['00_Delivery_Map.docx','START_HERE.html','README.md','01_Architecture/Architecture_Kit.docx','01_Architecture/HLD_and_Architecture_Review_Template.docx','01_Architecture/Architecture_Registers.xlsx','02_Engineering/Engineering_Kit.docx','02_Engineering/LLD_and_Engineering_Review_Template.docx','02_Engineering/Vendor_Realization_Cards.docx','02_Engineering/Engineering_Schedules.xlsx','03_Implementation/Implementation_Kit.docx','03_Implementation/MOP_Test_and_Handover_Template.docx','03_Implementation/Implementation_Tracker.xlsx','04_Shared/Worked_Delivery_Example.docx']
    for rel in required:add('required '+rel,(root/rel).is_file())
    for p in root.rglob('*.docx'):
        try:infos[p.resolve()]=doc_info(p)
        except Exception as exc:add('DOCX readable '+str(p.relative_to(root)),False,type(exc).__name__)
    all_tags=[];new_docs=0
    for p,info in infos.items():
        frozen='05_Reference_v1_4' in p.parts
        if not frozen:
            new_docs+=1
            add('unique bookmarks '+p.name,len(info['bookmarks'])==len(set(info['bookmarks'])))
            add('table headers '+p.name,info['missing_headers']==0)
            add('unique response tags '+p.name,len(info['tags'])==len(set(info['tags'])))
            all_tags.extend(info['tags'])
        for target,anchor in info['links']:
            if not target:
                internal+=1
                if anchor and anchor not in info['bookmarks']:
                    (warnings if frozen else checks).append({'check':'internal link '+p.name,'passed':False,'detail':str(anchor)})
                continue
            u=urlsplit(target)
            if u.scheme in ('http','https','mailto'):
                web+=1;continue
            cross+=1
            dest=(p.parent/unquote(u.path)).resolve();frag=unquote(u.fragment) or anchor
            valid=dest.is_file() and (not frag or (dest in infos and frag in infos[dest]['bookmarks']))
            if not valid:
                entry={'check':'cross-file link '+p.name,'passed':False,'detail':target+(' #'+frag if frag else '')}
                (warnings if frozen else checks).append(entry)
    nav_count=0; nav_bad=[]; nav_info={}
    for f in list(root.rglob('*.html'))+list(root.rglob('*.md')):
        try:nav_info[f.resolve()]=text_links(f)
        except (OSError,UnicodeError) as exc:nav_bad.append(f.name+': '+type(exc).__name__)
    for f,(targets,ids) in nav_info.items():
        for target in targets:
            u=urlsplit(target)
            if u.scheme or target.startswith('//'):continue
            nav_count+=1
            dest=(f.parent/unquote(u.path)).resolve() if u.path else f
            fragment=unquote(u.fragment)
            valid=(dest==root or root in dest.parents) and dest.exists()
            if valid and fragment:
                if dest in infos:valid=fragment in infos[dest]['bookmarks']
                elif dest in nav_info:valid=fragment in nav_info[dest][1]
                else:valid=False
            if not valid:nav_bad.append(str(f.relative_to(root))+': '+target)
    add('HTML and Markdown local links resolve',not nav_bad,'; '.join(nav_bad) or str(nav_count)+' links')
    add('no shipped font files',not any(p.suffix.lower() in ('.ttf','.otf','.woff','.woff2') for p in root.rglob('*')))
    add('new DOCX count',new_docs==9,str(new_docs))
    add('all new response tags unique',len(all_tags)==len(set(all_tags)),str(len(all_tags)))
    for name in ['HLD_and_Architecture_Review_Template.docx','LLD_and_Engineering_Review_Template.docx','MOP_Test_and_Handover_Template.docx']:
        matches=[i for p,i in infos.items() if p.name==name];add('editable response controls '+name,bool(matches) and len(matches[0]['tags'])>=40)
    add('new local hyperlink targets resolve',not any(not c['passed'] and ('link ' in c['check']) for c in checks))
    req=load_csv(root/'04_Shared/requirements.csv');original=load_csv(root/'05_Reference_v1_4/registers/requirement_document_crosswalk.csv')
    add('194 requirement IDs retained',len(req)==194 and len({x['requirementId'] for x in req})==194)
    add('exact inherited requirement text', {x['requirementId']:x['text'] for x in req}=={x['requirementId']:x['text'] for x in original})
    deliver=load_csv(root/'04_Shared/deliverables.csv');add('27 delivery outputs',len(deliver)==27 and len({x['id'] for x in deliver})==27)
    steps=load_csv(root/'04_Shared/build_step_catalogue.csv');add('61 unique runbook steps',len(steps)==61 and len({x['step_id'] for x in steps})==61)
    add('10 runbooks',len(list((root/'03_Implementation/runbooks').glob('RB-*.md')))==10)
    for name,count in [('conformance_tests_reference.json',80),('realization_verification_addenda.json',12)]:
        rows=json.loads((root/'05_Reference_v1_4/registers'/name).read_text());add(name+' not-run',len(rows)==count and all(x.get('executionStatus')=='not-run' for x in rows))
    a=load_csv(root/'05_Reference_v1_4/registers/v1_4_verification_assertions.csv');add('12 W14 assertions not run',len(a)==12 and all('NOT RUN' in x['mapped_procedures_and_status'] for x in a))
    fingerprints=json.loads((root/'04_Shared/baseline_fingerprints.json').read_text())['files']
    for rel,row in fingerprints.items():
        p=root/'05_Reference_v1_4'/rel
        add('frozen baseline '+rel,p.is_file() and sha(p)==row['sha256'])
    workbook_stats=[]
    for p in root.rglob('*.xlsx'):
        try:
            with zipfile.ZipFile(p) as z:
                tree=E.fromstring(z.read('xl/workbook.xml'));sheets=tree.findall('.//'+M+'sheet');errors=[];formula_count=0
                for n in z.namelist():
                    if n.startswith('xl/worksheets/sheet') and n.endswith('.xml'):
                        x=E.fromstring(z.read(n));formula_count+=len(list(x.iter(M+'f')))
                        errors += [(n,c.get('r')) for c in x.iter(M+'c') if c.get('t')=='e']
            add('xlsx cached error cells '+p.name,not errors,str(errors));workbook_stats.append({'file':str(p.relative_to(root)),'sheets':len(sheets),'formulas':formula_count})
        except Exception as exc:add('xlsx readable '+p.name,False,type(exc).__name__)
    add('three workbooks',len(workbook_stats)==3)
    if verify_manifest:
        p=root/'RELEASE_MANIFEST.json'
        if p.is_file():
            manifest=json.loads(p.read_text());bad=[]
            for x in manifest['files']:
                f=(root/x['path']).resolve()
                if root not in f.parents or not f.is_file() or sha(f)!=x['sha256']:bad.append(x['path'])
            add('release manifest file hashes',not bad,'; '.join(bad))
            names=[x['path'] for x in manifest['files']]
            add('manifest paths unique',len(names)==len(set(names)))
            exclusions=set(manifest.get('excluded_paths',[]))
            actual={f.relative_to(root).as_posix() for f in root.rglob('*') if f.is_file() and '__pycache__' not in f.parts and f.suffix!='.pyc'}
            add('manifest payload coverage',actual-exclusions==set(names),'; '.join(sorted((actual-exclusions)^set(names))))
        else:add('release manifest present',False)
    return {'scope':'Local package/document/record checks only. No deployed infrastructure, native provider or authorization evaluated.','passed':sum(c['passed'] for c in checks),'failed':sum(not c['passed'] for c in checks),'checks':checks,'inherited_link_warnings':warnings,'link_counts':{'internal':internal,'cross_file':cross,'web_not_network_checked':web},'text_navigation_links':nav_count,'new_response_controls':len(all_tags),'workbooks':workbook_stats}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--skip-manifest',action='store_true');args=p.parse_args(argv)
    try:r=check(args.root,not args.skip_manifest)
    except (OSError,ValueError,KeyError,zipfile.BadZipFile,E.ParseError) as exc:
        print(json.dumps({'error':type(exc).__name__,'detail':str(exc),'scope':'Local check could not complete'}));return 2
    print(json.dumps(r,indent=2,ensure_ascii=False));return 1 if r['failed'] else 0
if __name__=='__main__':raise SystemExit(main())
