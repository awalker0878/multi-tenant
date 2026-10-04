"""Observe exact registry digests for declared synthetic installation candidates."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    candidates_path = root / 'deploy/dependencies/candidates.json'
    candidates = json.loads(candidates_path.read_text())
    args.output.mkdir(parents=True, exist_ok=False)
    images = {}
    for name, record in candidates['images'].items():
        command = ['docker', 'buildx', 'imagetools', 'inspect', '--raw', record['candidate']]
        result = subprocess.run(command, capture_output=True, check=True, timeout=120)
        raw = result.stdout
        (args.output / f'{name}-index.json').write_bytes(raw)
        index = json.loads(raw)
        matches = [m for m in index['manifests'] if m.get('platform') == {'architecture':'amd64', 'os':'linux'}]
        if len(matches) != 1:
            raise ValueError('A unique linux/amd64 manifest is required')
        digest = matches[0]['digest']
        repository = record['candidate'].rsplit(':', 1)[0]
        child = subprocess.run(['docker','buildx','imagetools','inspect','--raw',repository+'@'+digest],capture_output=True,check=True,timeout=120).stdout
        if 'sha256:'+hashlib.sha256(child).hexdigest() != digest:
            raise ValueError('Child manifest digest mismatch')
        (args.output / f'{name}-manifest.json').write_bytes(child)
        images[name] = {**record, 'index_digest':'sha256:'+hashlib.sha256(raw).hexdigest(), 'digest':digest, 'reference':repository+'@'+digest}
    revision = subprocess.run(['git','rev-parse','HEAD'],cwd=root,capture_output=True,text=True,check=True).stdout.strip()
    report = {'schema_version':1,'scope':candidates['scope'],'platform':candidates['platform'],'source_revision':revision,'candidate_sha256':hashlib.sha256(candidates_path.read_bytes()).hexdigest(),'images':images}
    (args.output/'inputs.lock.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'source_revision':revision,'images':images}))


if __name__ == '__main__':
    main()
