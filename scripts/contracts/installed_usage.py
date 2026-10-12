"""Independent runtime, packaging, generation and CI evidence for every installed copy."""
from __future__ import annotations

import ast
import json
from pathlib import Path

from runtime_inventory import executable_contract_loads


def verify_installed_usage(root: Path, registry: dict) -> int:
    ledger = json.loads((root / "architecture/installed-contract-usage.json").read_text())
    if ledger.get("schema_version") != 1 or not isinstance(ledger.get("copies"), list):
        raise ValueError("Installed contract usage ledger is invalid")
    indexed = {
        path: release["path"]
        for release in registry["active_releases"]
        for path in release.get("copies", [])
    }
    rows = ledger["copies"]
    actual = [row.get("copy") for row in rows]
    if len(actual) != len(set(actual)) or set(actual) != set(indexed):
        raise ValueError("Installed contract usage ledger does not cover active installed copies")
    workflow = (root / ".github/workflows/ci.yml").read_text()
    for required in ("python scripts/contracts/check.py",
                     "python scripts/contracts/build.py --check"):
        if required not in workflow:
            raise ValueError(f"CI does not execute contract usage prerequisite: {required}")
    for row in rows:
        copy = row["copy"]
        name = Path(copy).name
        if row["canonical"] != indexed[copy]:
            raise ValueError(f"Installed copy canonical binding changed: {copy}")
        if (root / copy).read_bytes() != (root / row["canonical"]).read_bytes():
            raise ValueError(f"Installed copy byte drift: {copy}")
        loader = root / row["loader"]
        if not loader.is_file() or Path(copy).parts[:2] != Path(row["loader"]).parts[:2]:
            raise ValueError(f"Installed copy loader outside bounded component: {copy}")
        if row["load_kind"] == "literal":
            if name not in executable_contract_loads(loader):
                raise ValueError(f"No verified executable JSON loader for installed copy: {copy}")
        elif row["load_kind"] == "planning_typed":
            if not copy.startswith("services/planning/src/planning/infrastructure/inputs/"):
                raise ValueError(f"Unqualified typed owner loader: {copy}")
            tree = ast.parse(loader.read_text())
            table = [
                ast.literal_eval(node.value)
                for node in tree.body
                if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
                and node.target.id == "OWNER_OPERATIONS"
            ]
            basenames = {entry[3] for item in table for entry in item}
            actual_loader = (root / "services/planning/src/planning/infrastructure/owners.py").read_text()
            if (len(table) != 1 or Path(copy).stem not in basenames
                    or 'joinpath(name + ".json")' not in actual_loader
                    or "contract_for_operation" not in actual_loader):
                raise ValueError(f"Typed owner operation has no runtime schema binding: {copy}")
        else:
            raise ValueError(f"Unknown executable loader kind: {copy}")

        packaging = root / row["packaging"]
        if not packaging.is_file() or row["packaging_marker"] not in packaging.read_text():
            raise ValueError(f"Installed JSON not included in runtime image: {copy}")
        if Path(row["packaging"]).parts[:2] != Path(copy).parts[:2]:
            raise ValueError(f"Packaging evidence belongs to another component: {copy}")
        if row["package_data"] is not None:
            metadata = root / row["package_data"]
            if not metadata.is_file() or row["package_data_marker"] not in metadata.read_text():
                raise ValueError(f"Installed JSON excluded from packaged Python wheel: {copy}")
            if Path(row["package_data"]).parts[:2] != Path(copy).parts[:2]:
                raise ValueError(f"Packaged Python wheel belongs to another component: {copy}")
        elif row["package_data_marker"] is not None:
            raise ValueError(f"Unexpected package-data marker: {copy}")

        generator = row["generator"]
        if generator is None:
            if row["generation_mode"] != "canonical_snapshot":
                raise ValueError(f"Unverified generator omission: {copy}")
        elif row["generation_mode"] == "generated_or_source_assembled":
            file = root / generator
            if not file.is_file():
                raise ValueError(f"Missing installed copy generator: {generator}")
            if generator.endswith("/manifest.json"):
                manifest = json.loads(file.read_text())
                if copy not in manifest.get("copies", []) or row["canonical"] != manifest["target"]:
                    raise ValueError(f"Source assembly manifest does not generate copy: {copy}")
            elif generator.endswith(".py"):
                if copy not in file.read_text():
                    raise ValueError(f"Generator no longer emits installed copy: {copy}")
                if f"python {generator} --check" not in workflow:
                    raise ValueError(f"Generator is not checked by contract CI: {generator}")
            else:
                raise ValueError(f"Unsupported generator type: {generator}")
        else:
            raise ValueError(f"Missing authoritative generator classification: {copy}")
        if row["ci"] != ".github/workflows/ci.yml":
            raise ValueError(f"Installed copy lacks contract-integrity CI ownership: {copy}")
    return len(rows)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    registry = json.loads((root / "architecture/contract-consumers.json").read_text())
    print(f"Verified {verify_installed_usage(root, registry)} installed contract usage records")
