# ADR-019 — Console rendering and session model

Owner role: Product engineering lead. Related phases: P00, P01, P02. Record date: 2026-10-04.

Origin: `DESIGN`. Disposition: `PROPOSED` as recorded in the [decision register](decision-register.md).

This record develops the existing baseline for review. No accountable-owner acceptance, experiment result or native qualification is claimed; the register disposition is unchanged.

## Context

The console must present long-running work accurately while fitting the requested Laravel/Inertia/Vue stack. Compiled assets, server sessions and polling are proposed initially. Server-side rendering and live events should be introduced only for a measured user or operating requirement.

## Decision and scope

Compiled console assets/server sessions/polling initially; SSR and live events only if justified.

Use the [frontend engineering standard](../engineering/frontend.md) for implementation conventions. The Laravel/Inertia server remains the browser presentation boundary; domain services retain authorization and records. Inertia's first-party integration does not justify a separate frontend token store, client-side authority or direct browser access to worker/broker interfaces.

Research reviewed on 2026-10-04 confirms the [Laravel 13 Vue starter kit](https://laravel.com/docs/13.x/starter-kits) uses Inertia 3, and [Inertia 3 documentation](https://inertiajs.com/docs/v3/getting-started) is available for the released major. Exact versions, adapter/plugin compatibility and production/browser tests still belong to P00.03; this research does not change the decision's `PROPOSED` disposition.

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
- Page presenters allowlist disclosed data across initial HTML, shared/deferred props, prefetch and history. History encryption and context clearing supplement server authorization; secrets never become browser props.
- Tenant/context changes clear cached and remembered data, dispose of subscriptions/polling, and reject stale in-flight responses. Explicit tenant/resource scope avoids cross-tab session-selection ambiguity.
- Type checks, production builds, real browser security tests and WCAG 2.2 AA assessment are separate evidence obligations. The accessibility target is not a current conformance claim.

## Unresolved details and evidence needed

- Ratify the actual managed browser/assistive-technology support matrix, session expiry and privilege-transition policy, polling intervals and retry/backoff budgets. The engineering standard supplies WCAG 2.2 AA as the target and distinguishes upstream compatibility floors from supported browser versions.
- Identify the measured trigger for live updates or SSR and the additional support responsibilities.
- For any live-event proposal, specify subscription authorization, reconnect/revocation, deduplication, revision ordering and authoritative gap recovery. For any SSR proposal, include its runtime ownership, private data isolation, CSP and deployment/rollback impact.

## Acceptance and validation

- Confirm the build and production session path before P01.01.
- Exercise session expiry, revoked access, held operations and connection loss before P02.05.
- Exercise a tenant switch with delayed responses, history/back navigation after logout, real CSRF middleware, permission changes and form error isolation. Prove that an altered UI still cannot authorize a denied command.
- Assess accessibility, task completion and update performance at G03/G10 before expanding the delivery model.

Record actual reviewer identity, decision date and evidence references when review occurs. Record delivery and gate outcomes in the delivery register; updating this ADR does not complete a work package.

## Revisit conditions

User evidence shows unacceptable task latency or accessibility behavior, or a browser/security constraint requires a different session or rendering approach.

## Related records

- [Decision register](decision-register.md) — authority for disposition, origin and blocking checkpoint.
- [Phased implementation plan](../implementation/phased-plan.md) — package and gate sequence.
- [ADR authoring template](../templates/adr.md) — required decision-record fields.
