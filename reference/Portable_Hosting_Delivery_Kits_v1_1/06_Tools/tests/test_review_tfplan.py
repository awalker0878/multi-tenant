import importlib.util
import json
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('planreview',Path(__file__).resolve().parents[1]/'review_tfplan.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def fixture(actions=None):
 changes=[] if actions is None else [{'address':'test_resource.example','change':{'actions':actions,'before':{'password':'SENTINEL-NOT-TO-PRINT'},'after':{'password':'SENTINEL-NOT-TO-PRINT'}}}]
 return {'format_version':'1.2','planned_values':{},'resource_changes':changes}
class ReviewTests(unittest.TestCase):
 def test_empty_array_is_metadata_only(self):
  r=m.review(fixture());self.assertEqual(r['resource_count'],0);self.assertIn('NOT EVALUATED',r['authorization'])
 def test_create_does_not_approve(self):
  r=m.review(fixture(['create']));self.assertEqual(r['review_triggers'],[]);self.assertIn('still required',r['summary'])
 def test_values_never_printed(self):
  self.assertNotIn('SENTINEL',json.dumps(m.review(fixture(['create']))))
 def test_delete_flagged(self):
  self.assertEqual(m.review(fixture(['delete']))['review_triggers'][0]['trigger'],'deletion')
 def test_replace_flagged(self):
  for actions in [['delete','create'],['create','delete']]:self.assertEqual(m.review(fixture(actions))['review_triggers'][0]['trigger'],'replacement')
 def test_forget_flagged(self):
  self.assertEqual(m.review(fixture(['forget']))['review_triggers'][0]['trigger'],'management removed')
 def test_unknown_flagged(self):
  p=fixture(['update']);p['resource_changes'][0]['change']['after_unknown']={'password':True};self.assertEqual(len(m.review(p)['review_triggers']),1)
 def test_drift_flagged(self):
  p=fixture();p['resource_drift']=[{}];self.assertEqual(m.review(p)['review_triggers'][0]['trigger'],'drift present')
 def test_incomplete_and_deferred_flagged(self):
  p=fixture();p.update(complete=False,deferred_changes=[{}]);self.assertEqual(len(m.review(p)['review_triggers']),2)
 def test_malformed_root(self):
  with self.assertRaises(m.PlanError):m.review([])
 def test_missing_changes_is_not_empty_success(self):
  p=fixture();del p['resource_changes']
  with self.assertRaises(m.PlanError):m.review(p)
 def test_bad_action(self):
  with self.assertRaises(m.PlanError):m.review(fixture(['deploy']))
 def test_duplicate_address(self):
  p=fixture(['update']);p['resource_changes']*=2
  with self.assertRaises(m.PlanError):m.review(p)
 def test_format_major(self):
  p=fixture();p['format_version']='2.0'
  with self.assertRaises(m.PlanError):m.review(p)
 def test_state_not_plan(self):
  with self.assertRaises(m.PlanError):m.review({'format_version':'1.0','values':{}})
 def test_invalid_actions_container(self):
  p=fixture(['create']);p['resource_changes'][0]['change']['actions']='create'
  with self.assertRaises(m.PlanError):m.review(p)
if __name__=='__main__':unittest.main()
