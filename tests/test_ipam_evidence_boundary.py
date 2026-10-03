"""Read-only IPAM export boundaries; no allocation-service or native contact."""
from __future__ import annotations

from contextlib import contextmanager, redirect_stdout
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from provisioner import repository
from provisioner.allocations import ipam_evidence as records
from tests.test_ipam_allocation_handoff import AS_OF, allocation_index, allocation_record


class IPAMEvidenceBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name); self.path=self.root/'index.json'
        self.document=records.load(); self.raw=json.dumps(self.document).encode('utf-8')
        self.path.write_bytes(self.raw)

    def test_regular_export_is_read_without_mutation_or_shared_cache(self):
        self.assertEqual(records.load(self.path),self.document)
        value=records.load(self.path); value['records'].append({'not':'shared'})
        self.assertEqual(records.load(self.path),self.document)
        self.assertEqual(self.path.read_bytes(),self.raw)

    def test_canonical_confirmation_digest_is_unchanged(self):
        value=allocation_record('CONFIRMED')
        result=records.validate(allocation_index(value),as_of=AS_OF)['records'][0]
        expected=hashlib.sha256(json.dumps({
            'allocation_id':value['allocation_id'],'operation_id':value['operation_id'],
            'generation':value['generation'],'reservation_id':value['reservation_id'],
            'request_id':value['request_id'],'wsd_engineering_ref':value['wsd_engineering_ref'],
            'intent_sha256':value['intent_sha256'],'allocation_policy':value['allocation_policy'],
            'overlap_exception_ref':value['overlap_exception_ref'],'family':value['family'],
            'allocation_kind':value['allocation_kind'],'requested_prefix_length':value['requested_prefix_length'],
            'delegated_scope_ref':value['delegated_scope_ref'],
            'authoritative_system':{'system_ref':value['authoritative_system']['system_ref'],
                                    'record_ref':value['authoritative_system']['record_ref']},
            'allocation_ref':value['allocation_ref'],'confirmed_at':result['confirmed_at'],
            'realization_ref':value['realization_ref']},sort_keys=True,separators=(',',':'),
            ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()
        self.assertEqual(result['confirmation_sha256'],expected)

    def test_lifecycle_semantics_survive_relocation(self):
        for state in records.STATES:
            value=allocation_record(state)
            if state=='UNCERTAIN':
                value['hold_expires_at']='2026-09-18T18:10:00Z'
            result=records.validate(allocation_index(value),as_of=AS_OF)
            self.assertEqual(result['records'][0]['state'],state)
            self.assertEqual(result['unresolved_count'],int(state=='UNCERTAIN'))

    def test_empty_oversized_missing_directory_and_device_fail_without_fallback(self):
        for raw in (b'',b' '*(records.MAX_INDEX_BYTES+1)):
            self.path.write_bytes(raw)
            with self.assertRaises(ValueError): records.load(self.path)
        self.path.unlink()
        with self.assertRaises(FileNotFoundError): records.load(self.path)
        with self.assertRaises((ValueError,OSError)): records.load(self.root)
        if os.name=='posix':
            with self.assertRaises(ValueError): records.load(Path('/dev/null'))

    def test_exact_file_size_bound_has_no_off_by_one(self):
        self.path.write_bytes(b'{}'+b' '*(records.MAX_INDEX_BYTES-2))
        self.assertEqual(records.load(self.path),{})
        with self.path.open('ab') as stream: stream.write(b' ')
        with self.assertRaises(ValueError): records.load(self.path)

    def test_duplicate_nonfinite_malformed_and_excessive_nesting_fail_closed(self):
        for raw in (b'{"x":1,"x":2}',b'{"x":{"k":1,"k":2}}',b'{"x":NaN}',
                    b'{"x":Infinity}',b'{"x":1e999}',b'\xff',b'[]',b'null',b'{} {}'):
            self.path.write_bytes(raw)
            with self.subTest(raw=raw),self.assertRaises(ValueError): records.load(self.path)
        self.path.write_bytes(b'{"x":'+b'['*2000+b'0'+b']'*2000+b'}')
        out=io.StringIO()
        with redirect_stdout(out): code=records.main(['--index',str(self.path)])
        self.assertEqual(code,2); self.assertEqual(json.loads(out.getvalue())['status'],'FAILED_EXPORTED_AUTHORITATIVE_IPAM_RECORDS')
        self.assertNotIn('Traceback',out.getvalue())

    @unittest.skipUnless(hasattr(os,'mkfifo'),'POSIX FIFO boundary')
    def test_fifo_is_rejected_without_waiting(self):
        self.path.unlink(); os.mkfifo(self.path)
        run=subprocess.run([sys.executable,'-m','provisioner.allocations.ipam_evidence','--index',str(self.path)],
            cwd=records.ROOT,capture_output=True,text=True,timeout=5)
        self.assertEqual(run.returncode,2,run.stdout+run.stderr)
        self.assertEqual(json.loads(run.stdout)['status'],'FAILED_EXPORTED_AUTHORITATIVE_IPAM_RECORDS')

    def test_final_link_and_linked_ancestor_are_rejected(self):
        alias=self.root/'alias.json'; alias.symlink_to(self.path)
        with self.assertRaises(ValueError): records.load(alias)
        directory=self.root/'linked'; directory.symlink_to(self.root,target_is_directory=True)
        with self.assertRaises(ValueError): records.load(directory/self.path.name)

    def test_observed_mutation_and_path_replacement_are_rejected(self):
        fdopen=os.fdopen
        for replacement in (False,True):
            self.path.write_bytes(self.raw)
            @contextmanager
            def changed(*args,**kwargs):
                with fdopen(*args,**kwargs) as stream:
                    yield stream
                    if replacement:
                        other=self.root/'replacement'; other.write_bytes(self.raw); other.replace(self.path)
                    else:self.path.write_bytes(self.raw+b' ')
            with self.subTest(replacement=replacement),patch.object(records.os,'fdopen',changed):
                with self.assertRaises((ValueError,OSError)): records.load(self.path)

    def test_repository_reference_is_exact_regular_and_unlinked(self):
        (self.root/'docs').mkdir(); (self.root/'docs/evidence.md').write_text('synthetic')
        self.assertEqual(records.repository_ref('docs/evidence.md',self.root),'docs/evidence.md')
        for value in ('./docs/evidence.md','docs//evidence.md','docs/../docs/evidence.md','docs/evidence.md/',
                      'docs\\evidence.md','../outside','C:/file',str(self.root/'docs/evidence.md'),'docs','.','missing.md'):
            with self.subTest(value=value),self.assertRaises(ValueError): records.repository_ref(value,self.root)
        target=self.root/'actual'; target.mkdir(); (target/'evidence').write_text('synthetic')
        (self.root/'link').symlink_to(target,target_is_directory=True)
        with self.assertRaises(ValueError): records.repository_ref('link/evidence',self.root)

    def test_retired_import_absent_and_consumers_share_owner(self):
        from provisioner.allocations import ipam_preflight as check_ipam_allocation_preflight, dns_preflight as check_dns_registration_preflight
        from provisioner.allocations import dns_evidence as check_dns_registration_records
        self.assertIsNone(importlib.util.find_spec('scripts.check_ipam_allocation_records'))
        self.assertIs(check_ipam_allocation_preflight.ipam,records)
        self.assertIs(check_dns_registration_records.ipam,records)
        self.assertIs(check_dns_registration_preflight.ipam,records)
        with patch.object(records,'load',return_value=self.document) as loaded:
            self.assertIs(repository.ipam_allocation_records(),self.document); loaded.assert_called_once_with(records.INDEX)
        self.assertEqual(records.load.__module__,'provisioner.allocations.ipam_evidence')

    def test_reading_exports_never_opens_network_connections(self):
        with patch('socket.socket',side_effect=AssertionError('No IPAM contact')):
            result=records.validate(records.load(self.path),as_of=AS_OF)
        self.assertEqual(result['record_count'],0)


if __name__=='__main__': unittest.main()
