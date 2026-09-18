"""Independent regressions for CA-01 through CA-11, no native target calls."""
from __future__ import annotations
import copy,hashlib,json,shlex,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET
import yaml
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from convert_word_docs import code_text,q,Source,build
from documentation_structure import check as structure,visible
from adr_lifecycle import validate,render
from build_documentation import Builder
from check_current_design import check as current_check
from check_assurance_allocation import check as allocation_check
from tools.check_release import verify,verify_snapshot


class CodeStructureTests(unittest.TestCase):
    def test_break_tab_indentation_and_carriage_return(self):
        el=ET.fromstring('<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:r><w:t>first</w:t><w:br/><w:t xml:space="preserve">  second</w:t><w:tab/><w:t>third</w:t><w:cr/><w:t>end</w:t></w:r></w:p>')
        self.assertEqual(code_text(el),'first\n  second\tthird\nend')
        self.assertEqual(visible(el),'first\n  second\tthird\nend')
    def test_page_break_is_not_a_code_newline(self):
        el=ET.fromstring('<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:r><w:t>a</w:t><w:br w:type="page"/><w:t>b</w:t></w:r></w:p>')
        self.assertEqual(code_text(el),'ab')
    def test_all_original_code_and_positioned_table_cells(self):
        result=structure(ROOT);self.assertEqual(result['errors'],[])
        self.assertEqual((result['tables'],result['cells'],result['code_paragraphs']),(486,7976,13))
    def test_nsx_continuation_has_no_space_only_argument(self):
        from bs4 import BeautifulSoup
        import mistune
        p=ROOT/'docs/implementation/increment-04/06-transport-credentials-and-protected-evidence.md'
        codes=BeautifulSoup(mistune.html(p.read_text()),'html.parser').select('pre code')
        command=next(c.get_text() for c in codes if '/secure/nsx-expected.json' in c.get_text());command=command[command.index('python tools/nsx_observe.py /secure'):]
        self.assertIn('\\\n',command)
        argv=shlex.split(command.replace('\\\n',''))
        self.assertNotIn(' ',argv);self.assertEqual(len(argv),10)
        self.assertEqual(argv[3],'--read-authorized-target')
    def test_restored_historical_yaml_is_parseable(self):
        from bs4 import BeautifulSoup
        import mistune
        p=ROOT/'docs/archive/handbook-v1-1/71-appendix-b-worked-requests-and-terraform-execution-boundary.md'
        codes=BeautifulSoup(mistune.html(p.read_text()),'html.parser').select('pre code')
        docs=[yaml.safe_load(c.get_text()) for c in codes[:2]]
        self.assertEqual(docs[0]['kind'],'WorkloadSecurityDomain');self.assertEqual(docs[1]['kind'],'FlowIntent')
    def test_table_cell_swap_rejected(self):
        # Patch reads in memory: no delivered file is changed by the negative probe.
        original=Path.read_text
        path='docs/architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md'
        first='Declared public service through an external boundary; no direct attachment to internal workloads'
        second='Management-specific access boundary and privileged identity; never a workload transit shortcut'
        def changed(p,*a,**kw):
            text=original(p,*a,**kw)
            if str(p)==str(ROOT/path):text=text.replace(first,'__SWAP__').replace(second,first).replace('__SWAP__',second)
            return text
        with patch.object(Path,'read_text',changed):self.assertTrue(structure(ROOT)['errors'])


class DecisionLifecycleTests(unittest.TestCase):
    def setUp(self):self.records=json.loads((ROOT/'sources/documentation/adr_records.json').read_text());self.a=copy.deepcopy(self.records[3]);self.builder=Builder(ROOT)
    def test_current_proposals_are_not_auto_accepted(self):
        self.assertTrue(all(a['status']=='Proposed' for a in self.records));self.assertEqual(validate(self.records),[])
    def accepted(self,record):
        record['status']='Accepted';record['governance'].update(deciding_authority='Unit-test synthetic authority',decision_date='2026-01-01',decision_record='TEST-ONLY-DECISION-001',decision_rationale='Hypothetical test record; not actual organizational approval',evidence_refs=['TEST-ONLY-EVIDENCE-001'])
    def test_hypothetical_accepted_record_roundtrip(self):
        self.accepted(self.a);self.assertEqual(validate([self.a]),[])
        text=render(self.a,self.builder);self.assertIn('**Status:** Accepted',text);self.assertIn('Unit-test synthetic authority',text)
    def test_no_missing_authority_acceptance(self):
        self.a['status']='Accepted';self.assertTrue(validate([self.a]))
    def test_no_fake_placeholder_authority(self):
        self.accepted(self.a);self.a['governance']['deciding_authority']='NOT RECORDED';self.assertTrue(validate([self.a]))
    def test_date_must_be_real_not_future(self):
        self.accepted(self.a);self.a['governance']['decision_date']='2999-01-01';self.assertTrue(validate([self.a]))
    def test_rejected_requires_a_decision(self):
        self.a['status']='Rejected';self.assertTrue(validate([self.a]))
    def test_supersession_requires_accepted_successor(self):
        next_record=copy.deepcopy(self.a);next_record['id']='ADR-0099'
        self.accepted(self.a);self.a['status']='Superseded';self.a['governance']['superseded_by']='ADR-0099'
        self.assertTrue(validate([self.a,next_record]));self.accepted(next_record);self.assertEqual(validate([self.a,next_record]),[])
    def test_supersession_cycle_rejected(self):
        next_record=copy.deepcopy(self.a);next_record['id']='ADR-0099'
        for record,target in ((self.a,'ADR-0099'),(next_record,self.a['id'])):
            self.accepted(record);record['status']='Superseded';record['governance']['superseded_by']=target
        self.assertTrue(validate([self.a,next_record]))
    def test_actual_page_exactly_renders_source_fields(self):
        p=ROOT/self.builder.adrpath(self.a);self.assertEqual(p.read_text(),render(self.a,self.builder))
    def test_opposite_rendered_decision_is_not_accepted(self):
        p=ROOT/self.builder.adrpath(self.a);actual=p.read_text();wrong=actual.replace(self.a['decision'],'Use unrestricted transit instead of the required ZIP.')
        self.assertNotEqual(wrong,render(self.a,self.builder))
    def test_rendered_status_cannot_change_independently(self):
        text=render(self.a,self.builder);self.assertNotEqual(text.replace('**Status:** Proposed','**Status:** Accepted'),render(self.a,self.builder))
    def test_accountable_role_is_required(self):
        self.a['governance']['accountable_role']='';self.assertTrue(validate([self.a]))


class DesignAndAssuranceTests(unittest.TestCase):
    def test_current_workspace_complete(self):self.assertEqual(current_check(ROOT)['errors'],[])
    def test_ordinary_current_prose_revision_is_allowed(self):
        read=Path.read_text
        def edited(p,*a,**kw):
            text=read(p,*a,**kw)
            if p==ROOT/'docs/current/TAD-infrastructure.md':text=text.replace('A commissioned hosting cell provides','A qualified infrastructure cell supplies')
            return text
        with patch.object(Path,'read_text',edited):self.assertEqual(current_check(ROOT)['errors'],[])
    def test_current_missing_acceptance_cannot_pass(self):
        read=Path.read_text
        def edited(p,*a,**kw):
            text=read(p,*a,**kw)
            if p==ROOT/'sources/documentation/current_design_records.json':text=text.replace('"status": "Proposed"','"status": "Accepted"')
            return text
        with patch.object(Path,'read_text',edited):self.assertTrue(current_check(ROOT)['errors'])
    def test_source_refresh_cannot_target_current(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'sources/documentation').mkdir(parents=True)
            (root/'sources/documentation/source_inventory.json').write_text(json.dumps({'documents':[{'destination':'docs/current/unsafe'}]}))
            with self.assertRaises(ValueError):build(root)
    def test_all_requirements_and_test_families_allocated(self):
        r=allocation_check(ROOT);self.assertEqual(r['errors'],[]);self.assertEqual(r['requirements'],194);self.assertGreater(r['allocation_rows'],400)
    def test_mandatory_management_facets_are_separate(self):
        rows=json.loads((ROOT/'sources/assurance/implementation_assertions.json').read_text());facets=[r for r in rows if r['requirement_id']=='MGT-005'];self.assertGreaterEqual(len(facets),6)
        self.assertTrue(all('EXTERNAL' in r['implementation_disposition'] and 'NATIVE_NOT_RUN' in r['evidence_class'] for r in facets))
    def test_missing_original_scope_not_fabricated(self):
        d=json.loads((ROOT/'sources/documentation/source_scope_disposition.json').read_text())
        self.assertEqual(d['owner_acceptance'],'NOT_RECORDED');self.assertEqual(len(d['missing_originals']),8)
    def test_historical_closure_not_invented(self):
        import csv
        p=ROOT/'sources/assurance/historical_audit_dispositions.csv'
        with p.open(newline='') as f:rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),24);self.assertTrue(all(x['closure_status']=='NOT_CLOSED_BY_THIS_AUDIT' for x in rows))


class CurrentIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        subprocess.run(['git','init','-q',str(self.root)],check=True)
        (self.root/'one.txt').write_text('original\n')
        for args in [['add','.'],['-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','Synthetic local fixture']]:subprocess.run(['git','-C',str(self.root),*args],check=True)
    def test_fresh_checkout_passes_current_command(self):self.assertEqual(verify(self.root)['status'],'HASHES_MATCH')
    def test_modified_tracked_file_fails(self):
        (self.root/'one.txt').write_text('changed');self.assertTrue(verify(self.root)['issues'])
    def test_untracked_source_is_not_current_release(self):
        (self.root/'extra').write_text('uncommitted');self.assertTrue(verify(self.root)['issues'])
    def test_staged_difference_is_not_current_head(self):
        (self.root/'one.txt').write_text('changed');subprocess.run(['git','-C',str(self.root),'add','.'],check=True);self.assertTrue(verify(self.root)['issues'])
    def test_export_needs_explicit_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);(p/'x').write_text('x');self.assertEqual(verify(p)['status'],'BLOCKED_NO_CURRENT_CHECKOUT')
            manifest=p/'snapshot.json';manifest.write_text(json.dumps({'file_sha256':{'x':hashlib.sha256(b'x').hexdigest()}}))
            self.assertEqual(verify_snapshot(p,manifest)['status'],'HASHES_MATCH')
    def test_snapshot_traversal_is_rejected(self):
        p=self.root/'manifest.json';p.write_text(json.dumps({'file_sha256':{'../x':'bad'}}));self.assertTrue(verify_snapshot(self.root,p)['issues'])


class EngineBoundaryTests(unittest.TestCase):
    def test_root_schema_guard_and_lock_mode(self):
        import ast
        tree=ast.parse((ROOT/'tools/verify_terraform.py').read_text())
        guard=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.If) and ast.unparse(node.test)=="family == 'modules'" and any(isinstance(x,ast.Constant) and x.value=='schema' for x in ast.walk(node)):
                guard.append(node)
        self.assertEqual(len(guard),1)
        body=ast.get_source_segment((ROOT/'tools/verify_terraform.py').read_text(),guard[0])
        self.assertIn('NOT_RUN_ROOT_BACKEND_BOUNDARY',body)
        self.assertIn('-lockfile=readonly',(ROOT/'tools/verify_terraform.py').read_text())
    def test_actual_ci_generated_locks_exist_for_every_root(self):
        roots=ROOT/'terraform/roots'
        for root in roots.iterdir():
            if root.is_dir():
                text=(root/'.terraform.lock.hcl').read_text();self.assertIn('hashes = [',text);self.assertIn('registry.terraform.io/',text)
    def test_ansible_negative_timeout_not_success(self):
        text=(ROOT/'scripts/verify_ansible.py').read_text();self.assertIn('code not in (0,124,126)',text)


if __name__=='__main__':unittest.main()
