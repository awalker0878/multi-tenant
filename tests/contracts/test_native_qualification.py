"""E2 real RSA controls for native record resolution; never a native qualification run."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from native_qualification_fixture import signed_fixture

ROOT = Path(__file__).resolve().parents[2]


class NativeQualificationTest(unittest.TestCase):
    def test_signed_native_custody_and_negative_controls(self):
        with tempfile.TemporaryDirectory(prefix='native-qualification-e2-') as directory:
            source = json.loads((ROOT / 'contracts/fixtures/planning/synthetic-inputs-v1.json').read_text())
            bundle, keys = signed_fixture(source['qualification'], Path(directory)/'keys')
            fixture = Path(directory)/'fixture.json'
            fixture.write_text(json.dumps({'bundle':bundle,'keys':keys,'scope':bundle['record']['scope']}))
            result = subprocess.run([os.environ.get('CAPABILITY_PHP_BIN','php'),
                                     str(ROOT/'scripts/check_native_qualification.php'),str(fixture)],
                                    check=True,capture_output=True,text=True)
            self.assertIn('eight negative controls passed (E2)',result.stdout)

    def test_receiving_acceptance_is_independent_and_bound(self):
        with tempfile.TemporaryDirectory(prefix='receiving-protocol-e2-') as directory:
            source=json.loads((ROOT/'contracts/fixtures/planning/synthetic-inputs-v1.json').read_text())
            bundle,keys=signed_fixture(source['qualification'],Path(directory)/'keys',receiving=True)
            fixture=Path(directory)/'fixture.json'
            fixture.write_text(json.dumps({'bundle':bundle,'keys':keys,'scope':bundle['record']['scope']}))
            result=subprocess.run([os.environ.get('CAPABILITY_PHP_BIN','php'),
                                   str(ROOT/'scripts/check_native_receiving.php'),str(fixture)],
                                  check=True,capture_output=True,text=True)
            self.assertIn('receiving signature controls passed (E2)',result.stdout)


if __name__ == '__main__':
    unittest.main()
