"""The live Catalogue wire probe must bind both the schema and its active AsyncAPI channel."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/contracts"))

import catalogue_foundation_assurance as proof  # noqa: E402
from planning.infrastructure.messaging.codec import canonical  # noqa: E402
from planning.infrastructure.messaging.generated import GeneratedEvent  # noqa: E402


class CatalogueChannelAssuranceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        for relative in (proof.RELEASE, proof.ASYNCAPI):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / relative).read_bytes())
        registry = {
            "active_releases": [
                {"path": release, "owner": "catalogue", "consumers": ["planning"]}
                for release in (proof.RELEASE, proof.ASYNCAPI)
            ]
        }
        catalogue = self.root / "architecture/contract-consumers.json"
        catalogue.parent.mkdir(parents=True, exist_ok=True)
        catalogue.write_text(json.dumps(registry))
        event = GeneratedEvent(
            event_type="catalogue.foundation.recorded",
            schema_version=1,
            event_id="10000000-0000-4000-8000-000000000001",
            correlation_id="10000000-0000-4000-8000-000000000002",
            tenant_id="tenant_a",
            actor_id="actor_a",
            record_id="record_a",
            revision="1",
            payload_sha256="a" * 64,
            source_revision="b" * 40,
            occurred_at="2026-10-08T00:00:00Z",
        )
        self.wire = canonical(event)

    def measure(self) -> list[dict]:
        with (
            patch.object(proof, "ROOT", self.root),
            patch.object(
                proof.subprocess,
                "run",
                return_value=SimpleNamespace(stdout=self.wire, stderr=b""),
            ),
        ):
            return proof.verify()

    def test_executable_wire_binding_covers_schema_and_channel(self) -> None:
        rows = self.measure()
        self.assertEqual(
            {(row["key"], row["claim"]) for row in rows},
            {
                (proof.RELEASE, "producer"),
                (proof.RELEASE, "consumer"),
                (proof.ASYNCAPI, "consumer"),
            },
        )
        # A validated event codec is not evidence that the publisher sent
        # the message over the declared broker channel.
        self.assertNotIn((proof.ASYNCAPI, "producer"),
                         {(row["key"], row["claim"]) for row in rows})
        self.assertTrue(all(row["result"] == "PASS" for row in rows))

    def test_wrong_channel_or_payload_binding_cannot_earn_asyncapi_proof(self) -> None:
        channel = self.root / proof.ASYNCAPI
        original = channel.read_text()
        for replaced in (
            original.replace("catalogue.foundation.recorded.v1", "catalogue.unpublished.v1"),
            original.replace("../schemas/events/catalogue-foundation-recorded-v1.json",
                             "../schemas/events/obsolete-v1.json"),
        ):
            with self.subTest(change=replaced != original):
                channel.write_text(replaced)
                with self.assertRaisesRegex(ValueError, "AsyncAPI release differs"):
                    self.measure()

    def test_unregistered_channel_cannot_earn_evidence(self) -> None:
        registry = self.root / "architecture/contract-consumers.json"
        document = json.loads(registry.read_text())
        document["active_releases"].pop()
        registry.write_text(json.dumps(document))
        with self.assertRaisesRegex(ValueError, "channel are not registered"):
            self.measure()


if __name__ == "__main__":
    unittest.main()
