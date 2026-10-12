"""Change impact comes from active-release producer/consumer relationships."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/p01"))
from admission.policy import affected, Denied


class ContractImpactTests(unittest.TestCase):
    def setUp(self):
        self.components = {
            name: {"path": f"services/{name}"}
            for name in ("inventory", "planning", "lifecycle", "assurance")
        }

    def graph(self, contracts=None, edges=None):
        return {
            "contracts": contracts or {},
            "active_releases": [
                {"path": f"contracts/openapi/{provider}-v1.json",
                 "owner": provider, "consumers": consumers}
                for provider, consumers in (edges or {}).items()
            ],
        }

    def test_transitive_consumers_follow_active_releases(self):
        graph = self.graph(edges={
            "inventory": ["planning"],
            "planning": ["lifecycle"],
            "assurance": [],
        })
        impact = affected(["services/inventory/app.py"],
                          self.components, self.components, graph, graph)
        self.assertEqual(impact["components"], ["inventory", "lifecycle", "planning"])

    def test_deleted_edge_in_proposal_still_impacts_base_consumers(self):
        base = self.graph(edges={"inventory": ["planning"]})
        head = self.graph(edges={"inventory": []})
        outcome = affected(["services/inventory/app.py"],
                           self.components, self.components, base, head)
        self.assertIn("planning", outcome["components"])

    def test_changed_contract_direct_consumers_come_from_both_revisions(self):
        path = "contracts/schemas/planning/foo-v1.json"
        base = self.graph(contracts={path: ["planning"]})
        head = self.graph(contracts={path: ["lifecycle"]})
        selected = affected([path], self.components, self.components, base, head)
        self.assertEqual(selected["components"], ["lifecycle", "planning"])

    def test_unregistered_contract_change_selects_every_component(self):
        selected = affected(["contracts/openapi/new.json"], self.components,
                            self.components, self.graph(), self.graph())
        self.assertEqual(selected["components"], sorted(self.components))

    def test_malformed_active_release_consumers_are_rejected(self):
        broken = {"active_releases": [{"owner": "inventory", "consumers": "planning"}]}
        with self.assertRaisesRegex(Denied, "invalid_contract_consumer"):
            affected(["services/inventory/a.py"], self.components, self.components,
                     broken, broken)


if __name__ == "__main__":
    unittest.main()
