"""Regression intents retained after consolidating the two correction variants.

These exercise the active ADR, source-structure, maintained-design and assurance
records. Synthetic CLI responses test command boundaries, NOT provider execution.
The discarded block-amendment model cannot overwrite immutable transcriptions.
"""
from __future__ import annotations
import copy,csv,io,json,shlex,subprocess,sys,tempfile,unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import documentation_controls as control
import documentation_structure as structure
import check_current_design
import check_assurance_allocation as assurance
from build_documentation import Builder
from convert_word_docs import Source,q,code_text
from tools import verify_terraform as tf
from record_doc_amendment import proposed


def soup(text):return BeautifulSoup(structure.MD(text),'html.parser')


def accepted(record):
    record['status']='Accepted'
    record['governance'].update(deciding_authority='Synthetic unit-test authority',
        decision_date='2026-01-01',decision_record='TEST-ONLY-DECISION',
        evidence_refs=['TEST-ONLY-EVIDENCE'],decision_rationale='Hypothetical unit test, no organizational approval')


class ContentFidelity(unittest.TestCase):
    def test_newline_tab_and_backslash_preserved(self):
        p=ET.fromstring(r'<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:r><w:t>command \</w:t><w:br/><w:tab/><w:t>--flag value</w:t></w:r></w:p>')
        expected='command '+chr(92)+'\n\t--flag value'
        self.assertEqual(code_text(p),expected);self.assertEqual(structure.visible(p),expected)
        good='```text\n'+expected+'\n```'
        self.assertEqual(structure.compare_code([(1,expected)],soup(good)),[])
        self.assertTrue(structure.compare_code([(1,expected)],soup(good.replace('\n\t',' '))))
    def test_actual_all_code_paragraphs(self):
        result=structure.check(ROOT);self.assertEqual(result['errors'],[])
        self.assertEqual(result['code_paragraphs'],13)
        page=ROOT/'docs/implementation/increment-04/06-transport-credentials-and-protected-evidence.md'
        command=next(c.get_text() for c in soup(page.read_text()).select('pre code') if '/secure/nsx-expected.json' in c.get_text())
        args=shlex.split(command[command.index('python tools/nsx_observe.py /secure'):].replace(chr(92)+'\n',''))
        self.assertNotIn(' ',args);self.assertNotIn(chr(92),args);self.assertEqual(len(args),10)
    def test_table_mutation_rejected_without_count_change(self):
        rows=[['Relationship','Treatment'],['Public to PAZ','Governed ingress'],['Workload to management','No direct path']]
        node=ET.fromstring('<w:tbl xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'+''.join('<w:tr>'+''.join('<w:tc><w:p><w:r><w:t>'+x+'</w:t></w:r></w:p></w:tc>' for x in row)+'</w:tr>' for row in rows)+'</w:tbl>')
        good='|Relationship|Treatment|\n|---|---|\n|Public to PAZ|Governed ingress|\n|Workload to management|No direct path|'
        bad=good.replace('Governed ingress','TMP').replace('No direct path','Governed ingress').replace('TMP','No direct path')
        self.assertEqual(structure.compare_table(node,soup(good).table),(6,[]))
        count,errors=structure.compare_table(node,soup(bad).table)
        self.assertEqual(count,6);self.assertEqual(len(errors),2)
    def test_bad_boundaries_rejected(self):
        self.assertTrue(structure.compare_code([(1,'must stay code')],soup('must stay code')))
    def test_explicit_current_revision_not_silent_source_loss(self):
        original=Path.read_text;target=ROOT/'docs/current/TAD-infrastructure.md'
        def revised(p,*args,**kwargs):
            text=original(p,*args,**kwargs)
            return text.replace('## Design content','## Design content\n\nProposed explicit engineering refinement for review.') if p==target else text
        with patch.object(Path,'read_text',revised):
            self.assertEqual(check_current_design.check(ROOT)['errors'],[])
        self.assertTrue(structure.compare_code([(1,'unchanged source')],soup('```text\nunreviewed source replacement\n```')))


class ADRGovernance(unittest.TestCase):
    def setUp(self):
        self.records=json.loads((ROOT/'sources/documentation/adr_records.json').read_text());self.builder=Builder(ROOT)
    def test_current_proposals_valid(self):self.assertEqual(control.lifecycle_errors(self.records),[])
    def test_decision_reversal_in_rendered_page_detected(self):
        a=next(a for a in self.records if a['id']=='ADR-0006');expected=control.adr_text(self.builder,a)
        mutation=expected.replace(a['decision'],'Use unrestricted transit instead of the governed boundary.')
        self.assertNotEqual(mutation,expected);self.assertEqual((ROOT/self.builder.adrpath(a)).read_text(),expected)
    def test_status_only_page_mutation_detected(self):
        expected=control.adr_text(self.builder,self.records[0])
        self.assertNotEqual(expected,expected.replace('**Status:** Proposed','**Status:** Accepted'))
    def test_accepted_missing_evidence_rejected(self):
        a=copy.deepcopy(self.records[0]);a['status']='Accepted';self.assertTrue(control.lifecycle_errors([a]))
    def test_accepted_supported_with_real_record_fields(self):
        a=copy.deepcopy(self.records[0]);accepted(a);self.assertEqual(control.lifecycle_errors([a]),[])
        text=control.adr_text(self.builder,a);self.assertIn('**Status:** Accepted',text);self.assertIn('TEST-ONLY-EVIDENCE',text)
    def test_proposed_cannot_impersonate_acceptance(self):
        a=copy.deepcopy(self.records[0]);a['governance']['deciding_authority']='Synthetic authority'
        self.assertTrue(control.lifecycle_errors([a]))
    def test_owner_required(self):
        a=copy.deepcopy(self.records[0]);a['governance']['accountable_role']='';self.assertTrue(control.lifecycle_errors([a]))
    def test_superseded_requires_resolved_accepted_successor(self):
        a,b=copy.deepcopy(self.records[:2]);accepted(a);a['status']='Superseded';a['governance']['superseded_by']=b['id']
        self.assertTrue(control.lifecycle_errors([a,b]));accepted(b);self.assertEqual(control.lifecycle_errors([a,b]),[])
        b['status']='Superseded';b['governance']['superseded_by']=a['id'];self.assertTrue(control.lifecycle_errors([a,b]))
    def test_rejected_needs_rationale(self):
        a=copy.deepcopy(self.records[0]);accepted(a);a['status']='Rejected';a['governance']['decision_rationale']=None
        self.assertTrue(control.lifecycle_errors([a]));a['governance']['decision_rationale']='TEST ONLY rejection';self.assertEqual(control.lifecycle_errors([a]),[])


class AllocationAndFamilies(unittest.TestCase):
    def test_all_original_requirements_allocated(self):
        result=assurance.check(ROOT);self.assertEqual(result['errors'],[])
        self.assertEqual(result['requirements'],194);self.assertEqual(result['allocation_rows'],540)
    def test_state_not_implemented_by_backend_declaration(self):
        rows=json.loads((ROOT/'sources/assurance/implementation_assertions.json').read_text());state=[r for r in rows if r['requirement_id']=='STATE-002']
        self.assertGreater(len(state),1)
        self.assertTrue(all('NATIVE_NOT_RUN' in r['evidence_class'] and r['remaining_dependency'] for r in state))
        self.assertTrue(all('EXTERNAL' in r['implementation_disposition'] for r in state))
    def test_all_verification_families_retained(self):
        families=json.loads((ROOT/'sources/assurance/verification_families.json').read_text())
        self.assertEqual(families['families'],{'CT':80,'RA':12,'W14':12,'Q11':12})
        self.assertEqual(assurance.verification_errors(ROOT,families),[])
    def test_historical_findings_not_falsely_closed(self):
        with (ROOT/'sources/assurance/historical_audit_dispositions.csv').open(newline='') as f:records=list(csv.DictReader(f))
        self.assertEqual({r['original_finding'] for r in records},{f'F{i:02d}' for i in range(1,25)})
        for r in records:
            self.assertEqual(r['closure_authority'],'NOT_RECORDED');self.assertEqual(r['closure_status'],'NOT_CLOSED_BY_THIS_AUDIT')
            self.assertTrue((ROOT/r['source_path']).is_file())


class MaintainedAuthoringLifecycle(unittest.TestCase):
    def test_proposed_edit_keeps_originals_unapproved(self):
        records=json.loads((ROOT/'sources/documentation/current_design_records.json').read_text())
        self.assertTrue(all(r['status']=='Proposed' and r['decision_authority'] is None for r in records))
        self.assertEqual(check_current_design.check(ROOT)['errors'],[])
    def test_retired_amendment_writer_refuses_before_touching_files(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);sentinel=root/'keep.txt';sentinel.write_text('keep')
            with self.assertRaisesRegex(ValueError,'not active'):proposed(root,'T',1,'reason','role',[],[])
            self.assertEqual(list(root.iterdir()),[sentinel]);self.assertEqual(sentinel.read_text(),'keep')


class TerraformCommandBoundary(unittest.TestCase):
    def test_synthetic_command_recording_not_real_provider_test(self):
        calls=[]
        def fake(argv,**kwargs):
            calls.append(argv)
            if argv[1:]==['version','-json']:return subprocess.CompletedProcess(argv,0,json.dumps({'terraform_version':'TEST_FIXTURE_NOT_ENGINE'}),'')
            directory=Path(argv[1].removeprefix('-chdir='));cmd=argv[2:]
            if cmd[:1]==['init']:
                self.assertIn('-backend=false',cmd);self.assertIn('-lockfile=readonly',cmd)
                out='' # Do not overwrite the actual lock in the fixture copy.
            elif cmd[:1]==['validate']:out='{"valid":true}'
            elif cmd[:1]==['test']:self.assertEqual(directory.parent.name,'modules');out='synthetic unit response, no real provider'
            elif cmd==['providers','schema','-json']:
                self.assertEqual(directory.parent.name,'modules');out='{"provider_schemas":{"TEST-FIXTURE":{}}}'
            else:raise AssertionError(cmd)
            return subprocess.CompletedProcess(argv,0,out,'')
        with tempfile.TemporaryDirectory() as td,patch.object(tf.shutil,'which',return_value='/synthetic-terraform'),patch.object(tf.subprocess,'run',side_effect=fake),patch.object(sys,'argv',['verify','--mock-tests','--output',str(Path(td)/'report.json')]),redirect_stdout(io.StringIO()):
            self.assertEqual(tf.main(),0);report=json.loads((Path(td)/'report.json').read_text())
            self.assertEqual(len(report['roots']),10);self.assertEqual(len(report['modules']),10)
            self.assertTrue(all(r['validation']=='PASSED' and r['schema_export']=='NOT_RUN_ROOT_BACKEND_BOUNDARY' for r in report['roots']))
            self.assertEqual(sum(a[2:]==['providers','schema','-json'] for a in calls),10)
            self.assertFalse(any('apply' in a or 'destroy' in a for a in calls))

if __name__=='__main__':unittest.main()
