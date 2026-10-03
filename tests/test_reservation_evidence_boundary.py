"""Read-only export boundaries; no allocation service, database or native contact."""
from __future__ import annotations

from contextlib import contextmanager, redirect_stdout
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from provisioner import repository
from provisioner.allocations import reservation_evidence as records
from tests.test_reservation_preflight import AS_OF, intent, journal, reservation_record


class ReservationEvidenceBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.path = self.root / 'index.json'
        self.document = records.load()
        self.raw = json.dumps(self.document).encode('utf-8')
        self.path.write_bytes(self.raw)

    def test_regular_export_is_read_without_mutation_or_shared_cache(self):
        self.assertEqual(records.load(self.path), self.document)
        value = records.load(self.path)
        value['records'].append({'not': 'shared'})
        self.assertEqual(records.load(self.path), self.document)
        self.assertEqual(self.path.read_bytes(), self.raw)
        self.assertEqual(list(self.root.iterdir()), [self.path])

    def test_parser_preserves_supported_json_encodings_and_decimal_strings(self):
        document = {'quantity': '001.2500', 'unicode': 'Données', 'integer': 123}
        for encoding in ('utf-8', 'utf-16', 'utf-32'):
            self.path.write_bytes(json.dumps(document, ensure_ascii=False).encode(encoding))
            self.assertEqual(records.load(self.path), document)

    def test_canonical_record_digest_is_unchanged(self):
        value = reservation_record(intent())
        expected = hashlib.sha256(json.dumps(value, sort_keys=True,
            separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        self.assertEqual(records.canonical_digest(value), expected)
        self.assertEqual(repository.canonical_record_digest(value), expected)

    def test_existing_held_consumed_terminal_and_uncertain_semantics_survive(self):
        for state in records.STATES:
            value = reservation_record(intent(), state=state)
            if state == 'EXPIRED':
                value['expires_at'] = value['last_observed_at']
            index = journal(value)
            before = json.dumps(index, sort_keys=True)
            result = records.validate(index, as_of=AS_OF)
            self.assertEqual(result['records'][0]['state'], state)
            self.assertEqual(result['unresolved_count'], int(state == 'UNCERTAIN'))
            self.assertEqual(json.dumps(index, sort_keys=True), before)

    def test_empty_oversized_and_missing_inputs_do_not_fall_back(self):
        for raw in (b'', b' ' * (records.MAX_INDEX_BYTES + 1)):
            self.path.write_bytes(raw)
            with self.assertRaises(ValueError):
                records.load(self.path)
        self.path.unlink()
        with self.assertRaises(FileNotFoundError):
            records.load(self.path)

    def test_exact_file_size_bound_is_accepted_without_off_by_one(self):
        self.path.write_bytes(b'{}' + b' ' * (records.MAX_INDEX_BYTES - 2))
        self.assertEqual(records.load(self.path), {})
        with self.path.open('ab') as stream:
            stream.write(b' ')
        with self.assertRaises(ValueError):
            records.load(self.path)

    def test_duplicate_nonfinite_and_malformed_json_fail_closed(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":{"k":1,"k":2}}', b'{"x":NaN}',
                    b'{"x":Infinity}', b'{"x":-Infinity}', b'{"x":1e999}',
                    b'{"x":-1e999}', b'\xff', b'[]', b'null', b'true', b'{} {}'):
            self.path.write_bytes(raw)
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                records.load(self.path)

    def test_excessive_nesting_is_a_bounded_cli_failure_not_a_traceback(self):
        self.path.write_bytes(b'{"x":' + b'[' * 2000 + b'0' + b']' * 2000 + b'}')
        output = io.StringIO()
        with redirect_stdout(output):
            code = records.main(['--index', str(self.path)])
        self.assertEqual(code, 2)
        result = json.loads(output.getvalue())
        self.assertEqual(result['status'], 'FAILED_EXPORTED_RESERVATION_RECORDS')
        self.assertFalse(result['may_apply'])
        self.assertNotIn('Traceback', output.getvalue())

    def test_directory_and_device_are_not_json_sources(self):
        with self.assertRaises((ValueError, OSError)):
            records.load(self.root)
        if os.name == 'posix':
            with self.assertRaises(ValueError):
                records.load(Path('/dev/null'))

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'POSIX FIFO boundary')
    def test_fifo_is_rejected_without_waiting_for_a_writer(self):
        self.path.unlink()
        os.mkfifo(self.path)
        result = subprocess.run([sys.executable, '-m',
            'provisioner.allocations.reservation_evidence', '--index', str(self.path)],
            cwd=records.ROOT, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'FAILED_EXPORTED_RESERVATION_RECORDS')
        self.assertEqual(result.stderr, '')

    def test_final_symlink_and_linked_ancestor_are_rejected(self):
        alias = self.root / 'alias.json'
        alias.symlink_to(self.path)
        with self.assertRaises(ValueError):
            records.load(alias)
        directory = self.root / 'linked'
        directory.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            records.load(directory / self.path.name)

    def test_observed_mutation_and_path_replacement_during_read_are_rejected(self):
        fdopen = os.fdopen
        for replacement in (False, True):
            self.path.write_bytes(self.raw)
            @contextmanager
            def changed(*args, **kwargs):
                with fdopen(*args, **kwargs) as stream:
                    yield stream
                    if replacement:
                        other = self.root / 'replacement'
                        other.write_bytes(self.raw)
                        other.replace(self.path)
                    else:
                        self.path.write_bytes(self.raw + b' ')
            with self.subTest(replacement=replacement), patch.object(records.os, 'fdopen', changed):
                with self.assertRaises((ValueError, OSError)):
                    records.load(self.path)

    def test_descriptor_is_closed_after_success_or_parse_refusal(self):
        close = os.close
        for raw in (self.raw, b'[]', b'{"v":NaN}'):
            self.path.write_bytes(raw)
            with patch.object(records.os, 'close', wraps=close) as closed:
                try:
                    records.load(self.path)
                except ValueError:
                    pass
                self.assertEqual(closed.call_count, 1)
                with self.assertRaises(OSError):
                    os.fstat(closed.call_args.args[0])

    def test_repository_reference_is_exact_and_requires_a_regular_file(self):
        (self.root / 'docs').mkdir()
        (self.root / 'docs/evidence.md').write_text('Synthetic reference, not approval.')
        self.assertEqual(records.repository_ref('docs/evidence.md', self.root), 'docs/evidence.md')
        for value in ('./docs/evidence.md', 'docs//evidence.md', 'docs/../docs/evidence.md',
                      'docs/evidence.md/', 'docs\\evidence.md', '../outside', 'C:/file',
                      str(self.root / 'docs/evidence.md'), 'docs', '.', 'missing.md'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                records.repository_ref(value, self.root)

    def test_repository_reference_cannot_follow_an_outside_or_inside_alias(self):
        (self.root / 'actual').mkdir()
        (self.root / 'actual/evidence').write_text('synthetic')
        (self.root / 'link').symlink_to(self.root / 'actual', target_is_directory=True)
        with self.assertRaises(ValueError):
            records.repository_ref('link/evidence', self.root)
        (self.root / 'linked-file').symlink_to(self.path)
        with self.assertRaises(ValueError):
            records.repository_ref('linked-file', self.root)

    def test_repository_reference_rejects_nonstring_and_empty_values(self):
        for value in (None, [], {}, 1, True, '', 'a\n', 'x' * 513):
            with self.subTest(value=value), self.assertRaises(ValueError):
                records.repository_ref(value, self.root)

    def test_retired_import_is_absent_and_all_record_consumers_share_the_owner(self):
        from provisioner.allocations import reservation_preflight as check_reservation_preflight, ipam_preflight as check_ipam_allocation_preflight
        self.assertIsNone(importlib.util.find_spec('scripts.check_reservation_records'))
        self.assertIs(check_reservation_preflight.records, records)
        self.assertIs(check_ipam_allocation_preflight.reservation_records, records)
        with patch.object(records, 'load', return_value=self.document) as loaded:
            self.assertIs(repository.reservation_records(), self.document)
            loaded.assert_called_once_with(records.INDEX)
        self.assertEqual(records.load.__module__, 'provisioner.allocations.reservation_evidence')

    def test_reading_and_checking_exports_do_not_open_network_connections(self):
        with patch('socket.socket', side_effect=AssertionError('No allocation service contact')):
            result = records.validate(records.load(self.path), as_of=AS_OF)
        self.assertEqual(result['record_count'], 0)

    def test_expired_hold_is_still_refused_instead_of_becoming_free_capacity(self):
        value = reservation_record(intent())
        value['expires_at'] = value['last_observed_at']
        with self.assertRaisesRegex(ValueError, 'reconciliation'):
            records.validate(journal(value), as_of=AS_OF)


if __name__ == '__main__':
    unittest.main()
