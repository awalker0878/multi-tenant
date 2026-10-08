# Console frontend engineering

Owner: product engineering, with security, accessibility and service-owner review. Applies to `apps/console/` and P00.03, P01, P02.05, P03.04, P05.05, P06.06 and Q10. These are implementation and review requirements; delivery evidence belongs in the [delivery register](../implementation/delivery-register.yaml).

The [console service specification](../services/console.md) owns the product boundary. [ADR-019](../decisions/adr-019-console-rendering-and-session-model.md) retains the proposed compiled-assets, Laravel-session and bounded-polling model. This document defines how to implement that model safely as the console grows. It does not move authority from the owning domain services into the browser.

## Verified stack and compatibility decisions

Official sources were reviewed on **2026-10-04**. Laravel 13's Vue starter kit uses Inertia 3 and Vue 3 Composition API. Inertia 3 is a released major with version-specific documentation. Vite 8 is released and uses Rolldown; older Rollup/esbuild configuration examples require review against the selected release. Those facts support the requested stack, but do not establish that every exact dependency combination has passed this project's build and browser tests. [S1–S3]

P00.03 must record exact PHP, Laravel, Inertia Laravel/Vue adapters, Vue, TypeScript, Tailwind, Vite, Laravel Vite plugin, Node, package-manager and test-tool versions in the BOM and lockfiles. Confirm adapter and plugin peer constraints, clean installation, production build, session navigation, asset version changes and supported browsers. Use an actively supported Node release satisfying Vite's engine constraints; its published 20.19+/22.12+ minimums are compatibility information, not a recommendation to adopt an end-of-support release. Never suppress a peer conflict to make the baseline appear compatible. [S2–S3]

| Browser | Published Vite 8 production default | Tailwind 4 core floor | Derived minimum for this combination |
| --- | --- | --- | --- |
| Chrome | 111 | 111 | 111 |
| Edge | 111 | Chromium-based; qualify actual Edge build | 111, subject to qualification |
| Firefox | 114 | 128 | 128 |
| Safari | 16.4 | 16.4 | 16.4 |

This is a compatibility lower bound inferred from the two upstream documents, **not the application's support matrix**. P00 records maintained enterprise browser versions, managed policies, operating systems and assistive technology combinations actually supported. Optional CSS features can require newer browsers; a JavaScript legacy plugin does not make unsupported Tailwind CSS features work. Qualify restricted-network asset loading, secure-context history encryption, zoom and keyboard use on that matrix. [S4–S5]

## Structure and ownership

Keep Laravel presentation routing and controller composition in the console. Inertia connects that server to Vue pages; it does not require an additional client-side router or a duplicate browser-facing domain API. The console calls the service contracts server-side using approved delegation. [S1–S2]

| Location under `apps/console/` | Responsibility |
| --- | --- |
| `app/Http/Controllers/`, `app/Http/Requests/`, `app/Http/Presenters/` | Normal Laravel HTTP entrypoints, validation and explicit allowlisting for Inertia responses; a simple authorized read may stay in its controller. Presenters are the project's response-shaping convention. |
| `app/Application/<Capability>/Actions/` | Console use cases with `handle()`, authorization and remote-service orchestration; dependencies on external services use owned contracts. |
| `app/Domain/<Capability>/` | Console-owned behavior and any corresponding Eloquent models; no copies of another service's aggregates or database models. |
| `app/Infrastructure/` | Approved remote-service clients and external transport adapters. |
| `app/Policies/`, `app/Jobs/`, `app/Listeners/`, `app/Providers/` | Normal Laravel authorization, asynchronous entrypoints and dependency registration. |
| `bootstrap/`, `routes/`, `database/` | Framework bootstrapping, routing, migrations, factories and seeders for console-owned data. |
| `resources/js/app/` | Browser bootstrap, providers and shell composition. |
| `resources/js/pages/` and `journeys/` | Thin Inertia route entrypoints and cross-context operator journeys using public context interfaces. |
| `resources/js/contexts/<context>/features/<capability>/` | Context-aligned feature components, composables, view models, API adaptation and tests; private internals behind explicit exports. |
| `resources/js/contexts/<context>/index.ts` | Reviewed public presentation interface for that context; no blanket re-export of all internals. |
| `resources/js/shared/ui/`, `shared/lib/`, `shared/types/` | Accessible UI primitives and narrow technical utilities; no service aggregates, hidden API calls or tenant authority. |
| `resources/css/` | Tailwind theme tokens, typography and approved shared styles. |

The PHP layout follows [ADR-024](../decisions/adr-024-pragmatic-laravel-domain-convention.md) and the [context code model](../architecture/context-code-structure.md). It allows direct Eloquent access to console-owned data; DTOs and repositories need a concrete purpose. The TypeScript context and presenter conventions are project choices, extending Laravel's documented starter structure. Prefer Vue single-file components with `<script setup lang="ts">`, typed props/emits and Composition API. A feature cannot deep-import another frontend context's files or import an owning service's PHP/Python implementation. Cross-context composition belongs in `journeys/` and consumes reviewed context exports; capabilities within one frontend context can collaborate directly. Shared UI/utilities cannot import upward into contexts or pages. Enforce resolved aliases, relative paths and dynamic-import rules through the selected frontend boundary tooling in P01; TypeScript path aliases alone do not enforce architecture. Do not create a global store that duplicates every server aggregate. Keep temporary form state close to its feature. [S1, S6]

Enable TypeScript `strict`, run Vue-aware type checking separately from bundling, and fail CI on errors. Vite transformation is not a type-check gate. Share generated contract types from the canonical versioned schemas where available; presenters still own the narrower page contract. Treat network input as untrusted at runtime: a TypeScript assertion is not validation. Test schema-to-client generation for drift; do not hand-maintain competing definitions of job states or approval digests. Represent identifiers and revisions using their contract types without unsafe numeric coercion. [S6–S7]

## Page props and browser data boundaries

Treat every Inertia prop as disclosed to the authenticated browser, including initial HTML, deferred requests, partial reloads and remembered history. Serialize only the fields needed for the current authorized page. Never spread an Eloquent model, service response, exception or complete policy record into page props. Namespace minimal shared props, and ensure lazy/deferred evaluation applies the same current tenant and authorization checks as the initial page. Partial-response headers choose data to request; they never authorize it. [S8–S9]

| Data | Browser rule |
| --- | --- |
| Actor and tenant display | Minimal approved labels/IDs plus presentation capabilities; no directory-wide membership dump. |
| Page record | Authorized fields, resource revision/ETag, freshness time and explicit unavailable state. |
| `can`/capability hints | Explain available actions; every command is independently authorized server-side. |
| Secrets | No platform credentials, delegation tokens, session identifiers, private keys or secret payloads in props, URLs, bundles, logs, analytics or browser storage. |
| Evidence | Authorized summaries and controlled retrieval references; avoid embedding evidence artifacts or long-lived signed download URLs in page history. |

Prefer no-store responses for authenticated sensitive HTML/page data and keep reverse proxies/CDNs from caching them as shared pages. Any deliberately cached service composition is keyed by environment, tenant, actor/effective authorization scope, resource revision and freshness policy. Cache correctness and revocation must be tested before enabling the cache. Permission hints, approvals and current operation state must not use Inertia once props. Disable speculative prefetch for privileged or sensitive pages until its cache and revocation behavior are qualified. [S8–S10]

Use Inertia history encryption for authenticated pages and clear the history key on logout, effective tenant changes and privilege-context changes. Encryption reduces recovery of stale browser-history data after key clearing; it does not protect an active page from XSS or replace authorization. Inertia stores the key in session storage, so do not describe history as a secret vault. Only allowlist non-sensitive fields for remembered form state; exclude credentials, evidence, security policy bodies and destructive-action confirmations. [S11–S12]

## Authentication, CSRF and tenant changes

Follow [security and tenancy](security-and-tenancy.md) and [identity and trust](../operations/identity-and-trust.md) for issuer/delegation validation, proxy trust, cookies and endpoint authorization. Regenerate the Laravel session after authentication and privilege transitions. Logout invalidates the server session, regenerates its CSRF token and clears browser context; provider logout semantics remain ADR-009's responsibility. Implement the deployment-created local administrator, mandatory first-login password change and console OIDC configuration flow defined by [ADR-009](../decisions/adr-009-identity-delegation-and-authorization.md). Local login ends at verified OIDC activation. Password and client-secret fields are write-only and are excluded from page props, history and remembered state. Public self-registration and automatic local-password recovery are outside this setup flow. [S1, S13]

Keep browser mutation routes under the approved Laravel request-forgery protection and Inertia adapter cookie/header flow. Inertia's Laravel guidance specifically warns against a fixed `csrf-token` meta tag, because it interferes with token refresh. Test session rotation, cross-site denial and expired submissions with production middleware enabled. Display a recoverable session/request-verification error; do not silently replay a command after reauthentication. [S14]

A tenant switch is an explicit state transition:

1. Warn about unsaved changes and prevent new submission from the old view. Preserve drafts only under an explicitly approved, scoped policy.
2. Validate access to the destination tenant on the server. Rotate the browser context generation, clear the old page/history/cache/remembered state, and dispose of subscriptions, polling timers and feature stores.
3. Cancel outstanding view requests where possible and reject late responses whose tenant, actor/context generation or resource identity no longer matches the active page. Client cancellation does not cancel an accepted server command.
4. Perform a fresh authorized navigation and load the new tenant's capabilities and data before re-enabling actions. Do not let preserved layouts, once props or prefetch caches retain old tenant content.
5. Revalidate on tab restore, back/forward navigation and resume after disconnection. Multi-tab requests carry explicit tenant/resource scope; no endpoint derives a command's tenant solely from a mutable global session selection.

Revocation follows the same clearing and refresh rules. While current mandatory authority cannot be established, privileged controls remain unavailable. These transition rules are project-specific consequences of the multi-tenant model, not functionality assumed to be supplied by Inertia alone.

## Forms, conflicts and long-running work

Server validation is authoritative. Use Laravel request validation for the presentation command and let the owner service validate domain invariants and current authorization again. For normal Inertia forms, map validation failures into redirects and scoped error bags. Do not send a domain API's JSON `422` response unchanged to a page flow expecting Inertia's redirect/error-prop protocol. Separate direct JSON API clients follow their own documented contract. [S15]

Preserve safe user edits after validation or `412` conflicts, identify the affected fields, focus an error summary and offer a comparison with the current revision. Scope error bags so a failure in one form does not decorate another. Client validation improves feedback only. Never optimistically present an approval, job creation, cancellation or native effect as completed. An accepted request, an uncertain network result and a confirmed service outcome are separate states.

Retain the idempotency identity across a retry of the same command, and keep the fetched ETag and exact plan digest bound to the submission. After timeout or reconnect, ask the owner service for the recorded result before proposing a new command. The browser must show the outcome and safe choices described in the [contract examples](../contracts/examples.md), including held `outcome_unknown` operations.

Polling is read-only, authenticated, bounded and scoped to the visible work. Stop timers on unmount; reduce or pause unnecessary hidden-tab activity; apply backoff/jitter and respect retry guidance after failures. Track freshness and show stale data. Choose polling intervals from [operating targets](../product/operating-targets.md) and measured service load. Inertia provides polling lifecycle support, but it does not decide service capacity or authorize a subscription. [S16]

If ADR-019 later admits live notifications, every subscription requires server-authorized tenant/resource scope. Reconnect reauthenticates and reloads authoritative state; gaps, duplicates and out-of-order notifications cannot regress the displayed resource revision. Treat a notification as a refresh hint unless a separately reviewed versioned projection contract applies. A socket reconnect or browser navigation never cancels a backend workflow.

## Rendering security, accessibility and performance

Compile trusted templates; never compile user-supplied Vue templates. Render untrusted text through normal escaped interpolation. Prohibit `v-html` and direct `innerHTML` for user-controlled content unless a reviewed sanitizer and narrowly defined content requirement justify an exception; sanitize URLs and reject unsafe schemes before storage/use. Evidence or imported HTML should not run in the console's origin. CSP is an additional layer, not a substitute for these controls. [S17]

Use a reviewed production CSP with Laravel Vite nonce handling where needed; test scripts, styles, asset loading and any approved connections under enforcement. Do not add broad unsafe script allowances to fix development examples. Keep Vite's dev server and devtools out of the production deployment. All `VITE_*` values are public build inputs: credentials and internal signing material must never be placed there. Ship immutable versioned assets with the matching server release and a controlled source-map exposure policy. [S18–S19]

**WCAG 2.2 AA is the project accessibility target**, not a statement of present conformance or legal certification. Verify complete task journeys across the selected browser/assistive-technology matrix: semantic landmarks and labels; keyboard operation and visible, unobscured focus; contrast/reflow/zoom; error identification and correction; status announcements; target sizing; accessible authentication; alternatives to dragging; and destructive-action review. Track the applicable success criteria and exceptions explicitly. Automated checks cover only part of this assessment. [S20]

For Inertia navigation, update the page title and provide deliberate focus management; preserve focus during background polling and announce meaningful changes without reading an entire table repeatedly. Dialogs restore focus, tables retain headers and row meaning, and a color alone cannot communicate safe/blocked/unknown. Build reusable field/error/dialog/status components so accessibility fixes apply consistently. Each journey must remain usable while a dependent service is unavailable.

Measure before introducing rendering complexity. Use page-level code splitting, small shared props, server pagination and bounded tables; virtualize large results only after keyboard and screen-reader evaluation. Avoid unbounded watchers, polling storms and whole-page re-rendering for a single status change. Record bundle size, page readiness, interaction latency and stale-update lag under representative data volume and network conditions. Agree numeric budgets through the operating-target process. SSR remains an ADR decision, not a default fix for slow queries. [S21]

## Verification and change evidence

| Layer | Required evidence |
| --- | --- |
| Static/build | Formatting/lint and Vue-aware type checks; lockfile installation; production build; dependency/secret checks; compatible server/asset manifest. |
| Laravel/Inertia HTTP | Correct component/props and missing forbidden fields; server authorization and tenant isolation; scoped validation errors; deferred/partial/once behavior; safe service error translation. |
| Component/composable | User-observable forms, focus, disabled/held/stale states, request cleanup, tenant-generation rejection and accessibility behavior. |
| Browser integration | Real middleware/session/CSRF; denied direct request despite modified UI; tenant switch with late response; back/history after logout; expired/revoked grant; stale edit; duplicate submission and timeout; asset release change; partial service outage. |
| Qualification | Representative create/review/approve/observe/recover journeys with actual service outcomes, accessibility review, supported browsers and measured performance. |

Use Inertia's Laravel assertions for page contracts and Vue's unit/component/end-to-end approach for distinct failure modes; do not replace authority tests with snapshots of hidden buttons. Select and lock compatible test tools in P00/P01. Test production-built pages against actual browser middleware: framework tests that bypass request-forgery protection do not demonstrate that control. Attach findings to the relevant Q01/Q03/Q04/Q10 evidence and work package; fix or explicitly disposition release-blocking findings. [S22–S23]

For each console change, update the affected page/service contract and tests, then record any changed browser requirement, data-disclosure boundary, authorization rule, user workflow, accessibility criterion or budget in this document or its owning specification. ADR-019 changes only for rendering/session/transport decisions; routine component changes do not need an ADR.

## Primary references

Reviewed 2026-10-04. Sources describe upstream capabilities; the stricter tenancy, disclosure and review rules above are project engineering decisions.

- **S1:** [Laravel 13 starter kits](https://laravel.com/docs/13.x/starter-kits).
- **S2:** [Inertia 3 introduction and support policy](https://inertiajs.com/docs/v3/getting-started).
- **S3:** [Vite 8 release and Node requirements](https://vite.dev/blog/announcing-vite8).
- **S4:** [Vite production browser targets](https://vite.dev/guide/build).
- **S5:** [Tailwind CSS 4 compatibility](https://tailwindcss.com/docs/compatibility).
- **S6:** [Vue TypeScript tooling](https://vuejs.org/guide/typescript/overview.html).
- **S7:** [TypeScript strict configuration](https://www.typescriptlang.org/tsconfig/strict.html).
- **S8:** [Inertia shared data](https://inertiajs.com/docs/v3/data-props/shared-data) and [responses](https://inertiajs.com/docs/v3/the-basics/responses).
- **S9:** [Inertia authorization](https://inertiajs.com/docs/v3/security/authorization).
- **S10:** [Inertia once props](https://inertiajs.com/docs/v3/data-props/once-props) and [prefetching](https://inertiajs.com/docs/v3/data-props/prefetching).
- **S11:** [Inertia history encryption](https://inertiajs.com/docs/v3/security/history-encryption).
- **S12:** [Inertia remembering state](https://inertiajs.com/docs/v3/data-props/remembering-state).
- **S13:** [Laravel 13 authentication and session lifecycle](https://laravel.com/docs/13.x/authentication).
- **S14:** [Inertia CSRF protection](https://inertiajs.com/docs/v3/security/csrf-protection).
- **S15:** [Inertia validation](https://inertiajs.com/docs/v3/the-basics/validation).
- **S16:** [Inertia polling](https://inertiajs.com/docs/v3/data-props/polling).
- **S17:** [Vue security](https://vuejs.org/guide/best-practices/security.html).
- **S18:** [Laravel 13 Vite integration and CSP nonce](https://laravel.com/docs/13.x/vite).
- **S19:** [Vite environment variable exposure](https://vite.dev/guide/env-and-mode).
- **S20:** [W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/).
- **S21:** [Vue performance](https://vuejs.org/guide/best-practices/performance.html).
- **S22:** [Inertia testing](https://inertiajs.com/docs/v3/advanced/testing).
- **S23:** [Vue testing](https://vuejs.org/guide/scaling-up/testing.html).

## Console theme and operator inputs

The console uses shared navy/teal theme tokens, a common Workload Mobility brand
mark, tenant-scoped navigation, consistent controls and responsive cards. The
sidebar becomes an explicit keyboard-accessible navigation disclosure on narrow
screens. Focus outlines, skip navigation, labels, text status indicators and
minimum 44-pixel controls are part of the shared shell. This is implementation
coverage, not an assertion of complete WCAG conformance.

The Operator readiness page consumes Inventory-provided field metadata and
requirements. It keeps drafts in component memory, preserves zero targets,
freezes an uncertain command for exact retry and shows stale-save errors without
discarding the user's edits. A deliberate refresh discards those edits. Saved
packet downloads use a fresh authenticated request; no draft or evidence enters
browser local storage. Existing native authorization and polling boundaries remain
owned by their services.
