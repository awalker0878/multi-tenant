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

def safe_source_file(folder: Path, name: str) -> Path:
    """Resolve a source partition without allowing manifest-controlled traversal."""
    if (not isinstance(name, str) or not name.endswith(".json")
            or Path(name).is_absolute() or ".." in Path(name).parts):
        raise ValueError(f"Unsafe contract source fragment: {name}")
    resolved = (folder / name).resolve()
    if not resolved.is_relative_to(folder.resolve()):
        raise ValueError(f"Escaping contract source fragment: {name}")
    return resolved


def safe_destination(relative: str, *, canonical: bool) -> Path:
    if (not isinstance(relative, str) or not relative.endswith(".json")
            or Path(relative).is_absolute() or ".." in Path(relative).parts):
        raise ValueError(f"Unsafe contract destination: {relative}")
    parts = Path(relative).parts
    if canonical:
        allowed = (len(parts) >= 3 and parts[:1] == ("contracts",)
                   and parts[1] in {"openapi", "schemas", "capabilities", "platforms"})
    else:
        allowed = (
            len(parts) >= 5 and parts[0] in {"apps", "services", "workers"}
            and parts[2:4] == ("resources", "contracts")
        ) or (
            len(parts) >= 7 and parts[0] == "services" and parts[2] == "src"
            and parts[4] == "infrastructure" and parts[5] in {"inputs", "contracts"}
        )
    if not allowed:
        raise ValueError(f"Unapproved contract destination: {relative}")
    resolved = (ROOT / relative).resolve()
    if not resolved.is_relative_to(ROOT.resolve()):
        raise ValueError(f"Escaping contract destination: {relative}")
    return resolved


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def assemble(manifest_path: Path):
    manifest = read(manifest_path)
    if manifest["schema_version"] != 1:
        raise ValueError(f"Unknown contract source manifest: {manifest_path}")
    folder = manifest_path.parent
    document = read(safe_source_file(folder, manifest["base"]))
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
                fragment = read(safe_source_file(folder, filename))
                if not isinstance(fragment, dict) or set(fragment).intersection(value):
                    raise ValueError(f"Duplicate or invalid contract object fragment: {filename}")
                value.update(fragment)
        elif part["kind"] == "array":
            value = []
            for filename in part["files"]:
                fragment = read(safe_source_file(folder, filename))
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
        target = manifest["target"]
        canonical = safe_destination(target, canonical=True)
        if canonical.is_file():
            # A changed authoring fragment must publish a NEW contract version.
            # Never reorder or overwrite historical canonical JSON as a side
            # effect of rebuilding its semantically equivalent source parts.
            if read(canonical) != rendered:
                raise ValueError(f"Published contract requires a new version: {target}")
        elif write:
            canonical.parent.mkdir(parents=True, exist_ok=True)
            canonical.write_text(
                json.dumps(rendered, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        else:
            raise ValueError(f"Missing canonical contract bundle: {target}")
        checked += 1
        canonical_bytes = canonical.read_bytes()
        for path in manifest.get("copies", []):
            destination = safe_destination(path, canonical=False)
            if write:
                destination.parent.mkdir(parents=True, exist_ok=True)
                # Preserve the exact published canonical representation.
                destination.write_bytes(canonical_bytes)
            elif not destination.is_file() or destination.read_bytes() != canonical_bytes:
                raise ValueError(f"Packaged contract byte drift: {path}")
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
