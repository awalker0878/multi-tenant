"""Compose a complete, immutable P01 evidence set; never authorize promotion."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys

from bundle import digest, encode, evaluate_scans, require

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verify_retained import retained_path, verify_record  # noqa: E402


def assemble(root: Path, run_path: str) -> dict:
    run = retained_path(root, run_path)
    retrieval_path = run / 'retrieval.json'
    integrity = verify_record(retrieval_path)
    retrieval = json.loads(retrieval_path.read_bytes())
    require(retrieval['result'] == 'VERIFIED', 'unverified_retrieval')
    source = retrieval['source_revision']
    require(re.fullmatch(r'[0-9a-f]{40}', source), 'invalid_source_revision')
    registry_path = root / 'deploy/build/components.json'
    registry = json.loads(registry_path.read_bytes())['components']
    expected = {c['id']: c for c in registry}
    require(len(expected) == len(registry) and len(expected) > 0, 'ambiguous_component_registry')
    bindings_path = run / 'source-verification.json'
    require(digest(bindings_path) == retrieval['source_verification_sha256'], 'source_verification_mismatch')
    bindings = json.loads(bindings_path.read_bytes())['revisions']
    matching = [b for b in bindings if b['source_revision'] == source]
    require(len(matching) == 1, 'source_binding_missing')
    source_hashes = {b['path']: b['sha256'] for b in matching[0]['bindings']}
    require(source_hashes.get('deploy/build/components.json') == digest(registry_path), 'component_registry_changed')
    observed = {p.parent.name: p for p in run.glob('*/report.json')}
    require(set(observed) == set(expected), 'incomplete_component_set')
    components = []
    for name, path in sorted(observed.items()):
        report = json.loads(path.read_bytes())
        require(report['component'] == name and report['source_revision'] == source
                and report['result'] == 'PASSED_CONTROLS', 'invalid_component_report')
        require(all(source_hashes.get(p) == h for p, h in report['source_sha256'].items()),
                'component_source_binding_mismatch')
        base = path.parent
        for relative, sha in report['retained_sha256'].items():
            require(digest(retained_path(base, relative)) == sha, 'retained_component_mismatch')
        bundle = base / 'bundle-record'
        manifest = json.loads((bundle / 'release.json').read_bytes())
        require(manifest['component'] == name and manifest['source_revision'] == source
                and manifest['image'] == report['image'], 'component_manifest_mismatch')
        for relative, sha in manifest['files'].items():
            # The hosted run checked layers before discarding them. This inventory
            # rechecks retained small files and never claims a layer replay.
            if not relative.startswith('image/'):
                require(digest(retained_path(bundle, relative)) == sha, 'manifest_file_mismatch')
        build_path = base / 'build/report.json'
        require(digest(build_path) == report['build_report_sha256'], 'build_report_mismatch')
        build = json.loads(build_path.read_bytes())
        require(build['source_revision'] == source and build['result'] == 'PASSED'
                and build['component'] == name and build['image']['id'] == report['image']['config_digest'],
                'build_identity_mismatch')
        scans = [json.loads((bundle / (scope + '-scan.json')).read_bytes()) for scope in ('image', 'source')]
        require([s['scope'] for s in scans] == ['image', 'source']
                and all(s['source_revision'] == source for s in scans)
                and scans[0]['config_digest'] == report['image']['config_digest'], 'scan_identity_mismatch')
        # Historical observations are evaluated at their recorded completion time;
        # they are not fresh admission scans for a later promotion.
        findings = evaluate_scans(scans, datetime.fromisoformat(report['completed_at']))
        require(findings == report['security_findings'], 'findings_mismatch')
        expected_admission = 'HELD' if findings else 'ADMITTED_DEVELOPMENT'
        require(report['candidate_admission'] == expected_admission, 'candidate_admission_overclaim')
        rows = [v for s in scans for row in s['results'] for v in row.get('Vulnerabilities', [])
                if v['Severity'] in {'HIGH', 'CRITICAL', 'UNKNOWN'}]
        locks = {p: h for p, h in report['source_sha256'].items()
                 if p.startswith(expected[name]['context'] + '/')
                 and Path(p).name in {'composer.lock', 'package-lock.json', 'uv.lock'}}
        require(locks, 'component_lock_missing')
        components.append({
            'id': name, 'source_path': expected[name]['context'], 'source_revision': source,
            'image': report['image'], 'locks': locks,
            'report': {'path': str(path.relative_to(root)), 'sha256': digest(path)},
            'build_report_sha256': digest(build_path),
            'manifest_sha256': digest(bundle / 'release.json'),
            'sboms': {scope: digest(bundle / (scope + '-sbom.cdx.json')) for scope in ('image', 'source')},
            'provenance_sha256': digest(bundle / 'provenance.json'),
            'signature_sha256': digest(bundle / 'signature.sigstore.json'),
            'development_key_sha256': digest(base / 'development-public-key.pem'),
            'candidate_admission_at_observation': expected_admission,
            'blocking_package_advisory_matches': len(rows),
            'distinct_blocking_advisories': len(set(v['VulnerabilityID'] for v in rows)),
            'matches_with_fixed_version': sum(bool(v.get('FixedVersion')) for v in rows),
            'source_blocking_findings': sorted({v['VulnerabilityID'] for row in scans[1]['results']
                for v in row.get('Vulnerabilities', []) if v['Severity'] in {'HIGH', 'CRITICAL', 'UNKNOWN'}}
                | {'secret:' + v['RuleID'] for row in scans[1]['results'] for v in row.get('Secrets', [])}),
            'transfer_integrity': report['transfer_integrity'],
            'negative_cases': report['denials'],
        })
    held = [c['id'] for c in components if c['candidate_admission_at_observation'] == 'HELD']
    return {
        'schema_version': 1, 'scope': 'p01-development-evidence-set',
        'candidate_id': 'p01-' + source, 'source_revision': source,
        'status': 'HELD' if held else 'REQUIRES_INDEPENDENT_QUALIFICATION',
        'promotion_authorized': False, 'held_components': held,
        'retrieval': {'path': str(retrieval_path.relative_to(root)), **integrity},
        'component_registry_sha256': digest(registry_path), 'components': components,
        'limitations': [
            'Historical build/scan observations; rescan and independently verify full artifacts before any future admission.',
            'Retained ephemeral development signatures do not supply operated trust or repository approval.',
            'Full image layers are not retained here. This inventory is not a deployable or signed product release.',
            'No native qualification, independent G01 review, operating acceptance or release authority is inferred.',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-path', required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--check', type=Path, help='Compare committed manifest with deterministic regeneration.')
    args = parser.parse_args()
    require(bool(args.output) != bool(args.check), 'choose_output_or_check')
    root = Path(__file__).resolve().parents[3]
    manifest = assemble(root, args.run_path)
    raw = encode(manifest)
    if args.check:
        require(args.check.read_bytes() == raw, 'stale_release_set')
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(raw)
    print(json.dumps({'status': manifest['status'], 'components': len(manifest['components']),
                      'held': len(manifest['held_components']), 'promotion_authorized': False}))


if __name__ == '__main__':
    main()
