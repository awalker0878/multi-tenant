"""Negative delivery admission without network or actual recipients."""
import unittest
from unittest.mock import patch
from alert_delivery import deliver, observed_alert, validate

class Alerts(unittest.TestCase):
    def test_sensitive_or_redirectable_origins_rejected_before_network(self):
        value=observed_alert('console','a'*40)
        with patch('urllib.request.build_opener') as connect:
            for endpoint in ['http://localhost/alerts','https://user:secret@localhost/alerts','https://localhost/alerts?token=secret','https://localhost/alerts#fragment']:
                with self.assertRaises(ValueError):deliver(endpoint,'synthetic','/missing',value)
            connect.assert_not_called()

    def test_payload_allowlist_prevents_accidental_secret_or_stack_inclusion(self):
        value=observed_alert('planning','a'*40)
        validate(value)
        for key in ('password','payload','trace','sql'):
            with self.assertRaises(ValueError):validate({**value,key:'must-not-send'})
