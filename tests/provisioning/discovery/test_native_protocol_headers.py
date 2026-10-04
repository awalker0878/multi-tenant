"""Public protocol assertions cannot override native custody or HTTP framing."""
from pathlib import Path
import unittest
from unittest.mock import patch

from provisioner.controlplane.discovery import native_https
from provisioner.controlplane.discovery.native_credentials import NativeReadHeld
from provisioner.controlplane.discovery.adapters.openstack import OpenStackServiceEndpoints
from tests.provisioning.discovery.test_openstack import ENDPOINTS, PROJECT


class NativeProtocolHeaderTests(unittest.TestCase):
    def test_header_overrides_injection_duplicate_case_and_bounds_fail_before_connection(self):
        invalid = (
            {'Host': 'other.invalid'}, {'X-Auth-Token': 'different-token'},
            {'Authorization': 'other-credential'}, {'Proxy-Authorization': 'other'},
            {'Connection': 'keep-alive'}, {'Content-Length': '0'}, {'Transfer-Encoding': 'chunked'},
            {'Cookie': 'other'}, {'Accept': '*/*'}, {'Accept-Encoding': 'gzip'},
            {'Protocol': 'value\r\nInjected: bad'}, {'Bad Name': 'value'}, {'Protocol': ''},
            {'Protocol': ' value'}, {'Protocol': 'é'}, {'Protocol': 'v'*129},
            {'Protocol': 'one', 'protocol': 'two'}, {f'Protocol-{i}': 'v' for i in range(9)},
            {'Protocol': True}, [('Protocol', 'v')],
        )
        for argument in ('request_headers', 'response_headers'):
            for value in invalid:
                with self.subTest(argument=argument, value=value), patch.object(
                        native_https.socket, 'create_connection') as connect:
                    with self.assertRaises(NativeReadHeld):
                        native_https.read_json(origin='https://localhost', connect_ip='127.0.0.1',
                            ca_digest='a'*64, ca_bundle=Path('/unused'), path='/read',
                            credential_header='X-Auth-Token', credential='synthetic-token-000',
                            timeout=1, max_response_bytes=1024, authorize=lambda: None,
                            **{argument: value})
                    connect.assert_not_called()

    def test_catalog_roots_reject_url_normalization_before_credential_binding(self):
        suffix = f'/v2.1/{PROJECT}'
        invalid = (
            'https://nova.site.example/\nv2.1/' + PROJECT,
            'https://n\rova.site.example' + suffix,
            'https://nova.site.example/%2e%2e' + suffix,
            'https://nova.site.example/prefix/' + suffix,
            'https://nova.site.example:' + suffix,
            'https://@nova.site.example' + suffix,
            'https://nova.site.example' + suffix + '?',
            'https://nova.site.example' + suffix + '#',
            'https://nova.site.example/..' + suffix,
            'https://nova.site.example\\other' + suffix,
        )
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                OpenStackServiceEndpoints(ENDPOINTS.endpoint_id, PROJECT, value,
                                         ENDPOINTS.volume, ENDPOINTS.network, ENDPOINTS.image)

    def test_explicit_safe_reverse_proxy_prefixes_remain_supported(self):
        roots = OpenStackServiceEndpoints(ENDPOINTS.endpoint_id, PROJECT,
            f'https://api.site.example:8774/compute/v2.1/{PROJECT}',
            f'https://api.site.example:8776/volume/v3/{PROJECT}',
            'https://api.site.example:9696/network/v2.0',
            'https://api.site.example:9292/image/v2')
        self.assertEqual(roots.project_id, PROJECT)


if __name__ == '__main__':
    unittest.main()
