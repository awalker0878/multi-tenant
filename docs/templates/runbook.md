# Runbook template — Action

Record owner/on-call responsibility, supported product/dependency versions, environment scope, rehearsal status/date and evidence references. Mark a design procedure unrehearsed until demonstrated.

## Trigger and prerequisites

Describe when to use this procedure, required access/approval, current health, backups, reservations, dependencies, information to gather and prohibited conditions. Identify any native side effects.

## Procedure

For every step state: actor, precise action/command, expected observation, timeout, stop condition and evidence to record. Distinguish read-only diagnostics from mutations. Use variable names and synthetic examples; never embed secrets or live endpoint details.

## Failure, stop and recovery

Define how to pause safely, preserve authority/operation state, reconcile uncertain outcomes and escalate. Explain rollback boundaries and when forward recovery or owner decisions are required. Do not repeat a possibly completed native operation merely because a command timed out.

## Verification and closure

Define service checks, denied-access/security checks as relevant, data integrity, monitoring/alert recovery, evidence, communication owner and cleanup. Record measured recovery/downtime, remaining limitations and follow-up work.
