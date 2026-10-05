"""Resolve signed PHP build APKs once; later builds consume exact hashed bytes."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

from bundle import digest, encode, require


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observation', type=Path, required=True)
    args = parser.parse_args()
    report = json.loads((args.observation / 'report.json').read_bytes())
    selected = report['images']['php-alpine']
    require(selected['result'] == 'OBSERVED' and selected['blocking_matches'] == selected['secrets'] == 0,
            'candidate_not_clear')
    lock = {'schema_version': 1, 'platform': 'linux/amd64', 'distribution': 'alpine', 'release': '3.24.2',
            'base_reference': selected['reference'], 'observed_at': datetime.now(timezone.utc).isoformat(),
            'source_revision': report['source_revision'], 'groups': {}, 'packages': {}}
    with tempfile.TemporaryDirectory(prefix='p01-apk-resolution-') as temporary:
        work = Path(temporary)
        for group, requested in [('build', '$PHPIZE_DEPS postgresql-dev linux-headers openssl'),
                                 ('runtime', 'libpq openssl'), ('composer', 'unzip')]:
            target = work / group; target.mkdir(); target.chmod(0o777)
            command = ('apk fetch --no-cache --recursive --url ' + requested + ' > /packages/urls.txt\n'
                       'apk fetch --no-cache --recursive --output /packages ' + requested + '\n'
                       'chmod -R a+rX /packages')
            result = subprocess.run(['docker', 'run', '--rm', '--platform', 'linux/amd64',
                                     '--mount', f'type=bind,src={target},dst=/packages',
                                     '--entrypoint', 'sh', selected['reference'], '-eu', '-c', command],
                                    capture_output=True, timeout=420)
            (args.observation / ('apk-' + group + '.log')).write_bytes(result.stdout + result.stderr)
            require(result.returncode == 0, 'apk_resolution_failed:' + group)
            urls = {}
            for line in (target / 'urls.txt').read_text().splitlines():
                require(re.fullmatch(r'https://dl-cdn.alpinelinux.org/alpine/v3\.24/(main|community)/x86_64/[a-zA-Z0-9.+_-]+\.apk', line),
                        'unexpected_apk_source')
                urls[line.rsplit('/', 1)[1]] = line
            files = sorted(target.glob('*.apk'))
            require(files and {p.name for p in files} == set(urls), 'apk_url_inventory_mismatch')
            lock['groups'][group] = [p.name for p in files]
            for path in files:
                match = re.fullmatch(r'(.+)-([0-9][^-]*-r[0-9]+)\.apk', path.name)
                require(match is not None, 'invalid_apk_name')
                item = {'name': match[1], 'version': match[2], 'url': urls[path.name],
                        'sha256': digest(path), 'bytes': path.stat().st_size}
                require(path.name not in lock['packages'] or lock['packages'][path.name] == item,
                        'package_changed_during_resolution')
                lock['packages'][path.name] = item
            installed = subprocess.run(['docker', 'run', '--rm', '--network', 'none', '--platform', 'linux/amd64',
                                        '--mount', f'type=bind,src={target},dst=/packages,readonly',
                                        '--entrypoint', 'sh', selected['reference'], '-eu', '-c',
                                        'apk add --no-network --repositories-file /dev/null /packages/*.apk'],
                                       capture_output=True, timeout=180)
            (args.observation / ('apk-' + group + '-offline-install.log')).write_bytes(installed.stdout + installed.stderr)
            require(installed.returncode == 0, 'apk_offline_install_failed:' + group)
        require(len([p for p in lock['packages'].values() if p['name'] == 'libpq']) == 1, 'ambiguous_runtime_libpq')
    lock['resolver_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (args.observation / 'alpine-packages.lock.json').write_bytes(encode(lock))
    print(json.dumps({'result': 'RESOLVED', 'packages': len(lock['packages']),
                      'group_sizes': {g: len(p) for g, p in lock['groups'].items()}}))


if __name__ == '__main__':
    main()
