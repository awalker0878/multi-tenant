"""CLI plumbing for explicit, authenticated platform observation."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
from provisioner.execution import readback_core as c

_READERS = frozenset({
    'neutron_observe', 'nutanix_observe', 'nutanix_vm_observe', 'nutanix_vm_task_observe',
    'nutanix_vm_activity_observe', 'nutanix_flow_observe', 'nutanix_flow_activity_observe',
    'vsphere_observe', 'vsphere_task_observe', 'vsphere_task_tree_observe',
    'vsphere_port_observe', 'vsphere_network_observe', 'nsx_observe',
    'nsx_segment_observe', 'nsx_domain_observe', 'nsx_domain_switch_observe',
})
_LAUNCH = ('import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); '
           'runpy.run_module(sys.argv.pop(1),run_name="__main__",alter_sys=True)')


def module_command(adapter, arguments):
    """Launch a fixed read-only owner from this installation in isolated Python.

    The package root comes from the actual imported owner, never from cwd,
    PYTHONPATH, a selected source checkout or an operator module argument.
    """
    name = getattr(adapter, '__name__', '')
    if (name not in {'provisioner.execution.' + item for item in _READERS}
            or Path(adapter.__file__).resolve().parent != Path(__file__).resolve().parent):
        raise ValueError('Only an actual package-owned fixed observer can be dispatched')
    root = Path(__file__).resolve().parents[2]
    return [sys.executable, '-I', '-B', '-c', _LAUNCH, str(root), name, *arguments]


def run(adapter,credential_prefix, *, session=False, client_factory=None):
    p=argparse.ArgumentParser(description=adapter.__doc__)
    p.add_argument('manifest',type=Path)
    p.add_argument('--read-authorized-target',action='store_true')
    p.add_argument('--expected-origin')
    p.add_argument('--ca-file')
    p.add_argument('--output',type=Path)
    p.add_argument('--rounds',type=int,default=3)
    p.add_argument('--interval',type=float,default=0.2)
    a=p.parse_args()
    try:
        m=c.load(a.manifest);adapter.validate(m)
        if not a.read_authorized_target:
            print(json.dumps({'status':'INPUT_VALID_NO_CONTACT','manifest_sha256':c.digest(m),
                'planned_get_targets':len(adapter.targets(m)),'target_contacted':False,'may_activate':False},indent=2))
            return 0
        if not m['contact_enabled'] or not a.expected_origin or not a.output:
            raise ValueError('Explicit enabled manifest, expected origin and new private output required')
        if '.invalid' in m['origin']:
            raise ValueError('Documentation endpoint cannot be contacted')
        if type(a.rounds) is not int or not 2<=a.rounds<=10 or not 0<=a.interval<=10:
            raise ValueError('Bounded polling values required')
        client=client_factory(m,a) if client_factory else c.ReadClient(m['origin'],a.expected_origin,
            None if session else os.environ.get(credential_prefix+'_USERNAME',''),
            None if session else os.environ.get(credential_prefix+'_PASSWORD',''),
            adapter.targets(m),ca_file=a.ca_file,
            session_token=os.environ.get(credential_prefix+'_SESSION','') if session else None)
        with c.PrivateJournal(a.output) as journal:
            report=c.observe(m,client,adapter,a.rounds,a.interval);journal.write(report)
        print(json.dumps({'outcome':report['outcome'],'requests':report['request_count'],
            'may_apply':False,'may_delete':False,'may_activate':False},indent=2))
        return 0 if report['outcome']=='READBACK_MATCH_NOT_QUALIFIED' else 2
    except (ValueError,OSError,TypeError,KeyError,RecursionError):
        # Never echo service/credential-bearing exceptions or manifest values.
        print(json.dumps({'status':'INPUT_OR_OUTPUT_REJECTED','may_activate':False}))
        return 2
