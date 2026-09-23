"""The hosting command line.

The command line is a transport. `validate`, `resolve`, `plan`, `status`, `verify`
and `evidence` all call the same core library that the pipeline uses; no command
decides policy, placement, allocation or authority for itself. `apply` exists so
the refusal is explicit and machine-readable, not so a change can be made.

Usage:
    python -m provisioner.cli plan examples/requests/internal-production.yaml

This module is the transport, not an entry point: `provisioner/cli/__main__.py` is
the one entry point, and the active documents name it.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from provisioner.cli import apply as apply_command
from provisioner.cli import evidence as evidence_command
from provisioner.cli import plan as plan_command
from provisioner.cli import resolve as resolve_command
from provisioner.cli import status as status_command
from provisioner.cli import validate as validate_command
from provisioner.cli import verify as verify_command
from provisioner.cli.support import EXIT_INTERNAL, EXIT_OK, EXIT_REFUSED, emit
from provisioner.domain.errors import ProvisioningError
from provisioner.execution.service import build_context

PROGRAM = 'hosting'
COMMANDS = ('validate', 'resolve', 'plan', 'apply', 'status', 'verify', 'evidence')

DESCRIPTION = ('Portable hosting provisioning interface. '
               'Planning is enabled; execution is refused by design.')


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=PROGRAM, description=DESCRIPTION)
    parser.add_argument('command', choices=COMMANDS, help='Command to run')
    parser.add_argument('request', help='Path to a portable request document')
    parser.add_argument('--inventory', default=None,
                        help='Reviewed inventory document (defaults to the non-authoritative fixture)')
    parser.add_argument('--profiles-root', default=None,
                        help='Alternate profile catalog root; the repository catalogs are the default')
    parser.add_argument('--approved-plan', default=None,
                        help='Digest of an already reviewed plan (apply only)')
    parser.add_argument('--approvals', default=None,
                        help='Recorded external approvals bound to a plan digest (apply only)')
    parser.add_argument('--no-compile', action='store_true',
                        help='Resolve the environment document without invoking the existing compiler')
    parser.add_argument('--observations', default=None,
                        help='Native observations document (verify only)')
    parser.add_argument('--generation', type=int, default=1,
                        help='The WSD generation the caller claims (defaults to the first)')
    parser.add_argument('--source-commit', default=None,
                        help='The clean 40-hex commit the delivery handoff binds (apply only)')
    parser.add_argument('--reservation-index', default=None,
                        help='Exported reservation record index used to reconcile capacity')
    parser.add_argument('--capacity-facts', default=None,
                        help='Recorded capacity owner facts used to compile the reservation request')
    return parser


def _load_observations(path):
    if not path:
        return ()
    from provisioner.domain.request import loads
    from provisioner.observation import native as native_module

    target = Path(path)
    document = loads(target.read_text(encoding='utf-8'), str(target))
    rows = document.get('observations') if isinstance(document, dict) else None
    if not isinstance(rows, list):
        raise ProvisioningError('SCHEMA_VALIDATION_FAILED',
                                'An observation document must list observations',
                                path=str(target))
    return tuple(native_module.observed(**row) for row in rows)


def dispatch(argv=None) -> tuple[int, dict]:
    """Route one invocation to its command module and return exit code and payload."""
    args = build_parser().parse_args(argv)
    context = build_context(args.request, args.inventory, args.profiles_root,
                            generation=args.generation)

    if args.command == 'validate':
        return validate_command.run(context)
    if args.command == 'resolve':
        return resolve_command.run(context)
    if args.command == 'plan':
        return plan_command.run(context, compile_environment=not args.no_compile)
    if args.command == 'status':
        return status_command.run(context, args.reservation_index, args.capacity_facts)
    if args.command == 'verify':
        return verify_command.run(context, _load_observations(args.observations),
                                  args.reservation_index, args.capacity_facts)
    if args.command == 'evidence':
        return evidence_command.run(context, args.reservation_index, args.capacity_facts)
    approvals = apply_command.load_approvals(args.approvals)
    return apply_command.run(context, args.approved_plan, approvals,
                             source_commit=args.source_commit,
                             reservation_index=args.reservation_index,
                             capacity_facts=args.capacity_facts)


def main(argv=None) -> int:
    try:
        code, payload = dispatch(argv)
    except ProvisioningError as error:
        emit({'format': 'hosting-cli-result/1', 'status': 'REFUSED',
              'errors': [error.to_dict()], 'native_contact': False})
        return EXIT_REFUSED
    except OSError as error:
        emit({'format': 'hosting-cli-result/1', 'status': 'INTERNAL',
              'errors': [{'code': 'REQUEST_SOURCE_UNREADABLE', 'layer': 'syntax',
                          'message': str(error)}], 'native_contact': False})
        return EXIT_INTERNAL
    emit(payload)
    return code if code in (EXIT_OK, EXIT_REFUSED) else EXIT_INTERNAL