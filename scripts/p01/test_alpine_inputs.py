"""Reject package closure substitutions before building a service image."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from alpine_inputs import validate_apks, validate_cache


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
        self.assertEqual(set(self.check(self.lock)), {'musl', 'libpq', 'libcrypto3', 'libssl3', 'openssl'})

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

    def test_retained_current_apk_is_exactly_the_previously_reviewed_artifact(self):
        root = Path(__file__).resolve().parents[2]
        for component in ('apps/console', 'services/assurance', 'services/catalogue', 'services/governance'):
            proved = validate_cache(root/component/'build/apk-cache', self.lock)
            self.assertEqual(list(proved), ['zlib-1.3.2-r0.apk'])

    def test_cache_rejects_tampering_extra_files_symlinks_and_missing_inputs(self):
        root = Path(__file__).resolve().parents[2]
        current = root/'services/assurance/build/apk-cache/zlib-1.3.2-r0.apk'
        with tempfile.TemporaryDirectory() as temporary:
            cache = Path(temporary)/'cache'
            with self.assertRaises(ValueError): validate_cache(cache, self.lock)
            cache.mkdir()
            with self.assertRaises(ValueError): validate_cache(cache, self.lock)
            target = cache/current.name
            raw = current.read_bytes()
            for changed in (raw[:-1], bytes([raw[0] ^ 1])+raw[1:]):
                target.write_bytes(changed)
                with self.assertRaises(ValueError): validate_cache(cache, self.lock)
            target.write_bytes(raw)
            extra = cache/'unreviewed.apk'
            extra.write_bytes(raw)
            with self.assertRaises(ValueError): validate_cache(cache, self.lock)
            extra.unlink()
            target.unlink()
            target.symlink_to(current)
            with self.assertRaises(ValueError): validate_cache(cache, self.lock)


if __name__ == '__main__':
    unittest.main()
