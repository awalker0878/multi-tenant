"""Assemble immutable deployment bundles from small, reviewable contract sources.

Usage: python scripts/contracts/build.py --check (default) or --write.
A published version is never rewritten by CI; --write is an explicit developer operation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "contracts" / "source"

def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def assemble(manifest_path: Path):
    manifest = read(manifest_path)
    if manifest["schema_version"] != 1:
        raise ValueError(f"Unknown contract source manifest: {manifest_path}")
    folder = manifest_path.parent
    document = read(folder / manifest["base"])
    for dotted, part in manifest["parts"].items():
        keys = dotted.split(".")
        parent = document
        for key in keys[:-1]:
            parent = parent.setdefault(key, {})
        name = keys[-1]
        if name in parent:
            raise ValueError(f"Source bundle contains duplicate parent key: {dotted}")
        if part["kind"] == "object":
            value = {}
            for filename in part["files"]:
                fragment = read(folder / filename)
                if not isinstance(fragment, dict) or set(fragment).intersection(value):
                    raise ValueError(f"Duplicate or invalid contract object fragment: {filename}")
                value.update(fragment)
        elif part["kind"] == "array":
            value = []
            for filename in part["files"]:
                fragment = read(folder / filename)
                if not isinstance(fragment, list):
                    raise ValueError(f"Invalid contract array fragment: {filename}")
                value.extend(fragment)
        else:
            raise ValueError(f"Unknown fragment kind: {part['kind']}")
        parent[name] = value
    return manifest, document

def verify(write: bool = False):
    manifests = sorted(SOURCE.rglob("manifest.json"))
    if not manifests:
        raise ValueError("Missing contract source manifests")
    checked = 0
    for manifest_path in manifests:
        manifest, rendered = assemble(manifest_path)
        for target in [manifest["target"], *manifest.get("copies", [])]:
            destination = ROOT / target
            if write:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(json.dumps(rendered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            elif not destination.is_file() or read(destination) != rendered:
                raise ValueError(f"Contract source and published bundle drift: {target}")
            checked += 1
    return len(manifests), checked

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true")
    group.add_argument("--write", action="store_true")
    args = parser.parse_args()
    count, copies = verify(write=args.write)
    print(f"Contract bundles: {count} source manifests, {copies} canonical/distributed outputs verified")
