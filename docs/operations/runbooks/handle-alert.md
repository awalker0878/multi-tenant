# Handle an operational alert

Use this procedure to receive, assess, contain and close alerts from the product's services, dependencies, workers and evidence controls. [Observability](../observability.md) defines signal ownership and reviewed alert conditions; [support](../support.md) defines escalation and incident responsibility. An alert's severity does not grant native execution or recovery authority.

## Ownership and inputs

The receiving on-call engineer acknowledges and triages the alert. The service owner diagnoses the affected component; lifecycle and native owners handle uncertain effects, IAM/security handles trust or isolation failures, and assurance handles evidence or qualification failures. An incident commander coordinates multi-service or significant tenant impact.

Gather the alert ID, rule revision, environment, first/last observation times, affected tenant/site/job/operation references, signal freshness, correlation identifiers, current release/configuration and recently approved changes. Retrieve only records permitted to the investigator; do not broaden tenant access to simplify diagnosis.

Use release-specific diagnostic interfaces and deployment tooling whose access is already approved. The application has no assumed operational CLI in this document. Record which interface supplied each observation and redact credentials, payload contents and sensitive endpoint details.

## Prerequisites

- Confirm access to the incident record, named escalation paths, protected telemetry and the relevant service owner.
- Confirm the alert source and environment are authentic, including whether the alert belongs to a rehearsal or live operation.
- Read the rule's accepted threshold, measurement window, missing-data behavior and routing policy; do not substitute guessed SLOs.
- Identify the scope and expiry of any administrative or break-glass access, with the required audit/review ownership.
- Before changing execution state, obtain current job/operation, native writer and recovery-boundary information.

## Receive and assess

1. Acknowledge the alert in its authoritative incident system and record who is responsible for the next action. An acknowledgement means ownership, not resolution.
2. Check whether duplicate alerts share an incident, operation or dependency. Link them while retaining distinct tenant impact and independent failure evidence.
3. Compare event time, ingestion time and current telemetry health. If observations are stale or missing, classify the visibility gap explicitly rather than concluding the service recovered.
4. Establish impact from authorized user journeys, independent probes and owning-service state. Distinguish unavailable presentation, unavailable authority, delayed execution, uncertain native outcome and possible data/security harm.
5. Assign priority using the accepted support model, affected scope and ability to contain effects. Escalate a suspected isolation, integrity or uncontrolled-write problem immediately through its named security/native owners.
6. Record a next-update time under the applicable support agreement. Use the actual accepted response objective; an example or proposed SLO is not an operational commitment.

Expected observation: a named owner has acknowledged a verified alert, impact and uncertainty are recorded, and affected tenants/jobs are bounded as far as current evidence permits.

## Diagnose the signal

| Signal family | Read-only checks | First safe response |
| --- | --- | --- |
| Authorization, trust or clock failure | Issuer/audience/time validity, current decisions, dependency health and denial reasons | Hold new privilege-dependent work; involve IAM/security without widening grants |
| Stuck job or queue backlog | Workflow history, worker compatibility, queue age, native-operation journal and pool reachability | Determine whether progress is waiting, safely held or outcome-unknown before changing workers |
| Unknown native outcome or fencing conflict | Native request IDs, independent platform readback, current ownership and old-worker reachability | Preserve resource holds and reconcile; do not replay effects |
| Discovery staleness or incomplete inventory | Generation completeness, endpoint authorization, pagination and observed capture times | Mark dependent assessment/admission inputs unusable until trustworthy observations return |
| Evidence backlog, digest failure or qualification expiry | Staging/finalization records, bytes/digests, provenance, current decision validity | Hold dependent completion or admission; preserve artifacts for assurance review |
| Persistence, broker or workflow-engine failure | Dependency health, saturation, recovery points, replay watermarks and operation state | Bound admission and backpressure; involve owning operators before repair or restoration |
| Application/policy/service failure | Intended exposure, observed traffic, source/target writers, mandatory service receipts and guest checks | Contain unsafe exposure and protect data under the approved application recovery decision |

7. Correlate the affected job and operation across the console, owning service, workflow history, worker and native observer. Record disagreement between sources instead of choosing the most reassuring status.
8. Compare the onset with deployment, configuration, credential, profile and native-platform changes. Correlation is a lead; require observations before attributing cause.
9. Check available capacity, dependency budgets and retry behavior. Avoid aggressive polling or unbounded retries that increase saturation or hide the original failure.
10. Preserve relevant redacted logs, metrics, traces, audit and native receipts before retention or recovery actions remove them.

Expected observation: the record identifies confirmed facts, remaining hypotheses, affected execution boundaries and the next bounded diagnostic action.

## Contain and recover

11. Choose the narrowest effective containment scope that covers the observed risk: affected admission, resource hold, worker pool, endpoint path or exposed application route. Record the owner and justification.
12. If old workers might still write, have IAM and native owners revoke or isolate their effective native authority and independently verify denial. Disabling polling or waiting for lease expiry does not establish containment.
13. Continue observing already accepted native operations after a cancellation or revocation. A cancellation request does not prove an effect stopped or reversed.
14. Request bounded reconciliation for ambiguous outcomes through the authorized behavior in [lifecycle](../../services/lifecycle.md). Retain holds until independent facts establish the result and permitted next action.
15. For a release regression, follow [rollback deployment](rollback-deployment.md) only after checking schema, workflow-history and evidence compatibility. Restore damaged state through [recovery](recovery.md) and [restore control plane](restore-control-plane.md).
16. For application data divergence after target writes, preserve the target data and source fencing. Obtain an approved data-return or forward-recovery plan from the application and lifecycle owners before changing writers.
17. Apply the approved remediation through its owning service or operational procedure. Record action, authority, expected observation, bounded waiting interval and the point at which escalation replaces further attempts.
18. If alert suppression is needed for coordinated maintenance, use the reviewed scope and expiry and retain incident ownership. Suppression changes notification only; it does not resolve the condition or relax admission controls.

Expected observation: containment prevents additional unsafe effects, recovery follows an authorized path, and any uncertainty remains visible as a hold rather than disappearing through a forced success state.

## Verify and close

19. Observe recovery through at least the rule's accepted evaluation window and service-specific acceptance checks. Verify fresh telemetry, not merely absence of notifications.
20. Confirm affected user journeys, dependency health and independent native/application postconditions. Exercise a relevant denied path when authority or tenant isolation was involved.
21. Check that queues, evidence backlogs and outbox/inbox processing have recovered without duplicate effects or prematurely released allocations. Retain explicit exceptions for unresolved work.
22. Confirm alert delivery and acknowledgement still function after changes to telemetry, routing or credentials. Remove only incident-specific temporary suppression and excess access when safe.
23. The incident owner records resolution or a clearly bounded transfer of ownership, remaining restrictions and the next review. Receiving operations accepts the handover; a green dashboard alone is not closure.

## Stop conditions and evidence

Stop mutation-based remediation when ownership is unclear, native outcome is unknown, required authority is unavailable, evidence integrity fails or the effect crosses an unapproved data-recovery boundary. Preserve diagnostics and escalate; repeated worker restart is not a substitute for reconciliation.

The evidence record includes rule/version, timestamps, delivery and acknowledgement, impact, diagnostic sources, approved actions, containment proof, independent postconditions and closure acceptance. Record actual time to detect, acknowledge, contain and recover against the accepted objectives, plus gaps in signal coverage.

Link the incident or rehearsal to R15/R16/R24/R29/R30/R31 and applicable Q04/Q09/Q10 cases in [requirements and qualification](../../implementation/requirements-and-qualification.md). Update the owned rule, procedure or contract when a verified gap changes future behavior.
