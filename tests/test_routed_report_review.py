"""Offline integrity and completeness checks, not native packet observations."""
from __future__ import annotations
from pathlib import Path
import tempfile
import unittest
from lab import ipv6_fixture as f


class ReportCompletenessTests(unittest.TestCase):
    """Synthetic reports test rejection logic, never count as executed packet proof."""
    def setUp(self):
        import hashlib
        from scripts import check_routed_lab_results as review
        self.review=review
        self.report={'kind':'LOCAL_ROUTED_IPV6_PACKET_FIXTURE','status':'PASSED_IPV6_FIXTURE',
            'passed':49,'failed':0,'namespace_count':17,'native_vendor_qualification':'NOT_RUN','native_apply':'NOT_RUN',
            'fixture_sha256':f.FIXTURE_SHA256,'original_namespace_configuration_unchanged':True,
            'original_configuration_sha256_before':'a'*64,'original_configuration_sha256_after':'a'*64,
            'source_sha256':{p:hashlib.sha256((f.ROOT/p).read_bytes()).hexdigest() for p in review.SOURCES[6]},
            'checks':[{'id':f'IP6-{i:03}','name':'Synthetic checker-only case','status':'PASS','observed':{}} for i in range(1,50)]}
        self.report['checks'][38]['observed']={'large':{'success':True,'path_mtu':1280,'bytes_echoed':8192},'before':{'related_error':0},'after':{'related_error':1}}
    def test_expected_shape(self):self.assertEqual(self.review.validate(self.report,6)['observations'],49)
    def test_label_without_observations(self):
        self.report['checks']=[]
        with self.assertRaises(ValueError):self.review.validate(self.report,6)
    def test_partial_run(self):
        self.report['checks'].pop()
        with self.assertRaises(ValueError):self.review.validate(self.report,6)
    def test_failed_observation(self):
        self.report['checks'][1]['status']='FAIL'
        with self.assertRaises(ValueError):self.review.validate(self.report,6)
    def test_duplicate_id(self):
        self.report['checks'][1]['id']='IP6-001'
        with self.assertRaises(ValueError):self.review.validate(self.report,6)
    def test_wrong_source(self):
        self.report['source_sha256']['lab/ipv6_fixture.py']='0'*64
        with self.assertRaises(ValueError):self.review.validate(self.report,6)
    def test_incomplete_source_set(self):
        self.report['source_sha256'].pop('lab/ipv6_worker.py')
        with self.assertRaises(ValueError):self.review.validate(self.report,6)
    def test_modified_original_namespace(self):
        self.report['original_namespace_configuration_unchanged']=False
        with self.assertRaises(ValueError):self.review.validate(self.report,6)
    def test_mismatched_original_digest(self):
        self.report['original_configuration_sha256_after']='b'*64
        with self.assertRaises(ValueError):self.review.validate(self.report,6)
    def test_native_qualification_label_refused(self):
        self.report['native_vendor_qualification']='QUALIFIED'
        with self.assertRaises(ValueError):self.review.validate(self.report,6)
    def test_bool_not_number(self):
        self.report['failed']=False
        with self.assertRaises(ValueError):self.review.validate(self.report,6)
    def test_no_large_path_mtu_witness(self):
        self.report['checks'][38]['observed']['large']['path_mtu']=1500
        with self.assertRaises(ValueError):self.review.validate(self.report,6)
    def test_blocked_report_refused(self):
        self.report['status']='BLOCKED_RUNTIME'
        with self.assertRaises(ValueError):self.review.validate(self.report,6)
    def test_duplicate_json_report_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'report.json';p.write_text('{"status":"FAIL","status":"PASS"}')
            with self.assertRaises(ValueError):self.review.load(p)


if __name__=='__main__':unittest.main()
