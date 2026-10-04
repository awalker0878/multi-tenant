# Identity and trust

Owners: IAM/security for trust and grants; service owners for enforcement; SRE for deployment and recovery. Scope: R02–R04/R14/R16/R29/R31/R32 and ADR-009/010/011/020 in the [decision register](../decisions/decision-register.md). The [governance specification](../services/governance.md) owns application authorization semantics.

## Principals and authority

| Principal | Required identity and scope | Authority excluded by default |
| --- | --- | --- |
| Human user | Enterprise issuer/subject identity; current tenant membership and resource/action grants | Native credentials, another tenant's data or automatic approval rights |
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

1. SRE and IAM record the environment, trust roots, accepted issuers/audiences, PKI chains, discovery endpoints, time source and recovery owners in controlled configuration. Validate endpoint ownership independently of values presented by a new worker.
2. Establish workload identities through the selected runtime/PKI mechanism. Bind them to expected environment, context, workload and purpose; record expiry and revocation behavior.
3. Bootstrap the first human administrative grant using an explicitly verified identity and controlled one-time operation. Audit the grant and disable or restrict further bootstrap entry.
4. Enroll each site worker against an independently verified site/endpoint record. Assign only its required pool, task scopes, egress destinations and secret references. A registration handshake gives no native write authority.
5. Exercise allowed and denied calls: wrong audience/issuer, expired identity, unknown worker, wrong tenant, excessive delegation, private-database access and unexpected endpoint trust.

Accepted configuration is an input to the installation; the procedure must stop if required trust/identity configuration is absent. Record actual products and supported authentication mechanisms in the [configuration and BOM](configuration-and-bom.md); this document selects no identity vendor.

For browser access, that configuration also records accepted hosts, ingress proxy/header trust, enterprise callback/redirect destinations, session-cookie domain and security attributes, session lifetime, logout/revocation behavior and any reauthentication requirement. Verify the actual Laravel 13 request-forgery middleware and browser flow through the deployed ingress. Do not infer these controls from framework feature tests that bypass CSRF or from a successful identity-provider login.

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

Restore governance and trust state in quarantine. Reconcile revocations and changes after the recovery point against independent audit/identity records; if current authority cannot be established, reissue reviewed grants rather than resurrecting historical ones. Use the [recovery procedure](runbooks/recovery.md) before resuming mutation.

Audit who requested, authenticated, delegated, authorized and performed each privileged action, including denial, bootstrap, rotation and support elevation. Preserve tenant/resource scope, immutable references, timestamps and correlation identifiers. Redact bearer tokens, private keys, connection strings and guest secrets.

Acceptance evidence includes allow/deny matrices, cross-environment denial, revocation latency and old-worker containment, rotation with in-flight work, lost-key/identity recovery and attributable break-glass review. Link exact artifact/configuration revisions and limitations; role names in this document do not appoint people or confer access.
