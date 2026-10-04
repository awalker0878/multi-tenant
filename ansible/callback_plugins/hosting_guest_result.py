"""Write bounded host counters, never task payloads or credentials, for the guest runner."""
import os
from pathlib import Path
import sys
from ansible.plugins.callback import CallbackBase

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from provisioner.execution.run_files import encoded, utcnow, write_new


class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'aggregate'
    CALLBACK_NAME = 'hosting_guest_result'
    CALLBACK_NEEDS_ENABLED = True

    def v2_playbook_on_stats(self, stats):
        destination = os.environ.get('HOSTING_GUEST_RESULT')
        if not destination: return
        write_new(Path(destination), encoded({'format': 'hosting-guest-stats/1',
            'completed_at': utcnow().isoformat(),
            'hosts': {name: stats.summarize(name) for name in sorted(stats.processed)}}))
