"""Main-merge regression coverage, not native controls or organizational approval."""
import copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import adr_lifecycle as adr
import documentation_controls as legacy
import check_current_design as current
import check_assurance_allocation as allocation
import check_documentation_integration as integration
import build_assurance_indexes
import build_assurance


class MainRecordIntegration(unittest.TestCase):
    def setUp(self):
        self.records=json.loads((ROOT/'sources/documentation/adr_records.json').read_text())
        self.record=copy.deepcopy(self.records[0])
    def test_proposed_decision_authority_rejected(self):
        self.record['governance']['deciding_authority']='Synthetic authority';self.assertTrue(adr.validate([self.record]))
    def test_proposed_evidence_rejected(self):
        self.record['governance']['evidence_refs']=['TEST-ONLY'];self.assertTrue(adr.validate([self.record]))
    def test_obsolete_acceptance_alias_rejected(self):
        self.record['governance']['accepting_authority']='Synthetic authority';self.assertTrue(adr.validate([self.record]))
    def test_obsolete_supersedes_list_rejected(self):
        self.record['governance']['supersedes']=[];self.assertTrue(adr.validate([self.record]))
    def test_legacy_renderer_delegates_without_translation(self):
        from build_documentation import Builder
        b=Builder(ROOT);self.assertEqual(legacy.adr_text(b,self.record),adr.render(self.record,b))
        self.assertIs(legacy.lifecycle_errors,adr.validate)
    def test_malformed_governance_returns_errors(self):
        for bad in (None,[],True,'bad'):
            with self.subTest(value=bad):
                self.record['governance']=bad;self.assertTrue(adr.validate([self.record]))
    def test_malformed_record_list_returns_errors(self):
        for bad in (None,{},[],[None],[{'id':[]}],True):
            with self.subTest(value=bad):self.assertTrue(adr.validate(bad))
    def test_malformed_status_returns_errors(self):
        self.record['status']=[];self.assertTrue(adr.validate([self.record]))
    def test_malformed_successor_returns_errors(self):
        self.record['governance']['superseded_by']=[];self.assertTrue(adr.validate([self.record]))
    def test_malformed_evidence_returns_errors(self):
        self.record['governance']['evidence_refs']=[{}];self.assertTrue(adr.validate([self.record]))
    def test_duplicate_record_rejected(self):self.assertTrue(adr.validate([self.record,self.record]))
    def test_all_actual_records_keep_original_proposed_state(self):
        self.assertTrue(all(x['status']=='Proposed' for x in self.records));self.assertEqual(adr.validate(self.records),[])


class MainPublicationIntegration(unittest.TestCase):
    def mutate_read(self,path,mutator):
        original=Path.read_text
        def changed(p,*args,**kwargs):
            text=original(p,*args,**kwargs)
            return mutator(text) if p==ROOT/path else text
        return patch.object(Path,'read_text',changed)
    def test_single_authority_gate_passes(self):self.assertEqual(integration.check(ROOT)['errors'],[])
    def test_retired_authoring_command_never_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=subprocess.run([sys.executable,str(ROOT/'scripts/record_doc_amendment.py'),'RA','177','--write-record'],
                             cwd=tmp,capture_output=True,text=True,timeout=10)
            self.assertEqual(p.returncode,2);self.assertIn('RETIRED_AUTHORING_MODEL',p.stderr)
            self.assertEqual(list(Path(tmp).iterdir()),[])
    def test_old_builder_is_same_callable(self):self.assertIs(build_assurance.build,build_assurance_indexes.build)
    def test_retired_amendment_cannot_become_active(self):
        with self.mutate_read('sources/documentation/amendments.json',lambda _: '[{"status":"Accepted"}]'):
            self.assertTrue(integration.check(ROOT)['errors'])
    def test_alias_cannot_become_a_second_decision(self):
        record=json.loads((ROOT/'sources/documentation/integration_authority.json').read_text())['path_aliases'][0]
        with self.mutate_read(record['path'],lambda s:s+'\n**Status:** Accepted\n'):
            self.assertTrue(integration.check(ROOT)['errors'])
    def test_unregistered_duplicate_adr_rejected(self):
        original=Path.glob
        def extra(p,pattern):
            result=list(original(p,pattern))
            if p==ROOT/'docs/adr':result.append(p/'0037-unregistered-second-decision.md')
            return iter(result)
        with patch.object(Path,'glob',extra):self.assertTrue(integration.check(ROOT)['errors'])
    def test_historical_view_cannot_claim_current_authority(self):
        with self.mutate_read('docs/assurance/implementation-allocation.md',lambda s:s.replace('<!-- RETAINED-HISTORICAL-PROPOSAL -->','')):
            self.assertTrue(integration.check(ROOT)['errors'])
    def test_current_header_status_change_rejected(self):
        with self.mutate_read('docs/current/TAD-infrastructure.md',lambda s:s.replace('**Status:** Proposed','**Status:** Accepted')):
            self.assertTrue(current.check(ROOT)['errors'])
    def test_current_header_owner_change_rejected(self):
        with self.mutate_read('docs/current/TAD-infrastructure.md',lambda s:s.replace('**Accountable role:** Platform, network and security engineering.','**Accountable role:** Unassigned.')):
            self.assertTrue(current.check(ROOT)['errors'])
    def test_current_header_version_change_rejected(self):
        with self.mutate_read('docs/current/TAD-infrastructure.md',lambda s:s.replace('**Version:** 0.1','**Version:** 0.2')):
            self.assertTrue(current.check(ROOT)['errors'])
    def test_current_prose_can_evolve_without_source_amendments(self):
        with self.mutate_read('docs/current/TAD-infrastructure.md',lambda s:s.replace('## Design content','## Design content\n\nProposed engineering refinement for review.')):
            self.assertEqual(current.check(ROOT)['errors'],[])


class OriginalVerificationAssociations(unittest.TestCase):
    def setUp(self):self.index=json.loads((ROOT/'sources/assurance/verification_families.json').read_text())
    def test_current_original_mappings_agree(self):self.assertEqual(allocation.verification_errors(ROOT,self.index),[])
    def test_different_valid_ct_reference_rejected(self):
        self.index['supplemental_mappings'][0]['base_tests']=['CT-001'];self.assertTrue(allocation.verification_errors(ROOT,self.index))
    def test_count_only_match_cannot_mask_missing_record(self):
        self.index['supplemental_mappings'].pop();self.assertTrue(allocation.verification_errors(ROOT,self.index))
    def test_original_worked_assertion_change_rejected(self):
        row=next(r for r in self.index['supplemental_mappings'] if r['family']=='W14')
        row['original_record']['assertion']='Changed relationship';self.assertTrue(allocation.verification_errors(ROOT,self.index))
    def test_promoting_specification_to_passed_rejected(self):
        self.index['supplemental_mappings'][0]['execution_status']='passed';self.assertTrue(allocation.verification_errors(ROOT,self.index))
    def test_count_boolean_is_not_integer(self):
        self.index['families']['RA']=True;self.assertTrue(allocation.verification_errors(ROOT,self.index))


if __name__=='__main__':unittest.main()
