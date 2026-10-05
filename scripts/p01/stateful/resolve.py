"""Observe reviewed dependency images, a fixed source archive and client wheel closure."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request


def command(argv):
    return subprocess.run(argv, capture_output=True, check=True, timeout=180).stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    args.output.mkdir(parents=True, exist_ok=False)
    candidate = root/'deploy/dependencies/stateful/candidates.json'
    data = json.loads(candidate.read_text())
    images = {}
    for name, record in data['images'].items():
        raw = command(['docker', 'buildx', 'imagetools', 'inspect', '--raw', record['candidate']])
        (args.output/(name+'-index.json')).write_bytes(raw)
        index = json.loads(raw)
        if 'manifests' in index:
            matches = [m for m in index['manifests'] if m.get('platform', {}).get('os') == 'linux' and m.get('platform', {}).get('architecture') == 'amd64' and m.get('platform', {}).get('variant') in (None, '')]
            if len(matches) != 1:
                raise ValueError('Expected one linux/amd64 manifest: '+name)
            sha = matches[0]['digest']
        else:
            sha = 'sha256:'+hashlib.sha256(raw).hexdigest()
        repository = record['candidate'].rsplit(':', 1)[0]
        child = command(['docker', 'buildx', 'imagetools', 'inspect', '--raw', repository+'@'+sha])
        if 'sha256:'+hashlib.sha256(child).hexdigest() != sha:
            raise ValueError('Registry manifest hash mismatch')
        (args.output/(name+'-manifest.json')).write_bytes(child)
        images[name] = {**record, 'index_digest': 'sha256:'+hashlib.sha256(raw).hexdigest(), 'digest': sha, 'reference': repository+'@'+sha}
    with urllib.request.urlopen(data['minio_source']['url'], timeout=120) as response:
        archive = response.read(64*1024*1024+1)
    if len(archive) > 64*1024*1024:
        raise ValueError('Source archive exceeded bound')
    source = {**data['minio_source'], 'sha256': hashlib.sha256(archive).hexdigest(), 'bytes': len(archive)}
    uv = json.loads((root/'deploy/build/inputs.lock.json').read_text())['images']['uv']['reference']
    requirements = root/'scripts/p01/stateful/requirements.in'
    result = command(['docker', 'run', '--rm', '--platform', 'linux/amd64', '-v', str(requirements)+':/requirements.in:ro', '-v', str(args.output.resolve())+':/output', uv,
                      'pip', 'compile', '--python-version', '3.12', '--python-platform', 'x86_64-manylinux_2_28', '--generate-hashes', '--no-annotate', '--no-header', '--only-binary', ':all:', '/requirements.in', '-o', '/output/requirements.txt'])
    (args.output/'client-resolution.log').write_bytes(result)
    report = {'schema_version': 1, 'scope': data['scope'], 'platform': 'linux/amd64', 'images': images, 'minio_source': source,
              'source_revision': command(['git', 'rev-parse', 'HEAD']).decode().strip(), 'candidate_sha256': hashlib.sha256(candidate.read_bytes()).hexdigest(),
              'client_input_sha256': hashlib.sha256(requirements.read_bytes()).hexdigest(), 'client_lock_sha256': hashlib.sha256((args.output/'requirements.txt').read_bytes()).hexdigest()}
    (args.output/'inputs.lock.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'result': 'OBSERVED', 'images': list(images), 'client_lock_sha256': report['client_lock_sha256']}))


if __name__ == '__main__':
    main()
