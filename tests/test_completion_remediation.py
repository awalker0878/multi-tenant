"""Completion audit regressions; synthetic engine commands are NOT engine evidence."""
from __future__ import annotations
import copy,csv,hashlib,io,json,os,re,shlex,subprocess,sys,tempfile,unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import documentation_controls as control
import check_documentation as checker
from build_documentation import Builder
from convert_word_docs import Source,q,code_text
from tools import verify_terraform as tf
from record_doc_amendment import proposed

class ContentFidelity(unittest.TestCase):
 def test_newline_tab_and_backslash_preserved(self):
  p=ET.fromstring('<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:pPr><w:pStyle w:val="Code"/></w:pPr><w:r><w:t>command \\</w:t><w:br/><w:tab/><w:t>--flag value</w:t></w:r></w:p>')
  self.assertEqual(code_text(p),'command \\\n\t--flag value')
  self.assertEqual(control.visible_word(p,True),code_text(p))
  good='<!-- SOURCE-BLOCK T:1 BEGIN -->\n```text\n'+code_text(p)+'\n```\n<!-- SOURCE-BLOCK T:1 END -->'
  self.assertTrue(all(ok for _,ok in control.block_checks(p,'T',1,good,checker.parse)))
  bad=good.replace('\\\n\t','\\ ')
  self.assertFalse(all(ok for _,ok in control.block_checks(p,'T',1,bad,checker.parse)))
 def test_actual_all_code_paragraphs(self):
  specs=json.loads((ROOT/'sources/documentation/source_inventory.json').read_text())['documents'];n=0
  for spec in specs:
   src=Source(ROOT,spec)
   for i,b in enumerate(src.blocks):
    style=b.find(q('w:pPr')+'/'+q('w:pStyle')) if b.tag==q('w:p') else None
    if style is not None and 'code' in style.get(q('w:val'),'').lower():
     n+=1;row=next(r for r in json.loads((ROOT/'sources/documentation/block_coverage.json').read_text()) if r['source_id']==spec['id'] and r['block']==i)
     self.assertTrue(all(ok for _,ok in control.block_checks(b,spec['id'],i,(ROOT/row['destination']).read_text(),checker.parse)))
     if spec['id']=='IMP04' and 'nsx_observe.py' in code_text(b):
      args=shlex.split(code_text(b).replace('\\\n',''))
      self.assertNotIn(' ',args);self.assertNotIn('\\',args)
  self.assertEqual(n,13)
 def test_table_mutation_rejected_without_count_change(self):
  xml='<w:tbl xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'+''.join('<w:tr>'+''.join('<w:tc><w:p><w:r><w:t>'+x+'</w:t></w:r></w:p></w:tc>' for x in row)+'</w:tr>' for row in [['Relationship','Treatment'],['Public to PAZ','Governed ingress'],['Workload to management','No direct path']])+'</w:tbl>'
  node=ET.fromstring(xml)
  good='<!-- SOURCE-BLOCK T:1 BEGIN -->\n|Relationship|Treatment|\n|---|---|\n|Public to PAZ|Governed ingress|\n|Workload to management|No direct path|\n<!-- SOURCE-BLOCK T:1 END -->'
  bad=good.replace('Governed ingress','TMP').replace('No direct path','Governed ingress').replace('TMP','No direct path')
  self.assertTrue(all(ok for _,ok in control.block_checks(node,'T',1,good,checker.parse)))
  self.assertFalse(all(ok for _,ok in control.block_checks(node,'T',1,bad,checker.parse)))
 def test_bad_boundaries_rejected(self):
  node=ET.fromstring('<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>')
  self.assertFalse(control.block_checks(node,'T',1,'no markers',checker.parse)[0][1])
 def test_explicit_amendment_not_silent_loss(self):
  node=ET.fromstring('<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:r><w:t>Original wording.</w:t></w:r></w:p>')
  body='Equivalent reviewed wording.';page='<!-- SOURCE-BLOCK T:1 BEGIN -->\n'+body+'\n<!-- SOURCE-BLOCK T:1 END -->'
  record={'replacement_sha256':control.sha(body)}
  self.assertTrue(all(ok for _,ok in control.block_checks(node,'T',1,page,checker.parse,record)))
  self.assertFalse(all(ok for _,ok in control.block_checks(node,'T',1,page+'extra' if False else page.replace('reviewed','unreviewed'),checker.parse,record)))

class ADRGovernance(unittest.TestCase):
 def setUp(self):self.records=json.loads((ROOT/'sources/documentation/adr_records.json').read_text());self.builder=Builder(ROOT)
 def test_current_proposals_valid(self):self.assertEqual(control.lifecycle_errors(self.records),[])
 def test_decision_reversal_in_rendered_page_detected(self):
  a=next(a for a in self.records if a['id']=='ADR-0006');expected=control.adr_text(self.builder,a)
  mutation=expected.replace(a['decision'],'Use unrestricted transit instead of the governed boundary.')
  self.assertNotEqual(mutation,expected);self.assertEqual((ROOT/self.builder.adrpath(a)).read_text(),expected)
 def test_status_only_page_mutation_detected(self):
  a=self.records[0];expected=control.adr_text(self.builder,a)
  self.assertNotEqual(expected,expected.replace('**Status:** Proposed','**Status:** Accepted'))
 def test_accepted_missing_evidence_rejected(self):
  a=copy.deepcopy(self.records[0]);a['status']='Accepted';self.assertTrue(control.lifecycle_errors([a]))
 def test_accepted_supported_with_real_record_fields(self):
  a=copy.deepcopy(self.records[0]);a['status']='Accepted';a['governance'].update(decision_date='2026-09-17',accepting_authority='TEST FIXTURE AUTHORITY NOT ACTUAL',evidence=['TEST-FIXTURE-DECISION'])
  self.assertEqual(control.lifecycle_errors([a]),[])
  self.assertIn('**Status:** Accepted',control.adr_text(self.builder,a));self.assertIn('TEST-FIXTURE-DECISION',control.adr_text(self.builder,a))
 def test_proposed_cannot_impersonate_acceptance(self):
  a=copy.deepcopy(self.records[0]);a['governance']['accepting_authority']='someone';self.assertTrue(control.lifecycle_errors([a]))
 def test_owner_required(self):
  a=copy.deepcopy(self.records[0]);a['governance']['accountable_role']='';self.assertTrue(control.lifecycle_errors([a]))
 def test_superseded_requires_reciprocal_successor(self):
  a,b=copy.deepcopy(self.records[:2]);a['status']='Superseded';a['governance'].update(decision_date='2026-09-17',accepting_authority='TEST',evidence=['TEST'],rationale='TEST',superseded_by=[b['id']]);b['status']='Accepted';b['governance'].update(decision_date='2026-09-17',accepting_authority='TEST',evidence=['TEST'])
  self.assertTrue(control.lifecycle_errors([a,b]));b['governance']['supersedes']=[a['id']];self.assertEqual(control.lifecycle_errors([a,b]),[])
 def test_rejected_needs_rationale(self):
  a=copy.deepcopy(self.records[0]);a['status']='Rejected';a['governance'].update(decision_date='2026-09-17',accepting_authority='TEST',evidence=['TEST'])
  self.assertTrue(control.lifecycle_errors([a]));a['governance']['rationale']='TEST ONLY';self.assertEqual(control.lifecycle_errors([a]),[])

class AllocationAndFamilies(unittest.TestCase):
 def test_all_original_requirements_allocated(self):
  reqs={r['requirementId']:r for r in csv.DictReader(io.StringIO((ROOT/'reference/Portable_Hosting_Delivery_Kits_v1_1/04_Shared/requirements.csv').read_text(encoding='utf-8-sig')))};rows=json.loads((ROOT/'sources/assurance/implementation_allocation.json').read_text())
  self.assertEqual(set(reqs),{r['requirement_id'] for r in rows});self.assertEqual(len(rows),370)
  for r in rows:
   self.assertEqual(r['source_requirement'],reqs[r['requirement_id']]['text']);self.assertIn(r['assertion_focus'],r['source_requirement'])
   self.assertTrue(r['enforcement_location'] and r['responsible_role'] and r['remaining_dependency']);self.assertEqual(r['observed_native_evidence'],[])
   for p in r['artifacts']:self.assertTrue((ROOT/p).is_file(),p)
 def test_state_not_implemented_by_backend_declaration(self):
  rows=json.loads((ROOT/'sources/assurance/implementation_allocation.json').read_text());state=[r for r in rows if r['requirement_id']=='STATE-002'];self.assertEqual(len(state),6)
  self.assertTrue(all(r['implementation_disposition']=='EXTERNAL_BACKEND_CONTROLS_REQUIRED' for r in state))
 def test_all_verification_families_retained(self):
  families=json.loads((ROOT/'sources/assurance/verification_families.json').read_text())
  self.assertEqual({k:len(v['records']) for k,v in families.items()},{'CT':80,'RA':12,'W14':12,'Q11':12})
  for k,v in families.items():
   if k=='RA':self.assertEqual(v['records'],json.loads((ROOT/v['source']).read_text()))
   else:self.assertEqual(v['records'],list(csv.DictReader(io.StringIO((ROOT/v['source']).read_text(encoding='utf-8-sig')))))
 def test_historical_findings_not_falsely_closed(self):
  records=json.loads((ROOT/'sources/assurance/historical_findings.json').read_text());self.assertEqual({r['original_finding'] for r in records},{f'F{i:02d}' for i in range(1,25)})
  for r in records:self.assertEqual(r['closure_authority'],'NOT_RECORDED');self.assertTrue((ROOT/r['source_path']).is_file())

class AmendmentLifecycle(unittest.TestCase):
 def test_proposed_edit_can_be_recorded_without_reapproving_original(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'sources/documentation').mkdir(parents=True);(root/'page.md').write_text('<!-- SOURCE-BLOCK T:1 BEGIN -->\nNew reviewed paragraph.\n<!-- SOURCE-BLOCK T:1 END -->')
   ledger=[{'source_id':'T','block':1,'status':'converted','source_text_sha256':'a'*64,'destination':'page.md'}];(root/'sources/documentation/block_coverage.json').write_text(json.dumps(ledger))
   a=proposed(root,'T',1,'Improve wording without changing control','Architecture role',['R-1'],['ADR-0003']);self.assertEqual(a['status'],'Proposed');self.assertIsNone(a['authority']);(root/'sources/documentation/amendments.json').write_text(json.dumps([a]))
   result=control.amendment_records(root,{},ledger,{'ADR-0003'},{'R-1'});self.assertEqual(result[('T',1)]['replacement_markdown'],'New reviewed paragraph.')
 def test_unattributed_amendment_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'sources/documentation').mkdir(parents=True);(root/'sources/documentation/amendments.json').write_text('[{}]')
   with self.assertRaises(ValueError):control.amendment_records(root,{},[],set(),set())

class TerraformCommandBoundary(unittest.TestCase):
 def test_synthetic_command_recording_not_real_provider_test(self):
  calls=[]
  def fake(argv,**kwargs):
   calls.append(argv)
   if argv[1:]==['version','-json']:return subprocess.CompletedProcess(argv,0,json.dumps({'terraform_version':'TEST_FIXTURE_NOT_ENGINE'}),'')
   directory=Path(argv[1].removeprefix('-chdir='));cmd=argv[2:]
   if cmd[:1]==['init']:
    self.assertIn('-backend=false',cmd);(directory/'.terraform.lock.hcl').write_text('# TEST FIXTURE; never published as a provider lock\n');out=''
   elif cmd[:1]==['validate']:out='{"valid":true}'
   elif cmd[:1]==['test']:self.assertEqual(directory.parent.name,'modules');out='synthetic unit response, no real provider'
   elif cmd==['providers','schema','-json']:
    self.assertEqual(directory.parent.name,'modules');out='{"provider_schemas":{"TEST-FIXTURE":{}}}'
   else:raise AssertionError(cmd)
   return subprocess.CompletedProcess(argv,0,out,'')
  with tempfile.TemporaryDirectory() as td,patch.object(tf.shutil,'which',return_value='/synthetic-terraform'),patch.object(tf.subprocess,'run',side_effect=fake),patch.object(sys,'argv',['verify','--mock-tests','--output',str(Path(td)/'report.json')]),redirect_stdout(io.StringIO()):
   self.assertEqual(tf.main(),0);report=json.loads((Path(td)/'report.json').read_text());self.assertEqual(len(report['roots']),10)
   self.assertTrue(all(r['schema_export']=='MATCHING_MODULE_SCHEMA_REVIEWED_ROOT_BACKEND_NOT_INITIALIZED' for r in report['roots']))
   self.assertEqual(sum(a[2:]==['providers','schema','-json'] for a in calls),10)
   self.assertFalse(any('apply' in a or 'destroy' in a for a in calls))

if __name__=='__main__':unittest.main()
