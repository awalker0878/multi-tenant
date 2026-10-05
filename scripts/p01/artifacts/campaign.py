"""Scan, sign and verify one previously built image without rebuilding it.

Only redacted findings and small verification records leave private temporary storage.
Development admission is separate from operated promotion and repository admission.
"""
from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile

from bundle import BUILDER, digest, docker_to_oci, encode, evaluate_scans, inventory, require, verify
from tools import install

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts/p01'))
from run_images import load_inputs  # noqa: E402


def redacted_results(raw):
    """Never retain matched secret bytes, source snippets or arbitrary scanner fields."""
    results = []
    for item in raw.get('Results', []):
        row = {k: item[k] for k in ('Target', 'Class', 'Type') if k in item}
        row['packages_count'] = len(item.get('Packages') or [])
        row['Vulnerabilities'] = [{k: v[k] for k in ('VulnerabilityID', 'PkgName', 'InstalledVersion',
                                    'FixedVersion', 'Severity', 'Status') if k in v}
                                  for v in item.get('Vulnerabilities') or []]
        row['Secrets'] = [{k: s[k] for k in ('RuleID', 'Severity', 'StartLine', 'EndLine') if k in s}
                          for s in item.get('Secrets') or []]
        results.append(row)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--build-report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    built = json.loads(args.build_report.read_text())
    report = {'schema_version': 1, 'result': 'FAILED', 'candidate_admission': 'HELD',
              'source_revision': built['source_revision'], 'component': built['component'],
              'scope': 'P01 real-image development scan/signature/transfer; no operated trust or deployment',
              'build_report_sha256': digest(args.build_report), 'started_at': datetime.now(timezone.utc).isoformat(),
              'commands': [], 'denials': []}
    bound = [ROOT / p for p in ['.github/workflows/p01-images.yml', 'release/artifact-tools.lock.json',
             'release/development-signing.json', 'scripts/p01/run_images.py', 'scripts/p01/python_lock.py',
             'deploy/build/components.json', 'deploy/build/inputs.lock.json']]
    bound += sorted((ROOT / 'scripts/p01/artifacts').glob('*.py'))
    report['source_sha256'] = dict(built['source_sha256']) | {str(p.relative_to(ROOT)): digest(p) for p in bound}

    def run(name, argv, *, cwd=None, env=None, timeout=600):
        result = subprocess.run(list(map(str, argv)), cwd=cwd, env=env, capture_output=True, timeout=timeout)
        # Tool output can include a secret match. Keep it private; record only status and arguments.
        report['commands'].append({'name': name, 'argv': list(map(str, argv)), 'exit_code': result.returncode})
        require(result.returncode == 0, name + '_failed')
        return result.stdout

    def denied(name, bundle, anchor, key, cosign, expected):
        try:
            verify(bundle, anchor, key, cosign)
        except ValueError as error:
            code = str(error)
            require(code.startswith(expected), 'unexpected_denial:' + name + ':' + code)
            report['denials'].append({'case': name, 'observed': code})
        else:
            raise ValueError('denial_not_observed:' + name)

    try:
        require(built['result'] == 'PASSED', 'unverified_build')
        revision = run('exact-source', ['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
        require(revision == built['source_revision'], 'build_source_mismatch')
        require(not run('clean-inputs', ['git', 'status', '--porcelain', '--untracked-files=all', '--',
                                      *report['source_sha256']], cwd=ROOT).strip(), 'dirty_inputs')
        _, component, sources = load_inputs(ROOT, built['component'])
        require(all(report['source_sha256'].get(str(p.relative_to(ROOT))) == digest(p) for p in sources),
                'build_material_mismatch')
        with tempfile.TemporaryDirectory(prefix='p01-private-artifact-') as private:
            work = Path(private); bundle = work / 'bundle';bundle.mkdir()
            tools = install(ROOT, work / 'tools');cosign = tools['cosign'];trivy = tools['trivy']
            report['tools'] = {'lock_sha256': digest(ROOT / 'release/artifact-tools.lock.json'),
                               'installed_sha256': {name: digest(Path(path)) for name, path in tools.items()}}
            source = work / 'source';source.mkdir()
            owned = ROOT / component['context']
            for p in sources:
                target = source / p.relative_to(owned);target.parent.mkdir(parents=True, exist_ok=True);shutil.copyfile(p, target)
            archive = work / 'image.tar'
            run('export-existing-image', ['docker', 'save', '--output', archive, built['image']['id']])
            image = docker_to_oci(archive, bundle / 'image', built['image']['id'], revision)
            report['image'] = {'manifest_digest': image, 'config_digest': built['image']['id'], 'platform': 'linux/amd64'}
            cache = work / 'trivy-cache'
            run('download-advisory-database', [trivy, 'image', '--cache-dir', cache, '--download-db-only', '--no-progress'])
            database = json.loads((cache / 'db/metadata.json').read_text())
            database['sha256'] = digest(cache / 'db/trivy.db')
            report['database'] = database
            scans = []
            for scope in ['image', 'source']:
                command = [trivy, 'image' if scope == 'image' else 'fs', '--cache-dir', cache,
                           '--skip-db-update', '--no-progress', '--config', '', '--ignorefile', '', '--secret-config', '']
                # Dev/build dependency inclusion is a filesystem flag, not an image flag.
                command += ['--include-dev-deps'] if scope == 'source' else []
                target = ['--input', archive] if scope == 'image' else [source]
                raw_scan = work / (scope + '-raw.json')
                scan_options = ['--image-config-scanners', 'secret'] if scope == 'image' else []
                run(scope + '-scan', command + scan_options + ['--scanners', 'vuln,secret', '--list-all-pkgs',
                    '--format', 'json', '--output', raw_scan] + target)
                raw = json.loads(raw_scan.read_text())
                require(raw['SchemaVersion'] == 2 and raw.get('Results'), 'missing_scan_results')
                sbom = bundle / (scope + '-sbom.cdx.json')
                run(scope + '-sbom', command + ['--format', 'cyclonedx', '--output', sbom] + target)
                sbom_data = json.loads(sbom.read_text())
                require(sbom_data['bomFormat'] == 'CycloneDX' and sbom_data.get('components'), 'empty_sbom')
                scan = {'scope': scope, 'scanner': 'trivy', 'version': '0.75.0', 'completed': True,
                        'observed_at': datetime.now(timezone.utc).isoformat(), 'source_revision': revision,
                        'config_digest': built['image']['id'] if scope == 'image' else None,
                        'database': database, 'results': redacted_results(raw)}
                require(sum(r['packages_count'] for r in scan['results']) > 0, 'empty_dependency_inventory')
                (bundle / (scope + '-scan.json')).write_bytes(encode(scan));scans.append(scan)
                report.setdefault('package_counts', {})[scope] = sum(r['packages_count'] for r in scan['results'])
                raw_scan.unlink()
            findings = evaluate_scans(scans, datetime.now(timezone.utc));report['security_findings'] = findings
            provenance = {'_type': 'https://in-toto.io/Statement/v1', 'predicateType': 'https://slsa.dev/provenance/v1',
                          'subject': [{'name': built['component'], 'digest': {'sha256': image[7:]}}],
                          'predicate': {'buildDefinition': {'buildType': BUILDER,
                            'externalParameters': {'source_revision': revision, 'component': built['component']},
                            'resolvedDependencies': [{'uri': 'git+https://github.com/awalker0878/multi-tenant#' + revision,
                                                       'digest': {'gitCommit': revision}}] +
                              [{'uri': path, 'digest': {'sha256': sha}} for path, sha in sorted(built['source_sha256'].items())]},
                            'runDetails': {'builder': {'id': BUILDER}, 'metadata': {
                              'invocationId': os.environ.get('GITHUB_RUN_ID', 'local'),
                              'startedOn': built['started_at'], 'finishedOn': built['completed_at']}}}}
            (bundle / 'provenance.json').write_bytes(encode(provenance))
            manifest = {'schema_version': 1, 'scope': 'p01-development', 'source_revision': revision,
                        'component': built['component'], 'image': report['image'], 'files': inventory(bundle)}
            (bundle / 'release.json').write_bytes(encode(manifest))
            env = os.environ | {'COSIGN_PASSWORD': secrets.token_urlsafe(32), 'HTTPS_PROXY': 'http://127.0.0.1:9',
                                'HTTP_PROXY': 'http://127.0.0.1:9', 'NO_PROXY': ''}
            run('generate-ephemeral-development-key', [cosign, 'generate-key-pair', '--output-key-prefix', work / 'key'], env=env)
            run('sign-development-manifest-offline', [cosign, 'sign-blob', '--yes', '--signing-config',
                ROOT / 'release/development-signing.json', '--key', work / 'key.key', '--bundle',
                bundle / 'signature.sigstore.json', bundle / 'release.json'], env=env)
            require(not json.loads((bundle / 'signature.sigstore.json').read_text())['verificationMaterial'].get('tlogEntries'),
                    'unexpected_transparency_upload')
            key = work / 'key.pub'
            anchor = {'scope': 'p01-development', 'transparency': 'synthetic-key-no-log',
                      'public_key_sha256': digest(key), 'revoked': False, 'source_revision': revision,
                      'component': built['component'], 'image_digest': image, 'builder_id': BUILDER}
            if findings:
                denied('real-findings-hold-candidate', bundle, anchor, key, cosign, 'security_findings:')
                target = work / 'receiving-quarantine';shutil.copytree(bundle, target)
                require(inventory(bundle) == inventory(target), 'transfer_changed_bytes')
                denied('quarantined-target-still-held', target, anchor, key, cosign, 'security_findings:')
                report['transfer_integrity'] = 'VERIFIED_UNPROMOTED_COPY'
                shutil.rmtree(target)
            else:
                report['source_admission'] = verify(bundle, anchor, key, cosign)
                target = work / 'receiving-store';shutil.copytree(bundle, target)
                require(inventory(bundle) == inventory(target), 'transfer_changed_bytes')
                report['target_admission'] = verify(target, anchor, key, cosign)
                report['candidate_admission'] = 'ADMITTED_DEVELOPMENT'
                report['transfer_integrity'] = 'VERIFIED_DEVELOPMENT_COPY'
                shutil.rmtree(target)
            # Use the exact real image; restore bytes after each negative, never rebuild.
            signature = bundle / 'signature.sigstore.json'; saved = signature.read_bytes();signature.unlink()
            denied('unsigned', bundle, anchor, key, cosign, 'missing_signature');signature.write_bytes(saved)
            for name, expected in [('release.json', 'signature_invalid'), ('image-sbom.cdx.json', 'bundle_content_mismatch'),
                                   ('image/blobs/sha256/' + built['image']['id'][7:], 'bundle_content_mismatch')]:
                p = bundle / name; saved = p.read_bytes();p.write_bytes(saved + b'changed')
                denied('altered-' + name, bundle, anchor, key, cosign, expected);p.write_bytes(saved)
            denied('wrong-source', bundle, dict(anchor, source_revision='0'*40), key, cosign, 'manifest_identity_mismatch')
            denied('revoked-signer', bundle, dict(anchor, revoked=True), key, cosign, 'revoked_signer')
            denied('operated-scope', bundle, dict(anchor, scope='production'), key, cosign, 'operated_trust_not_configured')
            retained = args.output / 'bundle-record';retained.mkdir()
            for p in bundle.iterdir():
                if p.is_file():shutil.copyfile(p, retained / p.name)
            shutil.copyfile(key, args.output / 'development-public-key.pem')
            (args.output / 'receiving-anchor.json').write_bytes(encode(anchor))
            # The anchor is retained as a campaign observation, never as production authorization.
            report['retained_sha256'] = inventory(args.output)
            report['result'] = 'PASSED_CONTROLS'
    except Exception as error:
        report['error'] = str(error) if isinstance(error, ValueError) else type(error).__name__
    finally:
        report['completed_at'] = datetime.now(timezone.utc).isoformat()
        (args.output / 'report.json').write_bytes(encode(report))
        print(json.dumps({k: report.get(k) for k in ['component', 'result', 'candidate_admission', 'error', 'security_findings']}))
    return 0 if report['result'] == 'PASSED_CONTROLS' and report['candidate_admission'] == 'ADMITTED_DEVELOPMENT' else 1


if __name__ == '__main__':
    raise SystemExit(main())
