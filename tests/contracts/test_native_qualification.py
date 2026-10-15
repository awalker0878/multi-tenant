"""E2 real RSA controls for native record resolution; never a native qualification run."""

import json
from copy import deepcopy
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch
import sys
from jsonschema import Draft202012Validator, FormatChecker

from native_qualification_fixture import signed_fixture

ROOT = Path(__file__).resolve().parents[2]


class NativeQualificationTest(unittest.TestCase):
    def test_qualification_scope_guard_rejects_values_the_closed_wire_cannot_return(self):
        scope = json.loads((ROOT/'contracts/fixtures/planning/synthetic-inputs-v1.json').read_text())['qualification']['scope']
        schema = json.loads((ROOT/'contracts/schemas/planning/qualification-v3.json').read_text())['properties']['scope']
        code = 'require $argv[1]; $s=json_decode(file_get_contents($argv[2]),true,64,JSON_THROW_ON_ERROR); echo App\\Domain\\Qualification\\QualificationScope::valid($s) ? "valid" : "invalid";'
        variants = [scope, {**scope, 'native_scope': 'é' * 1024}, {},
                    {**scope, 'endpoint_id': 'forged'}, {**scope, 'installed_tuple': []},
                    {**scope, 'artifacts': {}}, {**scope, 'action': 'invented'},
                    {**scope, 'native_scope': True}]
        with tempfile.TemporaryDirectory(prefix='qualification-scope-') as directory:
            path = Path(directory)/'scope.json'
            for value in variants:
                path.write_text(json.dumps(value))
                result = subprocess.check_output([os.environ.get('CAPABILITY_PHP_BIN', 'php'), '-r', code,
                    str(ROOT/'services/assurance/app/Domain/Qualification/QualificationScope.php'), str(path)], text=True)
                self.assertEqual(result == 'valid', Draft202012Validator(schema, format_checker=FormatChecker()).is_valid(value))

    def test_current_planning_snapshot_passes_actual_signed_owner_decoder(self):
        sys.path.insert(0, str(ROOT / 'services/planning/src'))
        sys.path.insert(0, str(ROOT / 'services/planning/tests'))
        import planning_fixture
        with patch.object(planning_fixture, 'NOW', int(time.time())):
            intent, destination, _, policy, qualification = planning_fixture.inputs()
            with tempfile.TemporaryDirectory(prefix='planning-signed-snapshot-e2-') as directory:
                snapshot = planning_fixture.snapshot_fixture(intent, destination, policy, qualification)
                bundle, keys = signed_fixture(qualification, Path(directory)/'keys',
                                              inventory=destination, snapshot=snapshot['data'])
                fixture = Path(directory)/'fixture.json'
                fixture.write_text(json.dumps({'bundle': bundle, 'keys': keys, 'scope': bundle['record']['scope']}))
                result = subprocess.run([os.environ.get('CAPABILITY_PHP_BIN', 'php'),
                                         str(ROOT/'scripts/check_native_qualification.php'), str(fixture)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('twelve negative controls passed (E2)', result.stdout)
                wire = subprocess.check_output([os.environ.get('CAPABILITY_PHP_BIN', 'php'),
                                                str(ROOT/'scripts/check_native_qualification.php'), str(fixture), '--wire'])
                resolved = json.loads(wire)
                installed = json.loads((ROOT/'services/planning/src/planning/infrastructure/inputs/qualification-v3.json').read_text())
                Draft202012Validator(installed, format_checker=FormatChecker()).validate(resolved)
                from planning.domain.qualification import verified
                self.assertTrue(verified(resolved, int(time.time())))
                missing_matrix = {k:v for k,v in resolved.items() if k != 'method_modes'}
                self.assertFalse(Draft202012Validator(installed).is_valid(missing_matrix))
                for field in ('mode', 'scope_sha256', 'readback_sha256', 'method'):
                    invalid = deepcopy(snapshot['data'])
                    sample = invalid['recovery_measurements'][0]
                    if field == 'method':
                        sample[field] = 'native_api_export_import'
                    else:
                        sample.pop(field)
                    rejected, _ = signed_fixture(qualification, Path(directory)/'keys',
                                                inventory=destination, snapshot=invalid)
                    fixture.write_text(json.dumps({'bundle': rejected, 'keys': keys, 'scope': rejected['record']['scope']}))
                    result = subprocess.run([os.environ.get('CAPABILITY_PHP_BIN', 'php'),
                                             str(ROOT/'scripts/check_native_qualification.php'), str(fixture)],
                                            capture_output=True, text=True)
                    self.assertNotEqual(result.returncode, 0, field)
                    self.assertIn('native_recovery_readback_invalid', result.stdout + result.stderr)

    def test_signed_native_custody_and_negative_controls(self):
        with tempfile.TemporaryDirectory(prefix='native-qualification-e2-') as directory:
            source = json.loads((ROOT / 'contracts/fixtures/planning/synthetic-inputs-v1.json').read_text())
            bundle, keys = signed_fixture(source['qualification'], Path(directory)/'keys')
            fixture = Path(directory)/'fixture.json'
            fixture.write_text(json.dumps({'bundle':bundle,'keys':keys,'scope':bundle['record']['scope']}))
            result = subprocess.run([os.environ.get('CAPABILITY_PHP_BIN','php'),
                                     str(ROOT/'scripts/check_native_qualification.php'),str(fixture)],
                                    check=True,capture_output=True,text=True)
            self.assertIn('twelve negative controls passed (E2)',result.stdout)

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
