"""CLI plumbing for explicit, authenticated, GET-only platform observation."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from tools import readback_core as c


def run(adapter,credential_prefix):
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
        client=c.ReadClient(m['origin'],a.expected_origin,os.environ.get(credential_prefix+'_USERNAME',''),
            os.environ.get(credential_prefix+'_PASSWORD',''),adapter.targets(m),ca_file=a.ca_file)
        with c.PrivateJournal(a.output) as journal:
            report=c.observe(m,client,adapter,a.rounds,a.interval);journal.write(report)
        print(json.dumps({'outcome':report['outcome'],'requests':report['request_count'],
            'may_apply':False,'may_delete':False,'may_activate':False},indent=2))
        return 0 if report['outcome']=='READBACK_MATCH_NOT_QUALIFIED' else 2
    except (ValueError,OSError,TypeError,KeyError,RecursionError):
        # Never echo service/credential-bearing exceptions or manifest values.
        print(json.dumps({'status':'INPUT_OR_OUTPUT_REJECTED','may_activate':False}))
        return 2
