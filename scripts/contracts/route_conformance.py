"""Compare deployed Laravel route manifests with independently published OpenAPI paths.

Run 'php artisan route:list --json' per bounded service. Matching a path alone
is insufficient: the declared verb must exist and all path parameters must match.
This check deliberately does not claim payload conformance; live response tests
run in each producer's product CI.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERBS = {"get", "post", "put", "patch", "delete", "options", "head"}
PARAMETER = re.compile(r"\{([^}]+)\}")


def routes_in_openapi(spec: dict) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for path, item in spec.get("paths", {}).items():
        if not isinstance(item, dict):
            raise ValueError(f"Invalid OpenAPI path item: {path}")
        for method in item:
            if method.lower() in VERBS:
                pairs.add((method.upper(), path))
    return pairs


def routes_in_laravel(entries: list[dict]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for entry in entries:
        uri = entry.get("uri")
        methods = entry.get("method")
        if not isinstance(uri, str) or not isinstance(methods, str):
            raise ValueError("Malformed Laravel route:list JSON")
        path = "/" + uri.lstrip("/")
        path = re.sub(r"\{([A-Za-z_][A-Za-z0-9_]*)\?\}", r"{\1}", path)
        for method in methods.upper().split("|"):
            if method != "HEAD" and method.lower() in VERBS:
                pairs.add((method, path))
    return pairs


def compare_declared(spec: dict, runtime: set[tuple[str, str]], label: str) -> None:
    declared = routes_in_openapi(spec)
    absent = sorted(declared - runtime)
    if absent:
        raise ValueError(f"OpenAPI operations without implemented routes in {label}: {absent}")


def verify_app(app: str, runtime: set[tuple[str, str]], root: Path = ROOT) -> int:
    if app not in {"governance", "catalogue", "assurance"}:
        raise ValueError(f"Unsupported Laravel service: {app}")
    registry = json.loads((root / "architecture/contract-consumers.json").read_text())
    releases = [
        row for row in registry["active_releases"]
        if row["owner"] == app and row["path"].startswith("contracts/openapi/")
    ]
    if not releases:
        raise ValueError(f"No active APIs registered for {app}")
    declared = set()
    for row in releases:
        doc = json.loads((root / row["path"]).read_text())
        compare_declared(doc, runtime, row["path"])
        declared |= routes_in_openapi(doc)
    # Every deployed v1/internal operation must be part of an active release.
    # Every deployed v1/internal operation must be declared; no aliases or exemptions.
    relevant = {(verb, path) for verb, path in runtime
                if path.startswith(("/v1/", "/internal/"))}
    extra = relevant - declared
    if extra:
        raise ValueError(f"Undocumented {app} runtime operations: {sorted(extra)}")
    return len(releases)



# This is deliberately a source-independent probe of the concrete router
# object, rather than another regular-expression extraction from OpenAPI.
SAMPLE_UUID = "10000000-0000-4000-8000-000000000001"


def synthetic_path(path: str) -> str:
    return PARAMETER.sub(SAMPLE_UUID, path)


def compare_inventory_discovery_routes(runtime_routes, declared: set[tuple[str, str]]) -> None:
    """Fail for either a new runtime Inventory route or a missing producer route."""
    for method, pattern, _, _ in runtime_routes:
        matching = [(verb, path) for verb, path in declared
                    if verb == method and re.fullmatch(pattern, synthetic_path(path))]
        if len(matching) != 1:
            raise ValueError(f"Undocumented Inventory discovery route: {method} {pattern}")
    for method, path in declared:
        if not any(m == method and re.fullmatch(pattern, synthetic_path(path))
                   for m, pattern, _, _ in runtime_routes):
            raise ValueError(f"Inventory OpenAPI operation without executable route: {method} {path}")


def compare_inventory_worker_routes(runtime_routes: frozenset[str] | set[str], declared: set[tuple[str, str]]) -> None:
    expected = {("POST", path) for path in runtime_routes}
    if declared != expected:
        raise ValueError(f"Undocumented Inventory worker route or inactive declaration: {sorted(expected ^ declared)}")


def verify_inventory(root: Path = ROOT) -> int:
    from inventory.interfaces.discovery import ROUTES, WORKER_ROUTES
    spec = json.loads((root / "contracts/openapi/inventory-v1.9.json").read_text())
    declared_discovery = routes_in_openapi(spec)
    compare_inventory_discovery_routes(ROUTES, declared_discovery)
    worker_spec = json.loads((root / "contracts/openapi/inventory-collection-worker-v1.json").read_text())
    compare_inventory_worker_routes(WORKER_ROUTES, routes_in_openapi(worker_spec))

    from inventory.interfaces.planning import PlanningInputApp
    import asyncio
    owner_api = json.loads((root / "contracts/openapi/inventory-native-input-v1.3.json").read_text())
    declared_owner = routes_in_openapi(owner_api)
    expected_owner = {
        (method, f"/{prefix}/tenants/{{tenant}}/{resource}/{{application}}/{{environment}}/{{site}}/{suffix}")
        for method in ("GET",)
        for prefix in ("internal", "v1")
        for resource, suffix in (
            ("migration-inputs", "{revision}/{digest}"),
            ("planning-inputs", "{endpoint}/{generation}"),
            ("planning-capability-inputs", "{endpoint}/{generation}"),
        ) if not (prefix == "internal" and resource == "planning-inputs")
    }
    if declared_owner != expected_owner:
        raise ValueError(f"Inventory PlanningInputApp contract omissions: {sorted(expected_owner ^ declared_owner)}")
    app = PlanningInputApp(discovery=None, authority=lambda *args: None)
    paths = sorted(
        f"/{prefix}/tenants/{SAMPLE_UUID}/{resource}/{SAMPLE_UUID}/{SAMPLE_UUID}/{SAMPLE_UUID}/{suffix}"
        for prefix in ("internal", "v1")
        for resource, suffix in (
            ("migration-inputs", f"1/{'a' * 64}"),
            ("planning-inputs", f"{SAMPLE_UUID}/{SAMPLE_UUID}"),
            ("planning-capability-inputs", f"{SAMPLE_UUID}/{SAMPLE_UUID}"),
        ) if not (prefix == "internal" and resource == "planning-inputs")
    )
    from jsonschema import Draft202012Validator
    common_error = json.loads((root / "contracts/schemas/common/error-v1.json").read_text())
    error_validator = Draft202012Validator(common_error)
    for prefix in ("internal", "v1"):
        for resource, suffix in (
            ("migration-inputs", "{revision}/{digest}"),
            ("planning-inputs", "{endpoint}/{generation}"),
            ("planning-capability-inputs", "{endpoint}/{generation}"),
        ):
            if prefix == "internal" and resource == "planning-inputs":
                continue
            template = f"/{prefix}/tenants/{{tenant}}/{resource}/{{application}}/{{environment}}/{{site}}/{suffix}"
            path = next(p for p in paths if p.startswith(f"/{prefix}/") and f"/{resource}/" in p)
            allowed = set(owner_api["paths"][template]["get"]["responses"])
            for label, headers, expected in (
                ("missing-header", [], 401),
                ("malformed-identity", [(b"authorization", b"Bearer short")], 401),
                ("header-bound", [(b"x-header", b"value")] * 41, 413),
            ):
                status, body = asyncio.run(_exchange(app, path, "GET", headers))
                if status != expected or str(status) not in allowed:
                    raise ValueError(f"Inventory owner status drift: {template} {label} => {status}")
                error_validator.validate(body)
            if asyncio.run(_probe_migration(app, path, "POST")) != 404:
                raise ValueError(f"Inventory owner-operation unexpectedly accepts POST: {path}")
    retired = f"/internal/tenants/{SAMPLE_UUID}/planning-inputs/{SAMPLE_UUID}/{SAMPLE_UUID}/{SAMPLE_UUID}/{SAMPLE_UUID}/{SAMPLE_UUID}"
    if asyncio.run(_probe_migration(app, retired, "GET")) != 404:
        raise ValueError("Retired unqualified internal planning-input alias remains exposed")
    for path in paths:
        if asyncio.run(_probe_migration(app, path, "GET")) != 401:
            raise ValueError(f"Inventory owner-operation route unavailable: GET {path}")
    # Positive native-reader path belongs to Inventory's installed runtime,
    # not Planning's package. A revoked reader must fail independently of the
    # response envelope, even if a previously accepted payload exists.
    from unittest.mock import patch
    from inventory.application.workload import WorkloadProfiles
    from inventory.domain.discovery import Rejected
    authorized = []
    def native_reader(*arguments):
        authorized.append(arguments)
    native_app = PlanningInputApp(
        discovery=None, authority=lambda *args: None,
        native_authority=native_reader,
    )
    native_path = next(p for p in paths if p.startswith('/internal/') and '/migration-inputs/' in p)
    headers = [(b"authorization", b"Bearer " + b"a" * 64)]
    with patch.object(WorkloadProfiles, "planning",
                      lambda *args: {"native_write_authorized": False}):
        status, response = asyncio.run(_exchange(native_app, native_path, "GET", headers))
        if status != 200 or response != {"native_write_authorized": False} or len(authorized) != 2:
            raise ValueError("Inventory authenticated native read failed")
        def revoked(*args):
            raise Rejected("native_reader_revoked", 403)
        native_app.native_authority = revoked
        status, _ = asyncio.run(_exchange(native_app, native_path, "GET", headers))
        if status != 403:
            raise ValueError("Inventory native reader accepted revoked authority")
        for code in (409, 422):
            native_app.native_authority = lambda *args, code=code: (_ for _ in ()).throw(Rejected("native_source_rejected", code))
            status, error = asyncio.run(_exchange(native_app, native_path, "GET", headers))
            if status != code or str(status) not in owner_api["paths"][
                "/internal/tenants/{tenant}/migration-inputs/{application}/{environment}/{site}/{revision}/{digest}"
            ]["get"]["responses"]:
                raise ValueError(f"Inventory native reader status {code} not contracted")
            error_validator.validate(error)
        native_app.native_authority = lambda *args: (_ for _ in ()).throw(RuntimeError("unavailable"))
        status, error = asyncio.run(_exchange(native_app, native_path, "GET", headers))
        if status != 503:
            raise ValueError("Inventory native reader unexpected exception did not fail closed")
        error_validator.validate(error)
    # Exercise every Inventory worker operation against the real ASGI boundary,
    # including authentication, method, content, response schema and denial.
    from types import SimpleNamespace
    from unittest.mock import patch as mocked
    from inventory.interfaces.discovery import InventoryApp
    from inventory.application.migration_collection_ledger import MigrationCollectionLedger
    workers = SimpleNamespace(worker=lambda *args: SimpleNamespace(identity="worker", fingerprint="current"))
    fake_discovery = SimpleNamespace(
        claim=lambda *args: {"job": None, "retry_after": 1},
        submit=lambda *args: {"accepted": True, "discovery_id": SAMPLE_UUID, "status": "running"},
    )
    from inventory.infrastructure.migration_collection_evidence import read_collection_coverages
    worker_app = InventoryApp(
        discovery=fake_discovery, authority=workers, evidence=None,
        collection_reader=read_collection_coverages,
    )
    good_headers = [(b"authorization", b"Bearer " + b"a" * 64),
                    (b"content-type", b"application/json")]
    bodies = {
        "claim": {},
        "pages": {},
        "profile-reads": {},
        "receipts": {},
    }
    from jsonschema import Draft202012Validator
    with mocked("inventory.interfaces.discovery.authorize_read",
                lambda *args: {"allowed": True, "retry_after": 0}), mocked.object(
                MigrationCollectionLedger, "publish",
                lambda *args: {"envelope_sha256": "a" * 64, "status": "recorded",
                               "coverage": [], "native_write_authorized": False}):
        for name, body in bodies.items():
            route = "/internal/collections/" + name
            operation = worker_spec["paths"][route]["post"]
            valid = set(operation["responses"])
            request_body = json.dumps(body).encode()
            for label, method, headers, expected in (
                ("missing-header", "POST", [], 400),
                ("malformed-workload", "POST", [(b"authorization", b"Bearer x")], 401),
                ("unsupported-method", "GET", good_headers, 405),
                ("missing-content-type", "POST", good_headers[:1], 415),
                ("header-bound", "POST", [(b"x-header", b"x")] * 41, 413),
            ):
                status, response = asyncio.run(_exchange(worker_app, route, method, headers, request_body))
                if status != expected or str(status) not in valid:
                    raise ValueError(f"Inventory worker emitted undeclared status: {name} {label}={status}")
                error_validator.validate(response)
            status, response = asyncio.run(_exchange(worker_app, route, "POST", good_headers, request_body))
            if status != 200 or "200" not in valid:
                raise ValueError(f"Inventory worker authorized route unavailable: {route}={status}")
            Draft202012Validator(operation["responses"]["200"]["content"]["application/json"]["schema"]).validate(response)
            # Exercise owner-raised denial statuses, not just schema fixtures.
            for denied in (403, 404, 409, 422, 423, 503):
                def reject(*args, denied=denied):
                    if denied == 503:
                        raise RuntimeError("unavailable")
                    raise Rejected("worker_rejected", denied)
                if name == "claim":
                    fake_discovery.claim = reject
                elif name == "pages":
                    fake_discovery.submit = reject
                elif name == "profile-reads":
                    worker_app.authority.worker = reject
                else:
                    worker_app.authority.worker = reject
                status, response = asyncio.run(_exchange(worker_app, route, "POST", good_headers, request_body))
                if status != denied or str(status) not in valid:
                    raise ValueError(f"Inventory worker denial drift: {route} {denied}=>{status}")
                error_validator.validate(response)
            fake_discovery.claim = lambda *args: {"job": None, "retry_after": 1}
            fake_discovery.submit = lambda *args: {"accepted": True, "discovery_id": SAMPLE_UUID, "status": "running"}
            worker_app.authority.worker = lambda *args: SimpleNamespace(identity="worker", fingerprint="current")
    return len(declared_discovery) + len(declared_owner) + len(WORKER_ROUTES)


async def _probe_migration(app, path: str, method: str) -> int:
    captured = []
    async def send(message):
        if message["type"] == "http.response.start":
            captured.append(message["status"])
    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}
    await app({
        "type": "http", "path": path, "method": method,
        "query_string": b"", "headers": [],
    }, receive, send)
    if len(captured) != 1:
        raise ValueError(f"Planning migration router did not return a response: {path}")
    return captured[0]


def assert_planning_composed_route(path: str, destination: str, method: str = "POST") -> None:
    """Probe the deployed router composition, not just its internal handler."""
    import asyncio
    from planning.bootstrap.server import PlanningRouter
    router = PlanningRouter.__new__(PlanningRouter)
    called = []
    for name in ("migration", "native", "planning", "invalidations", "foundation"):
        async def responder(scope, receive, send, owner=name):
            called.append(owner)
            data = json.dumps({"owner": owner}).encode()
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": data})
        setattr(router, name, responder)
    status, payload = asyncio.run(_exchange(router, path, method, []))
    if status != 200 or called != [destination] or payload != {"owner": destination}:
        raise ValueError(f"Composed Planning router dispatched {method} {path} to {called}, expected {destination}")


def verify_planning_migration(root: Path = ROOT) -> int:
    import asyncio
    from planning.interfaces.migration import MigrationPreparationApp
    app = MigrationPreparationApp(authority=None, prepare=lambda *args: {})
    spec = json.loads((root / "contracts/openapi/planning-migration-v1.6.json").read_text())
    declared = routes_in_openapi(spec)
    from planning.bootstrap.server import MIGRATION_SUFFIXES
    contracted = {"/" + path.rsplit("/", 1)[-1] for method, path in declared if method == "POST"}
    if set(MIGRATION_SUFFIXES) != contracted:
        raise ValueError(f"Undocumented Planning migration route: {sorted(set(MIGRATION_SUFFIXES) ^ contracted)}")
    for method, path in declared:
        status = asyncio.run(_probe_migration(app, synthetic_path(path), method))
        # Missing Authorization is rejected after successful route matching.
        # A 404 indicates no matching runtime route (or wrong HTTP method).
        if status == 404:
            raise ValueError(f"Planning migration OpenAPI lacks executable route: {method} {path}")
    for method, path in declared:
        assert_planning_composed_route(synthetic_path(path), "migration", method)
    return len(declared)



async def _exchange(app, path: str, method: str, headers, body: bytes = b""):
    captured = []
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    async def send(message):
        captured.append(message)
    await app({
        "type": "http", "path": path, "method": method,
        "headers": headers, "query_string": b"",
    }, receive, send)
    if len(captured) != 2:
        raise ValueError(f"Incomplete ASGI response: {method} {path}")
    return captured[0]["status"], json.loads(captured[1]["body"])


def verify_lifecycle_native(root: Path = ROOT) -> int:
    import asyncio
    from jsonschema import Draft202012Validator, FormatChecker
    from lifecycle.interfaces.native import NativeBoundaryApp

    spec = json.loads((root / "contracts/openapi/lifecycle-migration-boundary-v2.json").read_text())
    if routes_in_openapi(spec) != {("POST", "/internal/native-grants/checks")}:
        raise ValueError("Lifecycle native-boundary OpenAPI operation changed")
    request_schema = spec["components"]["schemas"]["BoundaryRequest"]
    response_schema = spec["components"]["schemas"]["BoundaryReceipt"]
    binding = {
        **{k: SAMPLE_UUID for k in (
            "tenant_id", "site_id", "resource_id", "job_id", "operation_id",
            "attempt_id", "campaign_id", "executor_id", "epoch",
            "custody_id", "project_id"
        )},
        **{k: "a" * 64 for k in (
            "plan_digest", "operation_plan_sha256", "ownership_digest"
        )},
        "custody_generation": 1, "expires_at": 20,
    }
    grant = {
        **{k: SAMPLE_UUID for k in (
            "job_id", "operation_id", "attempt_id", "grant_id", "epoch", "executor_id"
        )},
        "schema_version": 2, "stage": "capture", "plan_sha256": "a" * 64,
        "intent_digest": "b" * 64, "expires_at": 20, "native_binding": binding,
    }
    request = {"grant": grant, "boundary": "preflight"}
    receipt = {
        "binding_sha256": "a" * 64, "epoch": SAMPLE_UUID,
        "boundary": "preflight", "allowed": True, "authority_use": "native_boundary",
        "evaluated_at": 1, "expires_at": 20,
    }
    validator = FormatChecker()
    Draft202012Validator(request_schema, format_checker=validator).validate(request)
    Draft202012Validator(response_schema, format_checker=validator).validate(receipt)
    calls = []
    class Workflow:
        def boundary(self, tenant, submitted, worker, boundary):
            calls.append((tenant, submitted, worker, boundary))
            return receipt

    app = NativeBoundaryApp(
        Workflow(), lambda token: (SAMPLE_UUID, SAMPLE_UUID)
    )
    headers = [(b"authorization", b"Bearer " + b"a" * 64),
               (b"content-type", b"application/json")]
    path = "/internal/native-grants/checks"
    code, payload = asyncio.run(_exchange(
        app, path, "POST", headers, json.dumps(request).encode()
    ))
    if code != 200 or payload != receipt or len(calls) != 1:
        raise ValueError("Lifecycle native-boundary authorized response failed")
    Draft202012Validator(response_schema, format_checker=validator).validate(payload)
    invalid = {**request, "uncontracted_grant": True}
    code, _ = asyncio.run(_exchange(
        app, path, "POST", headers, json.dumps(invalid).encode()
    ))
    if code != 422 or len(calls) != 1:
        raise ValueError("Lifecycle native-boundary accepted uncontracted input")
    code, _ = asyncio.run(_exchange(app, path, "GET", headers))
    if code != 404:
        raise ValueError("Lifecycle native-boundary accepts uncontracted verb")
    return 1


def verify_planning_immutable(root: Path = ROOT) -> int:
    import asyncio
    from jsonschema import Draft202012Validator, FormatChecker
    from planning.interfaces.planning import PlanningApp

    spec = json.loads((root / "contracts/openapi/planning-immutable-plan-v2.json").read_text())
    if routes_in_openapi(spec) != {("GET", "/v1/tenants/{tenant}/plans/{plan}/revisions/{revision}")}:
        raise ValueError("Planning immutable-plan OpenAPI operation changed")
    bound = {
        "plan_id": SAMPLE_UUID, "revision": 1, "tenant_id": SAMPLE_UUID,
        "action": "application.provision", "site_id": SAMPLE_UUID,
        "environment": SAMPLE_UUID, "resource_id": SAMPLE_UUID,
        "requested_by": SAMPLE_UUID, "executor_ids": [SAMPLE_UUID],
        "valid_until": 20, "digest": "a" * 64,
        "content_digest": "b" * 64, "canonicalization": "p05-json-v1",
        "lane": "operational",
    }
    checked = []
    class Authority:
        def caller(self, credential, audience="console"):
            if audience != "governance_reader":
                raise ValueError("Incorrect immutable plan audience")
            checked.append(credential)

    class Planning:
        def bound_plan(self, tenant, plan, revision):
            if tenant != SAMPLE_UUID or plan != SAMPLE_UUID or revision != 1:
                from planning.domain.model import Rejected
                raise Rejected("not_found", 404)
            return bound

    app = PlanningApp(Planning(), Authority())
    path = f"/v1/tenants/{SAMPLE_UUID}/plans/{SAMPLE_UUID}/revisions/1"
    headers = [(b"authorization", b"Bearer " + b"a" * 64)]
    status, result = asyncio.run(_exchange(app, path, "GET", headers))
    if status != 200 or result != bound or checked != ["a" * 64]:
        raise ValueError("Planning immutable plan authorized response failed")
    schema = spec["components"]["schemas"]["BoundPlan"]
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(result)
    other = "10000000-0000-4000-8000-000000000002"
    rejected_path = f"/v1/tenants/{other}/plans/{SAMPLE_UUID}/revisions/1"
    status, error = asyncio.run(_exchange(app, rejected_path, "GET", headers))
    if status != 404 or error.get("code") != "not-found":
        raise ValueError("Planning immutable plan allowed a cross-tenant read")
    Draft202012Validator(
        spec["components"]["schemas"]["Error"], format_checker=FormatChecker()
    ).validate(error)
    status, error = asyncio.run(_exchange(
        app, path, "GET", [(b"authorization", b"Bearer bad")]
    ))
    if status != 401 or error.get("code") != "invalid-workload":
        raise ValueError("Planning immutable plan invalid credentials were not denied")
    Draft202012Validator(
        spec["components"]["schemas"]["Error"], format_checker=FormatChecker()
    ).validate(error)
    return 1



def verify_planning_lifecycle_reads(root: Path = ROOT) -> int:
    """Run both current producer endpoints with authorized and rejected requests."""
    import asyncio
    from jsonschema import Draft202012Validator, FormatChecker
    from planning.domain.model import Rejected
    from planning.interfaces.planning import PlanningApp

    spec = json.loads((root / "contracts/openapi/planning-lifecycle-reads-v1.json").read_text())
    expected = {
        ("GET", "/v1/tenants/{tenant}/execution-plans/{plan}/revisions/{revision}"),
        ("GET", "/internal/tenants/{tenant}/placement-proposals/{plan}/revisions/{revision}"),
    }
    if routes_in_openapi(spec) != expected:
        raise ValueError("Planning Lifecycle current read operations changed")
    fixture = json.loads((root / "contracts/fixtures/planning/synthetic-plan-v1.1.json").read_text())
    content, binding = fixture["content"], fixture["binding"]
    execution = {"content": content, "binding": binding, "invalidated": False}
    placement = {
        "scope": content["scope"], "plan_id": binding["plan_id"],
        "plan_revision": binding["revision"], "plan_digest": binding["digest"],
        "generation_id": content["inventory_generation"],
        "policy_sha256": "a" * 64, "placement_sha256": "b" * 64,
        "allocations": [{
            "workload_id": "workload-1", "pool_id": "pool-1",
            "native_ref": "pool-native-id", "failure_domain": "domain-1",
            "failure_group": "group-1",
            "vector": {"vcpus": 2, "memory_mib": 2048, "storage_gib": 10,
                       "addresses": 1, "storage_gib:gold": 10},
            "ledger_revision": 1,
        }],
        "native_write_authorized": False,
    }
    validator = Draft202012Validator(
        {"$ref": "#/components/schemas/ExecutionPlan", "components": spec["components"]},
        format_checker=FormatChecker()
    )
    validator.validate(execution)
    placement_validator = Draft202012Validator(
        {"$ref": "#/components/schemas/PlacementProposal", "components": spec["components"]},
        format_checker=FormatChecker()
    )
    placement_validator.validate(placement)
    if validator.is_valid(execution | {"native_write_authorized": True}):
        raise ValueError("Execution contract accepts additional native authority")
    if placement_validator.is_valid(placement | {"native_write_authorized": True}):
        raise ValueError("Placement contract accepted a write authorization flag")
    calls = []
    class Authority:
        def caller(self, credential, audience="console"):
            if audience != "lifecycle_reader" or credential != "a" * 64:
                raise Rejected("not_authorized", 403)
            calls.append(("authority", audience))
    class Planning:
        def execution_plan(self, tenant, plan, revision):
            calls.append(("execution", tenant, plan, revision))
            return execution
        def placement_proposal(self, tenant, plan, revision):
            calls.append(("placement", tenant, plan, revision))
            return placement

    app = PlanningApp(Planning(), Authority())
    base = f"/v1/tenants/{content['scope']['tenant_id']}/execution-plans/{binding['plan_id']}/revisions/1"
    internal = f"/internal/tenants/{content['scope']['tenant_id']}/placement-proposals/{binding['plan_id']}/revisions/1"
    headers = [(b"authorization", b"Bearer " + b"a" * 64)]
    for path, actual, validation in (
        (base, execution, validator), (internal, placement, placement_validator)
    ):
        status, document = asyncio.run(_exchange(app, path, "GET", headers))
        if status != 200 or document != actual:
            raise ValueError(f"Planning Lifecycle authorized read failed: {path}")
        validation.validate(document)
        status, _ = asyncio.run(_exchange(
            app, path, "GET", [(b"authorization", b"Bearer " + b"b" * 64)]
        ))
        if status != 403:
            raise ValueError(f"Planning Lifecycle reader denied request unexpectedly succeeded: {path}")
    if sum(1 for c in calls if c[0] == "authority") != 2:
        raise ValueError("Planning Lifecycle authority was not checked on each read")
    for path in (base, internal):
        assert_planning_composed_route(path, "planning", "GET")
    return 2


def compare_composed_routes(owner: str, runtime: set[tuple[str, str]],
                            releases: tuple[str, ...], root: Path = ROOT) -> int:
    declared = set()
    for name in releases:
        spec = json.loads((root / "contracts/openapi" / name).read_text())
        declared |= routes_in_openapi(spec)
    if declared != runtime:
        raise ValueError(f"Undocumented {owner} composed runtime route: {sorted(declared ^ runtime)}")
    return len(declared)


def verify_python_composition(root: Path = ROOT) -> int:
    from planning.bootstrap.server import HTTP_OPERATIONS as planning_routes
    from lifecycle.bootstrap.server import HTTP_OPERATIONS as lifecycle_routes
    return (compare_composed_routes("Planning", set(planning_routes), tuple(["planning-v1.2.json","planning-migration-v1.6.json","planning-native-v1.json","planning-immutable-plan-v2.json","planning-lifecycle-reads-v1.json","planning-qualification-events-v1.json"]), root)
            + compare_composed_routes("Lifecycle", set(lifecycle_routes), tuple(["lifecycle-v1.json","lifecycle-migration-campaigns-v1.json","lifecycle-internal-authority-v1.json"]), root))



def verify_lifecycle_native_jobs(root: Path = ROOT) -> int:
    """Exercise every native job handler route without claiming producer behavior."""
    import asyncio
    from lifecycle.interfaces.native_jobs import NativeJobsApp

    spec = json.loads((root / "contracts/openapi/lifecycle-native-jobs-v1.1.json").read_text())
    expected = {
        ("POST", "/v1/tenants/{tenant}/native-jobs"),
        ("GET", "/v1/tenants/{tenant}/native-jobs/{job}"),
        ("POST", "/v1/tenants/{tenant}/native-jobs/{job}/stop"),
        ("POST", "/v1/tenants/{tenant}/native-jobs/{job}/continue-transfer"),
    }
    if routes_in_openapi(spec) != expected:
        raise ValueError("Native job router differs from published operations")
    app = NativeJobsApp(workflow=None, authority=None, resolve=lambda *_: {})
    headers = [(b"authorization", b"Bearer short")]
    for method, template in sorted(expected):
        path = synthetic_path(template)
        code, body = asyncio.run(_exchange(app, path, method, headers))
        if code != 401 or body != {"error": "invalid_workload"}:
            raise ValueError(f"Native job handler missing authenticated route: {method} {path}")
        wrong = "GET" if method == "POST" else "POST"
        code, _ = asyncio.run(_exchange(app, path, wrong, headers))
        if code != 404:
            raise ValueError(f"Native job handler accepted uncontracted method: {wrong} {path}")
    code, _ = asyncio.run(_exchange(
        app, f"/v1/tenants/{SAMPLE_UUID}/native-jobs/{SAMPLE_UUID}/uncontracted",
        "POST", headers,
    ))
    if code != 404:
        raise ValueError("Native job handler accepted uncontracted route")
    return len(expected)


def verify_lifecycle_worker_effect_routes(root: Path = ROOT) -> int:
    """Exercise worker-native ASGI routes; invalid caller is not producer proof."""
    import asyncio
    from lifecycle_worker.interfaces.native import NativeEffectApp

    spec = json.loads((root / "contracts/openapi/worker-migration-effect-v2.1.json").read_text())
    expected = {
        ("POST", "/internal/native-effects"),
        ("POST", "/internal/native-transfer-continuations"),
    }
    if routes_in_openapi(spec) != expected:
        raise ValueError("Native effect router differs from published operations")
    app = NativeEffectApp(effects=None, caller=lambda *_: (SAMPLE_UUID, SAMPLE_UUID))
    headers = [(b"authorization", b"Bearer short")]
    for method, path in sorted(expected):
        code, body = asyncio.run(_exchange(app, path, method, headers))
        if code != 401 or body != {"error": "native_effect_held"}:
            raise ValueError(f"Native worker handler missing authenticated route: {method} {path}")
        code, _ = asyncio.run(_exchange(app, path, "GET", headers))
        if code != 404:
            raise ValueError(f"Native worker accepted uncontracted method: GET {path}")
    code, _ = asyncio.run(_exchange(app, "/internal/not-a-native-effect", "POST", headers))
    if code != 404:
        raise ValueError("Native worker accepted uncontracted route")
    return len(expected)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", choices=["governance", "catalogue", "assurance", "inventory", "planning-migration", "lifecycle-native", "lifecycle-native-jobs", "lifecycle-worker-effects", "planning-immutable", "planning-lifecycle", "python-composed"], required=True)
    parser.add_argument("--routes", type=Path)
    args = parser.parse_args()
    if args.app == "python-composed":
        count = verify_python_composition()
        print(json.dumps({"status": "PASS", "app": args.app, "runtime_operations": count}))
    elif args.app == "inventory":
        count = verify_inventory()
        print(json.dumps({"status": "PASS", "app": args.app, "runtime_operations": count}))
    elif args.app in {"lifecycle-native", "planning-immutable", "planning-lifecycle"}:
        count = (verify_lifecycle_native() if args.app == "lifecycle-native"
                 else verify_planning_immutable() if args.app == "planning-immutable"
                 else verify_planning_lifecycle_reads())
        print(json.dumps({"status": "PASS", "app": args.app, "runtime_operations": count}))
    elif args.app in {"lifecycle-native-jobs", "lifecycle-worker-effects"}:
        count = (verify_lifecycle_native_jobs() if args.app == "lifecycle-native-jobs"
                 else verify_lifecycle_worker_effect_routes())
        print(json.dumps({"status": "PASS", "app": args.app, "runtime_operations": count}))
    elif args.app == "planning-migration":
        count = verify_planning_migration()
        print(json.dumps({"status": "PASS", "app": args.app, "runtime_operations": count}))
    else:
        if args.routes is None:
            parser.error("--routes is required for Laravel services")
        routes = routes_in_laravel(json.loads(args.routes.read_text(encoding="utf-8")))
        count = verify_app(args.app, routes)
        print(json.dumps({"status": "PASS", "app": args.app, "active_apis": count,
                          "runtime_operations": len(routes)}))


if __name__ == "__main__":
    main()
