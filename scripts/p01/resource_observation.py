"""Read bounded cgroup-v2 counters without sampling environment or workload data."""
import re

FILES = ('cpu.stat', 'cpu.max', 'memory.current', 'memory.peak', 'memory.max',
         'memory.events', 'pids.current', 'pids.max')
PROBE = 'set -eu\n' + '\n'.join(
    f"printf '[{name}]\\n'; cat /sys/fs/cgroup/{name}" for name in FILES)


def parse(raw: bytes) -> dict:
    if len(raw) > 16384:
        raise ValueError('Oversized cgroup observation')
    sections: dict[str, list[str]] = {}
    current = None
    for line in raw.decode('ascii').splitlines():
        if line.startswith('[') and line.endswith(']'):
            current = line[1:-1]
            if current not in FILES or current in sections:
                raise ValueError('Unexpected or duplicate cgroup section')
            sections[current] = []
        elif current is None or not line:
            raise ValueError('Malformed cgroup observation')
        else:
            sections[current].append(line)
    if set(sections) != set(FILES):
        raise ValueError('Incomplete cgroup observation')

    def integer(value):
        if not re.fullmatch(r'[0-9]+', value):
            raise ValueError('Invalid cgroup counter')
        return int(value)

    def scalar(name, limit=False):
        lines = sections[name]
        if len(lines) != 1:
            raise ValueError('Ambiguous cgroup scalar')
        return None if limit and lines[0] == 'max' else integer(lines[0])

    def counters(name, required):
        result = {}
        for line in sections[name]:
            key, value = line.split()
            if key in result:
                raise ValueError('Duplicate cgroup counter')
            result[key] = integer(value)
        if not set(required) <= set(result):
            raise ValueError('Missing cgroup counter')
        return {key: result[key] for key in required}

    cpu = counters('cpu.stat', ('usage_usec', 'user_usec', 'system_usec', 'nr_throttled', 'throttled_usec'))
    events = counters('memory.events', ('oom', 'oom_kill', 'high', 'max'))
    if len(sections['cpu.max']) != 1:
        raise ValueError('Ambiguous CPU limit')
    quota, period = sections['cpu.max'][0].split()
    period_us = integer(period)
    if period_us == 0:
        raise ValueError('Invalid CPU period')
    memory = scalar('memory.current')
    pids = scalar('pids.current')
    if memory == 0 or pids == 0:
        raise ValueError('Empty running-container observation')
    return {'cgroup_version': 2, 'cpu': cpu,
            'cpu_quota_usec': None if quota == 'max' else integer(quota), 'cpu_period_usec': period_us,
            'memory_current_bytes': memory, 'memory_peak_bytes': scalar('memory.peak'),
            'memory_limit_bytes': scalar('memory.max', True), 'memory_events': events,
            'pids_current': pids, 'pids_limit': scalar('pids.max', True)}
