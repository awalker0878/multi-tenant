"""Added inline suppressions require an exact, prior approved exception."""
from collections import Counter
import re
from policy import need

MARKER = re.compile(r'type:\s*ignore|\bnoqa\b|phpstan-ignore|@ts-ignore|@ts-nocheck|eslint-disable|\bnosec\b', re.I)


def check_added_suppressions(path, before, after, exceptions, head):
    old = Counter(line.strip() for line in before.splitlines() if MARKER.search(line))
    new = Counter(line.strip() for line in after.splitlines() if MARKER.search(line))
    if new - old:
        need(any(e['kind'] == 'type-analysis' and e['rule_id'] == 'inline-type-suppression'
                 and path in e['paths'] and e['source_revision'] == head for e in exceptions),
             'unapproved_inline_suppression:' + path)
