#!/usr/bin/env python3
"""Review real engine-generated lock selections against exact provider pins.

The schema used here is intentionally restricted to exact-version configurations.
Terraform validates the lock hashes against downloaded packages; this check verifies
review scope/selection/structure, not publisher trust or a native service.
"""
import json,re,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check(root=ROOT):
 rows=[];errors=[]
 for config in sorted((root/'terraform').glob('*/*/main.tf.json')):
  required=json.loads(config.read_text())['terraform']['required_providers'];lock=config.parent/'.terraform.lock.hcl'
  if not lock.is_file():errors.append(str(lock.relative_to(root))+': missing actual lock');continue
  text=lock.read_text();blocks=dict(re.findall(r'provider\s+"([^"]+)"\s*\{([^}]+)\}',text,re.S))
  wanted={'registry.terraform.io/'+v['source']:v['version'].removeprefix('= ').strip() for v in required.values()}
  if set(blocks)!=set(wanted):errors.append(str(lock.relative_to(root))+': provider scope mismatch')
  for address,version in wanted.items():
   body=blocks.get(address,'');v=re.search(r'\bversion\s*=\s*"([^"]+)"',body);hashes=re.findall(r'"((?:zh:[0-9a-f]{64})|(?:h1:[A-Za-z0-9+/=]+))"',body)
   if not v or v[1]!=version or not hashes:errors.append(str(lock.relative_to(root))+': version/hash structure mismatch')
   rows.append({'lock':lock.relative_to(root).as_posix(),'provider':address,'expected_version':version,'observed_version':v[1] if v else None,'recorded_hashes':len(hashes),'lock_sha256':hashlib.sha256(lock.read_bytes()).hexdigest()})
 return {'status':'PASSED_LOCK_SELECTION_REVIEW' if not errors else 'BLOCKED_OR_FAILED_LOCK_REVIEW','records':rows,'errors':errors,'native_qualification':'NOT_RUN','trust_scope':'Actual Terraform package/hash validation remains separate; no publisher approval is issued.'}
if __name__=='__main__':
 r=check();out=ROOT/'build/reports/provider_lock_review.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));raise SystemExit(0 if not r['errors'] else 2)
