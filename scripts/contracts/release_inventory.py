"""Reproducible per-release Phase 1 evidence inventory; no runtime qualification claim."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import runpy
from pathlib import Path

from artifact_attestation import COMPONENTS
from discovery import read, reference_evidence, verify_dependencies, verify_manifests
from installed_usage import verify_installed_usage
from runtime_inventory import discover_runtime_copies, runtime_sources

ROOT = Path(__file__).resolve().parents[2]


def derive(root: Path = ROOT) -> dict:
    registry = read(root / "architecture/contract-consumers.json")
    releases = {row["path"]: row for row in registry["active_releases"]}
    dependencies = verify_dependencies(root, registry)
    manifests = verify_manifests(root, registry)
    verify_installed_usage(root, registry)
    usage = {
        row["copy"]: row
        for row in read(root / "architecture/installed-contract-usage.json")["copies"]
    }
    refs = reference_evidence(root, set(releases))
    installed = discover_runtime_copies(root)
    # Static executable paths/channels justify ownership and dependency scope.
    # Response behavior, denial and tenant isolation are independently measured
    # by Phase 2; a string match is never emitted as a passing runtime receipt.
    source_paths = set(runtime_sources(root))
    source_paths.update((root / "services").glob("*/routes/*.php"))
    source_paths.update((root / "apps").glob("*/routes/*.php"))
    source_paths.update((root / "services").glob("*/config/*.php"))
    texts = {str(path.relative_to(root)): path.read_text() for path in sorted(source_paths)}
    contexts = {component: owner for component, (owner, _) in COMPONENTS.items()}
    platform_outputs = runpy.run_path(str(root / "scripts/p04/generate_clients.py"))["outputs"]()

    def matching(marker, *, provider=None):
        return [
            {
                "source": source,
                "component": contexts["/".join(Path(source).parts[:2])],
                "kind": "wire-source",
                "marker": marker,
            }
            for source, body in texts.items()
            if marker in body
            and (
                provider is None
                or provider in source.lower()
                or provider in body.lower()
                or (provider == "lifecycle-workers" and "simulator" in body.lower())
            )
        ]

    rows = []
    for path, release in sorted(releases.items()):
        kind = path.split("/")[1]
        doc = read(root / path)
        evidence = list(refs[path])
        external = []
        if path == "contracts/capabilities/migration-collection-manifest-v1.json":
            external = [
                "Planning's independently provisioned PLANNING_MIGRATION_COLLECTION_REGISTRY_FILE and referenced manifest bytes are unavailable; their canonical release identity cannot be verified from this checkout."
            ]
            evidence.append(
                {
                    "source": "services/planning/src/planning/infrastructure/migration_collection_manifest.py",
                    "symbol": "binding",
                    "component": "planning",
                    "kind": "external-mounted-loader",
                    "marker": "PLANNING_MIGRATION_COLLECTION_REGISTRY_FILE",
                }
            )
        if kind == "openapi":
            for uri in doc["paths"]:
                parts = [part for part in uri.split("/") if part and "{" not in part]
                marker = (
                    "/" + parts[-1]
                    if parts[-1] not in {"tenants", "applications", "environments", "identity"}
                    else uri
                )
                evidence.extend(
                    matching(
                        marker,
                        provider=release["owner"]
                        if release["owner"] != "contract-platform"
                        else None,
                    )
                )
        elif kind == "asyncapi":
            for channel in doc["channels"].values():
                address = channel["address"]
                evidence.extend(matching(address))
                evidence.extend(matching(address.removesuffix(".v1")))
            for payload in dependencies[path]:
                for copy in releases[payload].get("copies", []):
                    evidence.append(
                        {
                            "source": usage[copy]["loader"],
                            "component": contexts["/".join(Path(copy).parts[:2])],
                            "kind": "installed-event-payload",
                            "marker": copy,
                        }
                    )
        elif kind == "platforms":
            platform = Path(path).parts[2]
            for output, expected in platform_outputs.items():
                if output.endswith("/" + platform + "_source_contract.py"):
                    if (root / output).read_text() != expected:
                        raise ValueError("Generated platform projection drift: " + output)
                    evidence.append(
                        {
                            "source": output,
                            "component": contexts["/".join(Path(output).parts[:2])],
                            "kind": "generated-projection",
                            "marker": path,
                        }
                    )
        if kind == "schemas" and len(doc.get("required", [])) >= 5:
            # Handwritten validators are source-bound without loading a JSON
            # copy. Recognize an exact root shape on the function's first input.
            for source, body in texts.items():
                if not source.endswith(".py"):
                    continue
                for function in ast.walk(ast.parse(body)):
                    if (
                        not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef))
                        or not function.args.args
                    ):
                        continue
                    first = function.args.args[0].arg
                    for call in ast.walk(function):
                        if (
                            not isinstance(call, ast.Call)
                            or not isinstance(call.func, ast.Name)
                            or call.func.id not in {"shape", "exact"}
                            or len(call.args) < 2
                            or not isinstance(call.args[0], ast.Name)
                            or call.args[0].id != first
                        ):
                            continue
                        try:
                            keys = ast.literal_eval(call.args[1])
                        except (ValueError, TypeError):
                            continue
                        if isinstance(keys, set) and keys == set(doc["required"]):
                            evidence.append(
                                {
                                    "source": source,
                                    "symbol": function.name,
                                    "component": contexts["/".join(Path(source).parts[:2])],
                                    "kind": "structural-validator",
                                    "marker": sorted(keys),
                                }
                            )
        for copy in release.get("copies", []):
            for loader in sorted(set(installed.get(copy, [])) | {usage[copy]["loader"]}):
                evidence.append(
                    {
                        "source": loader,
                        "component": contexts["/".join(Path(copy).parts[:2])],
                        "kind": "installed-loader",
                        "marker": copy,
                    }
                )
        # Independent code-generated projections, unlike an arbitrary source
        # filename mention, carry the canonical content digest.
        for item in evidence:
            if item["kind"] == "runtime-source-reference":
                component = "/".join(Path(item["source"]).parts[:2])
                item["component"] = contexts.get(component)
        for parent, deps in dependencies.items():
            if path in deps:
                evidence.append(
                    {
                        "source": parent,
                        "kind": "embedded-or-validation-dependency",
                        "component": releases[parent]["owner"],
                        "marker": path,
                    }
                )
                if kind == "schemas" and parent.startswith("contracts/schemas/"):
                    for copy in releases[parent].get("copies", []):
                        evidence.append(
                            {
                                "source": usage[copy]["loader"],
                                "component": contexts["/".join(Path(copy).parts[:2])],
                                "kind": "installed-embedded-schema",
                                "marker": copy,
                            }
                        )
        if path in manifests:
            evidence.extend(
                {"source": source, "kind": "source-assembly", "marker": path}
                for source in manifests[path]
            )
        # Report distinct claims. Tool validation keeps a schema alive but does
        # not justify a claimed deployable consumer.
        runtime_contexts = {
            item.get("component")
            for item in evidence
            if item["kind"]
            in {
                "wire-source",
                "installed-loader",
                "runtime-source-reference",
                "embedded-or-validation-dependency",
                "installed-event-payload",
                "generated-projection",
                "structural-validator",
                "installed-embedded-schema",
            }
        }
        missing = sorted(set(release["consumers"]) - runtime_contexts)
        rows.append(
            {
                "path": path,
                "canonical_sha256": hashlib.sha256((root / path).read_bytes()).hexdigest(),
                "owner": release["owner"],
                "consumers": release["consumers"],
                "classification": "active but requiring correction"
                if missing or not evidence
                else "active and verified",
                "verification_scope": "source integrity and lifecycle; runtime conformance is separately qualified",
                "lifecycle": "producer-owned or independently referenced validation/generation definition",
                "depends_on": sorted(dependencies[path]),
                "source_manifest": release.get("source_manifest"),
                "installed_copies": release.get("copies", []),
                "consumer_bindings_unverified": missing,
                "external_evidence_required": external,
                "evidence": sorted({json.dumps(item, sort_keys=True) for item in evidence}),
            }
        )
    for row in rows:
        row["evidence"] = [json.loads(item) for item in row["evidence"]]
        for item in row["evidence"]:
            item["source_sha256"] = hashlib.sha256((root / item["source"]).read_bytes()).hexdigest()
    return {
        "schema_version": 1,
        "external_limitations": [
            "Repository evidence cannot establish supported external consumer/deployment commitments.",
            "Static source bindings do not prove producer/consumer response or security conformance.",
        ],
        "summary": {
            "active_releases": len(rows),
            "canonical_dependency_edges": sum(map(len, dependencies.values())),
            "installed_copies": sum(len(row["installed_copies"]) for row in rows),
            "requiring_correction": sum(
                row["classification"] != "active and verified" for row in rows
            ),
        },
        "releases": rows,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = derive()
    serialized = json.dumps(report, indent=2) + "\n"
    if args.output:
        if args.check:
            if args.output.read_text() != serialized:
                raise ValueError("Phase 1 release evidence inventory is stale")
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(serialized)
    print(json.dumps(report["summary"], sort_keys=True))
