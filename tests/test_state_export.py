"""Private versioned state export over real TLS; no native state write path."""
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit

from tests import test_state_project as p
from tools import state_export as d,readback_core as c
from tools.run_files import digest,load_private


class StateExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p.StateProjectTests.setUpClass.__func__(cls)
        handler=cls.server.RequestHandlerClass; original=handler.do_GET
        def get(handler):
            if '/terraform/state/' not in handler.path: return original(handler)
            cls.calls.append((handler.command,handler.path,handler.headers.get('Authorization')))
            path=handler.path.split('/versions/')[0]; row=deepcopy(cls.states.get(path))
            if row is None: return handler.reply({},404)
            if '/versions/' in handler.path:
                if cls.version_differs: row['serial']+=1
                if not handler.path.endswith('/'+str(row['serial'])): return handler.reply({},404)
            else:
                cls.reads[path]=cls.reads.get(path,0)+1
                if cls.change_latest and cls.reads[path]>1: row['serial']+=1
                if cls.fail_latest and len(cls.reads)>1: return handler.reply({},503)
            return handler.reply(row)
        handler.do_GET=get
    @classmethod
    def tearDownClass(cls): p.StateProjectTests.tearDownClass.__func__(cls)
    def setUp(self):
        p.StateProjectTests.setUp(self)
        self.project=self.request
        self.receipt=p.d.operate(self.project,p.StateProjectTests.authority(self,'create'),self.token,self.ledger,
                                action='create',ca_file=self.ca,client=self.client)
        cls=type(self); cls.states={}; cls.reads={}; cls.change_latest=False; cls.version_differs=False; cls.fail_latest=False
        expected=[]
        for n,(key,backend) in enumerate(sorted(self.receipt['backends'].items()),1):
            lineage=f'00000000-0000-4000-8000-{n:012d}'
            cls.states[urlsplit(backend['address']).path]=dict(version=4,terraform_version='1.13.5',serial=5,lineage=lineage,
                outputs={'private':{'value':'TEST-SECRET-'+str(n),'type':'string','sensitive':True}},resources=[])
            expected.append(dict(state_key=key,lineage=lineage,minimum_serial=5))
        self.request=dict(format='hosting-state-export/1',enabled=True,source_commit='a'*40,operation_id='export-1',
            project_request_sha256=c.digest(self.project),project_receipt_sha256=c.digest(self.receipt),reader_id=2,
            states=expected,consistency_ref='TEST-QUIESCENCE',protection_ref='TEST-RESTIC-CUSTODY',output=str(self.ledger/'capture'))
        cls.actor['id']=2; cls.calls=[]
        check=patch.object(d,'verify',return_value={'status':'HASHES_MATCH','commit':'a'*40}); check.start(); self.addCleanup(check.stop)
    def authority(self):
        return dict(format='hosting-state-export-authority/1',request_sha256=c.digest(self.request),
            valid_from=p.utcnow().isoformat(),valid_until=(p.utcnow()+p.timedelta(minutes=10)).isoformat(),
            change_ref='TEST-EXPORT',token_sha256=digest(self.token),ca_sha256=digest(self.ca.read_bytes()))
    def capture(self,**kwargs):
        return d.capture(self.request,self.project,self.receipt,self.authority(),self.token,ca_file=self.ca,client=self.client,**kwargs)

    def test_versioned_capture_and_completed_reuse_are_private_readonly_and_historical(self):
        result=self.capture(); self.assertEqual(result['status'],'STATE_EXPORT_OBSERVED_REQUIRES_PROTECTION')
        self.assertFalse(result['state_written']); self.assertFalse(result['independent_backup_verified'])
        for state in result['states']:
            path=Path(result['export'])/state['file']; self.assertEqual(load_private(path)['lineage'],state['lineage'])
            self.assertEqual(path.stat().st_mode & 0o777,0o600)
        before=list(self.calls); self.assertEqual(self.capture(),result); self.assertEqual(self.calls,before)
        self.assertTrue(all(method=='GET' for method,_,_ in self.calls))
        self.assertEqual(len([path for _,path,_ in self.calls if '/versions/5' in path]),2)
        self.assertEqual(load_private(Path(result['export'])/'index.json')['states'],result['states'])

    def test_partial_capture_retries_only_reads_into_a_new_retained_attempt(self):
        cls=type(self); cls.fail_latest=True
        with self.assertRaises(p.HTTPError): self.capture()
        first=Path(self.request['output'])/'attempts/0001/export'
        self.assertEqual(len(list(first.glob('*.tfstate'))),1)
        original=next(first.glob('*.tfstate')).read_bytes(); cls.fail_latest=False
        result=self.capture(); self.assertIn('/0002/export',result['export'])
        self.assertEqual(next(first.glob('*.tfstate')).read_bytes(),original)
        self.assertTrue(all(method=='GET' for method,_,_ in self.calls))

    def test_lineage_change_serial_regression_missing_or_incompatible_state_hold(self):
        cls=type(self); path=next(iter(cls.states)); original=deepcopy(cls.states[path])
        for changes in ({'lineage':'00000000-0000-4000-8000-999999999999'},{'serial':4},
                        {'terraform_version':'1.12.0'},{'version':3}):
            cls.states[path]=original|changes
            with self.subTest(changes=changes),self.assertRaises(ValueError): self.capture()
        cls.states.pop(path)
        with self.assertRaisesRegex(ValueError,'Required state is missing'): self.capture()
        self.assertFalse((Path(self.request['output'])/'receipt.json').exists())

    def test_version_disagreement_and_changes_during_second_sweep_hold(self):
        type(self).version_differs=True
        with self.assertRaises(p.HTTPError): self.capture()
        type(self).version_differs=False; type(self).change_latest=True; type(self).reads={}
        with self.assertRaisesRegex(ValueError,'changed during export'): self.capture()
        self.assertFalse((Path(self.request['output'])/'receipt.json').exists())

    def test_explicit_unused_state_requires_absence_in_both_sweeps(self):
        state=self.request['states'][1]; state['lineage']=None; state['minimum_serial']=None
        with self.assertRaisesRegex(ValueError,'unused state slot'): self.capture()
        path=urlsplit(self.receipt['backends'][state['state_key']]['address']).path; type(self).states.pop(path)
        result=self.capture(); self.assertEqual(result['states'][1]['status'],'UNUSED_ABSENCE_OBSERVED')
        self.assertEqual(len(list(Path(result['export']).glob('*.tfstate'))),1)

    def test_changed_completed_export_is_held_without_native_reads_or_overwrite(self):
        result=self.capture(); path=Path(result['export'])/result['states'][0]['file']; path.write_bytes(b'CHANGED')
        before=list(self.calls)
        with self.assertRaisesRegex(ValueError,'export bytes changed'): self.capture()
        self.assertEqual(self.calls,before); self.assertEqual(path.read_bytes(),b'CHANGED')

    def test_project_restriction_or_reader_drift_prevents_state_read(self):
        type(self).project['visibility']='public'
        with self.assertRaisesRegex(ValueError,'restrictions differ'): self.capture()
        type(self).project['visibility']='private'; type(self).actor['id']=3
        with self.assertRaisesRegex(ValueError,'Wrong state export reader'): self.capture()
        self.assertFalse(any('/terraform/state/' in path for _,path,_ in self.calls))

    def test_incomplete_scope_handoff_or_authority_cannot_contact(self):
        original=deepcopy(self.request)
        for changes in ({'states':original['states'][:1]},{'project_receipt_sha256':'b'*64},{'reader_id':99}):
            with self.subTest(changes=list(changes)),self.assertRaises(ValueError): d.validate(original|changes,self.project,self.receipt)
        with self.assertRaises(ValueError):
            d.capture(self.request,self.project,self.receipt,self.authority()|{'token_sha256':'c'*64},self.token,
                      ca_file=self.ca,client=self.client)
        self.assertEqual(self.calls,[])

    def test_changed_request_or_symlink_does_not_adopt_a_partial_export(self):
        type(self).fail_latest=True
        with self.assertRaises(p.HTTPError): self.capture()
        self.request['operation_id']='renamed'
        with self.assertRaisesRegex(ValueError,'operation identity changed'): self.capture()
        self.request['operation_id']='export-1'; type(self).fail_latest=False
        directory=Path(self.request['output'])/'attempts/0001/export'; (directory/'foreign').symlink_to(self.ca)
        with self.assertRaisesRegex(ValueError,'Symlinks'): self.capture()
        self.assertFalse((Path(self.request['output'])/'receipt.json').exists())
