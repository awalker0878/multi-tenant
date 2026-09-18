"""Regression tests for loss-aware local document conversion and source decisions."""
from __future__ import annotations
import base64
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from zipfile import ZipFile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from convert_word_docs import Source, field_instruction, escape, slug
ROOT=Path(__file__).resolve().parents[1]
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
WP='http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'

def para(text,style=''):
    return '<w:p>'+('<w:pPr><w:pStyle w:val="'+style+'"/></w:pPr>' if style else '')+'<w:r><w:t>'+text+'</w:t></w:r></w:p>'

class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
    def source(self,body,extra=None,name='sample.docx'):
        path=self.root/name
        with ZipFile(path,'w') as z:
            z.writestr('word/document.xml',f'<w:document xmlns:w="{W}" xmlns:r="{R}" xmlns:a="{A}" xmlns:wp="{WP}"><w:body>{body}</w:body></w:document>')
            for k,v in (extra or {}).items():z.writestr(k,v)
        s=Source(self.root,dict(source=name,id='FIX',title='Fixture',destination='docs/fixture',version='Test fixture',status='Not approved'))
        return s
    def render(self,s,others=()):
        r=s.render({x.path.resolve():x for x in (s,*others)})
        txt='\n'.join(p.read_text() for p in (self.root/'docs/fixture').glob('*.md'))
        return r,txt
    def test_full_narrative_retained(self):
        s=self.source(para('1. Architecture','Heading1')+para('No general transit is authorized.'))
        _,txt=self.render(s);self.assertIn('No general transit is authorized.',txt)
    def test_source_hash_retained(self):
        s=self.source(para('Scope'));r,txt=self.render(s)
        self.assertIn(hashlib.sha256(s.path.read_bytes()).hexdigest(),txt)
    def test_word_bookmark_is_explicit_anchor(self):
        s=self.source('<w:p><w:bookmarkStart w:id="1" w:name="boundary"/><w:r><w:t>Boundary</w:t></w:r></w:p>')
        _,txt=self.render(s);self.assertIn('<a id="boundary"></a>',txt)
    def test_relationship_link_becomes_markdown_anchor(self):
        body='<w:p><w:bookmarkStart w:id="1" w:name="same"/><w:r><w:t>Target</w:t></w:r></w:p><w:p><w:hyperlink w:anchor="same"><w:r><w:t>Jump</w:t></w:r></w:hyperlink></w:p>'
        _,txt=self.render(self.source(body));self.assertIn('[Jump](README.md#same)',txt)
    def test_unknown_source_bookmark_is_recorded(self):
        s=self.source('<w:p><w:hyperlink w:anchor="missing"><w:r><w:t>Jump</w:t></w:r></w:hyperlink></w:p>')
        r,_=self.render(s);self.assertTrue(r['warnings'])
    def test_missing_source_artifact_not_invented(self):
        rels='<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="hyperlink" Target="missing.docx" TargetMode="External"/></Relationships>'
        s=self.source('<w:p><w:hyperlink r:id="rId1"><w:r><w:t>Missing source</w:t></w:r></w:hyperlink></w:p>',{'word/_rels/document.xml.rels':rels})
        r,txt=self.render(s);self.assertIn('source target unavailable',txt);self.assertTrue(r['warnings'])
    def test_table_text_and_shape(self):
        table='<w:tbl><w:tr><w:tc>'+para('Owner')+'</w:tc><w:tc>'+para('Scope')+'</w:tc></w:tr><w:tr><w:tc>'+para('Tenant')+'</w:tc><w:tc>'+para('Workload')+'</w:tc></w:tr></w:tbl>'
        s=self.source(table);r,txt=self.render(s);self.assertEqual(r['tables'],1);self.assertIn('| Tenant | Workload |',txt)
        self.assertEqual(s.rows[0]['cells'],4)
    def test_merged_table_requires_explicit_handling(self):
        s=self.source('<w:tbl><w:tr><w:tc><w:tcPr><w:gridSpan w:val="2"/></w:tcPr>'+para('Merged')+'</w:tc></w:tr></w:tbl>')
        with self.assertRaisesRegex(ValueError,'Merged'):self.render(s)
    def test_tracked_insertions_refused(self):
        with self.assertRaisesRegex(ValueError,'Tracked'):self.source('<w:p><w:ins>'+para('Pending edit')+'</w:ins></w:p>')
    def test_text_box_refused(self):
        with self.assertRaisesRegex(ValueError,'txbxContent'):self.source('<w:p><w:txbxContent>'+para('Hidden')+'</w:txbxContent></w:p>')
    def test_footnote_refused_instead_of_dropped(self):
        with self.assertRaisesRegex(ValueError,'footnote'):self.source('<w:p><w:r><w:footnoteReference w:id="2"/></w:r></w:p>')
    def test_form_prompt_is_retained(self):
        body='<w:sdt><w:sdtPr><w:tag w:val="owner"/></w:sdtPr><w:sdtContent>'+para('Enter actual owner')+'</w:sdtContent></w:sdt>'
        s=self.source(body);r,txt=self.render(s);self.assertEqual(len(r['form_fields']),1);self.assertIn('Enter actual owner',txt)
    def test_toc_control_is_not_an_input_field(self):
        body='<w:sdt><w:sdtPr><w:docPartObj/></w:sdtPr><w:sdtContent>'+para('Cached entry','TOC1')+'</w:sdtContent></w:sdt>'
        s=self.source(body);r,txt=self.render(s);self.assertFalse(r['form_fields']);self.assertNotIn('Cached entry',txt)
    def test_duplicate_heading_paths_are_unique(self):
        s=self.source(para('Topic','Heading1')+para('Topic','Heading1'));self.assertEqual(len({c['path'] for c in s.chapters}),2)
    def test_numbered_heading_from_word_numpr(self):
        num=f'<w:numbering xmlns:w="{W}"><w:abstractNum w:abstractNumId="7"><w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/></w:lvl></w:abstractNum><w:num w:numId="7"><w:abstractNumId w:val="7"/></w:num></w:numbering>'
        def numbered(t):return '<w:p><w:pPr><w:pStyle w:val="Heading2"/><w:numPr><w:ilvl w:val="0"/><w:numId w:val="7"/></w:numPr></w:pPr><w:r><w:t>'+t+'</w:t></w:r></w:p>'
        s=self.source(numbered('First')+numbered('Second'),{'word/numbering.xml':num})
        self.assertEqual([c['title'] for c in s.chapters],['1. First','2. Second'])
    def test_complex_hyperlink_instruction(self):
        self.assertEqual(field_instruction(' HYPERLINK "other.docx" \\l "Other_2" '),('link','other.docx','Other_2'))
    def test_page_reference_is_link_not_page_invention(self):
        self.assertEqual(field_instruction(' PAGEREF destination \\h '),('link','','destination'))
    def test_display_escape_keeps_literal_pipe(self):
        self.assertEqual(escape('PAZ|OZ'),r'PAZ\|OZ')
    def test_image_bytes_preserved(self):
        payload=b'test-byte-fixture-not-an-actual-png'
        rels='<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="im1" Type="image" Target="media/figure.png"/></Relationships>'
        body='<w:p><w:r><w:drawing><wp:docPr descr="Routing diagram"/><a:blip r:embed="im1"/></w:drawing></w:r></w:p>'
        s=self.source(body,{'word/_rels/document.xml.rels':rels,'word/media/figure.png':payload})
        r,txt=self.render(s);self.assertEqual((self.root/r['images'][0]['destination']).read_bytes(),payload);self.assertIn('![Routing diagram]',txt)

class DecisionTraceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records=json.loads((ROOT/'sources/documentation/adr_records.json').read_text())
    def test_all_fifteen_parent_decisions_mapped(self):
        actual={x for r in self.records for x in r['source_decision_ids']}
        self.assertTrue({f'AD-{i:02d}' for i in range(1,16)}<=actual)
    def test_all_worked_decisions_mapped(self):
        actual={x for r in self.records for x in r['source_decision_ids']}
        self.assertTrue({f'RD14-{i:02d}' for i in range(1,6)}|{'DEV-ADR-01'}<=actual)
    def test_no_acceptance_fabricated(self):
        from adr_lifecycle import validate
        self.assertEqual(validate(self.records), [])
    def test_every_decision_has_substantive_traceability(self):
        for r in self.records:
            for field in ('context','decision','alternatives','consequences','engineering_obligations','open_work'):
                self.assertGreater(len(r[field]),35,(r['id'],field))
            self.assertTrue(r['source_sections']);self.assertTrue(r['requirements']);self.assertTrue(r['implementation_paths'])
    def test_originals_are_not_unavailable_rad_tad_fabrications(self):
        inv=json.loads((ROOT/'sources/documentation/source_inventory.json').read_text())
        self.assertFalse(any(Path(x['source']).name in ('RAD_Adoption_and_Conformance.docx','TAD_Technical_Architecture.docx') for x in inv['documents']))
    def test_historical_audits_explicitly_marked(self):
        inv=json.loads((ROOT/'sources/documentation/source_inventory.json').read_text())
        for x in inv['documents']:
            if x['id'] in ('HB10','HB11','AUD11','REV12'):self.assertTrue(x['historical'])
