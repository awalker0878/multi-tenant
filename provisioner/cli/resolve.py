"""`hosting resolve` — show the fully resolved intent without selecting a site.

Resolution is deterministic and platform-independent: profiles, zones, lifecycle
and service bindings are decided here. Placement and allocation are not.
"""
from __future__ import annotations

from provisioner.cli.support import EXIT_OK, EXIT_REFUSED, Context
from provisioner.compiler import normalize as compiler_normalize
from provisioner.compiler import profiles as compiler_profiles
from provisioner.domain.errors import ProvisioningError
from provisioner.policy import diagnostics as policy_diagnostics
from provisioner.policy import semantic, standards

RESULT_FORMAT = 'hosting-resolve-result/1'


def run(context: Context) -> tuple[int, dict]:
    rules = standards.load_rules()
    try:
        request = compiler_normalize.normalize(context.document, source=context.source)
        resolution = compiler_profiles.resolve(request, context.catalog)
        diagnostics = compiler_profiles.validate(resolution, context.catalog)
        diagnostics.extend(semantic.validate(request.document, resolution,
                                             context.catalog).errors)
        policy_diagnostics.collect(request.document, rules, diagnostics)
        if diagnostics.errors:
            return EXIT_REFUSED, {'format': RESULT_FORMAT, 'status': 'REFUSED',
                                  'source': context.source,
                                  'errors': [e.to_dict() for e in diagnostics.errors]}
        payload = {'format': RESULT_FORMAT, 'status': 'RESOLVED',
                   'source': context.source, 'request_digest': request.digest,
                   'resolution': resolution.to_dict(),
                   'zones': list(compiler_normalize.zones(request)),
                                      'services': dict(resolution.services),
                   'warnings': [w.to_dict() for w in diagnostics.warnings],
                   'limits': ['Resolution is platform-independent intent',
                              'No site, cell, prefix or address is selected yet'],
                   'native_contact': False}
        return EXIT_OK, payload
    except ProvisioningError as error:
        return EXIT_REFUSED, {'format': RESULT_FORMAT, 'status': 'REFUSED',
                              'source': context.source, 'errors': [error.to_dict()]}