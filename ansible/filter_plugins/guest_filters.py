"""Pure/local inventory checks; never opens a native connection."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from datetime import datetime, timezone
from tools.guest_inventory import gate, timestamp


class FilterModule:
    def filters(self):
        return {'hosting_guest_gate': gate,
                'hosting_handoff_current': lambda value: timestamp(value) > datetime.now(timezone.utc)}
