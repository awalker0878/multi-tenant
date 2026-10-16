"""Admit actual successful journey wire measurements as producer proof only."""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from assurance import ROOT, inventory, operation_key


def producers(folder: Path, existing: list[dict], root: Path = ROOT) -> list[dict]:
    operations = {row["key"]: row for row in inventory(root)["operations"]}
    proved = {row["key"] for row in existing if row.get("claim") == "producer"}
    evidence = []
    expected = {"revision": os.environ.get("GITHUB_SHA"),
                "run_id": os.environ.get("GITHUB_RUN_ID"),
                "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT")}
    if not all(expected.values()):
        raise ValueError("Current journey CI provenance is required")
    validator = "scripts/contracts/route_conformance.py"
    validator_hash = hashlib.sha256((root / validator).read_bytes()).hexdigest()
    for wire in sorted(folder.rglob("http-conformance.json")):
        report = json.loads((wire.parent / "report.json").read_text())
        if any(report.get(name) != expected[name] for name in ("run_id", "run_attempt")) or (
            report.get("source_revision") != expected["revision"]
        ):
            raise ValueError("Stale journey run or source provenance")
        # A partly completed journey remains diagnostic. No global success is
        # inferred from a valid individual response in a failing campaign.
        if report.get("result") != "PASS" or report.get("source_unchanged") is not True:
            continue
        if (report.get("source_sha256", {}).get(validator) != validator_hash
                or report.get("artifact_sha256", {}).get(wire.name)
                != hashlib.sha256(wire.read_bytes()).hexdigest()):
            raise ValueError("Journey validator or measured wire bytes differ")
        rows = json.loads(wire.read_text())
        if not isinstance(rows, list):
            raise ValueError("Malformed journey measurements")
        for row in rows:
            if any(row.get(name) != value for name, value in expected.items()):
                raise ValueError("Stale journey measurement provenance")
            if row.get("positive_conformance") is not True:
                continue
            key = operation_key(row["owner"], row["method"], row["path"])
            operation = operations.get(key)
            if (operation is None or row.get("release") != operation["release"]
                    or row.get("release_sha256") != operation["release_sha256"]
                    or row.get("operation_id") != operation["operation_id"]):
                raise ValueError("Journey operation or canonical release differs")
            status = row.get("status_code")
            if (type(status) is not int or not 200 <= status < 300
                    or (str(status) not in operation["response_statuses"]
                        and "default" not in operation["response_statuses"])
                    or row.get("request_valid") is not True
                    or row.get("response_valid") is not True
                    or row.get("test") not in {
                        "scripts/p05/verify_live.py:wire", "scripts/p06/verify_live.py:wire"}
                    or not isinstance(row.get("response_sha256"), str)
                    or re.fullmatch(r"[0-9a-f]{64}", row["response_sha256"]) is None):
                raise ValueError("Journey lacks an independently validated positive response")
            # Repeated browser observations do not replace independently
            # executed consumer/security tests or fabricate image provenance.
            if key not in proved:
                evidence.append({"key": key, "claim": "producer", "source": "live-producer",
                                 "result": "PASS", "release_sha256": row["release_sha256"],
                                 "test": row["test"], "status_code": status,
                                 "response_sha256": row["response_sha256"], **expected})
                proved.add(key)
    return evidence


def security(folder: Path, existing: list[dict], root: Path = ROOT) -> list[dict]:
    """Admit measured authenticated denials only with positive and durable controls."""
    from assurance import assess
    operations = {row['key']: row for row in inventory(root)['operations']}
    proved = {(row['key'], row['claim']) for row in existing}
    expected = {'revision': os.environ.get('GITHUB_SHA'),
                'run_id': os.environ.get('GITHUB_RUN_ID'),
                'run_attempt': os.environ.get('GITHUB_RUN_ATTEMPT')}
    if not all(expected.values()):
        raise ValueError('Current journey CI provenance is required')
    sources = ('scripts/p06/live_execution.py', 'scripts/contracts/route_conformance.py')
    hashes = {source: hashlib.sha256((root/source).read_bytes()).hexdigest() for source in sources}
    evidence = []
    for file in sorted(folder.rglob('security-conformance.json')):
        report = json.loads((file.parent/'report.json').read_text())
        if (report.get('source_revision') != expected['revision']
                or any(report.get(key) != expected[key] for key in ('run_id', 'run_attempt'))):
            raise ValueError('Stale journey security provenance')
        if report.get('result') != 'PASS' or report.get('source_unchanged') is not True:
            continue
        if (any(report.get('source_sha256', {}).get(source) != digest for source, digest in hashes.items())
                or report.get('artifact_sha256', {}).get(file.name)
                != hashlib.sha256(file.read_bytes()).hexdigest()):
            raise ValueError('Journey security source or measured bytes differ')
        rows = json.loads(file.read_text())
        if not isinstance(rows, list):
            raise ValueError('Malformed journey security measurements')
        for row in rows:
            operation = operations.get(row.get('key'))
            positive = row.get('positive_status_code')
            before, after = row.get('state_before_sha256'), row.get('state_after_sha256')
            if (operation is None or row.get('claim') not in {'authorization', 'tenant_isolation'}
                    or any(row.get(key) != value for key, value in expected.items())
                    or row.get('test') != 'scripts/p06/live_execution.py:security_probes'
                    or row.get('authority_checked') != 'current-effective-authority'
                    or type(positive) is not int or not 200 <= positive < 300
                    or str(positive) not in operation['response_statuses']
                    or row.get('request_valid') is not True or row.get('response_valid') is not True
                    or not isinstance(before, str) or re.fullmatch(r'[a-f0-9]{64}', before) is None
                    or before != after):
                raise ValueError('Journey security lacks valid positive and unchanged-state controls')
            # Reuse the independent claim admission checks for tenant separation,
            # effective authority, exact release, disclosure and mutation verdicts.
            assess(root, [row], require_provenance=True)
            identity = (row['key'], row['claim'])
            if identity not in proved:
                evidence.append(row)
                proved.add(identity)
    return evidence


def consumers(folder: Path, existing: list[dict], root: Path = ROOT) -> list[dict]:
    """Qualify only actual Console loaders and their exercised request controls."""
    from assurance import assess
    operations = {row['key']: row for row in inventory(root)['operations']}
    releases = {row['path']: row for row in json.loads(
        (root/'architecture/contract-consumers.json').read_text())['active_releases']}
    expected = {'revision': os.environ.get('GITHUB_SHA'),
                'run_id': os.environ.get('GITHUB_RUN_ID'),
                'run_attempt': os.environ.get('GITHUB_RUN_ATTEMPT')}
    if not all(expected.values()):
        raise ValueError('Current journey CI provenance is required')
    prefix = '/v1/tenants/{tenant}/applications/{application}/environments/{environment}/'
    read_faults = ['id', 'tenant_id', 'application_id', 'environment']
    binding_faults = ['binding.plan_id', 'binding.tenant_id', 'binding.resource_id',
                      'binding.environment', 'binding.site_id']
    specifications = {
        'consumer-conformance.json': ('lifecycle', 'scripts/p06/verify_console_consumers.php',
            'apps/console/app/Infrastructure/Jobs/JobsClient.php', 'JobsClient', {
                ('POST', '/v1/tenants/{tenant}/jobs'): ['plan_id', 'plan_digest', 'approval_id', 'status_code'],
                ('GET', '/v1/tenants/{tenant}/jobs/{job}'): ['id', 'tenant_id', 'uncontracted', 'status_code'],
                ('POST', '/v1/tenants/{tenant}/jobs/{job}/commands'): ['job_id', 'command_id', 'action', 'status_code'],
            }),
        'planning-consumer-conformance.json': ('planning', 'scripts/p05/verify_console_consumers.php',
            'apps/console/app/Infrastructure/Planning/PlanningClient.php', 'PlanningClient', {
                ('POST', prefix+'assessments'): ['kind', 'uncontracted', 'status_code'],
                ('GET', prefix+'assessments/{record}'): [*read_faults, 'uncontracted', 'status_code'],
                ('POST', prefix+'plans'): ['kind', *binding_faults, 'binding.digest', 'uncontracted', 'status_code'],
                ('GET', prefix+'plans/{record}'): [*read_faults, *binding_faults,
                    *['content.scope.'+field for field in ['tenant_id', 'resource_id', 'environment', 'site_id']],
                    'uncontracted', 'status_code'],
                ('POST', prefix+'plans/{record}/validity'): ['uncontracted', 'status_code'],
                ('POST', prefix+'plans/{record}/diff'): ['uncontracted', 'status_code'],
            }),
    }
    proved = {(row['key'], row.get('consumer_id')) for row in existing if row.get('claim') == 'consumer'}
    evidence = []
    files = sorted(file for filename in specifications for file in folder.rglob(filename))
    for file in files:
        owner, witness, loader, client, controls = specifications[file.name]
        sources = [witness, loader]
        if owner == 'planning':
            sources += ['scripts/p05/live_campaign.py', 'scripts/p04/live_fixture.py']
        hashes = {path: hashlib.sha256((root/path).read_bytes()).hexdigest() for path in sources}
        report = json.loads((file.parent/'report.json').read_text())
        if (report.get('source_revision') != expected['revision']
                or any(report.get(key) != expected[key] for key in ('run_id', 'run_attempt'))):
            raise ValueError('Stale journey consumer provenance')
        if report.get('result') != 'PASS' or report.get('source_unchanged') is not True:
            continue
        if (any(report.get('source_sha256', {}).get(source) != digest for source, digest in hashes.items())
                or report.get('artifact_sha256', {}).get(file.name) != hashlib.sha256(file.read_bytes()).hexdigest()):
            raise ValueError('Journey consumer source or measured bytes differ')
        rows = json.loads(file.read_text())
        if not isinstance(rows, list):
            raise ValueError('Malformed journey consumer measurements')
        for row in rows:
            operation = operations.get(row.get('key'))
            status, digest = row.get('positive_status_code'), row.get('response_sha256')
            if (operation is None or operation['owner'] != owner
                    or row.get('test') != witness+':'+client or row.get('consumer_id') != 'console'
                    or row.get('claim') != 'consumer' or row.get('consumer_loader') != loader
                    or row.get('loader_sha256') != hashes[loader]
                    or any(row.get(key) != value for key, value in expected.items())
                    or (operation['method'], operation['path']) not in controls
                    or row.get('rejected_response_substitutions') != controls[(operation['method'], operation['path'])]
                    or type(status) is not int or not 200 <= status < 300
                    or str(status) not in operation['response_statuses']
                    or not isinstance(digest, str) or re.fullmatch('[0-9a-f]{64}', digest) is None):
                raise ValueError('Journey consumer lacks its executed loader and response controls')
            copy = row.get('installed_copy')
            if (copy not in releases[operation['release']].get('copies', [])
                    or row.get('installed_sha256') != operation['release_sha256']
                    or hashlib.sha256((root/copy).read_bytes()).hexdigest() != operation['release_sha256']):
                raise ValueError('Journey consumer installed release differs')
            assess(root, [row], require_provenance=True)
            identity = (row['key'], row['consumer_id'])
            if identity not in proved:
                evidence.append(row)
                proved.add(identity)
    return evidence
