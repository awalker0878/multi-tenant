"""Existing session injection preserves the bounded, GET-only transport."""
import unittest
from lab.native_readback_fixture import Fixture
from tools import readback_core as c


class SessionTransportTests(unittest.TestCase):
    def test_session_header_without_login_or_basic_auth(self):
        with Fixture() as f:
            f.routes = {'/exact': {'body': {'ok': True}}}
            client = c.ReadClient(f.origin, f.origin, None, None, {'/exact'}, str(f.directory / 'ca.pem'), session_token='fixture-session')
            self.assertEqual(client.get('/exact')[0], {'ok': True})
            self.assertEqual(f.requests, [{'method': 'GET', 'path': '/exact', 'has_basic_auth': False, 'has_session_auth': True}])
            with self.assertRaises(c.ObservationError): client.get('/discovery')
    def test_mixed_auth_empty_or_injectable_headers_rejected(self):
        for username, password, token in [('reader', 'secret', 'session'), (None, None, ''),
                (None, None, 'x\r\nInjected: y'), (None, None, 'non ascii é'), (None, None, 'x y')]:
            with self.subTest(token=token), self.assertRaises(ValueError):
                c.ReadClient('https://vc.invalid', 'https://vc.invalid', username, password, {'/exact'}, session_token=token)
    def test_redirect_does_not_forward_session(self):
        with Fixture() as f:
            f.routes = {'/exact': {'status': 302, 'headers': [('Location', '/foreign')], 'body': {}}}
            client = c.ReadClient(f.origin, f.origin, None, None, {'/exact'}, str(f.directory / 'ca.pem'), session_token='fixture-session')
            with self.assertRaises(c.ObservationError): client.get('/exact')
            self.assertEqual(len(f.requests), 1)


if __name__ == '__main__': unittest.main()
