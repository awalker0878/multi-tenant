#!/usr/bin/env python3
"""Transcribe frozen DOCX sources into chapter-sized Git Markdown.

No Office executable, network request, or infrastructure operation is used. Source
bytes are not modified. Tables, image bytes, bookmarks, cached field labels and
content-control placeholders are preserved. This is a publishing conversion, not
an assessment or an automatic approval of the source design.
"""
from __future__ import annotations
import argparse
import hashlib
import html
import json
import os
from pathlib import Path, PurePosixPath
import re
import unicodedata
from urllib.parse import quote, unquote, urlsplit
from zipfile import ZipFile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
NS = {"w":"http://schemas.openxmlformats.org/wordprocessingml/2006/main",
      "r":"http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "a":"http://schemas.openxmlformats.org/drawingml/2006/main",
      "wp":"http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
      "v":"urn:schemas-microsoft-com:vml"}
def q(n):
    p, name = n.split(':'); return '{'+NS[p]+'}'+name

def digest(data): return hashlib.sha256(data).hexdigest()
def slug(text):
    text=unicodedata.normalize('NFKD',text).encode('ascii','ignore').decode().lower()
    return re.sub(r'-+','-',re.sub(r'[^a-z0-9]+','-',text)).strip('-') or 'section'
def rel_link(source: Path, target: Path, anchor=''):
    out=quote(os.path.relpath(target, source.parent).replace(os.sep,'/'),safe='/-._~')
    return out + ('#'+quote(anchor,safe='_-:.') if anchor else '')
def clean_text(s): return (s or '').replace('\u00ad','').replace('\u200b','').replace('\xa0',' ')
def plain(el): return clean_text(''.join(n.text or '' for n in el.iter(q('w:t'))))
def escape(s):
    s=html.escape(clean_text(s),quote=False)
    return re.sub(r'([\\`*_\[\]|])',r'\\\1',s)
def style(p):
    s=p.find(q('w:pPr')+'/'+q('w:pStyle'))
    return s.get(q('w:val'),'') if s is not None else ''
def walk_blocks(parent):
    for c in parent:
        if c.tag in (q('w:p'),q('w:tbl')): yield c
        elif c.tag==q('w:sdt'):
            content=c.find(q('w:sdtContent'))
            if content is not None: yield from walk_blocks(content)
        elif c.tag in (q('w:customXml'),): yield from walk_blocks(c)
def field_instruction(s):
    s=s.strip()
    if re.match(r'HYPERLINK\b',s,re.I):
        loc=re.search(r'\\l\s+"([^"]+)"',s)
        dest=re.search(r'^HYPERLINK\s+"([^"]*)"',s,re.I)
        return ('link',dest.group(1) if dest else '',loc.group(1) if loc else '')
    m=re.match(r'(?:REF|PAGEREF)\s+([^\s]+)',s,re.I)
    if m:return ('link','',m.group(1).strip('"'))
    return ('plain','','')

class Source:
    def __init__(self, root, spec):
        self.spec=spec; self.root=root; self.path=root/spec['source']; self.out=root/spec['destination']
        self.zip=ZipFile(self.path); self.sha=digest(self.path.read_bytes())
        self.xml=ET.fromstring(self.zip.read('word/document.xml'))
        self.rels={}
        if 'word/_rels/document.xml.rels' in self.zip.namelist():
            for r in ET.fromstring(self.zip.read('word/_rels/document.xml.rels')):
                self.rels[r.get('Id')]=dict(r.attrib)
        self.blocks=list(walk_blocks(self.xml.find(q('w:body'))))
        self.chapters=[]; self.bookmarks={}; self.block_pages={}; self.omitted={}
        self.forms=[]; self.media=[]; self.links=[]; self.warnings=[]; self.rows=[]
        self.numbering = self.read_numbering()
        # Refuse to silently choose a view for unresolved tracked edits.
        if next(self.xml.iter(q('w:ins')),None) is not None or next(self.xml.iter(q('w:del')),None) is not None:
            raise ValueError(f'Tracked edits require explicit disposition: {self.path}')
        for n in self.xml.iter(q('w:sdt')):
            content=n.find(q('w:sdtContent')); prop=n.find(q('w:sdtPr'))
            if content is not None and plain(content) and (prop is None or prop.find(q('w:docPartObj')) is None):
                d={'text':plain(content)}
                if prop is not None:
                    for k in ('tag','alias'):
                        p=prop.find(q('w:'+k)); d[k]=p.get(q('w:val'),'') if p is not None else ''
                self.forms.append(d)
        # These features require explicit support, not silent omission.
        for feature in ('footnoteReference','endnoteReference','txbxContent','altChunk','object'):
            if next(self.xml.iter(q('w:'+feature)),None) is not None:
                raise ValueError(f'Unsupported source feature {feature}: {self.path}')
        self.prepare()

    def read_numbering(self):
        """Resolve automatic Word list labels without assuming all lists are bullets."""
        if 'word/numbering.xml' not in self.zip.namelist(): return {}
        xml = ET.fromstring(self.zip.read('word/numbering.xml'))
        abstracts = {x.get(q('w:abstractNumId')): x for x in xml.findall(q('w:abstractNum'))}
        nums = {}
        for n in xml.findall(q('w:num')):
            a = n.find(q('w:abstractNumId'))
            if a is None: continue
            abstract = abstracts.get(a.get(q('w:val')))
            if abstract is None: continue
            levels = {}
            for lev in abstract.findall(q('w:lvl')):
                def value(name, default):
                    x = lev.find(q('w:'+name))
                    return x.get(q('w:val'), default) if x is not None else default
                levels[int(lev.get(q('w:ilvl'),'0'))] = {
                    'start':int(value('start','1')), 'format':value('numFmt','decimal'),
                    'text':value('lvlText','%1.')}
            for ov in n.findall(q('w:lvlOverride')):
                start = ov.find(q('w:startOverride'))
                if start is not None:
                    level = int(ov.get(q('w:ilvl'),'0'))
                    levels.setdefault(level, {'format':'decimal','text':'%1.'})['start']=int(start.get(q('w:val')))
            nums[n.get(q('w:numId'))] = levels
        style_nums = {}
        if 'word/styles.xml' in self.zip.namelist():
            for st in ET.fromstring(self.zip.read('word/styles.xml')).findall(q('w:style')):
                pr = st.find(q('w:pPr')+'/'+q('w:numPr'))
                if pr is not None: style_nums[st.get(q('w:styleId'))]=pr
        counters = {}; result = {}
        for p in self.xml.iter(q('w:p')):
            pr = p.find(q('w:pPr')+'/'+q('w:numPr'))
            if pr is None: pr = style_nums.get(style(p))
            if pr is None: continue
            ni=pr.find(q('w:numId')); il=pr.find(q('w:ilvl'))
            if ni is None: continue
            number=ni.get(q('w:val')); level=int(il.get(q('w:val'),'0')) if il is not None else 0
            lev=nums.get(number,{}).get(level)
            if not lev or lev['format']=='none':continue
            if lev['format']=='bullet':
                result[id(p)]={'label':'-','level':level,'format':'bullet'}; continue
            if lev['format']!='decimal':
                raise ValueError(f'Unsupported numbering format {lev["format"]}: {self.path}')
            state=counters.setdefault(number,{})
            state[level]=state.get(level,lev['start']-1)+1
            for k in list(state):
                if k>level:del state[k]
            label=lev['text']
            for k in range(9):label=label.replace('%'+str(k+1),str(state.get(k,nums[number].get(k,{}).get('start',1))))
            result[id(p)]={'label':label,'level':level,'format':'decimal'}
        return result

    def heading_text(self, p):
        text=plain(p).strip(); num=self.numbering.get(id(p))
        if num and num['format']=='decimal' and not re.match(r'^\d+[.)]\s',text):
            return num['label']+' '+text
        return text

    def prepare(self):
        current=self.out/'README.md'; seen={}; section=0
        for i,b in enumerate(self.blocks):
            text=self.heading_text(b) if b.tag==q('w:p') else plain(b).strip(); st=style(b) if b.tag==q('w:p') else ''
            inst=' '.join(n.text or '' for n in b.iter(q('w:instrText')))
            toc=bool(re.match(r'^(?:TOC|Contents)\d',st,re.I) or re.search(r'\bTOC\s+\\',inst))
            if toc:self.omitted[i]='Automatic Word contents cache replaced by Markdown navigation'
            title_nav=text.lower() in ('contents','table of contents')
            is_h1=st in ('Heading1','Heading 1')
            numbered=bool(re.match(r'^\d+\.\s',text))
            is_subchapter=st in ('Heading2','Heading 2') and (numbered or re.match(r'^F\d{2}\s*[|—]',text))
            if not toc and not title_nav and (is_h1 or is_subchapter):
                section+=1
                base=slug(text)
                if len(base)>95:base=base[:95].rstrip('-')
                seen[base]=seen.get(base,0)+1
                name=base+('-%d'%seen[base] if seen[base]>1 else '')+'.md'
                # Alphabetical navigation remains stable even for unnumbered chapters.
                if not re.match(r'^\d+-',name):name=f'{section:02d}-'+name
                current=self.out/name
                self.chapters.append({'title':text,'path':current,'start':i,'source_style':st})
            if title_nav:self.omitted[i]='Word contents heading replaced by Markdown navigation'
            self.block_pages[i]=current
            for mark in b.iter(q('w:bookmarkStart')):
                key=mark.get(q('w:name'))
                if key and key!='_GoBack':self.bookmarks[key]=(current,key)
        for key,(p,a) in list(self.bookmarks.items()):
            # TOC bookmarks resolve to document contents, never a stale printed page.
            if any(key==m.get(q('w:name')) for i in self.omitted for m in self.blocks[i].iter(q('w:bookmarkStart'))):
                self.bookmarks[key]=(self.out/'README.md',key)

    def resolve(self, dest, anchor, page, all_sources):
        orig=dest; dest=unquote(dest).replace('\\','/')
        u=urlsplit(dest)
        if u.scheme and u.scheme not in ('file',):
            self.links.append({'kind':'external-retained','target':orig,'from':str(page.relative_to(self.root))})
            return orig+('#'+anchor if anchor and not u.fragment else '')
        if u.fragment and not anchor:anchor=u.fragment
        dest=u.path
        candidate=(self.path.parent/dest).resolve() if dest else self.path.resolve()
        target=all_sources.get(candidate)
        if target is None and dest:
            matches=[s for p,s in all_sources.items() if p.name==Path(dest).name]
            if len(matches)==1:target=matches[0]
        if target:
            if anchor and anchor not in target.bookmarks:
                self.warnings.append({'kind':'unresolved-source-bookmark','source_target':orig,'anchor':anchor})
                target_page=target.out/'README.md'; anchor=''
            elif anchor:target_page,anchor=target.bookmarks[anchor]
            else:target_page=target.out/'README.md'
            self.links.append({'kind':'word-to-markdown','target':str(target_page.relative_to(self.root)),'anchor':anchor,'from':str(page.relative_to(self.root))})
            return rel_link(page,target_page,anchor)
        if not dest and anchor:
            self.warnings.append({'kind':'unresolved-local-bookmark','anchor':anchor})
            return rel_link(page,self.out/'README.md')
        if candidate.is_relative_to(self.root.resolve()) and candidate.exists():
            self.links.append({'kind':'non-word-local-retained','target':str(candidate.relative_to(self.root)),'from':str(page.relative_to(self.root))})
            return rel_link(page,candidate,anchor)
        # No invented replacement for an unavailable source artifact.
        self.warnings.append({'kind':'unavailable-source-target','source_target':orig,'anchor':anchor})
        return ''

    def inline(self, el, page, all_sources):
        stack=[]; out=[]
        def append(s):
            if stack:
                if stack[-1]['result']:stack[-1]['parts'].append(s)
            else:out.append(s)
        def visit(n):
            tag=n.tag
            if tag==q('w:fldChar'):
                kind=n.get(q('w:fldCharType'))
                if kind=='begin':stack.append({'instruction':'','parts':[],'result':False})
                elif kind=='separate' and stack:stack[-1]['result']=True
                elif kind=='end' and stack:
                    f=stack.pop();s=''.join(f['parts']);typ,d,a=field_instruction(f['instruction'])
                    if typ=='link':
                        url=self.resolve(d,a,page,all_sources)
                        s=f'[{s}]({url})' if url else s+' (source target unavailable)'
                    append(s)
                return
            if tag==q('w:instrText'):
                if stack:stack[-1]['instruction']+=n.text or ''
                return
            if tag==q('w:hyperlink'):
                s=self.inline_children(n,page,all_sources)
                r=self.rels.get(n.get(q('r:id')),{});d=r.get('Target','');a=n.get(q('w:anchor'),'')
                url=self.resolve(d,a,page,all_sources)
                append(f'[{s}]({url})' if url else s+' (source target unavailable)');return
            if tag==q('w:fldSimple'):
                s=self.inline_children(n,page,all_sources);typ,d,a=field_instruction(n.get(q('w:instr'),''))
                if typ=='link':
                    url=self.resolve(d,a,page,all_sources);s=f'[{s}]({url})' if url else s
                append(s);return
            if tag==q('w:t'):append(escape(n.text or ''));return
            if tag==q('w:tab'):append(' ');return
            if tag in (q('w:br'),q('w:cr')):
                if n.get(q('w:type')) not in ('page','column'):append('<br>')
                return
            if tag==q('w:noBreakHyphen'):append('‑');return
            if tag==q('w:drawing') or tag==q('w:pict'):
                blips=list(n.iter(q('a:blip')))+list(n.iter(q('v:imagedata')))
                dp=next(n.iter(q('wp:docPr')),None)
                alt=(dp.get('descr') or dp.get('title') or '') if dp is not None else ''
                for im in blips:
                    rid=im.get(q('r:embed')) or im.get(q('r:id'));link=self.rels.get(rid,{})
                    source=link.get('Target','');arc=str(PurePosixPath('word')/source)
                    if arc not in self.zip.namelist():
                        self.warnings.append({'kind':'missing-image','source':source});continue
                    data=self.zip.read(arc);sha=digest(data);suffix=Path(source).suffix.lower()
                    dst=self.root/'docs/assets/diagrams'/(sha[:20]+suffix);dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(data)
                    label=' '.join(alt.split()) if alt else f'Source figure from {self.spec["id"]}; see adjacent caption'
                    append(f'![{escape(label)}]({rel_link(page,dst)})')
                    self.media.append({'source_part':arc,'sha256':sha,'destination':str(dst.relative_to(self.root)),'alt':label,'from':str(page.relative_to(self.root))})
                return
            if tag in (q('w:pPr'),q('w:rPr'),q('w:sdtPr'),q('w:bookmarkStart'),q('w:bookmarkEnd'),q('w:lastRenderedPageBreak')):return
            for c in n:visit(c)
        for c in el:visit(c)
        for f in stack:
            out.extend(f['parts']) # cross-paragraph TOC end is deliberately discarded separately
        return ''.join(out)
    def inline_children(self,n,page,all_sources):return self.inline(n,page,all_sources)

    def paragraph(self,p,page,all_sources,as_cell=False):
        txt=self.inline(p,page,all_sources).strip();st=style(p)
        if not txt:return ''
        if as_cell:return txt
        is_section=any(c['start']==self.blocks.index(p) for c in self.chapters) if p in self.blocks else False
        number=self.numbering.get(id(p))
        if is_section:return '# '+escape(self.heading_text(p))
        level=re.match(r'Heading\s*(\d+)',st)
        if level:
            chapter=next((c for c in self.chapters if c['path']==page),None)
            base=re.match(r'Heading\s*(\d+)',chapter['source_style']) if chapter else None
            relative=max(2,int(level.group(1))-(int(base.group(1)) if base else 1)+1)
            label=(number['label']+' ') if number and number['format']=='decimal' else ''
            return '#' * min(relative,6)+' '+label+txt
        if st=='Title':return '## '+txt
        if st=='Subtitle':return '*'+txt+'*'
        num=p.find(q('w:pPr')+'/'+q('w:numPr'))
        if num is not None or st.startswith('List'):
            lvl=num.find(q('w:ilvl')) if num is not None else None
            indent=int(lvl.get(q('w:val'),'0')) if lvl is not None else 0
            label=number['label'] if number else '-'
            return '  '*min(indent,4)+label+' '+txt
        if 'Code' in st or 'code' in st:
            return '```text\n'+plain(p)+'\n```'
        return txt

    def render(self,all_sources):
        self.out.mkdir(parents=True,exist_ok=True)
        pages={self.out/'README.md':[]}
        for c in self.chapters:pages[c['path']]=[]
        for i,b in enumerate(self.blocks):
            page=self.block_pages[i];anchors=[m.get(q('w:name')) for m in b.iter(q('w:bookmarkStart')) if m.get(q('w:name'))!='_GoBack']
            row={'source':self.spec['source'],'source_id':self.spec['id'],'block':i,'kind':'table' if b.tag==q('w:tbl') else 'paragraph',
                 'source_text_sha256':digest(plain(b).encode()),'source_text_characters':len(plain(b)),
                 'destination':str(page.relative_to(self.root)),'status':'converted'}
            if i in self.omitted:
                row['status']='publication-navigation-replaced';row['reason']=self.omitted[i]
                for a in anchors:pages[self.out/'README.md'].append(f'<a id="{html.escape(a,quote=True)}"></a>')
                self.rows.append(row);continue
            anchor_markup='\n'.join(f'<a id="{html.escape(a,quote=True)}"></a>' for a in anchors if a)
            if b.tag==q('w:p'):
                rendered=self.paragraph(b,page,all_sources)
            else:
                # Source tables have no merged cells. Explicitly fail instead of flattening one silently.
                if list(b.iter(q('w:gridSpan'))) or list(b.iter(q('w:vMerge'))):
                    raise ValueError(f'Merged table needs an explicit conversion: {self.path} block {i}')
                lines=[]
                for tr in b.findall(q('w:tr')):
                    cells=[]
                    for tc in tr.findall(q('w:tc')):
                        paras=[self.paragraph(p,page,all_sources,True) for p in tc.iter(q('w:p'))]
                        cells.append('<br>'.join(t for t in paras if t))
                    lines.append(cells)
                if lines:
                    width=max(map(len,lines));lines=[r+['']*(width-len(r)) for r in lines]
                    rendered='\n'.join(['| '+' | '.join(lines[0])+' |','| '+' | '.join(['---']*width)+' |']+['| '+' | '.join(r)+' |' for r in lines[1:]])
                else:rendered=''
                anchor_markup+=f'\n<a id="source-table-{i}"></a>'
                row['rows']=len(lines);row['cells']=sum(len(tr.findall(q('w:tc'))) for tr in b.findall(q('w:tr')))
            if anchor_markup:pages[page].append(anchor_markup)
            if rendered:pages[page].append(rendered)
            row['markdown_sha256']=digest(rendered.encode());row['markdown_text']=rendered
            self.rows.append(row)
        for page,parts in pages.items():
            is_index=page.name=='README.md'
            title=self.spec['title'] if is_index else next(c['title'] for c in self.chapters if c['path']==page)
            source=rel_link(page,self.path)
            top=[f'# {title}','','[Documentation home]('+rel_link(page,self.root/'docs/README.md')+') · [Source document]('+source+')']
            if not is_index:top[-1]+=' · [Chapter index]('+rel_link(page,self.out/'README.md')+')'
            top += ['',f'> **Source:** {self.spec["id"]} — {self.spec["version"]}. {self.spec["status"]}',
                    '> This is a source-content transcription, not a new approval or a current platform-validation result.',
                    '',f'<!-- source-sha256: {self.sha} -->','']
            if self.spec.get('historical'):
                top += ['> **Historical only.** Use the [v1.4 reference architecture]('+rel_link(page,self.root/'docs/architecture/reference/README.md')+') for the active design baseline. Conflicting historical text has not been silently reconciled.','']
            if is_index:
                top+=['## Chapters','']+[f'- [{c["title"]}]({quote(c["path"].name)})' for c in self.chapters]+['','## Source front matter','']
            # Strip duplicate split heading, while keeping its bookmark immediately before content.
            if not is_index:
                first_heading=next((j for j,p in enumerate(parts) if p.startswith('# ')),None)
                if first_heading is not None:parts.pop(first_heading)
            text='\n\n'.join(parts)
            # Join adjacent source code paragraphs into one text fence.
            text=text.replace('\n```\n\n```text\n','\n')
            tail=[]
            if not is_index:
                ci=next(j for j,c in enumerate(self.chapters) if c['path']==page)
                if ci>0:tail.append('[Previous chapter]('+quote(self.chapters[ci-1]['path'].name)+')')
                tail.append('[Chapter index](README.md)')
                if ci+1<len(self.chapters):tail.append('[Next chapter]('+quote(self.chapters[ci+1]['path'].name)+')')
            content='\n'.join(top)+text+'\n\n'+(' · '.join(tail)+'\n' if tail else '')
            page.write_text(content.rstrip()+'\n',encoding='utf-8')
        return {'id':self.spec['id'],'source':self.spec['source'],'source_sha256':self.sha,
                'title':self.spec['title'],'version':self.spec['version'],'historical':bool(self.spec.get('historical')),
                'index':str((self.out/'README.md').relative_to(self.root)),
                'chapters':[dict(title=c['title'],path=str(c['path'].relative_to(self.root)),source_block=c['start']) for c in self.chapters],
                'body_blocks':len(self.blocks),'text_characters':sum(len(plain(b)) for b in self.blocks),
                'tables':sum(b.tag==q('w:tbl') for b in self.blocks),'form_fields':self.forms,
                'images':self.media,'links':self.links,'warnings':self.warnings,
                'bookmarks':{k:{'path':str(p.relative_to(self.root)),'anchor':a} for k,(p,a) in self.bookmarks.items()}}

def build(root=ROOT):
    cfg=json.loads((root/'sources/documentation/source_inventory.json').read_text())
    sources=[Source(root,s) for s in cfg['documents']]
    lookup={s.path.resolve():s for s in sources}
    rows=[s.render(lookup) for s in sources]
    out=root/'sources/documentation';out.mkdir(parents=True,exist_ok=True)
    (out/'conversion_manifest.json').write_text(json.dumps({'kind':'DOCX_TO_MARKDOWN_LINEAGE','documents':rows},ensure_ascii=False,indent=2)+'\n')
    ledger=[]
    for s in sources:
        for row in s.rows:
            row.pop('markdown_text',None);ledger.append(row)
    (out/'block_coverage.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n')
    return rows,sources

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--root',type=Path,default=ROOT)
    a.add_argument('--refresh-from-frozen-sources',action='store_true',help='Explicitly regenerate Markdown in a review working tree. Never changes the DOCX sources.')
    args=a.parse_args()
    if not args.refresh_from_frozen_sources:a.error('Use --refresh-from-frozen-sources in a clean review branch; regeneration replaces chapter Markdown.')
    rows,_=build(args.root.resolve())
    print(json.dumps({'documents':len(rows),'chapters':sum(len(r['chapters']) for r in rows),'warnings':sum(len(r['warnings']) for r in rows)},indent=2))
if __name__=='__main__':main()
