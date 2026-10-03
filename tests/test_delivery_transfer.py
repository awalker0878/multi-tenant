"""Destination-scoped restore evidence remains bound to source and live authority."""
from pathlib import Path
from datetime import timedelta
import unittest
from unittest.mock import patch

from tools import delivery_steps as steps, restic_run
from provisioner.execution.run_files import digest, encoded, load_private, read_private, write_new, replace_private, utcnow


class DeliveryTransferTests(unittest.TestCase):
    def setUp(self):
        from tests.test_restic_transfer import TransferTests
        self.fixture=TransferTests(); self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        f=self.fixture
        from provisioner.domain.enterprise_records import plan_digest
        f.plan['spec']['selectedDatasetIds']=['dataset-1']
        f.plan['spec']['datasetMappings']=[row for row in f.plan['spec']['datasetMappings']
                                           if row['datasetId']=='dataset-1']
        f.plan['metadata']['planDigest']=plan_digest(f.plan)
        f.transfer['metadata']['planDigest']=f.plan['metadata']['planDigest']
        binary=f.root/'restic'; binary.write_bytes(b'fixture-only'); binary.chmod(0o700)
        f.config['restic_sha256']=digest(binary.read_bytes())
        f.envelope['source_config_sha256']=digest(encoded(f.config))
        f.restore_authority['config_sha256']=digest(encoded(f.config))
        f.configure_authority()
        self.step={'id':'dataset-restore','kind':'restic','needs':[]}
        self.plan={'scope':f.envelope['destination_execution_scope'],'steps':[self.step]}
        self.packet={'parameters':{'action':'restore','restic':str(binary),
            'restic_sha256':f.config['restic_sha256'],'target':str(f.target)},'files':{}}
        for name,value in dict(config=f.config,credentials={},receipt=f.receipt,manifest=f.manifest,
                               restore_authority=f.restore_authority,transfer_manifest=f.envelope).items():
            path=f.root/(name+'.json'); write_new(path,encoded(value))
            self.packet['files'][name]={'path':str(path),'sha256':digest(read_private(path))}
        self.directory=f.root/'steps/dataset-restore'; self.directory.mkdir(mode=0o700,parents=True)
        self.directory.parent.chmod(0o700)
        self.engine=patch.object(restic_run,'Restic',return_value=f.engine)
        self.engine.start(); self.addCleanup(self.engine.stop)
        original=Path.read_text
        def machine(path,*args,**kwargs):
            return 'f'*32 if str(path)=='/etc/machine-id' else original(path,*args,**kwargs)
        self.machine=patch.object(Path,'read_text',new=machine)
        self.machine.start(); self.addCleanup(self.machine.stop)

    def dispatch(self,**kwargs):
        return steps.dispatch(self.step,self.packet,self.directory,self.fixture.root,self.plan,
                              restic_run.ROOT,**kwargs)

    def recover(self):
        return steps.recover(self.step,self.packet,self.directory,self.fixture.root,self.plan,restic_run.ROOT)

    def dataset_packet(self):
        self.step['kind']='dataset_restore'
        spec=self.fixture.transfer['spec']
        self.packet['parameters'].update(transfer_manifest_sha256=digest(encoded(self.fixture.envelope)),
            dataset_id=spec['datasetId'],target_ref=spec['targetRef'],consistency_group_id=spec['consistencyGroupId'],
            source_scope=dict(self.fixture.config['scope']))

    def test_dataset_restore_requires_exact_reviewed_manifest_and_mapping(self):
        self.dataset_packet()
        self.packet['parameters']['target_ref']='another-target'
        with self.assertRaisesRegex(ValueError,'reviewed manifest or mapping'):
            self.dispatch(transfer_guard=self.fixture.guard)
        self.assertEqual(self.fixture.calls,[])

    def test_dataset_restore_refuses_a_foreign_reviewed_source_scope(self):
        self.dataset_packet()
        self.packet['parameters']['source_scope']['site_key']='another-source'
        with self.assertRaisesRegex(ValueError,'reviewed manifest or mapping'):
            self.dispatch(transfer_guard=self.fixture.guard)
        self.assertEqual(self.fixture.calls,[])

    def test_dataset_guard_for_another_child_is_rejected_before_contact(self):
        from dataclasses import replace
        self.dataset_packet()
        guard=replace(self.fixture.guard,step_id='other-dataset')
        with self.assertRaisesRegex(ValueError,'exact child step'):
            self.dispatch(transfer_guard=guard)
        self.assertEqual(self.fixture.calls,[])

    def test_typed_dataset_restore_runs_the_same_guarded_owner(self):
        self.dataset_packet()
        result,_=self.dispatch(transfer_guard=self.fixture.guard)
        self.assertEqual(result['dataset_id'],self.packet['parameters']['dataset_id'])
        self.assertEqual(result['target_ref'],self.packet['parameters']['target_ref'])
        self.assertEqual(result['scope'],self.plan['scope'])

    def group_packet(self):
        self.dataset_packet()
        values=self.packet['parameters']
        group={'id':'group','kind':'dataset_acceptance','needs':[self.step['id']]}
        packet={'parameters':{'group_id':values['consistency_group_id'],'datasets':[
            {key:values[key] for key in ('dataset_id','target_ref','transfer_manifest_sha256')}|{'step_id':self.step['id']}]},
            'files':{}}
        self.plan['steps'].append(group)
        path=self.fixture.root/'steps/group'; path.mkdir(mode=0o700)
        return group,packet,path

    def test_group_gate_joins_only_its_exact_completed_dataset(self):
        group,packet,path=self.group_packet()
        self.dispatch(transfer_guard=self.fixture.guard)
        result,names=steps.dispatch(group,packet,path,self.fixture.root,self.plan,restic_run.ROOT)
        self.assertEqual(result['status'],'DATASET_GROUP_FILE_BYTES_VERIFIED_NOT_APPLICATION_ACCEPTED')
        self.assertEqual(result['dataset_ids'],[self.packet['parameters']['dataset_id']])
        self.assertFalse(result['application_acceptance'])
        self.assertIn('owner-completion.json',names)

    def test_group_gate_rejects_missing_or_wrong_dataset_proof(self):
        group,packet,path=self.group_packet()
        with self.assertRaises(OSError):
            steps.dispatch(group,packet,path,self.fixture.root,self.plan,restic_run.ROOT)
        self.dispatch(transfer_guard=self.fixture.guard)
        packet['parameters']['datasets'][0]['dataset_id']='not-the-reviewed-dataset'
        with self.assertRaisesRegex(ValueError,'another plan, group or destination'):
            steps.dispatch(group,packet,path,self.fixture.root,self.plan,restic_run.ROOT)
        self.assertFalse((path/'owner-completion.json').exists())

    def test_interrupted_group_validation_recovers_without_restore_replay(self):
        group,packet,path=self.group_packet()
        self.dispatch(transfer_guard=self.fixture.guard)
        with patch.object(steps,'complete',side_effect=InterruptedError('coordinator lost')):
            with self.assertRaises(InterruptedError):
                steps.dispatch(group,packet,path,self.fixture.root,self.plan,restic_run.ROOT)
        calls=list(self.fixture.calls)
        result,_=steps.recover(group,packet,path,self.fixture.root,self.plan,restic_run.ROOT)
        self.assertEqual(result['status'],'DATASET_GROUP_FILE_BYTES_VERIFIED_NOT_APPLICATION_ACCEPTED')
        self.assertEqual(self.fixture.calls,calls)

    def service_gate(self):
        from provisioner.execution import readback_core as c
        group,group_packet,group_path=self.group_packet()
        service={'id':'services','kind':'acceptance','needs':['group']}
        self.plan['steps'].append(service)
        accepted=dict(format='hosting-delivery-acceptance/1',plan_sha256=c.digest(self.plan),
            step_id=service['id'],scope=self.plan['scope'],dependencies={'group':'a'*64},
            purpose='services',valid_from=(utcnow()-timedelta(seconds=1)).isoformat(),
            valid_until=(utcnow()+timedelta(minutes=5)).isoformat(),acceptance_ref='APP-OWNER-ACCEPTED')
        source=self.fixture.root/'service-acceptance.json'; write_new(source,encoded(accepted))
        packet={'parameters':{'purpose':'services'},'dependencies':accepted['dependencies'],
                'files':{'acceptance':{'path':str(source),'sha256':digest(read_private(source))}}}
        self.dispatch(transfer_guard=self.fixture.guard)
        write_new(group_path/'packet.json',encoded(group_packet))
        steps.dispatch(group,group_packet,group_path,self.fixture.root,self.plan,restic_run.ROOT)
        destination=self.fixture.root/'steps/services'; destination.mkdir(mode=0o700)
        return service,packet,destination

    def test_service_acceptance_retains_complete_canonical_dataset_coverage(self):
        service,packet,path=self.service_gate()
        result,names=steps.dispatch(service,packet,path,self.fixture.root,self.plan,restic_run.ROOT)
        self.assertEqual(result['status'],'EXTERNAL_ACCEPTANCE_RECORDED')
        self.assertIn('dataset-coverage.json',names)
        coverage=load_private(path/'dataset-coverage.json')
        self.assertEqual(coverage['dataset_ids'],['dataset-1'])
        self.assertFalse(coverage['application_acceptance'])

    def test_service_acceptance_cannot_omit_an_entire_selected_canonical_group(self):
        from provisioner.domain.enterprise_records import plan_digest
        f=self.fixture
        f.plan['spec']['selectedDatasetIds'].append('dataset-2')
        f.plan['spec']['datasetMappings'].append({'datasetId':'dataset-2',
            'targetRef':'target-dataset-2','consistencyGroupId':'group-02'})
        f.plan['metadata']['planDigest']=plan_digest(f.plan)
        f.transfer['metadata']['planDigest']=f.plan['metadata']['planDigest']
        f.configure_authority()
        source=Path(self.packet['files']['transfer_manifest']['path'])
        replace_private(source,encoded(f.envelope))
        self.packet['files']['transfer_manifest']['sha256']=digest(read_private(source))
        service,packet,path=self.service_gate()
        with self.assertRaisesRegex(ValueError,'All selected canonical dataset groups'):
            steps.dispatch(service,packet,path,f.root,self.plan,restic_run.ROOT)
        self.assertFalse((path/'owner-completion.json').exists())

    def test_interrupted_service_acceptance_recomputes_coverage_without_transfer_replay(self):
        service,packet,path=self.service_gate()
        calls=list(self.fixture.calls)
        with patch.object(steps,'complete',side_effect=InterruptedError('coordinator lost')):
            with self.assertRaises(InterruptedError):
                steps.dispatch(service,packet,path,self.fixture.root,self.plan,restic_run.ROOT)
        result,names=steps.recover(service,packet,path,self.fixture.root,self.plan,restic_run.ROOT)
        self.assertEqual(result['status'],'EXTERNAL_ACCEPTANCE_RECORDED')
        self.assertIn('dataset-coverage.json',names)
        self.assertEqual(self.fixture.calls,calls)

    def test_file_transfer_manifest_alone_is_held_before_repository_contact(self):
        with self.assertRaisesRegex(ValueError,'live trusted worker'):
            self.dispatch()
        self.assertEqual(self.fixture.calls,[])
        self.assertFalse(self.fixture.target.exists())

    def test_trusted_transfer_emits_separate_source_and_destination_receipts(self):
        result,names=self.dispatch(transfer_guard=self.fixture.guard)
        self.assertEqual(result['scope'],self.plan['scope'])
        source=load_private(self.directory/'receipt.json')
        self.assertEqual(source['scope'],self.fixture.config['scope'])
        self.assertNotEqual(source['scope'],result['scope'])
        self.assertIn('transfer-receipt.json',names)
        self.assertEqual(result['source_receipt_sha256'],digest(encoded(self.fixture.receipt)))

    def test_completed_transfer_recovers_without_replaying_repository_commands(self):
        with patch.object(steps,'complete',side_effect=InterruptedError('coordinator lost')):
            with self.assertRaises(InterruptedError): self.dispatch(transfer_guard=self.fixture.guard)
        calls=list(self.fixture.calls)
        result,names=self.recover()
        self.assertEqual(result['scope'],self.plan['scope'])
        self.assertEqual(self.fixture.calls,calls)
        self.assertIn('transfer-receipt.json',names)

    def test_interrupted_transfer_rejects_substituted_actual_machine_even_with_matching_receipt(self):
        from tools.restic_transfer import destination_receipt
        with patch.object(steps,'complete',side_effect=InterruptedError('coordinator lost')):
            with self.assertRaises(InterruptedError): self.dispatch(transfer_guard=self.fixture.guard)
        execution=self.directory/'execution'
        restored=load_private(execution/'receipt.json')
        restored['target_machine_id']='e'*32
        replace_private(execution/'receipt.json',encoded(restored))
        destination=destination_receipt(self.fixture.envelope,self.fixture.receipt,restored)
        replace_private(execution/'transfer-receipt.json',encoded(destination))
        replace_private(self.directory/'receipt.json',encoded(restored))
        replace_private(self.directory/'transfer-receipt.json',encoded(destination))
        calls=list(self.fixture.calls)
        with self.assertRaisesRegex(ValueError,'actual authorized restore machine and root'):
            self.recover()
        self.assertEqual(self.fixture.calls,calls)
        self.assertFalse((self.directory/'owner-completion.json').exists())

    def test_interrupted_transfer_rejects_legacy_unobserved_restore_identity(self):
        with patch.object(steps,'complete',side_effect=InterruptedError('coordinator lost')):
            with self.assertRaises(InterruptedError): self.dispatch(transfer_guard=self.fixture.guard)
        source=self.directory/'execution/receipt.json'; restored=load_private(source)
        for field in ('format','target_machine_id','restore_root'): restored.pop(field)
        replace_private(source,encoded(restored))
        calls=list(self.fixture.calls)
        with self.assertRaisesRegex(ValueError,'observed restore machine and exact root'):
            self.recover()
        self.assertEqual(self.fixture.calls,calls)
        self.assertFalse((self.directory/'owner-completion.json').exists())

    def test_completed_transfer_returns_and_revalidates_actual_restore_identity(self):
        from tools.delivery_run import artifact_receipt
        from tools.restic_transfer import destination_receipt
        original,_=self.dispatch(transfer_guard=self.fixture.guard)
        calls=list(self.fixture.calls)
        result,_=self.recover()
        self.assertEqual(result,original)
        self.assertEqual(result['target_machine_id'],self.fixture.restore_authority['machine_id'])
        self.assertEqual(result['restore_root'],str(self.fixture.target))
        # Model a retained, internally hashed completion from an older producer:
        # checksums alone must not bless a different actual restore machine.
        restored=load_private(self.directory/'receipt.json'); restored['target_machine_id']='e'*32
        replace_private(self.directory/'receipt.json',encoded(restored))
        replace_private(self.directory/'transfer-receipt.json',encoded(destination_receipt(
            self.fixture.envelope,self.fixture.receipt,restored)))
        completion=load_private(self.directory/'owner-completion.json')
        completion['artifacts']=artifact_receipt(self.directory,list(completion['artifacts']))
        replace_private(self.directory/'owner-completion.json',encoded(completion))
        with self.assertRaisesRegex(ValueError,'actual authorized restore machine and root'):
            self.recover()
        self.assertEqual(self.fixture.calls,calls)

    def test_missing_destination_receipt_cannot_be_reconstructed_or_replayed(self):
        with patch.object(steps,'complete',side_effect=InterruptedError('coordinator lost')):
            with self.assertRaises(InterruptedError): self.dispatch(transfer_guard=self.fixture.guard)
        (self.directory/'execution/transfer-receipt.json').unlink()
        calls=list(self.fixture.calls)
        with self.assertRaises(OSError): self.recover()
        self.assertEqual(self.fixture.calls,calls)
        self.assertFalse((self.directory/'owner-completion.json').exists())

    def test_destination_scope_cannot_be_substituted_by_packet_metadata(self):
        self.plan['scope']=self.plan['scope']|{'tenant_key':'foreign'}
        with self.assertRaisesRegex(ValueError,'Foreign delivery'):
            self.dispatch(transfer_guard=self.fixture.guard)
        self.assertEqual(self.fixture.calls,[])


if __name__=='__main__': unittest.main()
