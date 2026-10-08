"""P00 isolated contract generator experiment. No API or broker is contacted."""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError
from openapi_schema_validator import OAS30Validator
from openapi_spec_validator import validate_spec
from openapi_spec_validator.validation.exceptions import OpenAPIValidationError

ROOT = Path(__file__).resolve().parent
SOURCE_FILES = [
    'pyproject.toml', 'uv.lock', 'package.json', 'package-lock.json',
    'openapi.json', 'event.schema.json', 'fixtures.json',
    'config-php.json', 'config-python.json', 'config-typescript-fetch.json',
    'probe.py', 'probe-python.py', 'probe-typescript.ts',
    'probe-typescript-negative.ts', 'probe-php.php',
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(path: Path) -> dict[str, str]:
    return {str(x.relative_to(path)): digest(x) for x in sorted(path.rglob('*')) if x.is_file()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--require-php', action='store_true')
    args = parser.parse_args()
    results = args.results.resolve()
    results.mkdir(parents=True, exist_ok=True)
    if any(results.iterdir()):
        raise SystemExit('Refusing to overwrite retained experiment evidence')
    report: dict = {
        'started_at': datetime.now(timezone.utc).isoformat(), 'status': 'RUNNING',
        'source_revision': os.environ.get('GITHUB_SHA'),
        'github_run_id': os.environ.get('GITHUB_RUN_ID'),
        'github_run_attempt': os.environ.get('GITHUB_RUN_ATTEMPT'),
        'github_workflow_ref': os.environ.get('GITHUB_WORKFLOW_REF'),
        'workflow_sha256': {str(p.relative_to(ROOT.parents[2])): digest(p) for p in sorted((ROOT.parents[2] / '.github/workflows').glob('*contract*'))},
        'environment': {'python': platform.python_version(), 'system': platform.platform(),
                        'architecture': platform.machine()},
        'input_sha256': {name: digest(ROOT / name) for name in SOURCE_FILES},
        'packages': {name: importlib.metadata.version(name) for name in [
            'openapi-generator-cli', 'openapi-spec-validator', 'openapi-schema-validator',
            'jsonschema', 'pydantic', 'httpx']},
        'commands': [], 'fixture_results': [], 'schema_negative_controls': [],
        'limitations': [
            'Synthetic OpenAPI 3.0.4 subset; no product contract or service is implemented.',
            'JSON Schema event envelope validation does not implement AsyncAPI channels, broker behavior, outbox or inbox.',
            'Generated models/decoders are not complete runtime schema validators; validation must precede deserialization.',
            'No live HTTP endpoint, authentication authority, canonical digest protocol or native operation is tested.',
            'No independent service contract compatibility window or breaking-change checker is qualified.',
        ],
    }

    def run(label: str, command: list[str], cwd: Path, expected: int = 0, contains: str | None = None) -> str:
        observed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=180)
        log = observed.stdout + observed.stderr
        (results / f'{label}.log').write_text(log)
        report['commands'].append({'id': label, 'argv': command, 'exit_code': observed.returncode,
                                   'expected_exit': expected, 'log_sha256': digest(results / f'{label}.log')})
        if observed.returncode != expected or (contains is not None and contains not in log):
            raise AssertionError(f'{label} failed; inspect {label}.log')
        return log

    try:
        for label, command in [('node-version', ['node', '--version']), ('npm-version', ['npm', '--version']),
                               ('java-version', ['java', '-version']), ('uv-version', ['uv', '--version']),
                               ('generator-version', ['openapi-generator-cli', 'version'])]:
            report['environment'][label] = run(label, command, ROOT).strip()
        jars = list(Path(importlib.metadata.distribution('openapi-generator-cli').locate_file('openapi_generator_cli')).glob('*.jar'))
        if len(jars) != 1:
            raise AssertionError('Expected one bundled generator JAR')
        report['generator_jar_sha256'] = digest(jars[0])
        api = json.loads((ROOT / 'openapi.json').read_text())
        event = json.loads((ROOT / 'event.schema.json').read_text())
        validate_spec(api)
        run('openapi-validate', ['openapi-generator-cli', 'validate', '-i', str(ROOT / 'openapi.json')], ROOT)
        Draft202012Validator.check_schema(event)
        for fixture in json.loads((ROOT / 'fixtures.json').read_text()):
            validator = (Draft202012Validator(event, format_checker=FormatChecker()) if fixture['schema'] == 'Event'
                         else OAS30Validator(api['components']['schemas'][fixture['schema']], format_checker=FormatChecker()))
            errors = list(validator.iter_errors(fixture['value']))
            valid = not errors
            report['fixture_results'].append({'id': fixture['id'], 'expected_valid': fixture['valid'],
                                              'actual_valid': valid, 'rejections': [e.validator for e in errors]})
            if valid != fixture['valid']:
                raise AssertionError(f'Unexpected fixture verdict: {fixture["id"]}')
        malformed = copy.deepcopy(api)
        del malformed['paths']['/samples']['post']['responses']
        bad_event = copy.deepcopy(event)
        bad_event['properties']['schema_version'] = {'type': 'imaginary'}
        for name, candidate, validate, expected_error in [
            ('missing-operation-responses', malformed, validate_spec, OpenAPIValidationError),
            ('invalid-event-schema-type', bad_event, Draft202012Validator.check_schema, SchemaError),
        ]:
            try:
                validate(candidate)
            except expected_error as error:
                report['schema_negative_controls'].append({'id': name, 'rejected': True,
                                                           'exception': type(error).__name__})
            else:
                raise AssertionError(f'Malformed schema accepted: {name}')
        with tempfile.TemporaryDirectory(prefix='p00-contracts-') as temporary:
            work = Path(temporary)
            generated = work / 'first'
            manifests = {}
            for attempt in ['first', 'second']:
                for generator in ['php', 'python', 'typescript-fetch']:
                    target = work / attempt / generator
                    run(f'generate-{attempt}-{generator}', [
                        'openapi-generator-cli', 'generate', '-i', str(ROOT / 'openapi.json'),
                        '-g', generator, '-c', str(ROOT / f'config-{generator}.json'), '-o', str(target),
                        '--global-property', 'apiTests=false,modelTests=false,apiDocs=false,modelDocs=false',
                    ], ROOT)
                    manifests[f'{attempt}/{generator}'] = inventory(target)
            for generator in ['php', 'python', 'typescript-fetch']:
                if manifests[f'first/{generator}'] != manifests[f'second/{generator}']:
                    raise AssertionError(f'Non-deterministic generation: {generator}')
            (results / 'generated-sha256.json').write_text(json.dumps(manifests, indent=2, sort_keys=True) + '\n')
            report['generated_counts'] = {g: len(manifests[f'first/{g}']) for g in ['php', 'python', 'typescript-fetch']}
            report['deterministic_generation'] = True
            # Prove the output-drift comparison also detects a changed contract input.
            changed = copy.deepcopy(api)
            changed['components']['schemas']['Sample']['properties']['phase']['enum'].append('changed_probe')
            changed_path = work / 'changed.json'
            changed_path.write_text(json.dumps(changed))
            run('generate-changed-schema', ['openapi-generator-cli', 'generate', '-i', str(changed_path),
                '-g', 'typescript-fetch', '-c', str(ROOT / 'config-typescript-fetch.json'), '-o', str(work / 'changed'),
                '--global-property', 'apiTests=false,modelTests=false,apiDocs=false,modelDocs=false'], ROOT)
            if inventory(work / 'changed') == manifests['first/typescript-fetch']:
                raise AssertionError('Changed contract did not alter generated output')
            report['schema_drift_negative_control'] = 'PASS'
            run('python-compile', [sys.executable, '-m', 'compileall', '-q', str(generated / 'python')], ROOT)
            run('python-models', [sys.executable, str(ROOT / 'probe-python.py'), str(generated / 'python'), str(ROOT / 'fixtures.json')], ROOT)
            shutil.copyfile(ROOT / 'probe-typescript.ts', generated / 'probe-typescript.ts')
            config = {'compilerOptions': {'target': 'ES2022', 'module': 'Node16', 'moduleResolution': 'Node16',
                'strict': True, 'skipLibCheck': False, 'esModuleInterop': True, 'lib': ['ES2022', 'DOM', 'DOM.Iterable'],
                'types': ['node'], 'typeRoots': [str(ROOT / 'node_modules/@types')], 'outDir': str(work / 'compiled')},
                'include': ['typescript-fetch/src/**/*.ts', 'probe-typescript.ts']}
            (generated / 'tsconfig.json').write_text(json.dumps(config))
            tsc = str(ROOT / 'node_modules/typescript/bin/tsc')
            run('typescript-compile', ['node', tsc, '-p', str(generated / 'tsconfig.json')], ROOT)
            run('typescript-models-and-mock-http', ['node', str(work / 'compiled/probe-typescript.js'), str(ROOT / 'fixtures.json')], ROOT)
            shutil.copyfile(ROOT / 'probe-typescript-negative.ts', generated / 'probe-typescript-negative.ts')
            config['include'].append('probe-typescript-negative.ts')
            config['compilerOptions']['noEmit'] = True
            (generated / 'tsconfig.json').write_text(json.dumps(config))
            run('typescript-invalid-enum', ['node', tsc, '-p', str(generated / 'tsconfig.json')], ROOT, expected=2, contains='probe-typescript-negative.ts(2,68): error TS2322')
            php = shutil.which('php')
            if php:
                report['environment']['php'] = run('php-version', [php, '--version'], ROOT).strip()
                for index, source in enumerate(sorted((generated / 'php').rglob('*.php'))):
                    run(f'php-lint-{index:02}', [php, '-l', str(source)], ROOT)
                run('php-models', [php, str(ROOT / 'probe-php.php'), str(generated / 'php'), str(ROOT / 'fixtures.json')], ROOT)
                report['php_status'] = 'PASS'
            elif args.require_php:
                raise AssertionError('PHP required but unavailable')
            else:
                report['php_status'] = 'NOT_RUN'
            report['status'] = 'PASS' if php else 'LOCAL_PASS_PHP_NOT_RUN'
    except Exception as error:
        report['status'] = 'FAIL'
        report['error'] = str(error)
        (results / 'failure.log').write_text(traceback.format_exc())
    finally:
        report['finished_at'] = datetime.now(timezone.utc).isoformat()
        (results / 'report.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': report['status'], 'results': str(results)}))
    return 1 if report['status'] == 'FAIL' else 0


if __name__ == '__main__':
    raise SystemExit(main())
