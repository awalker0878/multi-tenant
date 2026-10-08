# Identity and trust

Owners: IAM/security for trust and grants; service owners for enforcement; SRE for deployment and recovery. Scope: R02–R04/R14/R16/R29/R31/R32 and ADR-009/010/011/020 in the [decision register](../decisions/decision-register.md). The [governance specification](../services/governance.md) owns application authorization semantics.

## Principals and authority

| Principal | Required identity and scope | Authority excluded by default |
| --- | --- | --- |
| Bootstrap administrator | One deployment-created local identity with password hash, required first-login change and retirement at verified OIDC activation | Automatic tenant-wide authority, service impersonation or reuse after federation activation |
| Human user | External OIDC issuer/subject identity configured through the console; current tenant membership and resource/action grants | Native credentials, another tenant's data or automatic approval rights |
| Console | Audience-specific service identity plus validated human delegation | Trusting a browser-supplied tenant/actor field as proof |
| Domain service | Unique environment/context identity; receiver-specific audience; owned persistence role | Private tables of another context or unlimited impersonation |
| Discovery worker | Enrolled site/pool identity and scoped read credential | Native create/update/delete or automatic management ownership |
| Infrastructure/guest/service/data worker | Distinct pool identity; job-bound action/resource authority and limited native secret grant | Other pools' networks/secrets or permission derived only from task routing |
| Deployment migrator | Attributable change identity with bounded schema administration | Routine runtime use or direct domain-record editing |
| Evidence producer/reviewer | Campaign/job-bound producer or independently assigned review scope | Producer self-qualification or unrestricted object-store administration |
| Support administrator | Approved time-bounded administrative scope with accountability | Inherited tenant approval or silent break-glass authority |

Environment separation applies to issuers/audiences, identities, credentials, data stores, worker registrations and signing policies. An integration token must not authenticate to production even when both use the same identity product.

The [security and tenant isolation engineering standard](../engineering/security-and-tenancy.md) governs Laravel guards/policies, request context and non-HTTP enforcement. Guards establish identity; policies evaluate action and resource scope. A global administrator policy hook must not skip tenant or separation-of-duties checks. First-party session authentication and machine delegation are different trust paths and must have separate acceptance cases.

## Trust establishment

1. SRE and IAM record environment/workload trust roots, service audiences, PKI chains, discovery endpoints, time source and recovery owners in controlled deployment configuration. External user OIDC settings are configured later through the console and stored by Governance. Validate endpoint ownership independently of values presented by a new worker.
2. Establish workload identities through the selected runtime/PKI mechanism. Bind them to expected environment, context, workload and purpose; record expiry and revocation behavior.
3. Run the controlled deployment bootstrap once: create the installation-local administrator, generate and display its random temporary password to the authorized installer, and persist only its hash with mandatory-change state. Require a password change at first login, then configure and verify OIDC through the console using the lifecycle below.
4. Enroll each site worker against an independently verified site/endpoint record. Assign only its required pool, task scopes, egress destinations and secret references. A registration handshake gives no native write authority.
5. Exercise allowed and denied calls: wrong audience/issuer, expired identity, unknown worker, wrong tenant, excessive delegation, private-database access and unexpected endpoint trust.

Required workload trust, secret/key access and infrastructure configuration are installation inputs. External OIDC provider configuration is application data entered through the console; its absence leaves the installation in local setup mode, not in a failed-deployment state. Record an activated connection revision and actual product/interface metadata in the [configuration and BOM](configuration-and-bom.md); do not copy its credentials into deployment values. The design selects no external identity vendor.

For browser access, deployment configuration records accepted hosts, ingress proxy/header trust and session-cookie security. The console-managed OIDC connection records provider/client settings, approved callback/redirect destinations and claim mappings. Session lifetime, logout/revocation and reauthentication follow the reviewed identity policy. Verify the actual Laravel 13 request-forgery middleware and browser flow through the deployed ingress. Do not infer these controls from framework feature tests that bypass CSRF or from a successful identity-provider login.

## Local administrator and OIDC lifecycle

[ADR-009](../decisions/adr-009-identity-delegation-and-authorization.md) defines the accepted bootstrap design. Governance owns the account, hash, setup state, identity connection and grants; Console owns the UI and server session.

| State | Permitted behaviour | Transition |
| --- | --- | --- |
| Fresh installation | Authorized deployment operation creates exactly one local administrator and displays its random temporary password once | Persist hash and mandatory-change state atomically; no shared default credential |
| Password change required | Successful local login can access only password change and logout; direct protected API calls are denied | Choose a different password; invalidate the temporary credential and rotate session/CSRF state |
| Local administration | Changed-password administrator uses scoped console functions and creates/tests the OIDC connection | Verify a federated identity with an explicit administrative grant; failed tests preserve local setup |
| OIDC active | Federated login and ordinary governed authorization | Activation disables the local account and revokes local sessions/delegation; provider loss does not reactivate it |

Display the account name, temporary password and console URL only to the authenticated installation operator through the deployment presentation channel. Prevent that output from entering retained/shared CI or deployment logs, pod/application logs, telemetry, artifacts or evidence. Store only the password hash; audit creation/change/retirement without credential values. The installer must use a release-specific protected display binding, including for automated deployment.

Bootstrap is idempotent and persists across replicas, retries, restarts and upgrades. None of those events regenerate or redisplay a password, clear mandatory-change state or resurrect a retired account. If delivery is interrupted or the password is lost, the authorized operator uses the release's explicit authenticated recovery procedure before OIDC activation; a failed login or restart cannot trigger a reset. Recovery after activation is a separately controlled operating action and never an automatic local-login fallback.

OIDC connection secrets are write-only inputs from the console to protected server-side custody. Governance stores scoped references and non-secret settings/revisions. APIs expose status and references, not secret values. Validate discovery/redirect destinations against the authorized network/trust policy; entering a URL does not authorize arbitrary server egress. Test provider login and administrative authority before the atomic activation/retirement transition.

## Request and effect validation

At each owner API, authenticate the transport/caller, validate issuer/audience/time and bind the effective actor through the reviewed delegation mechanism. Intersect service authority, actor authority, tenant membership and resource/action scope. Check revision and idempotency conditions only after authorization; guessed identifiers must not expose resource existence.

For privileged effects, lifecycle additionally validates the current exact approval/plan binding, commissioning, qualification, reservation and ownership/fencing state. The worker validates the admitted job, intended endpoint, operation scope, authority lifetime and its own audience before using a native credential. Capture the authorization decision revision/time and operation attempt; never store the credential in the journal.

Queued work carries an attributable tenant/actor/delegation reference, not a reusable browser session or an assumed authorization result. Each consumer establishes fresh scope and reloads current authority before its required action boundary. Clear identity and tenant state after every successful or failed job/request in long-lived processes. Cached authorization and protected download capabilities must have explicit expiry/revocation behavior; neither cache isolation nor a signed URL establishes current permission by itself.

A signed token proves a claim from a trusted issuer under its validation rules; it is not proof that current approval, qualification or resource ownership remains valid. Select explicit freshness and maximum-skew limits before P06/P07. If current mandatory checks cannot be performed, hold the effect under the approved safe-point policy.

## Rotation and revocation

| Action | Required procedure | Completion observation |
| --- | --- | --- |
| Routine certificate/key rotation | Inventory consumers and old in-flight work; introduce bounded overlap; distribute new trust; exercise both intended and denied paths; retire old trust | New identity works within scope; old identity fails after its deadline; no unrelated trust broadened |
| Native credential rotation | Hold affected new effects; determine in-flight native state; provision limited replacement; update secret reference revision and reconcile authority | Scoped readback succeeds; old credential denied; held jobs revalidate rather than inheriting new rights |
| Worker revocation | Stop new assignment; invalidate worker/grant/secret access; fence or isolate its native path; reconcile dispatched operations | Old worker cannot cause additional effects; native outcomes separately established |
| Emergency key compromise | Security defines affected trust/artifacts; suspend affected admission/promotion; distribute replacement roots through independent recovery channel | Compromised identity/signatures rejected and affected support/approval claims reviewed |

Revocation events accelerate holds; authoritative checks remain required when the broker is delayed. Lease expiry or marking a worker disabled does not prove a process with cached credentials stopped. The selected platform/path must demonstrate effective fencing, including partitioned workers.

## Recovery, audit and acceptance

Recover identity/key services before their dependent encrypted data and signatures. Keep restore credentials separate from runtime credentials and protect recovery quorum/access material according to the selected custody policy. Test recovery when the primary identity or secret service is unavailable; an undocumented administrator password fallback is not an acceptable dependency.

Restore governance and trust state in quarantine. Preserve password-change completion and OIDC activation/local-account retirement; reconcile with independent current records so a stale backup cannot re-enable a temporary password or retired local administrator. Reconcile revocations and changes after the recovery point against independent audit/identity records; if current authority cannot be established, reissue reviewed grants rather than resurrecting historical ones. Use the [recovery procedure](runbooks/recovery.md) before resuming mutation.

Audit who requested, authenticated, delegated, authorized and performed each privileged action, including denial, bootstrap, rotation and support elevation. Preserve tenant/resource scope, immutable references, timestamps and correlation identifiers. Redact bearer tokens, private keys, connection strings and guest secrets.

Acceptance evidence includes allow/deny matrices, cross-environment denial, revocation latency and old-worker containment, rotation with in-flight work, lost-key/identity recovery and attributable break-glass review. Link exact artifact/configuration revisions and limitations; role names in this document do not appoint people or confer access.
