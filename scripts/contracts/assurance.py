"""Contract assurance inventory: derived from the active canonical registry, never a hand-maintained operation list.

Separate structural validity from measured producer, consumer and authorization
evidence. An absent, stale or synthetic result NEVER qualifies an operation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate_spec

ROOT = Path(__file__).resolve().parents[2]
METHODS = frozenset({"get", "post", "put", "patch", "delete"})
KINDS = ("openapi", "asyncapi", "schemas", "capabilities", "platforms")
CLAIMS = ("route", "producer", "consumer", "authentication", "authorization", "tenant_isolation")
PROVIDER = {
    "contracts/capabilities/definitions-v1.json":
        "contracts/schemas/capabilities/definitions-v1.json",
    "contracts/capabilities/migration-collection-manifest-v1.json":
        "contracts/schemas/capabilities/migration-collection-manifest-v1.json",
    "contracts/capabilities/migration-feature-policy-v1.json":
        "contracts/schemas/capabilities/migration-feature-policy-v1.json",
    "contracts/capabilities/migration-field-crosswalk-v1.json":
        "contracts/schemas/capabilities/migration-field-crosswalk-v1.json",
    "contracts/capabilities/native-security-api-registry-v1.json":
        "contracts/schemas/capabilities/native-security-api-registry-v1.json",
    "contracts/platforms/ahv/source-profile-v1.json":
        "contracts/schemas/platforms/source-profile-v1.json",
    "contracts/platforms/openstack/source-profile-v1.json":
        "contracts/schemas/platforms/source-profile-v1.json",
}


def read(path: Path):
    if path.suffix in {".yaml", ".yml"}:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    return json.loads(path.read_text(encoding="utf-8"))


def fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def operation_key(owner: str, method: str, path: str) -> str:
    return json.dumps([owner, method.upper(), path], separators=(",", ":"))


def inventory(root: Path = ROOT) -> dict:
    registry = read(root / "architecture/contract-consumers.json")
    releases, operations = [], []
    seen_releases, seen_operations = set(), set()
    for release in registry["active_releases"]:
        path = release["path"]
        if path in seen_releases:
            raise ValueError(f"Duplicate contract: {path}")
        seen_releases.add(path)
        if not path.startswith(tuple("contracts/" + p + "/" for p in KINDS)):
            raise ValueError(f"Unknown canonical contract location: {path}")
        disk = root / path
        if not disk.is_file():
            raise ValueError(f"Missing canonical contract: {path}")
        doc = read(disk)
        if not isinstance(doc, dict):
            raise ValueError(f"Malformed canonical contract: {path}")
        kind = path.split("/")[1]
        releases.append({
            "path": path, "kind": kind, "owner": release["owner"],
            "consumers": sorted(set(release.get("consumers", []))),
            "sha256": fingerprint(disk),
            "operation_count": 0,
        })
        if kind == "openapi":
            validate_spec(doc)
            for uri, item in doc["paths"].items():
                for method, spec in item.items():
                    if method not in METHODS:
                        continue
                    identity = operation_key(release["owner"], method, uri)
                    if identity in seen_operations:
                        raise ValueError(f"Duplicate contract operation: {identity}")
                    seen_operations.add(identity)
                    if not spec.get("operationId") or not isinstance(spec.get("responses"), dict):
                        raise ValueError(f"Missing operation identity/responses: {identity}")
                    security = spec.get("security", doc.get("security", []))
                    if not isinstance(security, list):
                        raise ValueError(f"Invalid operation security: {identity}")
                    cases = sorted(spec["responses"])
                    if not cases:
                        raise ValueError(f"No HTTP responses contracted: {identity}")
                    operations.append({
                        "key": identity, "release": path,
                        "release_sha256": releases[-1]["sha256"],
                        "owner": release["owner"], "consumers": releases[-1]["consumers"],
                        "method": method.upper(), "path": uri, "operation_id": spec["operationId"],
                        # An explicit empty security alternative makes an
                        # operation publicly callable even if other alternatives
                        # require credentials.
                        "security_required": bool(security) and all(bool(x) for x in security),
                        # Shared foundation health is service-scoped diagnostic
                        # access, not a tenant-bound authority operation. Bearer
                        # checks still apply, but a fabricated tenant credential
                        # cannot be required to qualify a tenantless health read.
                        "tenant_isolation_required": bool(security) and all(bool(x) for x in security)
                        and not (release["owner"] == "contract-platform"
                                 and uri.startswith("/health/")),
                        "response_statuses": cases,
                        "has_request_body": bool(spec.get("requestBody")),
                    })
                    releases[-1]["operation_count"] += 1
        elif kind in {"capabilities", "platforms"}:
            source = PROVIDER.get(path)
            if not source:
                raise ValueError(f"Unmapped provider catalogue schema: {path}")
            schema = read(root / source)
            Draft202012Validator.check_schema(schema)
            Draft202012Validator(schema, format_checker=FormatChecker()).validate(doc)
        elif kind == "schemas":
            Draft202012Validator.check_schema(doc)
        elif kind == "asyncapi":
            if doc.get("asyncapi") != "3.0.0":
                raise ValueError(f"Invalid active AsyncAPI release: {path}")
    return {
        "schema_version": 1,
        "releases": sorted(releases, key=lambda x: x["path"]),
        "operations": sorted(operations, key=lambda x: x["key"]),
        "counts": dict(Counter(x["kind"] for x in releases)),
    }


def assess(root: Path = ROOT, observations: list[dict] | None = None,
           require_provenance: bool = False) -> dict:
    data = inventory(root)
    operations = {r["key"]: r for r in data["operations"]}
    releases = {r["path"]: r for r in data["releases"]}
    proofs = {key: {} for key in [*operations, *releases]}
    consumer_proofs = {key: {} for key in proofs}

    def consumers_for(key: str) -> list[str]:
        boundary = operations[key] if key in operations else releases[key]
        # A source-only definition needs its owner's actual validator, never
        # an invented remote consumer. Other boundaries require every caller.
        return boundary["consumers"] or [boundary["owner"]]

    for observation in observations or []:
        key = observation.get("key")
        claim = observation.get("claim")
        if key not in proofs or claim not in CLAIMS:
            raise ValueError(f"Unregistered operation or evidence claim: {key} {claim}")
        if key in operations:
            expected_hash = operations[key]["release_sha256"]
        else:
            expected_hash = releases[key]["sha256"]
        if observation.get("release_sha256") != expected_hash:
            raise ValueError(f"Stale operation evidence: {key}")
        if require_provenance:
            run_id, revision = os.environ.get("GITHUB_RUN_ID"), os.environ.get("GITHUB_SHA")
            attempt = os.environ.get("GITHUB_RUN_ATTEMPT")
            if (not run_id or not revision or not attempt
                    or re.fullmatch(r"[1-9][0-9]*", attempt) is None
                    or observation.get("run_id") != run_id
                    or observation.get("revision") != revision
                    or observation.get("run_attempt") != attempt):
                raise ValueError(f"Unattested operation evidence for current CI run: {key}")
        if observation.get("source") not in {"live-router", "live-producer", "live-consumer", "live-denial"}:
            raise ValueError(f"Non-executable evidence is inadmissible: {key}")
        appropriate = {
            "route": "live-router", "producer": "live-producer",
            "consumer": "live-consumer", "authentication": "live-denial",
            "authorization": "live-denial",
            "tenant_isolation": "live-denial",
        }[claim]
        if observation["source"] != appropriate or observation.get("result") != "PASS":
            raise ValueError(f"Wrong evidence source or verdict: {key} {claim}")
        if not isinstance(observation.get("test"), str) or not observation["test"].strip():
            raise ValueError(f"Missing executable test identity: {key} {claim}")
        # Missing or invalid credentials cannot prove authenticated tenant isolation.
        if claim == "authentication" and (
            observation.get("denial_kind") not in {"missing-credential", "invalid-credential"}
            or observation.get("status_code") not in (401, 403)
        ):
            raise ValueError(f"Authentication evidence lacks a real credential denial: {key}")
        if claim == "authorization" and (
            observation.get("authenticated") is not True
            or observation.get("authority_checked") != "current-effective-authority"
            or observation.get("denial_kind") not in {
                "revoked-membership", "revoked-role", "revoked-delegation",
                "wrong-scope", "unauthorized-service", "insufficient-authority",
            }
            or observation.get("status_code") not in (403, 404)
            or observation.get("unauthorized_disclosure") is not False
            or observation.get("unauthorized_mutation") is not False
        ):
            raise ValueError(f"Authorization evidence requires an authenticated current-authority denial without effects: {key}")
        if claim == "tenant_isolation" and (
            observation.get("denial_kind") != "cross-tenant"
            or observation.get("authenticated") is not True
            or observation.get("status_code") not in (403, 404)
            or not isinstance(observation.get("credential_tenant"), str)
            or not observation["credential_tenant"]
            or not isinstance(observation.get("requested_tenant"), str)
            or not observation["requested_tenant"]
            or observation["credential_tenant"] == observation["requested_tenant"]
            or observation.get("unauthorized_disclosure") is not False
            or observation.get("unauthorized_mutation") is not False
        ):
            raise ValueError(f"Tenant isolation evidence requires an authenticated cross-tenant denial: {key}")
        if key in releases and claim not in {"producer", "consumer"}:
            raise ValueError(f"Release assurance cannot claim HTTP-only evidence: {key} {claim}")
        if claim == "consumer":
            consumer = observation.get("consumer_id")
            boundary = operations[key] if key in operations else releases[key]
            if (not isinstance(consumer, str) or consumer not in consumers_for(key)
                    or (not boundary["consumers"]
                        and observation.get("consumer_boundary") != "owner-local")):
                raise ValueError(f"Consumer evidence must name its executed registered or owner-local boundary: {key}")
            if consumer in consumer_proofs[key]:
                raise ValueError(f"Duplicate operation assurance evidence: {key} consumer {consumer}")
            consumer_proofs[key][consumer] = {"source": observation["source"], "test": observation["test"]}
            continue
        if claim in proofs[key]:
            raise ValueError(f"Duplicate operation assurance evidence: {key} {claim}")
        proofs[key][claim] = {"source": observation["source"], "test": observation["test"]}

    def consumer_coverage(key: str) -> dict:
        required = consumers_for(key)
        verified = sorted(consumer_proofs[key])
        return {"required": required, "verified": verified,
                "missing": sorted(set(required) - set(verified))}

    for key in proofs:
        if not consumer_coverage(key)["missing"]:
            proofs[key]["consumer"] = consumer_proofs[key]
    coverage = []
    for key, operation in operations.items():
        required = ["route", "producer", "consumer"]
        if operation["security_required"]:
            required.extend(("authentication", "authorization"))
            if operation["tenant_isolation_required"]:
                required.append("tenant_isolation")
        missing = [claim for claim in required if claim not in proofs[key]]
        coverage.append({
            "key": key, "release": operation["release"],
            "required": required, "verified": sorted(proofs[key]),
            "missing": missing, "qualified": not missing,
            "consumer_coverage": consumer_coverage(key),
        })
    groups: dict[str, list[dict]] = {}
    for operation in coverage:
        groups.setdefault(operation["release"], []).append(operation)
    release_coverage = []
    for path, release in releases.items():
        if release["kind"] == "openapi":
            members = groups.get(path, [])
            if len(members) != release["operation_count"] or not members:
                raise ValueError(f"Active HTTP release has no complete operation coverage: {path}")
            qualified = all(member["qualified"] for member in members)
            missing = sorted({claim for member in members for claim in member["missing"]})
            verified = sorted(set.intersection(*(set(member["verified"]) for member in members)))
            required = sorted({claim for member in members for claim in member["required"]})
        else:
            required = ["producer", "consumer"]
            verified = sorted(proofs[path])
            missing = [claim for claim in required if claim not in proofs[path]]
            qualified = not missing
        release_coverage.append({
            "path": path, "kind": release["kind"],
            "required": required, "verified": verified,
            "missing": missing, "qualified": qualified,
            **({"consumer_coverage": consumer_coverage(path)}
               if release["kind"] != "openapi" else {}),
        })
    data["coverage"] = coverage
    data["release_coverage"] = release_coverage
    data["summary"] = {
        "canonical_releases": len(releases),
        "http_operations": len(operations),
        "qualified_canonical_releases": sum(c["qualified"] for c in release_coverage),
        "unqualified_canonical_releases": sum(not c["qualified"] for c in release_coverage),
        "qualified_http_operations": sum(c["qualified"] for c in coverage),
        "unqualified_http_operations": sum(not c["qualified"] for c in coverage),
        "required_claims": sum(len(c["required"]) for c in coverage)
                           + sum(len(c["required"]) for c in release_coverage
                                 if c["kind"] != "openapi"),
        "verified_claims": sum(len(c["verified"]) for c in coverage)
                           + sum(len(c["verified"]) for c in release_coverage
                                 if c["kind"] != "openapi"),
        "required_consumer_boundaries": sum(len(consumers_for(key)) for key in [
            *operations, *(p for p, r in releases.items() if r["kind"] != "openapi")]),
        "verified_consumer_boundaries": sum(len(consumer_proofs[key]) for key in [
            *operations, *(p for p, r in releases.items() if r["kind"] != "openapi")]),
    }
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observations", type=Path, help="JSON array of measured execution evidence")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-qualified", action="store_true")
    args = parser.parse_args()
    evidence = read(args.observations) if args.observations else []
    result = assess(observations=evidence, require_provenance=args.require_qualified)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["summary"], sort_keys=True))
    if args.require_qualified and (result["summary"]["unqualified_http_operations"] or result["summary"]["unqualified_canonical_releases"]):
        print("UNQUALIFIED operations: " + ", ".join(
            item["key"] for item in result["coverage"] if not item["qualified"]
        )[:3500])
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
