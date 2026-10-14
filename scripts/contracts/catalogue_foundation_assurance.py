"""Execute Catalogue's PHP event producer through Planning's installed decoder.

E2 only: no broker, delivery acknowledgement or E3/E4 custody is claimed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

from jsonschema.exceptions import ValidationError
from planning.infrastructure.messaging.codec import canonical, decode

ROOT = Path(__file__).resolve().parents[2]
RELEASE = "contracts/schemas/events/catalogue-foundation-recorded-v1.json"


def verify() -> list[dict]:
    registry = json.loads((ROOT / "architecture/contract-consumers.json").read_text())
    registered = [item for item in registry["active_releases"]
                  if item["path"] == RELEASE and item["owner"] == "catalogue"
                  and "planning" in item["consumers"]]
    if len(registered) != 1:
        raise ValueError("Current Catalogue/Planning event release is not registered")
    producer = subprocess.run(
        ["php", str(ROOT / "scripts/contracts/catalogue_foundation_wire.php")],
        cwd=ROOT, capture_output=True, check=True, timeout=30,
    )
    wire = producer.stdout
    if not wire or producer.stderr:
        raise ValueError("Catalogue emitted an invalid or noisy wire event")
    accepted = decode(wire)
    if (accepted.event_type != "catalogue.foundation.recorded"
            or accepted.tenant_id != "tenant_a"
            or accepted.source_revision != "b" * 40
            or canonical(accepted) != wire):
        raise ValueError("Planning installed decoder disagrees with Catalogue's wire")

    document = json.loads(wire)
    for invalid in (
        {**document, "native_write_authorized": True},
        {**document, "schema_version": 2},
        {key: value for key, value in document.items() if key != "tenant_id"},
    ):
        try:
            decode(json.dumps(invalid).encode())
        except (ValueError, ValidationError):
            pass
        else:
            raise ValueError("Planning accepted an invalid Catalogue event")
    try:
        decode(b'{"tenant_id":"foreign",' + wire[1:])
    except (ValueError, ValidationError):
        pass
    else:
        raise ValueError("Planning accepted a duplicate tenant identifier")

    fingerprint = hashlib.sha256((ROOT / RELEASE).read_bytes()).hexdigest()
    return [{
        "key": RELEASE, "claim": claim, "source": source,
        "result": "PASS", "release_sha256": fingerprint,
        "test": "catalogue_foundation_assurance.py:php_codec_to_planning_decoder",
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "revision": os.environ.get("GITHUB_SHA"),
    } for claim, source in (
        ("producer", "live-producer"), ("consumer", "live-consumer"),
    )]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evidence = verify()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n")
    print("Catalogue PHP producer and Planning installed decoder executed")


if __name__ == "__main__":
    main()
