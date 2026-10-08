"""Negative controls for redaction, bounded dimensions and missing-signal truth."""
import json
from pathlib import Path
import tempfile
import unittest

from telemetry import batch_is_accounted, export, freshness, records


class TelemetryTest(unittest.TestCase):
    def setUp(self):
        self.row = dict(schema_version=1, event='http.response', service='planning',
                        source_revision='a' * 40, environment='p01-compose', timestamp_unix_us=1000000,
                        trace_id='b' * 32, span_id='c' * 16, parent_span_id=None,
                        route='/health/live', method='GET', status=200, duration_us=1500)

    def parse(self, row):
        return records((json.dumps(row) + '\n').encode(), 'planning', 'a' * 40, 'p01-compose')

    def test_rejects_secrets_unbounded_labels_invalid_measurements_and_wrong_owner(self):
        for field, value in [('authorization', 'canary'), ('route', '/tenant/private'),
                             ('method', 'unbounded'), ('service', 'lifecycle'),
                             ('source_revision', 'd' * 40), ('trace_id', '0' * 32),
                             ('parent_span_id', '0' * 16), ('status', True), ('duration_us', -1),
                             ('environment', 'unknown')]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.parse({**self.row, field: value})

    def test_rejects_truncated_oversized_duplicate_records_and_fields(self):
        raw = (json.dumps(self.row) + '\n').encode()
        for value in (raw[:-1], raw * 200, raw * 2,
                      raw.replace(b'"schema_version": 1', b'"schema_version": 1, "schema_version": 1')):
            with self.assertRaises(ValueError):
                records(value, 'planning', 'a' * 40, 'p01-compose')

    def test_missing_stale_and_clock_error_never_become_zero_healthy(self):
        self.assertEqual(freshness([], 1000000, 1000), 'MISSING')
        self.assertEqual(freshness([self.row], 1000001, 1000), 'FRESH')
        self.assertEqual(freshness([self.row], 1001001, 1000), 'STALE')
        self.assertEqual(freshness([self.row], -1000001, 1000), 'CLOCK_INVALID')

    def test_concurrent_readiness_spans_cannot_hide_batch_loss_or_create_false_loss(self):
        samples = [{'span_id': 'accepted', 'state': 'buffered'}, {'span_id': 'lost', 'state': 'full'}]
        rows = [{'span_id': 'accepted'}, {'span_id': 'background-readiness'}]
        self.assertTrue(batch_is_accounted(samples, rows))
        self.assertFalse(batch_is_accounted(samples, rows + [{'span_id': 'lost'}]))
        self.assertFalse(batch_is_accounted(samples, rows[1:]))

    def test_counts_spans_and_histograms_agree_without_identity_labels(self):
        rows = self.parse(self.row) + self.parse({**self.row, 'span_id': 'd' * 16, 'duration_us': 11000})
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'signals'
            result = export(rows, target)
            self.assertEqual(result['records'], result['spans'])
            self.assertEqual(result['response_count'], 2)
            metrics = json.loads((target / 'metrics.json').read_text())
            series = metrics['series'][0]
            self.assertEqual(series['duration_buckets_cumulative'], [0, 1, 2, 2, 2])
            self.assertEqual(series['duration_sum_us'], 12500)
            self.assertEqual(set(series['labels']), {'service', 'route', 'method', 'status_class'})
            self.assertFalse(metrics['missing_data_is_zero'])


if __name__ == '__main__':
    unittest.main()
