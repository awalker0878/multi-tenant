"""Execute Catalogue's PHP wire encoder through Planning's installed decoder.

E2 only: never award AsyncAPI send/producer evidence without executing the
publisher; no broker, delivery acknowledgement or E3/E4 custody is claimed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

from jsonschema.exceptions import ValidationError
import yaml
from planning.infrastructure.messaging.codec import canonical, decode

ROOT = Path(__file__).resolve().parents[2]
RELEASE = "contracts/schemas/events/catalogue-foundation-recorded-v1.json"
ASYNCAPI = "contracts/asyncapi/catalogue.yaml"


def verify() -> list[dict]:
    registry = json.loads((ROOT / "architecture/contract-consumers.json").read_text())
    registered = [item for item in registry["active_releases"]
                  if item["path"] in {RELEASE, ASYNCAPI}
                  and item["owner"] == "catalogue"
                  and "planning" in item["consumers"]]
    if {item["path"] for item in registered} != {RELEASE, ASYNCAPI}:
        raise ValueError("Current Catalogue/Planning event and channel are not registered")
    # The executed PHP publisher must match the *active* AsyncAPI address,
    # event message and referenced payload schema. Static channel discovery
    # alone cannot prove that the producer or installed consumer works.
    api = yaml.safe_load((ROOT / ASYNCAPI).read_text(encoding="utf-8"))
    channel = api["channels"]["foundationFacts"]
    operation = api["operations"]["publishRecorded"]
    message = api["components"]["messages"]["Recorded"]
    schema_ref = message["payload"]["schema"]["$ref"]
    if (api["asyncapi"] != "3.0.0"
            or channel["address"] != "catalogue.foundation.recorded.v1"
            or channel["messages"] != {"recorded": {"$ref": "#/components/messages/Recorded"}}
            or operation != {"action": "send", "channel": {"$ref": "#/channels/foundationFacts"}}
            or message["contentType"] != "application/json"
            or (ROOT / "contracts/asyncapi" / schema_ref).resolve()
            != (ROOT / RELEASE).resolve()):
        raise ValueError("Catalogue AsyncAPI release differs from executable producer/consumer wire")
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

    # The PHP encoder + installed Planning decoder qualify their concrete
    # payload schema. The AsyncAPI channel binding is checked, but the
    # Catalogue outbox / broker send operation was NOT executed. Therefore
    # award only channel-side consumer proof, never publisher proof.
    measured = (
        (RELEASE, "producer", "live-producer"),
        (RELEASE, "consumer", "live-consumer"),
        (ASYNCAPI, "consumer", "live-consumer"),
    )
    return [{
        "key": path, "claim": claim, "source": source,
        "result": "PASS",
        "release_sha256": hashlib.sha256((ROOT / path).read_bytes()).hexdigest(),
        "test": "catalogue_foundation_assurance.py:php_codec_to_planning_decoder",
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "revision": os.environ.get("GITHUB_SHA"),
    } for path, claim, source in measured]


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
