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
    if app not in {"governance", "catalogue"}:
        raise ValueError(f"Unsupported Laravel service: {app}")
    registry = json.loads((root / "architecture/contract-consumers.json").read_text())
    releases = [
        row for row in registry["active_releases"]
        if row["owner"] == app and row["path"].startswith("contracts/openapi/")
    ]
    if not releases:
        raise ValueError(f"No active APIs registered for {app}")
    for row in releases:
        doc = json.loads((root / row["path"]).read_text())
        compare_declared(doc, runtime, row["path"])
    return len(releases)



# This is deliberately a source-independent probe of the concrete router
# object, rather than another regular-expression extraction from OpenAPI.
SAMPLE_UUID = "10000000-0000-4000-8000-000000000001"


def synthetic_path(path: str) -> str:
    return PARAMETER.sub(SAMPLE_UUID, path)


def verify_inventory(root: Path = ROOT) -> int:
    from inventory.interfaces.discovery import ROUTES
    spec = json.loads((root / "contracts/openapi/inventory-v1.9.json").read_text())
    missing = []
    for method, path in routes_in_openapi(spec):
        concrete = synthetic_path(path)
        if not any(m == method and re.fullmatch(pattern, concrete) for m, pattern, _, _ in ROUTES):
            missing.append((method, path))
    if missing:
        raise ValueError(f"Inventory OpenAPI operations without executable route matches: {sorted(missing)}")

    # Inventory's PlanningInputApp is a distinct authenticated ASGI router.
    # Probe it directly; discovery.ROUTES omits this internal producer entirely.
    import asyncio
    from inventory.interfaces.planning import PlanningInputApp
    app = PlanningInputApp(discovery=None, authority=lambda *args: None)
    tenant, application, environment, site = [SAMPLE_UUID] * 4
    paths = (
        f"/internal/tenants/{tenant}/migration-inputs/{application}/{environment}/{site}/1/{'a' * 64}",
        f"/v1/tenants/{tenant}/migration-inputs/{application}/{environment}/{site}/1/{'a' * 64}",
        f"/internal/tenants/{tenant}/planning-capability-inputs/{application}/{environment}/{site}/{SAMPLE_UUID}/{SAMPLE_UUID}",
    )
    for path in paths:
        # Missing auth is 400 after matching; 404 means route/verb not matched.
        if asyncio.run(_probe_migration(app, path, "GET")) != 400:
            raise ValueError(f"Inventory owner-operation route unavailable: GET {path}")
        if asyncio.run(_probe_migration(app, path, "POST")) != 404:
            raise ValueError(f"Inventory owner-operation unexpectedly accepts POST: {path}")
    return len(routes_in_openapi(spec)) + len(paths)


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


def verify_planning_migration(root: Path = ROOT) -> int:
    import asyncio
    from planning.interfaces.migration import MigrationPreparationApp
    app = MigrationPreparationApp(authority=None, prepare=lambda *args: {})
    spec = json.loads((root / "contracts/openapi/planning-migration-v1.6.json").read_text())
    declared = routes_in_openapi(spec)
    for method, path in declared:
        status = asyncio.run(_probe_migration(app, synthetic_path(path), method))
        # Missing Authorization is rejected after successful route matching.
        # A 404 indicates no matching runtime route (or wrong HTTP method).
        if status == 404:
            raise ValueError(f"Planning migration OpenAPI lacks executable route: {method} {path}")
    return len(declared)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", choices=["governance", "catalogue", "inventory", "planning-migration"], required=True)
    parser.add_argument("--routes", type=Path)
    args = parser.parse_args()
    if args.app == "inventory":
        count = verify_inventory()
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
