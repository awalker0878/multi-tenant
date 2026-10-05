# G02 engineering assessment — 2026-10-05

Recorded by Codex for implementation handoff. **G02 remains NOT_REVIEWED**;
this is not an independent receiving decision. P02.01–P02.05 work and verification
remain IN_PROGRESS. G01 receiving inputs still apply.

The [delivery register](../../implementation/delivery-register.yaml) owns evidence
and state. EV-P02-001 retains local bootstrap. EV-P02-002 retains the signed-token
OIDC adapter regression. EV-P02-003 retains the current 44-check campaign,
55 PostgreSQL feature tests (952 assertions), two real compiled browser journeys,
four HTTPS/PKCE exchanges, six artifact hashes and 218 exact source bindings at
`6fd44860f61d66bf858c92b8099f29a97479758b`. Its provider and immutable plans are
explicitly synthetic. Positive and negative observations are bounded to the
implemented Governance/Console surfaces.

| Criterion | Observed implementation/evidence | Remaining qualification or implementation |
| --- | --- | --- |
| G02.01 — identity and tenant boundaries | Forced password change; Console-only OIDC settings/test/activation; current federated sessions; explicit membership/role/grant scopes; two-tenant API and browser denials; real CSRF and workload separation. | Full user/service caller and projection/search/export/evidence matrix as owners expose those surfaces; service actor delegation; complete published HTTP wire conformance across language clients; supported deployment identity topology. |
| G02.02 — immutable approval binding | Exact synthetic plan ID/revision/digest/action/scope/actors/validity; independent reviewer; named executor; rejection, revocation, expiry and loss/regrant of authority. | Integrate the real P05.04 plan producer; owning-service/native pre-effect admission; approved exceptional-access policy and implementation. No observation JSON is a native permit. |
| G02.03 — failure/revocation boundaries | Wrong claims/signature/replay/proof/session/revision denied; failed provider test preserves setup; verified handover retires local password/sessions; changed/revoked membership or grants prevent new decisions. | Real provider/DNS/key rotation and issuer-loss interoperability; deployed bootstrap/retry/restore/authority-epoch reconciliation; service credential rotation/delegation; approved provider revocation/recovery extensions. |
| G02.04 — durable history and browser journey | Real PostgreSQL; command receipts and audit/outbox transaction rollback; distinct tenant histories; compiled tenant navigation, quota persistence and cross-browser revoked access; keyboard-operated setup controls and page/error focus. | Governance outbox delivery and background expiry; restart/restore/replay qualification of approval history; complete multi-tab/late-response and assistive-technology campaign, supported browser floor and actual support ownership. |

## Next executable increments and owners

1. Governance: define explicit immutable event schemas for tenant/membership/grant/
   quota/approval changes, implement the publisher and background expiry, then
   measure duplicate delivery, recovery and retained history without granting
   authority from events. Existing direct decisions remain uncached.
2. IAM/security and owning services: settle and implement service actor delegation,
   audience/scope/revocation constraints and pre-effect admission. Define an explicit
   support/break-glass approval, expiry and audit policy; current unknown/support
   actions remain denied.
3. SRE/IAM: bind deployment and restore to approved secret/key custody and
   revocation reconciliation using actual operating inputs; test no resurrection.
4. Console/quality: complete controlled late-response/multi-tab and assistive-
   technology cases. Current lists have explicit 200-row bounds (audit 100);
   pagination is not yet implemented.
5. Independent IAM/security, Governance, quality/product and SRE reviewers: review
   every G02 criterion with its measured boundary and record the receiving decision.

The [correction history](../../../verification/p02/corrections.md) retains the
failed timing run and the rejected published-contract edit. The edit was restored
to its original bytes; no policy exclusion changed. Hosted regression outcomes
and source identities must be inspected separately; a successful development
campaign does not supply actual operating identities, promotion approval or native
qualification.
