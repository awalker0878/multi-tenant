"""hosting mobility-plan — plan a sovereign cross-platform workload move.

The command is a transport over the shared provisioning/mobility service. It never
contacts either platform and never moves workload state.
"""
from __future__ import annotations

from provisioner.cli.support import EXIT_OK, EXIT_REFUSED
from provisioner.domain.errors import ProvisioningError
from provisioner.execution.service import Context, mobility_plan_for

RESULT_FORMAT = 'hosting-mobility-plan-result/1'


def run(context: Context, mobility_intent, target_inventory=None,
        artifact_registry=None) -> tuple[int, dict]:
    if not mobility_intent:
        error = ProvisioningError(
            'SCHEMA_VALIDATION_FAILED',
            'mobility-plan requires --mobility-intent',
            path='$.mobility')
        return EXIT_REFUSED, {'format': RESULT_FORMAT, 'status': 'REFUSED',
                              'source': context.source, 'errors': [error.to_dict()],
                              'native_contact': False}
    try:
        plan = mobility_plan_for(context, mobility_intent, target_inventory,
                                 artifact_registry)
    except ProvisioningError as error:
        return EXIT_REFUSED, {'format': RESULT_FORMAT, 'status': 'REFUSED',
                              'source': context.source, 'mobility_source': str(mobility_intent),
                              'errors': [error.to_dict()], 'native_contact': False}
    payload = dict(plan)
    payload['format'] = RESULT_FORMAT
    payload['source'] = context.source
    payload['mobility_source'] = str(mobility_intent)
    return EXIT_OK, payload
