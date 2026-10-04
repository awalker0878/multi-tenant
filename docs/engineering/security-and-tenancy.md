# Security and tenant isolation engineering standard

Owners: IAM/security and the owner of each enforcing service. Applies to every Laravel service, the console and equivalent Python boundaries. Reviewed: 2026-10-04 against Laravel 13 documentation and the primary sources below. These are implementation and review requirements; this document records no completed security assessment or operating authorization.

The [governance specification](../services/governance.md) defines authority; [identity and trust](../operations/identity-and-trust.md) defines issuance, rotation and recovery; the [threat model](../operations/threat-model.md) defines abuse cases. This document translates those boundaries into code and verification obligations. It does not select an identity provider, tenancy package, database isolation topology or session duration in place of ADR-006/009/010/019.

## Verification baseline

Use **OWASP ASVS 5.0.0** as the versioned application-security requirements catalogue and the **OWASP API Security Top 10, 2023 edition** to review API abuse cases. The Top 10 is a risk-awareness reference, not an exhaustive acceptance checklist. Security and product owners must record the applicable ASVS level and requirement set before P02 acceptance. Assess Level 2 as the starting target for the application and explicitly evaluate stronger requirements for execution grants, privileged approvals, secrets and recovery because these paths can affect native infrastructure. This is a risk-based engineering recommendation, not an assertion that a level has been achieved. [S01–S03]

For each applicable ASVS requirement, record its version-qualified identifier, enforcing service, implementation reference, automated or manual verification, evidence revision and reviewer. Record a reason for exclusions and time-bounded exceptions. Do not copy identifier numbers from ASVS 4 into a 5.0.0 assessment. P00.05 owns scope selection; P02 and P06 implement the controls; Q01/Q03/Q04/Q09 exercise them; P10.03 reviews the release evidence. Use the existing delivery register for completion and gate decisions.

## Request identity and authorization

1. Authenticate the principal using the selected guard and verified issuer/audience. Authentication establishes an identity; a user, service token or successful login alone grants no resource action.
2. Build an explicit request-scoped authorization context from verified actor, caller service, environment, current tenant membership and permitted delegation. Treat tenant IDs in URLs, headers and form bodies as requested scope, then validate them against that context. Do not infer an authorized tenant solely from a hostname or a client-selected session value.
3. Resolve the resource inside the authorized tenant boundary, then evaluate action and resource policy. Both the parent tenant and child resource require authorization; a valid nested relationship alone is insufficient.
4. Let the owning service decide authorization even when the console already checked it. A shared policy interface may standardize calls; it must not move ownership of another service's data into governance or the console.
5. Validate and execute only after the required authority checks. Recheck mutable approval, revision and execution conditions at the privileged boundary defined by the service contract. Capture the decision identity without putting credentials into domain records.

In Laravel, use named policies for resource actions and gates for capabilities without a natural model. Apply them consistently to web routes, APIs, jobs and administrative commands. `FormRequest::authorize()` may delegate to the same policy, but validation rules and a hidden UI action do not replace authorization. Do not introduce a `Gate::before` administrator allow-all, inline bypass or support role that skips tenant scope, separation of duties or current admission conditions. A break-glass operation uses its explicit scoped grant and audit path. [S04]

Verify middleware ordering so authentication and tenant-context establishment occur before tenant-dependent model resolution. Keep tenant context request-scoped and mandatory for tenant queries. Routes intentionally operating on global resources declare that boundary explicitly; a missing tenant is not a request to query all tenants.

Laravel session authentication fits a same-origin Inertia interface; enterprise login and service delegation still follow ADR-009/019. Sanctum or Passport is not automatically required because services expose APIs. If Sanctum is selected for a use case, token abilities remain only one input to authorization: `tokenCan()` returns true for first-party SPA requests under Sanctum's stateful authentication, so owner policies must still enforce membership and resource scope. [S05, S06]

Use a maintained OIDC client for enterprise login and configure the issuer and callback destinations through reviewed trust configuration. Validate the received identity token according to that client's OIDC flow, including issuer, intended audience, signature/algorithm, time and nonce where applicable; never trust a decoded token or fetch arbitrary key URLs from untrusted token fields. Do not use an ID token as a general service access token. IAM must define which privileged actions require MFA or fresh authentication, how verified authentication-context evidence is obtained and how expiry/recovery works. An unverified browser claim of MFA cannot unlock approval or break-glass rights. [S21, S22]

## Tenant isolation on every surface

All tenant-bearing models, commands, events and views must identify their boundary. Document genuinely global resources explicitly. A query scope or database constraint can reinforce isolation, but no ORM feature covers all entry paths automatically. The following rules specialize the product's existing tenant and ownership model. [S07, S08]

| Surface | Required implementation rule | Denial or isolation check |
| --- | --- | --- |
| Route binding and lookup | Use scoped nested binding where appropriate and explicit tenant-filtered queries elsewhere; never bind an arbitrary model globally and rely only on its UUID | Tenant A submits B's known ID, including nested, deleted, historical and restore endpoints |
| Lists, relations and validation | Scope joins, search, aggregates, counts, pagination and `exists`/`unique` checks; bind relationship writes to authorized objects in the same allowed scope | B's names, counts or membership cannot be inferred through filters, errors or relationship IDs |
| Bulk commands | Authorize every selected object and define whole-request rejection or an explicitly safe partial-result contract | A mixed A/B selection cannot mutate B or leak its attributes |
| Queued jobs and scheduled work | Carry verified tenant, actor/delegation reference and operation IDs; establish a fresh context and reload scoped records. Pending commands/effects require current actor authority; committed-fact processing uses the consumer's current scoped service authority | Revoke between enqueue and command execution: deny the command. Revoke after a fact commits: preserve authorized audit/evidence/projection processing without restoring actor access |
| Long-lived workers | Clear tenant, actor, locale, log context and tenant-dependent connections after success and failure; do not capture them in process-wide singletons or static state | Alternate A/B jobs and requests in one process, including exception and retry paths |
| Cache and idempotency | Namespace by environment/service and tenant; include actor or policy revision when the result varies by them; authorize protected reads and apply the selected revocation/invalidation bounds | Warm A's cache, read as B, then revoke A; neither shared keys nor stale results grant access |
| Files and exports | Authorize both export creation and retrieval; use tenant-bound object metadata and opaque generated keys; constrain archive members and download disposition | B cannot guess a storage key, reuse A's export ID or receive a URL through another tenant's projection |
| Events and webhooks | Verify producer and registered integration scope; validate tenant ownership and event contract before inbox processing | Forged tenant, wrong integration, replayed ID and changed payload cannot mint authority |
| Notifications and live channels | Resolve recipients from current authorized scope and protect channel subscription; include no secrets in notification payloads | Tenant switching or revoked membership cannot keep receiving protected updates |
| Support and observability | Use dedicated, scoped inspection actions and restricted telemetry access; exclude tenant payloads from broad dashboards | Support without an active grant cannot inspect a tenant through traces, debug tools or health output |

Use the [command-versus-fact execution rules](data-and-messaging.md) when implementing background authorization. The original actor remains attributable on committed records even after revocation. Authenticating and retaining such a fact cannot authorize a new command, native effect or disclosure to a revoked recipient.

Shared hosting does not imply shared database credentials. Retain each context's private persistence and runtime identity. If row-level security or a tenancy package is selected, test its raw SQL, connection pooling, CLI and background-worker behavior; package installation is not isolation evidence.

Signed download URLs are bearer capabilities for their lifetime. Decide whether sensitive evidence needs an authenticated download proxy or a short-lived scoped URL, and document revocation limitations before exposing either. URL signing cannot make an already issued object URL instantly revocable. [S14]

## Input and output boundaries

Use a dedicated Form Request or equivalent command validator for each external command. Pass only explicitly validated, intended fields into application actions; allowlist nested array keys and bound list length, body size, depth and uploaded bytes. Keep tenant, actor, approval status, ownership, audit metadata and privilege fields server-assigned. Reject attempted authority-field overrides rather than silently accepting a misleading payload. Validate tenant-scoped references before constructing the command. [S09]

Maintain explicit mass-assignment allowlists and treat `forceFill`, `forceCreate` and unguarded models as privileged internal escape hatches requiring review. Never pass `request()->all()` into model creation or update. Validation and fillable fields reinforce one another; neither proves that the actor may change a particular field. Use application actions for privileged transitions so callers cannot write a status column to bypass the state machine. [S10]

Bind SQL values and map sort/filter names to server-owned column expressions. Parameters do not sanitize column identifiers, raw SQL fragments or an arbitrary query language. For `Rule::unique()->ignore()`, use the authorized model or its server-resolved key, not a request-supplied ignore value. Recheck invariants through database constraints where needed because pre-write validation can race. [S09, S10]

Return explicit response resources or DTOs and allowlisted Inertia props, not whole Eloquent models or unconstrained relationship serialization. Apply field-level read policy to sensitive approval reasons, connection details and evidence metadata. Encode untrusted text for its output context. A frontend component hiding a field cannot protect a value already delivered to the browser.

## Browser session, request forgery and edge trust

Use HTTPS for operated environments. Configure trusted proxies and forwarded headers to match the actual ingress; block direct bypass of that ingress when trust depends on it. Configure accepted hostnames explicitly, including whether subdomains are trusted, and validate redirect targets. Do not trust an arbitrary `Host` or forwarded protocol/IP header to select a tenant, generate login links or determine rate-limit identity. [S11]

Retain Laravel 13's `PreventRequestForgery` middleware on session-authenticated state-changing routes. Its default checks same-origin `Sec-Fetch-Site` and falls back to CSRF token validation. Do not globally exempt an Inertia/API prefix or switch to origin-only or same-site expansion without assessing the actual browser and subdomain trust boundary. Webhooks that cannot supply browser tokens use narrowly separated routes with their own sender authentication and replay protection. [S12]

Set the session cookie `Secure` and `HttpOnly`; select `SameSite`, cookie domain, idle/absolute lifetimes and any reauthentication requirement against the enterprise login flow. The session cookie and the JavaScript-readable CSRF helper cookie have different purposes. Regenerate the session ID after login and privilege changes; invalidate the session and regenerate the CSRF token on logout. Exercise back navigation, tenant change and concurrent tabs without assuming the browser forgot protected data. [S05, S10]

Define one owner for security headers across ingress and application. Use a tested CSP, restrictive framing policy, MIME-sniffing protection and referrer policy; enable HSTS only with the intended HTTPS/domain scope understood. Keep CORS origins/methods/headers explicit if cross-origin access is required. CORS is a browser response rule, not caller authentication or an authorization boundary. Browser behavior and allowed content need a deployed test, including CSP failures. [S19]

## Integration endpoints, SSRF and webhooks

The product intentionally contacts private native endpoints. A blanket prohibition on private addresses would break the design; arbitrary tenant-supplied URLs would break its trust boundary. Workers must resolve a registered endpoint identity to an approved scheme, host, port, certificate trust, site and egress path. Secret access is bound to that endpoint and operation. A request cannot substitute a new URL while retaining the old endpoint's credential.

Allow only required protocols; reject embedded user credentials, malformed addresses and metadata/loopback destinations unless an explicit infrastructure dependency requires an independently reviewed exception. Validate resolution and the connected destination, including IPv6 and DNS changes, against the approved endpoint policy. Disable redirects by default; where a native API requires them, validate each destination and never forward credentials outside its approved identity. Enforce egress at the network boundary as well as in code. Bound connection/read time, pages, response size and concurrency. [S13]

Inbound webhooks authenticate the registered producer, verify signatures over the required original bytes using the producer's documented scheme, constrain delivery age where supported and deduplicate by integration-scoped event identity and payload digest. Validate schema and scope before processing. Outbound webhooks use the same endpoint-registration and SSRF controls; retry delivery cannot trigger unrestricted rediscovery. Preserve inbox/outbox transaction rules. Do not treat possession of a callback URL or a valid CSRF exclusion as sender identity.

## Uploaded artifacts and sensitive storage

Keep uploads private and quarantined until their type, size and required inspection pass. Generate storage names; retain an original filename only as escaped metadata. Validate allowed extensions and actual media/content independently, without trusting the client content type. Prevent traversal, overwrite, executable serving and archive expansion beyond bounded member count, depth and total size. Reject or safely transform active content according to the accepted artifact type. Do not feed a quarantined artifact to an execution or conversion worker. [S15]

Authorize inspection and download separately from upload. Scan using the approved isolated inspection process and record the artifact digest, inspection revision and outcome. The absence of malware detections does not qualify a guest image or make a conversion parser trusted. Apply the hostile-image isolation already required by T08 and preserve the immutable bytes used for plan/evidence checks.

Secret values belong in the selected secret custody system, not git, job/event payloads, browser props, logs or release manifests. Use environment- and service-specific `APP_KEY` material; stable protected replicas of one service share the key needed for their encrypted data, while another service receives no copy merely for convenience. Plan key rotation together with old-data decryption and session invalidation. Do not run key generation at every container start. Environment files and configuration caches containing secrets must not be served or published. [S16, S20]

## Denial, auditing and abuse controls

Use consistent external errors: unauthenticated calls fail authentication; known in-scope forbidden actions receive the documented denial; out-of-scope object lookup uses the contract's non-disclosing response. Do not reveal whether another tenant's resource exists through body details, redirects, validation messages, totals or timing-sensitive shortcuts. An unavailable policy service is an operational failure, never an allow decision. Return a correlation ID without stack traces, SQL, credentials or private topology. Production `APP_DEBUG` is false and debug/diagnostic consoles require separate restricted access. [S04, S17]

Separate protected audit events from high-volume diagnostic logs. Record effective actor, caller, tenant/resource scope, action, decision/reason code, policy or grant revision, correlation/operation identity and time; include denials, privilege changes and break-glass use. Sanitize user-controlled log fields and bound their size. Exclude tokens, session identifiers, secret values, private keys and unredacted request bodies. Restrict audit readers and preserve retention and integrity evidence. Mandatory privileged transitions follow the existing atomic audit/outbox rule; unavailable diagnostic export alone must not be confused with loss of the authoritative audit record. [S18]

Apply per-actor, per-tenant and service-wide limits to expensive actions, export generation, uploads, login initiation and integration calls. The shared rate-limit store and key design must behave across replicas. Choose actual budgets through the operating-target process and load evidence; IP-only limits are insufficient behind enterprise proxies and for tenant fairness. Throttling reduces abuse but does not authorize access or replace capacity reservations. [S03]

## Required review and qualification evidence

| Review area | Required scenarios | Existing delivery/campaign route |
| --- | --- | --- |
| Authorization and field control | Allowed and denied role/action matrix; direct service bypass attempt; mass assignment and cross-tenant relationship IDs | P02; Q01.02–Q01.04/Q01.07 |
| Revocation and background work | Revocation denies pending commands/disclosures while committed facts retain authorized custody; repeated job; context cleanup after exception; stale cache and restored authority | P02/P06; Q01.08/Q04/Q09 |
| Browser and edge | Real login/logout/tenant change; hostile Host/forwarded headers; cross-origin state-changing request; actual CSP and cookie behavior | P01/P02; Q01.03/Q01.10/Q09 |
| APIs and integrations | SSRF through redirects/DNS and URL variants; wrong webhook signer; replay/changed payload; bounded downstream response and retry | P04/P06; Q02/Q04 |
| Files and evidence | Cross-tenant download; expired capability; hostile filename/archive; quarantined artifact use; output and log redaction | P03/P06/P07; Q01.02/Q03/Q07/Q09 |
| Resource abuse | One tenant saturates expensive routes/queues; limiter store unavailable; retained uncertainty under dependency failure | P06/P10; Q04/Q10 |

Use the same two-tenant fixture across HTTP, queue, cache, file, search and notification paths. Inspect side effects and protected state independently of HTTP status. Test Laravel's actual request-forgery middleware outside its ordinary test bypass: the framework disables CSRF middleware during tests, so ordinary feature tests alone do not establish deployed CSRF behavior. Record the middleware/configuration under test, not just a test name. [S12]

An exception identifies the control and threat, exact affected scope, reason, compensating control, accountable reviewer, expiry and required requalification. No undocumented bypass may become a convenience option in production. Changes to identity, tenancy, raw queries, serialization, middleware, worker lifetime, endpoint handling or storage URLs trigger affected negative tests and a threat-model review.

## Primary references

Reviewed 2026-10-04. Framework references target Laravel 13; OWASP references are maintained guidance. The product-specific tenant, grant, native-effect and delivery rules above are this repository's application of those sources, not claims made by Laravel or OWASP.

- **S01:** [OWASP ASVS 5.0.0 and versioned requirement references](https://owasp.org/www-project-application-security-verification-standard/).
- **S02:** [OWASP Developer Guide — ASVS level selection](https://devguide.owasp.org/en/08-culture-process/04-asvs/); use the selected 5.0.0 release for actual requirement IDs.
- **S03:** [OWASP API Security Top 10 — 2023](https://owasp.org/API-Security/editions/2023/en/0x11-t10/).
- **S04:** [Laravel 13 authorization](https://laravel.com/docs/13.x/authorization).
- **S05:** [Laravel 13 authentication and session lifecycle](https://laravel.com/docs/13.x/authentication).
- **S06:** [Laravel 13 Sanctum — first-party UI initiated requests](https://laravel.com/docs/13.x/sanctum#first-party-ui-initiated-requests).
- **S07:** [Laravel 13 routing — scoped bindings](https://laravel.com/docs/13.x/routing#custom-keys-and-scoping).
- **S08:** [OWASP Multi-Tenant Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Multi_Tenant_Security_Cheat_Sheet.html).
- **S09:** [Laravel 13 validation — nested arrays, database checks and safe unique exclusions](https://laravel.com/docs/13.x/validation).
- **S10:** [OWASP Laravel Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Laravel_Cheat_Sheet.html).
- **S11:** [Laravel 13 requests — trusted proxies and hosts](https://laravel.com/docs/13.x/requests).
- **S12:** [Laravel 13 request-forgery protection](https://laravel.com/docs/13.x/csrf).
- **S13:** [OWASP SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html).
- **S14:** [Laravel 13 file storage — temporary URLs](https://laravel.com/docs/13.x/filesystem#temporary-urls).
- **S15:** [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html).
- **S16:** [Laravel 13 encryption and key rotation](https://laravel.com/docs/13.x/encryption).
- **S17:** [Laravel 13 deployment — debug mode](https://laravel.com/docs/13.x/deployment#debug-mode).
- **S18:** [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html).
- **S19:** [OWASP HTTP Headers Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html).
- **S20:** [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html).
- **S21:** [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html).
- **S22:** [OpenID Connect Core 1.0 — ID token validation](https://openid.net/specs/openid-connect-core-1_0.html#IDTokenValidation).
