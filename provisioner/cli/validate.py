"""`hosting validate` — refuse an unusable request before anything is resolved.

Validation covers syntax, structural schema, semantic consistency and standards
policy. It never contacts a platform and never selects a placement.
"""
from __future__ import annotations

from provisioner.cli.support import EXIT_OK, EXIT_REFUSED
from provisioner.compiler import normalize as compiler_normalize
from provisioner.compiler import profiles as compiler_profiles
from provisioner.domain.errors import ProvisioningError
from provisioner.execution.service import Context
from provisioner.policy import diagnostics as policy_diagnostics
from provisioner.policy import semantic, standards

RESULT_FORMAT = 'hosting-validate-result/1'


def run(context: Context) -> tuple[int, dict]:
    rules = standards.load_rules()
    try:
        request = compiler_normalize.normalize(context.document, source=context.source,
                                               catalog=context.catalog)
        resolution = compiler_profiles.resolve(request, context.catalog)
        diagnostics = compiler_profiles.validate(resolution, context.catalog)
        diagnostics.extend(semantic.validate(request.document, resolution,
                                             context.catalog).errors)
        violations = policy_diagnostics.collect(request.document, rules, diagnostics)
        policy = policy_diagnostics.summary(diagnostics, violations, len(rules))
        payload = {'format': RESULT_FORMAT, 'status': 'VALID',
                   'source': context.source, 'request_digest': request.digest,
                   'apiVersion': request.api_version, 'kind': request.kind,
                   'tenant': request.tenant, 'wsd': request.wsd,
                   'profiles': dict(resolution.profiles), 'policy': policy,
                   'errors': [], 'warnings': [w.to_dict() for w in diagnostics.warnings],
                   'native_contact': False}
        if diagnostics.errors:
            payload['status'] = 'REFUSED'
            payload['errors'] = [e.to_dict() for e in diagnostics.errors]
            return EXIT_REFUSED, payload
        return EXIT_OK, payload
    except ProvisioningError as error:
        return EXIT_REFUSED, {'format': RESULT_FORMAT, 'status': 'REFUSED',
                              'source': context.source, 'errors': [error.to_dict()],
                              'warnings': [], 'native_contact': False}