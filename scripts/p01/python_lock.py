"""Read the accepted Linux/CPython production closure without installing build tools.

uv remains responsible for resolving, checking and exporting the owned lock. This
independent inventory check deliberately rejects unknown or ambiguous lock shapes
instead of treating every package (including development tools) as deployable.
"""

from __future__ import annotations

import ast
import re
from typing import Any


TARGET_MARKERS = {
    "sys_platform": "linux",
    "platform_system": "Linux",
    "os_name": "posix",
    "implementation_name": "cpython",
    "platform_python_implementation": "CPython",
}


def canonical_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def target_marker(marker: str | None) -> bool:
    """Evaluate accepted string platform comparisons; reject new marker semantics."""
    if marker is None:
        return True

    def evaluate(node: ast.AST) -> bool:
        if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
            # Evaluate every branch so an unsupported expression never disappears
            # behind short-circuiting of a known false/true branch.
            values = [evaluate(value) for value in node.values]
            return all(values) if isinstance(node.op, ast.And) else any(values)
        if isinstance(node, ast.Compare) and len(node.ops) == len(node.comparators) == 1:
            left, right = node.left, node.comparators[0]
            if not isinstance(left, ast.Name) or left.id not in TARGET_MARKERS:
                raise ValueError(f"Unmeasured production marker: {marker}")
            if not isinstance(right, ast.Constant) or not isinstance(right.value, str):
                raise ValueError(f"Unmeasured production marker: {marker}")
            if isinstance(node.ops[0], ast.Eq):
                return TARGET_MARKERS[left.id] == right.value
            if isinstance(node.ops[0], ast.NotEq):
                return TARGET_MARKERS[left.id] != right.value
        raise ValueError(f"Unmeasured production marker: {marker}")

    return evaluate(ast.parse(marker, mode="eval").body)


def production_inventory(project: dict[str, Any], lock: dict[str, Any]) -> dict[str, str]:
    """Return the owned wheel plus only its locked production dependency graph."""
    if lock.get("version") != 1:
        raise ValueError("Unsupported uv lock version")
    packages: dict[str, dict[str, Any]] = {}
    for package in lock["package"]:
        name = canonical_name(package["name"])
        if name in packages:
            raise ValueError(f"Ambiguous locked package: {name}")
        packages[name] = package
    owner = canonical_name(project["name"])
    root = packages.get(owner)
    if root is None or root["version"] != project["version"] or root.get("source") != {"editable": "."}:
        raise ValueError("Owned project identity differs from its uv lock")
    inventory = {owner: project["version"]}
    visited: set[tuple[str, tuple[str, ...]]] = set()
    pending = list(root.get("dependencies", []))
    while pending:
        dependency = pending.pop()
        if not target_marker(dependency.get("marker")):
            continue
        name = canonical_name(dependency["name"])
        extras = tuple(sorted(dependency.get("extra", [])))
        identity = name, extras
        if identity in visited:
            continue
        visited.add(identity)
        if name == owner or name not in packages:
            raise ValueError(f"Invalid production dependency: {name}")
        package = packages[name]
        if package.get("source") != {"registry": "https://pypi.org/simple"}:
            raise ValueError(f"Unmeasured production package source: {name}")
        if dependency.get("version", package["version"]) != package["version"]:
            raise ValueError(f"Production dependency version mismatch: {name}")
        inventory[name] = package["version"]
        pending.extend(package.get("dependencies", []))
        for extra in extras:
            if extra not in package.get("optional-dependencies", {}):
                raise ValueError(f"Missing locked extra: {name}[{extra}]")
            pending.extend(package["optional-dependencies"][extra])
    return dict(sorted(inventory.items()))
