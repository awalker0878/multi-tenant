"""Every actual SSH invocation/retry requires its original live owner."""
import os
from pathlib import Path
import sys

from ansible.errors import AnsibleConnectionFailure
from ansible.plugins.connection.ssh import Connection as SSHConnection, DOCUMENTATION as SSH_DOCUMENTATION

DOCUMENTATION = SSH_DOCUMENTATION.replace('name: ssh', 'name: hosting_guarded_ssh', 1)
# Only the sealed reviewed source is admitted to this child process. The
# installed application/Temporal owners remain in the controller's listener.
_source = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_source))
from provisioner.execution import guest_command_client as client
if not Path(client.__file__).resolve().is_relative_to(_source):
    raise ImportError('The guest command client must belong to the sealed source')


class Connection(SSHConnection):
    transport = 'hosting_guarded_ssh'

    def _bare_run(self, cmd, in_data, sudoable=True, checkrc=True):
        try:
            session = client.load_session(os.environ['HOSTING_GUEST_COMMAND_SESSION'])
            target = session['target']
            if (len(cmd) < 3 or cmd[0].decode() != session['ssh']
                    or cmd[-2].decode() != target['address']
                    or self.get_option('host') != target['address']
                    or self.get_option('port') != target['port']
                    or self.get_option('remote_user') != target['user']):
                raise PermissionError('SSH command changed its original pinned endpoint or account')
            actual = list(cmd)
            actual[-1] = client.machine_command(actual[-1].decode('utf-8'), target, session['native']).encode('utf-8')
            command = [arg.decode('utf-8') for arg in actual]
            client.authorize(session, command=command, in_data=in_data)
        except (OSError, ValueError, KeyError, TypeError, UnicodeError, PermissionError) as exc:
            raise AnsibleConnectionFailure('Current original guest command authority is unavailable') from exc
        result = super()._bare_run(actual, in_data, sudoable=sudoable, checkrc=checkrc)
        # A completed transport cannot turn a revoked original task into proof.
        try:
            client.authorize(session, command=command, in_data=in_data)
        except (OSError, ValueError, KeyError, TypeError, PermissionError) as exc:
            raise AnsibleConnectionFailure('Guest command finished after its original authority became unavailable') from exc
        return result
