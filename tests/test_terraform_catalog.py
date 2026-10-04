import json
import shutil
import tempfile
import unittest
from pathlib import Path

from provisioner.execution.terraform_catalog import ROOT, entries


class TerraformCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / 'terraform', self.root / 'terraform',
                        ignore=shutil.ignore_patterns('.terraform'))

    def test_all_registered(self):
        self.assertTrue(entries(self.root))

    def test_unregistered_configuration_rejected(self):
        p = self.root / 'terraform/extra/main.tf.json'
        p.parent.mkdir()
        p.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Unregistered'):
            entries(self.root)

    def test_wrong_module_rejected(self):
        row = entries(self.root)[0]
        p = self.root / row['root'] / 'main.tf.json'
        doc = json.loads(p.read_text())
        doc['module']['owned']['source'] = '../wrong'
        p.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, 'ownership mismatch'):
            entries(self.root)

    def test_duplicate_rejected(self):
        p = self.root / 'terraform/catalog.json'
        doc = json.loads(p.read_text())
        doc['entries'].append(doc['entries'][0])
        p.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            entries(self.root)


class TerraformCatalogBoundaryTests(unittest.TestCase):
    """The native selection boundary reads reviewed bytes, not ambient modules."""
    setUp = TerraformCatalogTests.setUp
    def rewrite(self, path, value):
        path.write_text(json.dumps(value), encoding='utf-8')

    def catalog(self):
        return json.loads((self.root / 'terraform/catalog.json').read_text())

    def test_valid_content_and_order_are_preserved_without_fixed_counts(self):
        document = self.catalog()
        self.assertEqual(entries(self.root), document['entries'])
        row = document['entries'].pop()
        shutil.rmtree(self.root / row['module'])
        shutil.rmtree(self.root / row['root'])
        document['entries'].reverse()
        self.rewrite(self.root / 'terraform/catalog.json', document)
        self.assertEqual(entries(self.root), document['entries'])

    def test_catalog_and_all_native_files_remain_unmodified(self):
        import hashlib
        def identities():
            return {p.relative_to(self.root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in self.root.rglob('*') if p.is_file()}
        before = identities()
        entries(self.root)
        self.assertEqual(identities(), before)

    def test_closed_catalog_and_entry_fields(self):
        original = self.catalog()
        for change in (lambda d: d.update(extra=True), lambda d: d.pop('format'),
                       lambda d: d.update(entries={}), lambda d: d.update(entries=[]),
                       lambda d: d['entries'][0].update(extra=True),
                       lambda d: d['entries'].__setitem__(0, None)):
            with self.subTest(change=change):
                document = json.loads(json.dumps(original)); change(document)
                self.rewrite(self.root / 'terraform/catalog.json', document)
                with self.assertRaises(ValueError): entries(self.root)

    def test_identity_and_family_are_typed_bounded_and_explicit(self):
        original = self.catalog()
        for key in ('id', 'platform', 'kind', 'owner_scope'):
            for bad in (None, True, 3, [], {}, '', 'x\n', 'x'*129):
                with self.subTest(key=key, bad=bad):
                    document = json.loads(json.dumps(original))
                    document['entries'][0][key] = bad
                    self.rewrite(self.root / 'terraform/catalog.json', document)
                    with self.assertRaises(ValueError): entries(self.root)
        for key, value in (('platform', 'unknown-vendor'), ('kind', 'unreviewed')):
            document = json.loads(json.dumps(original)); document['entries'][0][key] = value
            self.rewrite(self.root / 'terraform/catalog.json', document)
            with self.assertRaises(ValueError): entries(self.root)

    def test_paths_reject_coercion_aliases_traversal_cache_and_foreign_roots(self):
        original = self.catalog()
        for key in ('module', 'root'):
            good = original['entries'][0][key]
            for bad in (None, 1, [], '/', str(self.root / good), '../'+good, './'+good,
                        good+'/', good.replace('/', '//', 1), good.replace('/', '\\'),
                        good.replace('/','/./',1), good+'/../'+good.rsplit('/',1)[-1],
                        'terraform/.terraform/'+good, 'outside/'+good, 'C:/'+good,
                        good+'\n', good+'%20', good+'?' , 'x'*1025):
                with self.subTest(key=key, bad=bad):
                    document = json.loads(json.dumps(original)); document['entries'][0][key] = bad
                    self.rewrite(self.root / 'terraform/catalog.json', document)
                    with self.assertRaises(ValueError): entries(self.root)

    def test_duplicate_properties_nonfinite_and_encoding_fail_in_every_json_file(self):
        row = self.catalog()['entries'][0]
        for relative in ('terraform/catalog.json', row['module']+'/main.tf.json', row['root']+'/main.tf.json'):
            target = self.root / relative; saved = target.read_bytes()
            for raw in (b'{"x":1,"x":2}', b'{"x":{"v":1,"v":2}}', b'{"x":NaN}',
                        b'{"x":Infinity}', b'{"x":1e999}', b'\xff', b'[]', b'null',
                        b'\xef\xbb\xbf{}', b'{"x":'+b'['*1200+b'0'+b']'*1200+b'}'):
                with self.subTest(relative=relative, raw=raw[:35]):
                    target.write_bytes(raw)
                    with self.assertRaises(ValueError): entries(self.root)
            target.write_bytes(saved)

    def test_json_entry_and_scan_budgets_are_enforced(self):
        from unittest.mock import patch
        from provisioner.execution import terraform_catalog as owner
        row = self.catalog()['entries'][0]
        for relative in ('terraform/catalog.json', row['module']+'/main.tf.json', row['root']+'/main.tf.json'):
            target = self.root/relative; saved = target.read_bytes()
            target.write_bytes(b' '*(owner.MAX_BYTES+1))
            with self.assertRaises(ValueError): entries(self.root)
            target.write_bytes(saved)
        with patch.object(owner, 'MAX_ENTRIES', len(self.catalog()['entries'])-1):
            with self.assertRaises(ValueError): entries(self.root)
        with patch.object(owner, 'MAX_PATHS', 1):
            with self.assertRaises(ValueError): entries(self.root)

    def test_only_exact_local_owned_module_is_allowed(self):
        row = self.catalog()['entries'][0]; target=self.root/row['root']/'main.tf.json'
        original=json.loads(target.read_text())
        for bad in (None, {}, '', 'registry/module/provider', 'git::https://example.invalid/module',
                    str(self.root/row['module']), original['module']['owned']['source']+'/',
                    original['module']['owned']['source'].replace('/', '//', 1),
                    original['module']['owned']['source'].replace('/', '/./', 1),
                    '../../../../terraform/'+row['module'].removeprefix('terraform/')):
            document=json.loads(json.dumps(original)); document['module']['owned']['source']=bad
            self.rewrite(target,document)
            with self.subTest(source=bad), self.assertRaises(ValueError): entries(self.root)
        for calls in ({}, None, [], {'owned':None}, {'owned':original['module']['owned'], 'other':{}}):
            document=json.loads(json.dumps(original));document['module']=calls;self.rewrite(target,document)
            with self.subTest(calls=calls),self.assertRaises(ValueError):entries(self.root)

    def test_provider_declarations_are_present_and_equal(self):
        row=self.catalog()['entries'][0];target=self.root/row['root']/'main.tf.json'
        original=json.loads(target.read_text())
        for declaration in (None,[],{}, {'required_providers':None}, {'required_providers':{}},
                            {'required_providers':{'different':{'source':'vendor/other','version':'1.0'}}}):
            document=json.loads(json.dumps(original));document['terraform']=declaration;self.rewrite(target,document)
            with self.subTest(declaration=declaration), self.assertRaises(ValueError):entries(self.root)

    def test_missing_configs_and_duplicate_registered_paths_are_rejected(self):
        document=self.catalog();target=self.root/document['entries'][0]['module']/'main.tf.json'
        target.unlink()
        with self.assertRaises(OSError):entries(self.root)
        target.write_text('{}')
        document['entries'][0]['root']=document['entries'][0]['module']
        self.rewrite(self.root/'terraform/catalog.json',document)
        with self.assertRaises(ValueError):entries(self.root)

    def test_symlinked_files_and_ancestors_are_not_followed_even_inside_the_tree(self):
        row=self.catalog()['entries'][0]
        for relative in ('terraform/catalog.json',row['module']+'/main.tf.json',row['root']+'/main.tf.json',
                         'terraform/modules', 'terraform'):
            target=self.root/relative; moved=target.with_name(target.name+'-real')
            target.rename(moved)
            try:
                target.symlink_to(moved, target_is_directory=moved.is_dir())
                with self.subTest(path=relative),self.assertRaises(ValueError):entries(self.root)
            finally:
                if target.is_symlink():target.unlink()
                moved.rename(target)

    def test_unregistered_linked_directory_is_not_silently_skipped(self):
        link=self.root/'terraform/alias';link.symlink_to(self.root/'terraform/modules',target_is_directory=True)
        with self.assertRaises(ValueError):entries(self.root)

    def test_provider_cache_is_not_an_extra_registered_writer(self):
        cache=self.root/'terraform/.terraform/modules/not-registered'
        cache.mkdir(parents=True);(cache/'main.tf.json').write_text('{}')
        self.assertEqual(entries(self.root),self.catalog()['entries'])

    def test_fifo_input_is_rejected_without_waiting_for_a_writer(self):
        import os
        if not hasattr(os, 'mkfifo'):self.skipTest('POSIX FIFO test')
        target=self.root/'terraform/catalog.json';target.unlink();os.mkfifo(target)
        with self.assertRaises(ValueError):entries(self.root)

    def test_read_errors_are_not_interpreted_as_complete_inventory(self):
        from unittest.mock import patch
        from provisioner.execution import terraform_catalog as owner
        def failed_scan(*args,**kwargs):
            kwargs['onerror'](PermissionError('unreadable source'))
            return iter(())
        with patch.object(owner.os,'walk',failed_scan):
            with self.assertRaises(PermissionError):entries(self.root)

    def test_catalog_is_read_fresh_and_returned_rows_are_not_a_shared_cache(self):
        rows=entries(self.root);rows[0]['platform']='corrupted-local-copy'
        self.assertEqual(entries(self.root),self.catalog()['entries'])
        document=self.catalog();document['entries'][0]['id']='new-reviewed-id'
        self.rewrite(self.root/'terraform/catalog.json',document)
        self.assertEqual(entries(self.root)[0]['id'],'new-reviewed-id')

    def test_legacy_module_absent_and_consumers_use_the_real_package_owner(self):
        import importlib.util
        from provisioner.execution import terraform_run
        from tools import verify_terraform
        from scripts import check_repository
        self.assertIsNone(importlib.util.find_spec('tools.terraform_catalog'))
        self.assertIs(terraform_run.entries,entries)
        self.assertIs(verify_terraform.entries,entries)
        self.assertIs(check_repository.terraform_entries,entries)
        self.assertEqual(entries.__module__,'provisioner.execution.terraform_catalog')
