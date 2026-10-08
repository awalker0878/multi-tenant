"""The required aggregate must not hide failed or cancelled selected builds."""
import importlib.util
from pathlib import Path
import unittest


SPEC = importlib.util.spec_from_file_location("p01_jobs", Path(__file__).with_name("check_jobs.py"))
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
COMPONENTS = {"planning": {"language": "python"}, "governance": {"language": "php"}}


class JobsTest(unittest.TestCase):
    def state(self, selected='["planning"]', result="success"):
        return {"selection": {"result": "success", "outputs": {"python": selected}}, "python": {"result": result}}

    def test_selected_success_and_empty_skip_are_accepted(self):
        MODULE.check(self.state(), ["python"], COMPONENTS)
        MODULE.check(self.state("[]", "skipped"), ["python"], COMPONENTS)

    def test_selected_failure_cancellation_and_skip_are_rejected(self):
        for result in ["failure", "cancelled", "skipped", None]:
            with self.subTest(result=result), self.assertRaises(ValueError):
                MODULE.check(self.state(result=result), ["python"], COMPONENTS)

    def test_invalid_selection_cannot_produce_success(self):
        for selected in ["", "null", "{}", '["unknown"]', '["governance"]', '["planning","planning"]', '[1]']:
            with self.subTest(selected=selected), self.assertRaises(ValueError):
                MODULE.check(self.state(selected), ["python"], COMPONENTS)

    def test_selection_failure_or_missing_output_is_rejected(self):
        for selection in [{"result": "failure"}, {"result": "cancelled"}, {"result": "success", "outputs": {}}]:
            with self.subTest(selection=selection), self.assertRaises(ValueError):
                MODULE.check({"selection": selection, "python": {"result": "skipped"}}, ["python"], COMPONENTS)


if __name__ == "__main__":
    unittest.main()
