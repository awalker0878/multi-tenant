"""Generate authority-release schema components from canonical owner contracts.

The generator never rewrites a published contract. In CI --check proves the
published release matches an independently reconstructed projection. --emit-dir
writes candidate release files elsewhere for review/versioning before publish.
"""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UUID = "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"


def read(path: str, root: Path = ROOT) -> dict:
    return json.loads((root / path).read_text(encoding="utf-8"))


def normalized(node):
    if isinstance(node, list):
        return [normalized(v) for v in node]
    if isinstance(node, dict):
        result = {key: normalized(value) for key, value in node.items()}
        if result.get("format") == "uuid":
            result["pattern"] = UUID
        return result
    return node


def current_intent(node):
    if isinstance(node, list):
        return [current_intent(v) for v in node]
    if isinstance(node, dict):
        result = {key: current_intent(value) for key, value in node.items()}
        link = result.get("$ref")
        if isinstance(link, str) and link.startswith("#/$defs/"):
            result["$ref"] = link.replace(
                "#/$defs/", "#/components/schemas/CurrentPlanningIntent/$defs/", 1
            )
        return result
    return node


RELEASES = {
    "catalogue-internal-v1.json": {
        "PlanningInput": "contracts/schemas/planning/catalogue-input-v1.json",
        "CurrentPlanningIntent": "contracts/schemas/planning/catalogue-current-v2.json",
    },
    "inventory-native-input-v1.3.json": {
        "PlanningInput": "contracts/schemas/planning/inventory-input-v1.json",
        "CapabilityInput": "contracts/schemas/planning/inventory-input-v2.json",
        "MigrationInput": "contracts/schemas/planning/migration-input-v4.json",
    },
    "lifecycle-internal-authority-v1.json": {
        "PlacementReceipt": "contracts/schemas/planning/placement-reservation-v1.json",
        "PlacementReserveCommand": "contracts/schemas/planning/placement-reservation-v1.json",
        "PlacementDigestCommand": "contracts/schemas/planning/placement-reservation-v1.json",
    },
    "assurance-qualification-v1.json": {
        "Qualification": "contracts/schemas/planning/qualification-v2.1.json",
        "MigrationSupport": "contracts/schemas/planning/migration-support-v2.json",
    },
    "planning-lifecycle-reads-v1.json": {
        "BoundPlan": "contracts/openapi/planning-v1.2.json",
        "Content": "contracts/openapi/planning-v1.2.json",
        "MigrationReadiness": "contracts/schemas/planning/migration-readiness-v2.2.json",
    },
}


def assemble(name: str, root: Path = ROOT) -> dict:
    if name not in RELEASES:
        raise ValueError(f"Unregistered authority release generator: {name}")
    output = copy.deepcopy(read("contracts/openapi/" + name, root))
    for component, source in RELEASES[name].items():
        value = read(source, root)
        if name == "planning-lifecycle-reads-v1.json":
            if component in {"BoundPlan", "Content"}:
                value = value["components"]["schemas"][component]
                if component == "Content":
                    current = output["components"]["schemas"][component]
                    extras = set(current["properties"]) - set(value["properties"])
                    if extras != {"native_provisioning", "native_migration", "migration_campaign"}:
                        raise ValueError("Planning Lifecycle content extension list drift")
                    value = copy.deepcopy(value)
                    value["properties"].update({key: current["properties"][key] for key in extras})
            else:
                value.pop("$id", None)
                value.pop("$schema", None)
                def relocate(node):
                    if isinstance(node, dict):
                        if isinstance(node.get("$ref"), str) and node["$ref"].startswith("#/$defs/"):
                            node["$ref"] = "#/components/schemas/MigrationReadiness/" + node["$ref"][2:]
                        for child in node.values():
                            relocate(child)
                    elif isinstance(node, list):
                        for child in node:
                            relocate(child)
                relocate(value)
            output["components"]["schemas"][component] = value
            continue
        if name == "lifecycle-internal-authority-v1.json":
            if component == "PlacementReserveCommand":
                value = value["$defs"]["ReserveCommand"]
            elif component == "PlacementDigestCommand":
                value = value["$defs"]["DigestCommand"]
            output["components"]["schemas"][component] = normalized(value)
            continue
        if name == "catalogue-internal-v1.json" and component == "PlanningInput":
            value.pop("components", None)
            value = normalized(value)
        if component == "CurrentPlanningIntent":
            value = normalized(current_intent(value))
        elif component != "MigrationInput":  # current embedded v4 wire payload
            value = normalized(value)
        output["components"]["schemas"][component] = value
    return output


def verify(root: Path = ROOT) -> int:
    for name in RELEASES:
        expected = assemble(name, root)
        current = read("contracts/openapi/" + name, root)
        if expected != current:
            raise ValueError(f"Authority generated response schema drift: {name}")
    return len(RELEASES)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--emit-dir", type=Path)
    args = parser.parse_args()
    if args.emit_dir is not None:
        args.emit_dir.mkdir(parents=True, exist_ok=True)
        for name in RELEASES:
            (args.emit_dir / name).write_text(
                json.dumps(assemble(name), indent=2) + "\n", encoding="utf-8"
            )
        return
    print(f"Authority schema source parity: {verify()} versioned releases")


if __name__ == "__main__":
    main()
