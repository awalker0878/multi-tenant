"""Replay locked clients and validate actual foundation HTTP wire contracts."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from openapi_schema_validator import OAS30Validator
from openapi_spec_validator import validate_spec

from compatibility import check

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(path: Path) -> dict[str, str]:
    return {str(p.relative_to(path)): digest(p) for p in sorted(path.rglob('*')) if p.is_file()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--base')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'result': 'RUNNING', 'source_revision': os.environ.get('GITHUB_SHA'),
              'commands': [], 'fixtures': [], 'limits': [
                  'Foundation diagnostic contract only; business API conventions remain separate.',
                  'Generated clients are disposable private conformance outputs, not authorization or complete validators.',
                  'Exact-byte existing-version freeze is conservative compatibility feedback, not protected admission.',
                  'No current live provider or business API is exercised by this generation job.']}
    def run(name: str, argv: list[str]) -> str:
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=180)
        log = args.output / (name + '.log')
        log.write_text(result.stdout + result.stderr)
        report['commands'].append({'name': name, 'exit_code': result.returncode,
                                   'log': log.name, 'sha256': digest(log)})
        if result.returncode:
            raise RuntimeError(name + ' failed; inspect retained log')
        return result.stdout
    try:
        report['input_sha256'] = {str(p.relative_to(ROOT)): digest(p)
            for folder in ('contracts', 'scripts/p01/contracts', 'tests/contracts')
            for p in sorted((ROOT / folder).rglob('*')) if p.is_file()
            and not any(x in p.parts for x in ('.venv', '__pycache__', 'node_modules'))}
        report['tools'] = {name: importlib.metadata.version(name) for name in
                          ('openapi-generator-cli', 'openapi-spec-validator', 'pydantic')}
        report['generator_version'] = run('generator-version', ['openapi-generator-cli', 'version']).strip()
        if report['generator_version'] != '7.25.0':
            raise ValueError('Unexpected generator version')
        run('compatibility-negative-cases', [sys.executable, str(HERE / 'test_compatibility.py')])
        if args.base:
            report['compatibility'] = check(ROOT, args.base)
        else:
            report['compatibility'] = {'result': 'NOT_RUN', 'reason': 'No Git base in local snapshot'}
        contract = ROOT / 'contracts/openapi/foundation-health-v1.json'
        api = json.loads(contract.read_text())
        validate_spec(api)
        run('openapi-validation', ['openapi-generator-cli', 'validate', '-i', str(contract)])
        fixtures = json.loads((ROOT / 'tests/contracts/health-fixtures.json').read_text())
        for item in fixtures:
            valid = OAS30Validator(api['components']['schemas'][item['schema']]).is_valid(item['value'])
            if valid != item['valid']:
                raise ValueError('Unexpected wire verdict: ' + item['id'])
            report['fixtures'].append({'id': item['id'], 'valid': valid})
        with tempfile.TemporaryDirectory(prefix='p01-health-clients-') as tmp:
            temporary = Path(tmp)
            manifests = {}
            for attempt in ('first', 'second'):
                for language in ('php', 'python', 'typescript-fetch'):
                    target = temporary / attempt / language
                    run('generate-' + attempt + '-' + language, [
                        'openapi-generator-cli', 'generate', '-i', str(contract), '-g', language,
                        '-c', str(HERE / ('config-' + language + '.json')), '-o', str(target),
                        '--global-property', 'apiTests=false,modelTests=false,apiDocs=false,modelDocs=false'])
                    manifests[attempt + '/' + language] = inventory(target)
            for language in ('php', 'python', 'typescript-fetch'):
                if manifests['first/' + language] != manifests['second/' + language]:
                    raise ValueError('Nondeterministic generation: ' + language)
            (args.output / 'generated-sha256.json').write_text(json.dumps(manifests, indent=2) + '\n')
            report['deterministic_generation'] = True
            generated = temporary / 'first'
            sys.path.insert(0, str(generated / 'python'))
            for item in fixtures:
                if item['valid']:
                    module = re.sub(r'(?<!^)(?=[A-Z])', '_', item['schema']).lower()
                    model = getattr(importlib.import_module('p01_health_client.models.' + module), item['schema'])
                    if model.from_dict(item['value']).to_dict() != item['value']:
                        raise ValueError('Python generated roundtrip changed ' + item['id'])
            for index, path in enumerate(sorted((generated / 'php').rglob('*.php'))):
                run('php-lint-' + str(index), ['php', '-l', str(path)])
            observed = json.loads(run('php-wire-and-models', ['php', str(ROOT / 'tests/contracts/health.php'), str(generated / 'php')]))
            if observed != report['fixtures']:
                raise ValueError('PHP/Python wire verdicts differ')
            report['cross_language'] = 'PASS'
            config = {'compilerOptions': {'target': 'ES2022', 'module': 'Node16', 'moduleResolution': 'Node16',
                      'strict': True, 'noEmit': True, 'lib': ['ES2022', 'DOM', 'DOM.Iterable']},
                      'include': ['typescript-fetch/src/**/*.ts']}
            (generated / 'tsconfig.json').write_text(json.dumps(config))
            run('typescript-compile', ['node', str(HERE / 'node_modules/typescript/bin/tsc'), '-p', str(generated / 'tsconfig.json')])
        report['result'] = 'PASS'
    except Exception as error:
        report['result'] = 'FAIL'
        report['error'] = str(error)
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('result', 'source_revision')}))
    return 0 if report['result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
