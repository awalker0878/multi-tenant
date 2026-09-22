"""`hosting plan` — the reference command of the provisioning interface.

One invocation derives the whole decision from the portable request: profiles,
policy, platform, site, cell, domain placement, service bindings, capacity and
address reservations, Terraform and Ansible scopes, the verification plan and the
activation hold. No provider-native identifier appears in the input.
"""
from __future__ import annotations

from provisioner.cli.support import EXIT_OK, EXIT_REFUSED
from provisioner.domain.errors import ProvisioningError
from provisioner.execution.service import Context, plan_for

RESULT_FORMAT = 'hosting-plan-result/1'


def run(context: Context, compile_environment: bool = True) -> tuple[int, dict]:
    try:
        plan = plan_for(context, compile_environment=compile_environment)
    except ProvisioningError as error:
        return EXIT_REFUSED, {'format': RESULT_FORMAT, 'status': 'REFUSED',
                              'source': context.source, 'errors': [error.to_dict()],
                              'native_contact': False}
    payload = plan.to_dict()
    payload['format'] = RESULT_FORMAT
    payload['source'] = context.source
    return EXIT_OK, payload