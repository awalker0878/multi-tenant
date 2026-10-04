"""Pending old workflows cannot starve later scoped completion readback."""
from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from provisioner.controlplane.jobs import StartReceipt
from provisioner.controlplane.persistence import TenantContext
from provisioner.controlplane.workflow.approval_gate import GateResult
from provisioner.controlplane.workflow.runtime import (
    ProjectionCursor, _pending_jobs, project_batch)


class ProjectionFairnessTests(unittest.TestCase):
    def setUp(self):
        self.context=TenantContext('org','tenant')
        self.at=datetime(2026,1,1,tzinfo=timezone.utc)
        self.active={f'job-{number:03d}':ProjectionCursor(self.at,f'job-{number:03d}')
                     for number in range(40)}
        self.completed=set(); self.checked=[]; self.events=[]; self.queries=[]
        outer=self
        class Jobs:
            def start_run(self,context,job_id):
                outer.assertEqual(context,outer.context)
                outer.checked.append(job_id)
                return StartReceipt('ns',job_id,'run-'+job_id,job_id,'plan',1,'a'*64,'b'*64)
            def append_progress(self,context,job_id,**event):
                outer.events.append((job_id,event)); outer.active.pop(job_id,None)
        self.jobs=Jobs()
        def completed_job(receipt):
            if receipt.job_id not in self.completed: return None
            return GateResult('GATE_PASSED',receipt.job_id,'plan',1,'a'*64,'approval','c'*64)
        self.workflow=SimpleNamespace(completed_job=completed_job)
        def pending(context,*,limit=32,after=None,through=None,newest_first=False):
            self.assertEqual(context,self.context)
            self.queries.append((after,through,newest_first))
            key=lambda row:(row.created_at,row.job_id)
            return tuple(row for row in sorted(self.active.values(),key=key,reverse=newest_first)
                         if (after is None or key(row)>key(after))
                         and (through is None or key(row)<=key(through)))[:limit]
        mock=patch('provisioner.controlplane.workflow.runtime._pending_jobs',side_effect=pending)
        mock.start(); self.addCleanup(mock.stop)

    def batch(self,previous=None):
        return project_batch(self.jobs,self.workflow,self.context,
            after=previous.next_cursor if previous else None,
            through=previous.upper_bound if previous else None)

    def test_first_32_pending_workflows_do_not_starve_later_completions(self):
        self.completed={f'job-{number:03d}' for number in range(32,40)}
        first=self.batch()
        self.assertEqual(first.checked,32); self.assertFalse(first.progressed)
        self.assertEqual(self.events,[])
        second=self.batch(first)
        self.assertEqual(second.checked,8); self.assertTrue(second.progressed)
        self.assertEqual({job for job,_ in self.events},self.completed)
        self.assertIsNone(second.next_cursor)
        third=self.batch(second)
        self.assertEqual(third.checked,32); self.assertFalse(third.progressed)
        self.assertTrue(all(event['status']=='HELD' for _,event in self.events))

    def test_an_early_completed_job_does_not_short_circuit_the_rest_of_its_page(self):
        self.completed=set(self.active)
        first=self.batch()
        self.assertEqual(first.checked,32); self.assertEqual(len(self.events),32)
        second=self.batch(first)
        self.assertEqual(second.checked,8); self.assertEqual(len(self.events),40)
        self.assertEqual(len(set(self.checked)),40)

    def test_removing_completed_rows_does_not_shift_the_cursor_or_skip_later_jobs(self):
        self.completed={'job-000','job-032','job-039'}
        first=self.batch(); second=self.batch(first)
        self.assertEqual(self.checked,list(f'job-{number:03d}' for number in range(40)))
        self.assertEqual({job for job,_ in self.events},self.completed)
        self.assertIsNone(second.next_cursor)

    def test_an_empty_tail_finishes_the_pass_then_rechecks_earlier_pending_jobs(self):
        first=self.batch()
        for number in range(32,40): self.active.pop(f'job-{number:03d}')
        tail=self.batch(first)
        self.assertEqual(tail.checked,0)
        self.assertIsNone(tail.next_cursor); self.assertIsNone(tail.upper_bound)
        result=self.batch(tail)
        self.assertEqual(result.checked,32)
        self.assertEqual(self.checked.count('job-000'),2)

    def test_continuous_arrivals_cannot_prevent_revisiting_an_older_pending_job(self):
        first=self.batch()
        self.assertEqual(first.upper_bound,ProjectionCursor(self.at,'job-039'))
        self.completed.add('job-000')
        # More than a page arrives after every scan. Without a fixed pass bound,
        # each following page stays full and the original job is never revisited.
        for number in range(40,80):
            key=f'job-{number:03d}'; self.active[key]=ProjectionCursor(self.at,key)
        second=self.batch(first)
        self.assertEqual(second.checked,8)
        self.assertIsNone(second.next_cursor); self.assertIsNone(second.upper_bound)
        for number in range(80,120):
            key=f'job-{number:03d}'; self.active[key]=ProjectionCursor(self.at,key)
        third=self.batch(second)
        self.assertEqual(third.checked,32)
        self.assertEqual(self.checked.count('job-000'),2)
        self.assertEqual([job for job,_ in self.events],['job-000'])
        self.assertEqual(third.upper_bound,ProjectionCursor(self.at,'job-119'))

    def test_reaching_a_full_final_page_wraps_without_an_extra_tail_query(self):
        self.active={key:row for key,row in self.active.items() if key<'job-032'}
        result=self.batch()
        self.assertEqual(result.checked,32)
        self.assertIsNone(result.next_cursor); self.assertIsNone(result.upper_bound)

    def test_no_jobs_is_a_bounded_idle_result(self):
        self.active.clear(); result=self.batch()
        self.assertEqual(result.checked,0); self.assertFalse(result.progressed)
        self.assertIsNone(result.next_cursor); self.assertEqual(self.checked,[])


class ProjectionQueryTests(unittest.TestCase):
    def test_query_uses_scoped_stable_keyset_order_and_bound_parameters(self):
        context=TenantContext('org','tenant'); at=datetime(2026,1,1,tzinfo=timezone.utc)
        after=ProjectionCursor(at,"job'; DROP TABLE jobs; --")
        through=ProjectionCursor(at,'job-999')
        recorded=[]
        class Cursor:
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def execute(self,query,parameters): recorded.append((query,parameters))
            def fetchall(self): return [('job-040',at)]
        cursor=Cursor()
        class Connection:
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def cursor(self): return cursor
        with patch('provisioner.controlplane.workflow.runtime._connect',return_value=Connection()), \
             patch('provisioner.controlplane.workflow.runtime._tenant') as tenant:
            result=_pending_jobs(context,limit=32,after=after,through=through)
            _pending_jobs(context,limit=1,newest_first=True)
        self.assertEqual(tenant.call_count,2)
        tenant.assert_called_with(cursor,context)
        query,parameters=recorded[0]
        self.assertIn('j.organization_id = %s AND j.tenant_id = %s',query)
        self.assertIn('(j.created_at, j.job_id) > (%s, %s)',query)
        self.assertIn('(j.created_at, j.job_id) <= (%s, %s)',query)
        self.assertIn('ORDER BY j.created_at, j.job_id LIMIT %s',query)
        self.assertNotIn(after.job_id,query)
        self.assertEqual(parameters,('org','tenant',at,after.job_id,at,through.job_id,32))
        self.assertEqual(result,(ProjectionCursor(at,'job-040'),))
        bound_query,bound_parameters=recorded[1]
        self.assertIn('j.organization_id = %s AND j.tenant_id = %s',bound_query)
        self.assertIn('ORDER BY j.created_at DESC, j.job_id DESC LIMIT %s',bound_query)
        self.assertEqual(bound_parameters,('org','tenant',1))

    def test_invalid_page_bound_fails_before_database_contact(self):
        with patch('provisioner.controlplane.workflow.runtime._connect') as connect:
            for limit in (0,129,True,-1):
                with self.subTest(limit=limit),self.assertRaises(ValueError):
                    _pending_jobs(TenantContext('org','tenant'),limit=limit)
        connect.assert_not_called()


if __name__=='__main__': unittest.main()
