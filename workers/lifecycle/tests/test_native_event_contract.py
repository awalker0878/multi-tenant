"""Every implemented native journal event must be admitted by the current SQL migration.

This catches missing CHECK-enum updates without claiming to exercise PostgreSQL.
The separate disposable-Postgres suite proves persistence and permissions.
"""

import ast
import re
from pathlib import Path


def test_native_event_contract_includes_all_implemented_adapter_receipts() -> None:
    root = Path(__file__).parents[1]
    migrations = sorted((root / "migrations/native").glob("*.sql"))
    current = migrations[-1].read_text()
    allowed = set(re.findall(r"'([a-z_]+)'", current))
    emitted: set[str] = set()
    for path in (root / "src").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "record"
                and len(node.args) >= 3
            ):
                event = node.args[1]
                candidates = [event.body, event.orelse] if isinstance(event, ast.IfExp) else [event]
                emitted.update(
                    candidate.value
                    for candidate in candidates
                    if isinstance(candidate, ast.Constant) and isinstance(candidate.value, str)
                )
    assert emitted and not emitted - allowed
