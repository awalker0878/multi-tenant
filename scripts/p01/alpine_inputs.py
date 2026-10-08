"""Validate the exact APK closure before handing it to independent build contexts."""
import json
from pathlib import Path
import re


def validate_apks(path: Path, base_reference: str) -> dict:
    lock = json.loads(path.read_bytes())
    if (lock['schema_version'] != 1 or lock['platform'] != 'linux/amd64'
            or lock['distribution'] != 'alpine' or lock['release'] != '3.24.2'
            or lock['base_reference'] != base_reference):
        raise ValueError('APK platform/base binding differs')
    groups, packages = lock['groups'], lock['packages']
    if set(groups) != {'build', 'runtime', 'composer'} or not packages:
        raise ValueError('APK groups are incomplete')
    for files in groups.values():
        if not files or len(files) != len(set(files)) or set(files) - set(packages):
            raise ValueError('APK group inventory differs')
    if set().union(*map(set, groups.values())) != set(packages):
        raise ValueError('APK closure contains undeclared bytes')
    identities = set()
    for filename, package in packages.items():
        if (not re.fullmatch(r'[a-zA-Z0-9.+_-]+\.apk', filename)
                or filename != package['name'] + '-' + package['version'] + '.apk'
                or not re.fullmatch(r'https://dl-cdn\.alpinelinux\.org/alpine/v3\.24/(main|community)/x86_64/'
                                    + re.escape(filename), package['url'])
                or not re.fullmatch(r'[0-9a-f]{64}', package['sha256'])
                or type(package['bytes']) is not int or not 0 < package['bytes'] <= 268435456
                or package['name'] in identities):
            raise ValueError('APK artifact identity is invalid or ambiguous')
        identities.add(package['name'])
    runtime = {packages[n]['name']: packages[n]['version'] for n in groups['runtime']}
    if set(runtime) != {'libpq', 'libcrypto3', 'libssl3', 'musl', 'openssl'}:
        raise ValueError('Unmeasured runtime APK closure')
    return runtime
