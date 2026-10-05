"""Prevent raw credential matches from crossing the retained evidence boundary."""
import unittest
from campaign import redacted_results


class RedactionTests(unittest.TestCase):
    def test_secret_bytes_and_snippets_are_not_retained(self):
        result = redacted_results({'Results': [{'Target': 'config.py', 'Class': 'secret',
            'Secrets': [{'RuleID': 'fixture', 'Severity': 'HIGH', 'StartLine': 4, 'EndLine': 4,
                         'Match': 'private-value', 'Code': {'Lines': ['private-value']},
                         'ExtraFutureField': 'private-value'}], 'PrivateFutureField': 'private-value'}]})
        self.assertNotIn('private-value', str(result))
        self.assertEqual(result[0]['Secrets'], [{'RuleID': 'fixture', 'Severity': 'HIGH', 'StartLine': 4, 'EndLine': 4}])

    def test_dependency_identity_and_remediation_survive_redaction(self):
        result = redacted_results({'Results': [{'Target': 'composer.lock', 'Packages': [{}, {}],
            'Vulnerabilities': [{'VulnerabilityID': 'CVE-EXAMPLE', 'Severity': 'HIGH', 'PkgName': 'fixture',
                                 'InstalledVersion': '1', 'FixedVersion': '2', 'Unknown': 'not-retained'}]}]})
        self.assertEqual(result[0]['packages_count'], 2)
        self.assertEqual(result[0]['Vulnerabilities'][0]['FixedVersion'], '2')
        self.assertNotIn('Unknown', result[0]['Vulnerabilities'][0])


if __name__ == '__main__':
    unittest.main()
