#!/usr/bin/env python3
"""Select private foundation builds from actual changed repository paths."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess

from admission.policy import affected


GLOBAL_PREFIXES = ("scripts/p01/", "deploy/build/", "release/", "architecture/", "contracts/", ".github/workflows/")
GLOBAL_FILES = {"scripts/validate_architecture.py", "tests/documentation/test_p01_selection.py"}
OWNER_WORKERS = {"inventory": "inventory-workers", "lifecycle": "lifecycle-workers"}


def select(changed: list[str], components: dict) -> tuple[list[str], str]:
    selected: set[str] = set()
    for raw in changed:
        path = PurePosixPath(raw)
        if path.is_absolute() or ".." in path.parts or "\\" in raw:
            raise ValueError("Changed paths must be relative normalized repository paths")
        if raw in GLOBAL_FILES or raw.startswith(GLOBAL_PREFIXES):
            return sorted(components), "shared build, control, or workflow inputs changed"
        matches = [name for name, component in components.items() if raw == component["path"] or raw.startswith(component["path"] + "/")]
        if not matches and raw.startswith(("services/", "workers/", "apps/", "packages/")):
            return sorted(components), "unregistered product or shared package path changed; conservative full selection"
        selected.update(matches)
    for owner, worker in OWNER_WORKERS.items():
        if owner in selected and worker in components:
            selected.add(worker)
    return sorted(selected), "changed components plus registered owner-dependent workers"


def changed_paths(event: dict, event_name: str, workspace: Path) -> tuple[list[str] | None, str]:
    if event_name == "workflow_dispatch":
        return None, "manual workflow request selects every candidate"
    if event_name == "push":
        base, head = event.get("before"), event.get("after")
    elif event_name == "pull_request":
        pull = event["pull_request"]
        base, head = pull["base"]["sha"], pull["head"]["sha"]
    else:
        return None, "unsupported event conservatively selects every candidate"
    if not all(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value) for value in (base, head)):
        raise ValueError("Diff revisions must be complete hexadecimal commit IDs")
    if base == "0" * 40 or head == "0" * 40:
        return None, "branch creation or deletion conservatively selects every candidate"
    if event_name == "pull_request":
        merged = subprocess.run(["git", "merge-base", base, head], cwd=workspace, capture_output=True, text=True, timeout=30)
        if merged.returncode:
            return None, "merge base unavailable; conservative full selection"
        base = merged.stdout.strip()
        if not re.fullmatch(r"[0-9a-f]{40}", base):
            raise ValueError("Git returned an invalid merge base")
    result = subprocess.run(["git", "diff", "--no-renames", "--name-only", "-z", base, head, "--"], cwd=workspace, capture_output=True, timeout=30)
    if result.returncode:
        return None, "diff unavailable; conservative full selection"
    return [value.decode("utf-8", errors="strict") for value in result.stdout.split(b"\0") if value], "commit diff"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--event-path", type=Path, default=os.environ.get("GITHUB_EVENT_PATH"))
    parser.add_argument("--event-name", default=os.environ.get("GITHUB_EVENT_NAME", "workflow_dispatch"))
    args = parser.parse_args()
    components = json.loads((args.workspace / "scripts/p01/candidates.json").read_text())["components"]
    event = json.loads(args.event_path.read_text()) if args.event_path else {}
    paths, reason = changed_paths(event, args.event_name, args.workspace)
    selected, explanation = (sorted(components), reason) if paths is None else select(paths, components)
    impact = None
    if paths is not None:
        base = event.get("before") if args.event_name == "push" else event["pull_request"]["base"]["sha"]
        head = event.get("after") if args.event_name == "push" else event["pull_request"]["head"]["sha"]
        if args.event_name == "pull_request":
            base = subprocess.run(["git", "merge-base", base, head], cwd=args.workspace,
                                  capture_output=True, text=True, check=True, timeout=30).stdout.strip()
        def read_base(path, default=None):
            observed = subprocess.run(["git", "show", base + ":" + path], cwd=args.workspace,
                                      capture_output=True, text=True, timeout=30)
            if observed.returncode:
                if default is not None:
                    return default
                raise ValueError("Base ownership inventory is unavailable")
            return json.loads(observed.stdout)
        base_components = read_base("scripts/p01/candidates.json")["components"]
        base_graph = read_base("architecture/contract-consumers.json", {})
        graph_path = args.workspace / "architecture/contract-consumers.json"
        head_graph = json.loads(graph_path.read_text()) if graph_path.exists() else {}
        impact = affected(paths, base_components, components, base_graph, head_graph)
        if impact["removed_components"]:
            raise ValueError("Removing a required deployable requires an explicit foundation inventory decision")
        selected = sorted(set(selected) | set(impact["components"]))
        explanation += "; union of base/head ownership and transitive contract consumers"
    result = {"components": selected, "reason": explanation, "changed_paths": paths, "impact": impact}
    for language in ("python", "php"):
        result[language] = [name for name in selected if components[name]["language"] == language]
    image_manifest = args.workspace / "deploy/build/components.json"
    approved_images = {component["id"] for component in json.loads(image_manifest.read_text())["components"]}
    if not approved_images.issubset(components):
        raise ValueError("Image manifest contains an unregistered foundation component")
    result["images"] = [name for name in selected if name in approved_images]
    print(json.dumps(result, indent=2))
    if os.environ.get("GITHUB_OUTPUT"):
        with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
            for language in ("python", "php", "images"):
                output.write(language + "=" + json.dumps(result[language], separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
