"""Combine all built image/wheel attestations into one immutable release-bound operation map.

An attestation only certifies source/artifact identity and bundled schema bytes;
operation-level HTTP authorization/behavior remains separately qualified by the
live contract-assurance job. Never upgrade declared bindings into live proof.
"""
from __future__ import annotations

from contract_io import read

import argparse
import json
import os
from pathlib import Path

from artifact_attestation import COMPONENTS, consumed_bindings, expected
from assurance import inventory

ROOT = Path(__file__).resolve().parents[2]



def bind_all_releases(documents: dict[tuple[str, str], dict], root: Path = ROOT) -> list[dict]:
    """Bind every current release to source-attested images without inventing consumption.

    Source-pinned image identity is distinct from actual installed JSON bytes.
    Releases without an installed copy remain explicit registry declarations.
    """
    import hashlib

    registry = read(root / "architecture/contract-consumers.json")
    owners = {owner: component for component, (owner, _) in COMPONENTS.items()}
    if len(owners) != len(COMPONENTS):
        raise ValueError("Ambiguous owner-to-runtime image mapping")
    releases = []
    seen = set()
    for release in registry["active_releases"]:
        path = release["path"]
        if path in seen:
            raise ValueError("Duplicate canonical release in runtime binding map: " + path)
        seen.add(path)
        source = root / path
        if not source.is_file():
            raise ValueError("Active canonical release missing from checked-out source: " + path)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        relationships = []
        declared = [("producer", release["owner"])] + [
            ("consumer", consumer) for consumer in release["consumers"]
        ]
        if len(release["consumers"]) != len(set(release["consumers"])):
            raise ValueError("Duplicate active release consumers: " + path)
        if release["owner"] in release["consumers"]:
            raise ValueError("Producer cannot also be its cross-service consumer: " + path)
        for role, owner in declared:
            if owner == "contract-platform" and role == "producer":
                # This is a shared protocol convention, not a running service.
                continue
            component = owners.get(owner)
            if component is None:
                raise ValueError(f"Active release has no attested runtime: {path} {owner}")
            image = documents[(component, "oci")]
            copies = sorted(
                item["path"] for item in image["installed_copies"]
                if item["canonical"] == path and item["sha256"] == digest
            )
            if any(item["canonical"] == path and item["sha256"] != digest
                   for item in image["installed_copies"]):
                raise ValueError(f"Built image contains stale canonical release: {path} {component}")
            if role == "consumer":
                consumption = [
                    item for item in image["consumed_releases"]
                    if item["canonical"] == path
                ]
                expected_evidence = (
                    "verified-installed-copy" if copies else "declared-consumption-only"
                )
                if len(consumption) != 1 or (
                    consumption[0]["canonical_sha256"] != digest
                    or consumption[0]["evidence"] != expected_evidence
                ):
                    raise ValueError(
                        f"Release consumer not independently attested: {path} {component}"
                    )
            relationships.append({
                "role": role,
                "owner": owner,
                "runtime_component": component,
                "runtime_image_sha256": image["artifact_sha256"],
                "installed_copies": copies,
                "binding_evidence": (
                    "verified-installed-bytes" if copies else "registry-declaration-only"
                ),
            })
        # A shared convention with no enrolled consumers is a legitimate
        # source-only contract, not an imaginary runtime artifact. Keep it in
        # the release inventory, explicitly unbound, until a real consumer is
        # registered and attested.
        source_only = release["owner"] == "contract-platform" and not release["consumers"]
        if not relationships and not source_only:
            raise ValueError("Canonical release has no runtime image binding: " + path)
        releases.append({
            "canonical": path,
            "kind": path.split("/")[1],
            "canonical_sha256": digest,
            "source_only": source_only,
            "relationships": relationships,
        })
    return sorted(releases, key=lambda row: row["canonical"])


def aggregate(folder: Path, root: Path = ROOT, revision: str | None = None) -> dict:
    revision = revision or os.environ.get("GITHUB_SHA")
    if not revision or len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
        raise ValueError("All runtime bindings need an exact source revision")
    documents: dict[tuple[str, str], dict] = {}
    for file in sorted(folder.rglob("*.json")):
        value = read(file)
        if not isinstance(value, dict):
            raise ValueError("Malformed built contract attestation: " + str(file))
        key = (value.get("component"), value.get("kind"))
        if key in documents:
            raise ValueError("Duplicate built runtime artifact attestation: " + str(key))
        documents[key] = value
    expected_keys = {
        (component, "oci") for component in COMPONENTS
    } | {
        (component, "wheel") for component, (_, kind) in COMPONENTS.items()
        if kind == "python"
    }
    if set(documents) != expected_keys:
        raise ValueError("Missing/extra release runtime artifact attestations: "
                         + repr(sorted(expected_keys ^ set(documents), key=str)))
    owners = {owner: component for component, (owner, _) in COMPONENTS.items()}
    binding_map: dict[str, dict] = {}
    for (component, kind), report in sorted(documents.items()):
        copies, operations = expected(component, root)
        if (report.get("source_revision") != revision
                or report.get("owner") != COMPONENTS[component][0]
                or report.get("installed_copies") != copies
                or report.get("owner_operations") != operations
                or report.get("consumed_releases") != consumed_bindings(component, root)):
            raise ValueError("Artifact/schema/operation binding does not match active source: "
                             + component)
        # A source SHA can be reused across different CI attempts. Never
        # aggregate an attestation produced in a different workflow run.
        if os.environ.get("GITHUB_ACTIONS") == "true":
            if (not os.environ.get("GITHUB_RUN_ID")
                    or not os.environ.get("GITHUB_RUN_ATTEMPT")
                    or report.get("github_run_id") != os.environ["GITHUB_RUN_ID"]
                    or report.get("github_run_attempt") != os.environ["GITHUB_RUN_ATTEMPT"]):
                raise ValueError("Built contract attestation belongs to a different CI run: "
                                 + component)
        digest = report.get("artifact_sha256")
        if not isinstance(digest, str) or len(digest) != 64 or any(
            c not in "0123456789abcdef" for c in digest
        ):
            raise ValueError("Malformed immutable artifact fingerprint: " + component)
        if kind != "oci":
            continue
        for operation in operations:
            key = operation["key"]
            if key in binding_map:
                raise ValueError("Multiple runtime images claim owned operation: " + key)
            binding_map[key] = {
                "operation": key,
                "release": operation["release"],
                "release_sha256": operation["release_sha256"],
                "source_revision": revision,
                "runtime_component": component,
                "runtime_image_sha256": digest,
                "binding_kind": "owned-runtime-source-attested",
            }
    current = inventory(root)["operations"]
    for op in current:
        if op["owner"] != "contract-platform":
            if op["key"] not in binding_map:
                raise ValueError("Owner operation without built runtime release binding: " + op["key"])
            continue
        # Foundation health/error conventions are shared declarations, not one
        # deployed service. Bind each declared consumer artifact explicitly.
        registry = read(root / "architecture/contract-consumers.json")
        release = next(x for x in registry["active_releases"] if x["path"] == op["release"])
        hosts = []
        for consumer in release["consumers"]:
            component = owners.get(consumer)
            if component is None:
                raise ValueError(f"Foundation consumer lacks an attested runtime: {consumer}")
            hosts.append({
                "runtime_component": component,
                "runtime_image_sha256": documents[(component, "oci")]["artifact_sha256"],
            })
        if not hosts:
            raise ValueError("Foundation operation is not bound to deployed consumers")
        binding_map[op["key"]] = {
            "operation": op["key"], "release": op["release"],
            "release_sha256": op["release_sha256"],
            "source_revision": revision,
            "runtime_components": sorted(hosts, key=lambda x: x["runtime_component"]),
            "binding_kind": "shared-foundation-declaration",
        }
    expected_ops = {x["key"] for x in current}
    if set(binding_map) != expected_ops:
        raise ValueError("Contract runtime release binding set differs from canonical OpenAPI")
    release_bindings = bind_all_releases(documents, root)
    return {
        "schema_version": 1,
        "source_revision": revision,
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "images": {component: documents[(component, "oci")]["artifact_sha256"]
                   for component in sorted(COMPONENTS)},
        "bindings": [binding_map[key] for key in sorted(binding_map)],
        "release_bindings": release_bindings,
        "summary": {
            "runtime_images": len(COMPONENTS),
            "active_releases": len(release_bindings),
            "source_only_releases": sum(row["source_only"] for row in release_bindings),
            "non_http_releases": sum(row["kind"] != "openapi" for row in release_bindings),
            "release_image_bindings": sum(len(row["relationships"]) for row in release_bindings),
            "verified_installed_release_bindings": sum(
                item["binding_evidence"] == "verified-installed-bytes"
                for row in release_bindings for item in row["relationships"]
            ),
            "verified_python_wheels": sum(kind == "python" for _, kind in COMPONENTS.values()),
            "contracted_http_operations": len(current),
            "source_attested_owner_operations": sum(
                b["binding_kind"] == "owned-runtime-source-attested"
                for b in binding_map.values()
            ),
            "shared_foundation_operations": sum(
                b["binding_kind"] == "shared-foundation-declaration"
                for b in binding_map.values()
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-directory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = aggregate(args.input_directory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
