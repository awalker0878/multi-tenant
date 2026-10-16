#!/usr/bin/env python3
"""Guard the one native-security API contract against divergent resolver literals."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "planning" / "src"))
from planning.domain.native_security_api import FEATURES  # noqa: E402


def main() -> int:
    source = ROOT / "contracts" / "capabilities" / "native-security-api-registry-v1.json"
    registry = json.loads(source.read_text(encoding="utf-8"))
    expected: dict[tuple[str, str, str], frozenset[str]] = {}
    for platform, profile in registry["providers"].items():
        namespace = profile["namespace"]
        for version, row in profile["versions"].items():
            key = (platform, namespace, version)
            if key in expected:
                raise ValueError("duplicate native API registry key: " + str(key))
            features = row["required_features"]
            if len(features) != len(set(features)) or not features:
                raise ValueError("invalid native API feature set: " + str(key))
            expected[key] = frozenset(features)
    if registry.get("schema_version") != 1 or expected != FEATURES:
        print("Native security API feature registry differs from Planning.", file=sys.stderr)
        return 1
    print(f"Native security API registry consistent: {len(expected)} installed API profiles.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
