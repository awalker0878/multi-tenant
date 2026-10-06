"""Process-level witnesses around the shipped dispatcher, workflows and authority clients."""
import asyncio
import json
import os
from pathlib import Path
import sys
from datetime import timedelta
from google.protobuf.duration_pb2 import Duration
from temporalio.client import Client
from temporalio.service import TLSConfig
from temporalio.api.workflowservice.v1 import RegisterNamespaceRequest
from temporalio.worker import Replayer
from lifecycle.bootstrap.server import execution_service
from lifecycle.infrastructure.store import Postgres
from lifecycle.infrastructure.temporal import Dispatcher
from lifecycle.infrastructure.workflows import SimulationJourney

async def client(admin=False):
    c=await asyncio.wait_for(Client.connect(os.environ['TEMPORAL_TARGET'],namespace='lifecycle',tls=TLSConfig(server_root_ca_cert=Path(os.environ['TEMPORAL_CA_FILE']).read_bytes(),domain='temporal')),5)
    c.rpc_metadata={'authorization':'Bearer '+Path(os.environ['P06_TEMPORAL_ADMIN_FILE' if admin else 'TEMPORAL_CREDENTIAL_FILE']).read_text().strip()}
    return c

async def main():
    mode=sys.argv[1]
    if mode=='initialize':
        last='not_started'
        for _ in range(45):
            try:
                c=await client(True)
                await c.workflow_service.register_namespace(RegisterNamespaceRequest(namespace='lifecycle',workflow_execution_retention_period=Duration(seconds=86400)),timeout=timedelta(seconds=3))
                return
            except Exception as error:
                last=type(error).__name__+': '+str(error)[:500]
                await asyncio.sleep(1)
        raise RuntimeError('temporal_namespace_unavailable: '+last)
    if mode in ['dispatch_lost','dispatch','replay']:
        c=await client()
        if mode=='replay':
            histories=[]
            for workflow in json.loads(Path(sys.argv[2]).read_text()):
                history=await c.get_workflow_handle(workflow).fetch_history()
                await Replayer(workflows=[SimulationJourney]).replay_workflow(history)
                histories.append({'workflow_id':workflow,'events':len(history.events),'replay':'PASS'})
            Path(sys.argv[3]).write_text(json.dumps(histories,indent=2)+'\n');return
        if mode=='dispatch_lost':
            class LostStart:
                async def start_workflow(self,*args,**kwargs):
                    await c.start_workflow(*args,**kwargs)
                    raise TimeoutError('accepted_start_response_lost')
            try:await Dispatcher(Postgres(),LostStart()).dispatch()
            except TimeoutError:os._exit(75)
            raise RuntimeError('fault_not_injected')
        await Dispatcher(Postgres(),c).dispatch();return
    service=execution_service();tenant,job=sys.argv[2:4]
    if mode=='reconcile':service.reconcile(tenant,job);return
    if mode=='checkpoint':service.checkpoint(tenant,job);return
    if mode in ['crash_before','crash_after']:
        grant=service.acquire(tenant,job,sys.argv[4],'sim-worker')
        path=Path(sys.argv[5]);path.write_text(json.dumps(grant));path.chmod(0o600)
        if mode=='crash_after':service.effects.execute(grant)
        os._exit(75)
    if mode=='effect':
        result=service.activity(tenant,job,sys.argv[4],'sim-worker')
        if result['state']!='confirmed_succeeded':raise RuntimeError(result['state'])
        return
    raise ValueError('unknown witness')

asyncio.run(main())
