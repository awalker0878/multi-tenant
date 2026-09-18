"""Independent source-structure checks; deliberately does not import converter text helpers."""
from __future__ import annotations
import json,re
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET
import mistune
from bs4 import BeautifulSoup
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
MD=mistune.create_markdown(escape=False,plugins=['table','strikethrough','task_lists'])


def visible(node):
    parts=[]
    for n in node.iter():
        if n.tag==W+'t':parts.append(n.text or '')
        elif n.tag in (W+'br',W+'cr') and n.get(W+'type') not in ('page','column'):parts.append('\n')
        elif n.tag==W+'tab':parts.append('\t')
    return ''.join(parts)


def norm(text):return re.sub(r'\s+','',text.replace('\u00ad','').replace('\ufeff',''))


def check(root:Path):
    sources=json.loads((root/'sources/documentation/conversion_manifest.json').read_text())['documents']
    ledger={(x['source_id'],x['block']):x for x in json.loads((root/'sources/documentation/block_coverage.json').read_text())}
    cache={};errors=[];tables=cells=codes=0
    def soup(path):
        if path not in cache:cache[path]=BeautifulSoup(MD(path.read_text()),'html.parser')
        return cache[path]
    for source in sources:
        with ZipFile(root/source['source']) as archive:tree=ET.fromstring(archive.read('word/document.xml'))
        blocks=[]
        def collect(parent):
            for child in parent:
                if child.tag in (W+'p',W+'tbl'):blocks.append(child)
                elif child.tag==W+'sdt':
                    content=child.find(W+'sdtContent')
                    if content is not None:collect(content)
        collect(tree.find(W+'body'))
        code_groups={}
        for i,b in enumerate(blocks):
            entry=ledger[(source['id'],i)]
            if entry['status']=='publication-navigation-replaced':continue
            dest=root/entry['destination'];page=soup(dest)
            if b.tag==W+'p':
                style=b.find(W+'pPr/'+W+'pStyle')
                if style is not None and 'code' in style.get(W+'val','').lower():
                    codes+=1;code_groups.setdefault(dest,[]).append((i,visible(b)))
            else:
                tables+=1;marker=page.find(id=f'source-table-{i}');out=marker.find_next('table') if marker else None
                before=b.findall(W+'tr');after=out.find_all('tr') if out else []
                if len(before)!=len(after):errors.append(f'{source["id"]}/{i}: table rows differ');continue
                for ri,(sr,dr) in enumerate(zip(before,after)):
                    sc=sr.findall(W+'tc');dc=dr.find_all(['th','td'],recursive=False)
                    if len(sc)!=len(dc):errors.append(f'{source["id"]}/{i}/{ri}: cell count differs');continue
                    for ci,(a,z) in enumerate(zip(sc,dc)):
                        cells+=1;want=norm(visible(a));actual=norm(z.get_text())
                        if want!=actual:errors.append(f'{source["id"]}/{i}/{ri}/{ci}: ordered cell text differs')
        for path,expected in code_groups.items():
            actual=[c.get_text()[:-1] if c.get_text().endswith('\n') else c.get_text() for c in soup(path).select('pre > code')]
            # Contiguous source code paragraphs are intentionally joined by one newline.
            groups=[]
            for index,text in expected:
                if groups and index==groups[-1][0]+1:groups[-1]=(index,groups[-1][1]+'\n'+text)
                else:groups.append((index,text))
            if [text for _,text in groups]!=actual:errors.append(f'{source["id"]}: code structure differs in {path.relative_to(root)}')
    return {'tables':tables,'cells':cells,'code_paragraphs':codes,'errors':errors}
