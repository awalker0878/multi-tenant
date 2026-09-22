"""The portable request contract: syntax, schema, defaults and identity."""
from __future__ import annotations

import copy
import unittest

from provisioner.compiler import normalize
from provisioner.domain.errors import ProvisioningError
from provisioner.domain.request import digest, loads
from tests.provisioning.support import reference_document


class RequestSyntaxTest(unittest.TestCase):
    def test_duplicate_keys_are_refused(self):
        with self.assertRaises(ProvisioningError) as caught:
            loads('apiVersion: hosting.platform/v1\napiVersion: hosting.platform/v1\n')
        self.assertEqual(caught.exception.code, 'REQUEST_SYNTAX_INVALID')

    def test_empty_document_is_refused(self):
        with self.assertRaises(ProvisioningError) as caught:
            loads('   ')
        self.assertEqual(caught.exception.code, 'REQUEST_SOURCE_UNREADABLE')

    def test_non_mapping_is_refused(self):
        with self.assertRaises(ProvisioningError) as caught:
            loads('- one\n- two\n')
        self.assertEqual(caught.exception.code, 'REQUEST_SYNTAX_INVALID')

    def test_json_is_accepted(self):
        self.assertEqual(loads('{"apiVersion": "x", "kind": "y"}')['kind'], 'y')

    def test_digest_is_canonical(self):
        self.assertEqual(digest({'b': 1, 'a': 2}), digest({'a': 2, 'b': 1}))
        self.assertNotEqual(digest({'a': 1}), digest({'a': 2}))


class RequestContractTest(unittest.TestCase):
    def setUp(self):
        self.document = reference_document()

    def test_reference_request_declares_the_reviewed_contract(self):
        self.assertEqual(self.document['apiVersion'], 'hosting.platform/v1')
        self.assertEqual(self.document['kind'], 'WorkloadSecurityDomain')
        self.assertEqual(self.document['metadata']['tenant'], 'tenant-01')
        self.assertEqual(self.document['metadata']['name'], 'wsd-01')

    def test_reference_request_carries_no_native_identity(self):
        text = str(self.document)
        for token in ('uuid', 'object_id', 'moref', 'subnet_id', 'project_id', 'hostname'):
            self.assertNotIn(token, text)

    def test_unknown_field_is_refused(self):
        document = copy.deepcopy(self.document)
        document['spec']['unsupportedFeature'] = True
        with self.assertRaises(ProvisioningError) as caught:
            normalize.normalize(document, source='<test>')
        self.assertEqual(caught.exception.code, 'SCHEMA_VALIDATION_FAILED')

    def test_unknown_api_version_is_refused(self):
        document = copy.deepcopy(self.document)
        document['apiVersion'] = 'hosting.platform/v2'
        with self.assertRaises(ProvisioningError) as caught:
            normalize.normalize(document, source='<test>')
        self.assertEqual(caught.exception.code, 'SCHEMA_VALIDATION_FAILED')

    def test_unknown_kind_is_refused(self):
        document = copy.deepcopy(self.document)
        document['kind'] = 'SomethingElse'
        with self.assertRaises(ProvisioningError):
            normalize.normalize(document, source='<test>')

    def test_normalization_applies_every_default(self):
        request = normalize.normalize(copy.deepcopy(self.document), source='<test>')
        for key in normalize.DEFAULTS:
            self.assertIn(key, request.spec)

    def test_normalization_is_idempotent(self):
        first = normalize.normalize(copy.deepcopy(self.document), source='<test>')
        second = normalize.normalize(copy.deepcopy(first.document), source='<test>')
        self.assertEqual(first.digest, second.digest)

    def test_identity_is_stable_across_loads(self):
        self.assertEqual(reference_document_digest(), reference_document_digest())

    def test_zones_follow_the_request(self):
        request = normalize.normalize(copy.deepcopy(self.document), source='<test>')
        self.assertEqual(normalize.zones(request), ('OZ', 'RZ'))


def reference_document_digest() -> str:
    from provisioner.domain.request import digest as digest_of

    return digest_of(reference_document())


if __name__ == '__main__':
    unittest.main()