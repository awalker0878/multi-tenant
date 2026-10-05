"""Bounded OCI conversion and independently anchored development-bundle admission."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile

MANIFEST_TYPE = 'application/vnd.oci.image.manifest.v1+json'
CONFIG_TYPE = 'application/vnd.oci.image.config.v1+json'
LAYER_TYPE = 'application/vnd.oci.image.layer.v1.tar'
BUILDER = 'https://github.com/awalker0878/multi-tenant/p01-development-builder/v1'


def require(condition, code):
    if not condition:
        raise ValueError(code)


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def encode(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True) + '\n').encode()


def path_in(root: Path, name: str) -> Path:
    p = PurePosixPath(name)
    require(bool(name) and not p.is_absolute() and '..' not in p.parts and '\\' not in name
            and str(p) == name and p.parts[0] != '.', 'unsafe_bundle_path')
    candidate = root / name
    require(not any(part.is_symlink() for part in [candidate, *candidate.parents])
            and candidate.resolve().is_relative_to(root.resolve()), 'symlinked_bundle_path')
    return candidate


def inventory(root: Path, omit=()) -> dict[str, str]:
    result = {}
    for p in sorted(root.rglob('*')):
        require(not p.is_symlink(), 'symlinked_bundle_path')
        if p.is_file() and str(p.relative_to(root)) not in omit:
            result[str(p.relative_to(root))] = digest(p)
    return result


def blob(root: Path, raw: bytes, media: str) -> dict:
    sha = hashlib.sha256(raw).hexdigest()
    target = root / 'blobs/sha256' / sha
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return {'mediaType': media, 'digest': 'sha256:' + sha, 'size': len(raw)}


def docker_to_oci(archive: Path, target: Path, config_digest: str, revision: str) -> str:
    """Convert an exported single image once; never extract arbitrary tar paths."""
    target.mkdir(parents=True, exist_ok=False)
    with tarfile.open(archive) as package:
        members = package.getmembers()
        require(len(members) < 100000 and len({m.name for m in members}) == len(members), 'ambiguous_archive')
        def read(name, limit):
            member = package.getmember(name)
            require(member.isfile() and member.size <= limit, 'unsafe_archive_member')
            return package.extractfile(member).read()
        entries = json.loads(read('manifest.json', 1024 * 1024))
        require(len(entries) == 1, 'single_image_required')
        entry = entries[0]
        config = read(entry['Config'], 4 * 1024 * 1024)
        require('sha256:' + hashlib.sha256(config).hexdigest() == config_digest, 'image_config_mismatch')
        data = json.loads(config)
        require(data['architecture'] == 'amd64' and data['os'] == 'linux', 'image_platform_mismatch')
        require(data['config']['Labels']['org.opencontainers.image.revision'] == revision, 'image_source_mismatch')
        layers = []
        require(0 < len(entry['Layers']) <= 100, 'invalid_layer_count')
        for name in entry['Layers']:
            member = package.getmember(name)
            require(member.isfile() and member.size <= 2 * 1024 ** 3, 'unsafe_archive_member')
            temporary = target / 'layer.tmp'
            with package.extractfile(member) as source, temporary.open('wb') as out:
                shutil.copyfileobj(source, out, 1024 * 1024)
            sha = digest(temporary); destination = target / 'blobs/sha256' / sha
            destination.parent.mkdir(parents=True, exist_ok=True); temporary.replace(destination)
            layers.append({'mediaType': LAYER_TYPE, 'digest': 'sha256:' + sha, 'size': member.size})
        require([x['digest'] for x in layers] == data['rootfs']['diff_ids'], 'layer_diff_id_mismatch')
        descriptor = blob(target, encode({'schemaVersion': 2, 'mediaType': MANIFEST_TYPE,
                          'config': blob(target, config, CONFIG_TYPE), 'layers': layers}), MANIFEST_TYPE)
    (target / 'oci-layout').write_bytes(encode({'imageLayoutVersion': '1.0.0'}))
    (target / 'index.json').write_bytes(encode({'schemaVersion': 2, 'manifests': [descriptor]}))
    return descriptor['digest']


def verify_oci(root: Path, expected: dict, source: str) -> None:
    require(json.loads((root / 'oci-layout').read_text()) == {'imageLayoutVersion': '1.0.0'}, 'invalid_oci_layout')
    index = json.loads((root / 'index.json').read_text())
    require(index['schemaVersion'] == 2 and len(index['manifests']) == 1, 'invalid_oci_index')
    def load(descriptor, media):
        value = descriptor['digest']
        require(re.fullmatch(r'sha256:[0-9a-f]{64}', value) and descriptor['mediaType'] == media, 'invalid_oci_descriptor')
        p = path_in(root, 'blobs/sha256/' + value[7:])
        require(p.is_file() and p.stat().st_size == descriptor['size'] and digest(p) == value[7:], 'oci_blob_mismatch')
        return p
    image = index['manifests'][0]
    require(image['digest'] == expected['manifest_digest'], 'image_manifest_mismatch')
    manifest = json.loads(load(image, MANIFEST_TYPE).read_text())
    require(manifest['schemaVersion'] == 2 and manifest['mediaType'] == MANIFEST_TYPE, 'invalid_oci_manifest')
    require(manifest['config']['digest'] == expected['config_digest'], 'image_config_mismatch')
    config = json.loads(load(manifest['config'], CONFIG_TYPE).read_text())
    require(config['os'] == 'linux' and config['architecture'] == 'amd64'
            and expected['platform'] == 'linux/amd64', 'image_platform_mismatch')
    require(config['config']['Labels']['org.opencontainers.image.revision'] == source, 'image_source_mismatch')
    require([x['digest'] for x in manifest['layers']] == config['rootfs']['diff_ids'], 'layer_diff_id_mismatch')
    for layer in manifest['layers']:
        load(layer, LAYER_TYPE)


def evaluate_scans(scans: list[dict], now: datetime) -> list[str]:
    findings = []
    require(len(scans) == 2, 'missing_scan_scope')
    require({s['scope'] for s in scans} == {'image', 'source'}, 'missing_scan_scope')
    for scan in scans:
        require(scan['scanner'] == 'trivy' and scan['version'] == '0.75.0'
                and scan['completed'] is True and isinstance(scan['results'], list), 'invalid_scan')
        captured = datetime.fromisoformat(scan['observed_at'])
        updated = datetime.fromisoformat(scan['database']['UpdatedAt'])
        require(captured.tzinfo is not None and updated.tzinfo is not None, 'invalid_scan_time')
        require(0 <= (now - captured).total_seconds() <= 86400 and
                0 <= (now - updated).total_seconds() <= 172800, 'stale_scan')
        for result in scan['results']:
            for finding in result.get('Vulnerabilities', []):
                if finding['Severity'] in {'HIGH', 'CRITICAL', 'UNKNOWN'}:
                    findings.append(finding['VulnerabilityID'])
            for finding in result.get('Secrets', []):
                findings.append('secret:' + finding['RuleID'])
    return sorted(set(findings))


def verify(root: Path, anchor: dict, public_key: Path, cosign: str, now=None) -> dict:
    """Anchor is supplied independently by the receiving policy, never the bundle."""
    require(anchor['scope'] == 'p01-development' and anchor['transparency'] == 'synthetic-key-no-log', 'operated_trust_not_configured')
    require(public_key.resolve() != root.resolve() and not public_key.resolve().is_relative_to(root.resolve()), 'self_supplied_trust_root')
    require(digest(public_key) == anchor['public_key_sha256'], 'untrusted_signer')
    require(not anchor.get('revoked', True), 'revoked_signer')
    signature = root / 'signature.sigstore.json'; manifest_path = root / 'release.json'
    require(signature.is_file() and not signature.is_symlink(), 'missing_signature')
    require(manifest_path.is_file() and not manifest_path.is_symlink(), 'missing_manifest')
    result = subprocess.run([cosign, 'verify-blob', '--key', str(public_key), '--bundle', str(signature),
                             '--insecure-ignore-tlog', str(manifest_path)], capture_output=True, timeout=45)
    require(result.returncode == 0, 'signature_invalid')
    m = json.loads(manifest_path.read_text())
    require(m['schema_version'] == 1 and m['scope'] == anchor['scope'], 'manifest_scope_mismatch')
    require(m['source_revision'] == anchor['source_revision'] and m['component'] == anchor['component'], 'manifest_identity_mismatch')
    require(m['image']['manifest_digest'] == anchor['image_digest'], 'image_manifest_mismatch')
    require(m['files'] == inventory(root, ('release.json', 'signature.sigstore.json')), 'bundle_content_mismatch')
    for name, sha in m['files'].items():
        require(re.fullmatch(r'[0-9a-f]{64}', sha) and digest(path_in(root, name)) == sha, 'bundle_content_mismatch')
    verify_oci(root / 'image', m['image'], m['source_revision'])
    sbom = json.loads((root / 'image-sbom.cdx.json').read_text())
    require(sbom['bomFormat'] == 'CycloneDX' and len(sbom.get('components', [])) > 0, 'missing_sbom')
    source_sbom = json.loads((root / 'source-sbom.cdx.json').read_text())
    require(source_sbom['bomFormat'] == 'CycloneDX', 'missing_source_sbom')
    provenance = json.loads((root / 'provenance.json').read_text())
    require(provenance['_type'] == 'https://in-toto.io/Statement/v1'
            and provenance['predicateType'] == 'https://slsa.dev/provenance/v1', 'invalid_provenance')
    require(provenance['subject'] == [{'name': m['component'], 'digest': {'sha256': anchor['image_digest'][7:]}}], 'provenance_subject_mismatch')
    predicate = provenance['predicate']
    require(predicate['runDetails']['builder']['id'] == anchor['builder_id'] == BUILDER, 'untrusted_builder')
    require(predicate['buildDefinition']['externalParameters']['source_revision'] == anchor['source_revision'], 'provenance_source_mismatch')
    scans = [json.loads((root / name).read_text()) for name in ('image-scan.json', 'source-scan.json')]
    require(scans[0]['config_digest'] == m['image']['config_digest'], 'scan_image_mismatch')
    require(all(s['source_revision'] == m['source_revision'] for s in scans), 'scan_source_mismatch')
    findings = evaluate_scans(scans, now or datetime.now(timezone.utc))
    require(not findings, 'security_findings:' + ','.join(findings))
    return {'result': 'ADMITTED_DEVELOPMENT', 'source_revision': m['source_revision'], 'image_digest': anchor['image_digest'],
            'manifest_sha256': digest(manifest_path), 'files': len(m['files'])}
