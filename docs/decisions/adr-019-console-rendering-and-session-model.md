# ADR-019 — Console rendering and session model

Owner role: Product engineering lead. Related phases: P00, P01, P02. Record date: 2026-10-04.

Origin: `DESIGN`. Disposition: `PROPOSED` as recorded in the [decision register](decision-register.md).

This record develops the existing baseline for review. No accountable-owner acceptance, experiment result or native qualification is claimed; the register disposition is unchanged.

## Context

The console must present long-running work accurately while fitting the requested Laravel/Inertia/Vue stack. Compiled assets, server sessions and polling are proposed initially. Server-side rendering and live events should be introduced only for a measured user or operating requirement.

## Decision and scope

Compiled console assets/server sessions/polling initially; SSR and live events only if justified.

Initial checkpoint: NOW: P00.03 before P01.01.

Refinement and validation: Browser/session/accessibility constraints before P02.05; user/performance evidence G03/G10.

## Options and trade-offs

| Option | Assessment |
| --- | --- |
| Compiled assets, server sessions and bounded polling | Limits initial runtime dependencies while requiring freshness indicators, polling backoff and clear operation states. |
| Add server-side rendering | May serve an identified rendering requirement but introduces another production execution and deployment path. |
| Add push/live event delivery | May reduce update latency but requires reconnect, ordering, authorization and missed-event recovery semantics. |

## Consequences

- The browser displays authoritative operation state and the age of its observation; navigation or disconnect does not cancel backend work.
- Session expiry, permission changes and failed refreshes need explicit user states and must not leave controls deceptively enabled.

## Unresolved details and evidence needed

- Set browser/accessibility targets, session policy, polling intervals and retry/backoff behavior.
- Identify the measured trigger for live updates or SSR and the additional support responsibilities.

## Acceptance and validation

- Confirm the build and production session path before P01.01.
- Exercise session expiry, revoked access, held operations and connection loss before P02.05.
- Assess accessibility, task completion and update performance at G03/G10 before expanding the delivery model.

Record actual reviewer identity, decision date and evidence references when review occurs. Record delivery and gate outcomes in the delivery register; updating this ADR does not complete a work package.

## Revisit conditions

User evidence shows unacceptable task latency or accessibility behavior, or a browser/security constraint requires a different session or rendering approach.

## Related records

- [Decision register](decision-register.md) — authority for disposition, origin and blocking checkpoint.
- [Phased implementation plan](../implementation/phased-plan.md) — package and gate sequence.
- [ADR authoring template](../templates/adr.md) — required decision-record fields.
