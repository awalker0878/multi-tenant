import unittest

from resource_observation import parse


FIXTURE = b'''[cpu.stat]
usage_usec 1000
user_usec 700
system_usec 300
nr_periods 12
nr_throttled 1
throttled_usec 20
[cpu.max]
100000 100000
[memory.current]
123456
[memory.peak]
234567
[memory.max]
268435456
[memory.events]
low 0
high 0
max 0
oom 0
oom_kill 0
[pids.current]
4
[pids.max]
64
'''


class ResourceObservationTests(unittest.TestCase):
    def test_preserves_units_and_counters(self):
        value = parse(FIXTURE)
        self.assertEqual(value['cpu']['usage_usec'], 1000)
        self.assertEqual(value['memory_current_bytes'], 123456)
        self.assertEqual(value['memory_limit_bytes'], 268435456)
        self.assertEqual(value['pids_current'], 4)

    def test_unlimited_is_explicit_and_not_zero(self):
        value = parse(FIXTURE.replace(b'100000 100000', b'max 100000')
                      .replace(b'268435456', b'max').replace(b'[pids.max]\n64', b'[pids.max]\nmax'))
        self.assertIsNone(value['cpu_quota_usec'])
        self.assertIsNone(value['memory_limit_bytes'])
        self.assertIsNone(value['pids_limit'])

    def test_missing_or_duplicate_data_is_rejected(self):
        for raw in (FIXTURE.replace(b'oom_kill 0\n', b''), FIXTURE.replace(b'oom_kill 0', b'oom_kill 0\noom_kill 0'),
                    FIXTURE + b'[memory.max]\n1\n', FIXTURE.replace(b'[pids.max]\n64\n', b'')):
            with self.subTest(raw=raw), self.assertRaises(ValueError): parse(raw)

    def test_malformed_empty_and_oversized_data_is_rejected(self):
        for raw in (b'x'*16385, b'', FIXTURE.replace(b'usage_usec 1000', b'usage_usec -1'),
                    FIXTURE.replace(b'100000 100000', b'100000 0'), FIXTURE.replace(b'[pids.current]\n4', b'[pids.current]\n0')):
            with self.subTest(raw=raw[:30]), self.assertRaises(ValueError): parse(raw)


if __name__ == '__main__':
    unittest.main()
