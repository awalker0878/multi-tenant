"""`hosting plan` — the reference command of the provisioning interface.

One invocation derives the whole decision from the portable request: profiles,
policy, platform, site, cell, domain placement, service bindings, capacity and
address reservations, Terraform and Ansible scopes, the verification plan and the
activation hold. No provider-native identifier appears in the input.
"""
from __future__ import annotations

from pathlib import Path

from provisioner.cli.support import EXIT_OK, EXIT_REFUSED, Context, build_context
from provisioner.domain.errors import ProvisioningError
from provisioner.execution import plan as execution_plan

RESULT_FORMAT = 'hosting-plan-result/1'


def plan_for(context: Context, compile_environment: bool = True):
    """Create the plan from an already built context."""
    return execution_plan.create_plan(context.document, context.source, context.inventory,
                                      context.catalog, compile_environment=compile_environment)


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


def run_from_path(request_path, inventory_path=None, profiles_root=None,
                  compile_environment: bool = True) -> tuple[int, dict]:
    """Convenience entry point used by tests and by the dispatcher."""
    try:
        context = build_context(request_path, inventory_path, profiles_root)
    except ProvisioningError as error:
        return EXIT_REFUSED, {'format': RESULT_FORMAT, 'status': 'REFUSED',
                              'source': str(Path(request_path)),
                              'errors': [error.to_dict()], 'native_contact': False}
    return run(context, compile_environment=compile_environment)