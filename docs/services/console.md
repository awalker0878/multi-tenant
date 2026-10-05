# Console service

Status: P02 local administrator sign-in, mandatory password change and setup/session controls are implemented in the [bootstrap increment](../implementation/p02-local-bootstrap.md). Console-managed [OIDC setup and handover](../implementation/p02-federation.md) and [tenant membership/quota administration](../implementation/p02-tenancy-and-approvals.md) are implemented with bounded development evidence; catalogue/plan/execution journeys and complete accessibility/receiving qualification remain open. Runtime: Laravel 13, Inertia 3, Vue 3, TypeScript, Tailwind CSS 4 and Vite 8, with exact private locks recorded in P01 evidence. Source: `apps/console/`. Owner: product engineering.

The [frontend engineering standard](../engineering/frontend.md) defines component structure, typed page contracts, browser data handling, session transitions, accessibility and verification. It includes primary-source compatibility research reviewed on 2026-10-04. Runtime and browser support require the exact BOM and qualification evidence; requested major versions alone do not demonstrate compatibility.

The [package replay](../implementation/p01-laravel-foundations.md) and [image measurements](../implementation/p01-laravel-images.md) bind actual source, dependency and execution results. Diagnostic liveness does not establish application readiness; readiness remains HTTP 503 until real dependencies and their probes are implemented.

## Purpose and responsibility boundary

Give application owners, reviewers and operators a coherent application journey: describe intent, inspect eligibility, review and approve an exact plan, observe a job and act on authorized recovery choices. Explain incomplete evidence, stale data and blocked actions in terms of the task the user is performing.

The console owns browser sessions, navigation, composed page state and presentation preferences. It does not own tenant authority, domain records, plans, jobs or qualification. It never reads service databases, accepts reusable platform credentials or sends browser-selected native commands to workers.

## Owned data and view model

| Record | Rule |
| --- | --- |
| Browser session | Bound to the local bootstrap identity during setup or a verified external OIDC identity after activation; server-side password-change restriction, lifecycle, CSRF and expiry/logout controls. |
| Presentation preference | User-owned theme/table/filter preferences; tenant-specific saved selections are reauthorized when loaded. |
| Page composition | Disposable view of API results with each source's version, freshness and authorization outcome. |
| Pending command presentation | Client retry key and response reference; the owning API remains authoritative for whether the command succeeded. |

Session and cache storage are private to console. Page caching must include effective tenant and authorization scope; shared fragments cannot reveal one tenant's names to another. Do not place credentials, evidence artifacts or complete intent documents in analytics.

Create explicit page presenters and allowlist serialized fields. The initial HTML, shared/deferred/partial props, prefetch caches and browser history all belong to the disclosure boundary. Do not expose a complete service response or model and rely on Vue to hide fields. Authorization hints, current approvals and operation status cannot be cached as once props. Use encrypted history and clear its key on logout or context changes; this does not make secret-bearing props acceptable.

## Proposed browser surface and backend calls

Browser routes are presentation routes, not a second public domain API. Exact route names are finalized with P02.05/P03.04 accessibility prototypes.

| Browser task | Owning API interaction |
| --- | --- |
| Initial login and mandatory password change | Governance authenticates the deployment-created local administrator and enforces change before any other protected function. |
| Administration → Identity provider | Governance persists external OIDC settings and mappings, protects secret input, tests the connection and activates verified federated administration. |
| `/tenants/{tenant_id}/applications` | Catalogue list/create with current authorized tenant selection. |
| `/tenants/{tenant_id}/applications/{id}` | Catalogue current revision/history; conditional edit retains the fetched ETag. |
| `/tenants/{tenant_id}/assessments/{id}` | Planning assessment result/status and input freshness. |
| `/tenants/{tenant_id}/plans/{id}` | Planning immutable plan plus separately sourced governance approval view. |
| `/tenants/{tenant_id}/jobs/{id}` | Lifecycle job/operation status and assurance evidence references. |
| `/tenants/{tenant_id}/sites/{id}` | Inventory observation health; lifecycle/assurance commissioning state shown distinctly. |

Server-side handlers call the service-relative `/v1/tenants/{tenant_id}` contracts using approved delegated identity. Cross-service actions retain the same correlation chain, but each command gets its own stable idempotency key. Polling is the initial status transport (ADR-019); it does not permit aggressive polling without service budgets.

## Authentication and authorization

Before OIDC activation, Governance authenticates the installation-local administrator; after activation, the external identity provider authenticates users. Governance evaluates tenant membership, resource scope, action and separation of duties in both cases. Console can hide unavailable actions for usability, while receiving APIs independently authorize every request. User-controlled tenant IDs, hidden fields or enabled buttons prove nothing.

On first login with the random password displayed during deployment, show the mandatory password-change screen. Server-side state denies every other protected console/API action until a different password is saved; hiding navigation is insufficient. Do not put either password in Inertia props, remembered forms, browser history, logs or audit payloads. Rotate session/CSRF state after the change and reject the temporary password thereafter.

The changed-password administrator configures external OIDC in Administration → Identity provider. The form collects provider/client details and mappings through Governance's authorized API; client secrets are write-only and never returned in settings or validation responses. Display the callback destination needed for external client registration. Provider settings are persisted application data; setup requires no OIDC environment variables, manifest values or configuration-file editing.

Keep setup access until a tested provider login establishes a federated identity with an explicit administrative grant. Successful activation disables the local account and invalidates its sessions and delegated authority. Invalid settings keep setup available; after activation, provider outages show the defined failure state without reopening local login. See [ADR-009](../decisions/adr-009-identity-delegation-and-authorization.md).

Validate issuer, audience and expiry through the selected federation design; renew only through the approved session flow. Preserve the effective actor and console service identity when delegating. Expiry during a form submission must not turn into an anonymous retry or new command identity. Logout clears local session state according to the chosen provider contract.

Regenerate the session after authentication and privilege transitions; invalidate it and regenerate the CSRF token on logout. Preserve the adapter's supported CSRF refresh flow and production middleware. Tenant changes clear remembered forms, prefetched props, history and feature stores; cancel view requests and ignore late results from the old tenant/context generation. Each command carries explicit tenant/resource scope, including in multiple tabs. Reauthorize after restore/reconnect before enabling privileged actions.

## Concurrency, retries and events

Carry the catalogue ETag from the displayed version to the revision command. A `412` preserves the user's local edits and offers a comparison/reload action; it never silently overwrites current intent. A changed plan digest invalidates the old approval presentation and requires a fresh review.

Map domain validation failures into the console's server-validated Inertia redirect/error-bag flow; do not pass an API JSON `422` through unchanged to an Inertia form. Preserve only safe form inputs, associate errors with fields and an accessible summary, and keep validation messages separate from authorization, conflict and uncertain-outcome states.

Reuse the command idempotency key after a connection failure, query the returned owning-service identifier and show an uncertain/pending response when status is unavailable. Do not invent a second job after an HTTP timeout. Native `outcome_unknown` is shown as held, with the recorded cause and allowed reconciliation action; cancellation is displayed as a request until the job confirms a safe stop.

Console publishes no authoritative domain events. It may later consume versioned notification projections, but those notifications only prompt an authorized refresh. Broker or live-transport access from the browser requires a separately designed tenant subscription policy.

Bound polling to active views, stop it on unmount and back off during failures. A future live channel must reauthorize on reconnect and recover gaps through the owning API; duplicated or older notifications cannot move a displayed revision backwards. Client cancellation of a request never proves that the server command was cancelled.

## Dependencies and degraded behavior

Session storage and service APIs are dependencies in every mode; external OIDC is required for federated login after activation. Before configuration, the protected local setup journey remains available without an external provider. A failed page subsection must show its source and unavailable/stale state; it cannot turn a partial view into a fabricated healthy summary. Governance failure disables new privileged commands. Planning failure can leave catalogue browsing available where authorized; lifecycle failure must not imply jobs stopped.

Bootstrap is P01 deployment plus P02 identity/governance establishment, then P03 real catalogue interaction. The explicit deployment bootstrap operation creates the local administrator and its setup grant. Starting/restarting console replicas creates no identities, grants, tenants or workload resources. Development fixtures remain explicitly synthetic.

## Deployment and operation

Build static assets reproducibly and bind their digest to the server release; keep secrets out of asset bundles. Run Laravel request workers with an approved session store; background UI notifications have bounded work queues. Configure trusted proxy and cookie behavior for the accepted topology. Server rendering is deferred unless ADR-019 changes.

Health distinguishes a live server from a ready session/API composition path. Measure critical-page latency, API dependency failures, session failures and stale/status refresh lag. Trace browser request → service request → job without logging sensitive input. Validate keyboard navigation, screen-reader states, visible focus, actionable errors and destructive-action review with representative roles.

Use WCAG 2.2 AA as the project target and record tested criteria and browser/assistive-technology combinations; do not claim conformance from an automated scan. Enforce a reviewed CSP, compile trusted Vue templates and prohibit unreviewed raw-HTML rendering. TypeScript/Vue checks run separately from the Vite build. Keep public build variables free of secrets and test old-page/new-asset behavior during releases.

## Verification and delivery

P02.01/P02.05 establish sessions/navigation; P03.04 delivers create/edit/history; P04.05 inventory; P05.05 review; P06.06 jobs; P07/P08 the native user journeys. Trace to R02–R05, R14–R15 and R33; Q01/Q03/Q04/Q10 provide evidence at the relevant stages.

Test direct API denial despite manipulated UI, tenant-switch cache isolation, expired session during retry, stale edit preservation, exact digest in approval, partial dependency outage, unknown operation status, polling authorization and safe cancel wording. End-to-end success requires recorded service outcomes; screenshots alone do not close native gates.

## Context source ownership and code control

Owned source root: `apps/console/app/`. Authenticated sessions, tenant navigation and operator task composition. Any Domain models describe console-owned behavior only; business-service models and invariants remain with their owners. Remote-service contracts belong to Application and their transport implementations to Infrastructure.

Use the [context code structure](../architecture/context-code-structure.md), [context registry](../../architecture/context-map.yaml) and [code-control policy](../engineering/code-control.md). This service owns its own `App\` namespace. Organize business behavior in `app/Domain/<Capability>/` and use cases in `app/Application/<Capability>/Actions/`, with `handle()` as the Action entrypoint. Keep external adapters in `app/Infrastructure/` and controllers, requests, jobs, listeners, policies and providers in normal Laravel directories. Domain code cannot depend on Application or Infrastructure; Eloquent and Laravel facilities remain available under [ADR-024](../decisions/adr-024-pragmatic-laravel-domain-convention.md). Same-context capabilities may collaborate directly; repositories and DTOs require a concrete reason. Public API/event schemas define cross-service access, and internal models, use cases and migrations remain private.

The service owner reviews source/dependency changes and maintains legal/forbidden import fixtures, contract consumers and isolated build inputs. Runtime data-access denials remain separate tests. Registration or a static check does not grant a worker additional native authority.

## P02 federation increment

The [federation increment](../implementation/p02-federation.md) adds console-managed provider settings, write-only secrets, browser-bound administrator testing and atomic activation. Provider values remain application settings. Native provider interoperability and full G02 receiving verification remain open.

## P02 tenant navigation increment

The [tenant authority implementation](../implementation/p02-tenancy-and-approvals.md) adds current-membership navigation, owner-checked tenant projections and membership/quota administration. Revoked and guessed tenant navigation returns to the current account page. Real CSRF, session rechecks and history clearing apply; no browser role or selector grants authority. Hosted campaign results and their limitations remain separate from complete browser/accessibility acceptance.
