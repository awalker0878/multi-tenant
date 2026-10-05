"""Reject package closure substitutions before building a service image."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from alpine_inputs import validate_apks


class AlpineInputsTest(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[2]
        self.lock = json.loads((root / 'deploy/build/alpine-packages.lock.json').read_bytes())

    def check(self, lock, base=None):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'lock.json'
            path.write_text(json.dumps(lock))
            return validate_apks(path, base or self.lock['base_reference'])

    def test_exact_runtime_closure(self):
        self.assertEqual(set(self.check(self.lock)), {'musl', 'libpq', 'libcrypto3', 'libssl3'})

    def test_wrong_base_or_platform(self):
        with self.assertRaises(ValueError):
            self.check(self.lock, 'docker.io/library/php@sha256:' + '0'*64)
        self.lock['platform'] = 'linux/arm64'
        with self.assertRaises(ValueError): self.check(self.lock)

    def test_missing_duplicate_or_undeclared_packages(self):
        for mutation in ('empty', 'missing', 'duplicate', 'unreferenced'):
            with self.subTest(mutation=mutation):
                lock = copy.deepcopy(self.lock)
                if mutation == 'empty': lock['groups']['build'] = []
                if mutation == 'missing': lock['groups']['build'].append('missing.apk')
                if mutation == 'duplicate': lock['groups']['build'].append(lock['groups']['build'][0])
                if mutation == 'unreferenced': lock['packages']['extra.apk'] = {}
                with self.assertRaises(ValueError): self.check(lock)

    def test_wrong_url_hash_size_or_name(self):
        filename = next(iter(self.lock['packages']))
        for field, value in [('url', 'https://untrusted.invalid/' + filename), ('sha256', '0'*63),
                             ('bytes', True), ('bytes', 268435457), ('name', '../escape')]:
            with self.subTest(field=field, value=value):
                lock = copy.deepcopy(self.lock)
                lock['packages'][filename][field] = value
                with self.assertRaises(ValueError): self.check(lock)


if __name__ == '__main__':
    unittest.main()
