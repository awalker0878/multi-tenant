# Illustrative contract exchanges

Status: proposed examples for schema review, not live endpoints or locked API definitions. IDs, times, qualification references and digests are synthetic. Repeated hexadecimal values are fixture placeholders, not hashes computed from these documents. All execution shown here is explicitly `simulation`; no native capability or authorization is asserted.

These exchanges use the application in the [walkthrough](../product/application-walkthrough.md). Each HTTP request targets its owning service origin. Authentication headers are omitted: actual requests require trusted service identity and delegated actor scope; no example token is a reusable credential. Correlation `corr_demo_01` ties the journey together, while each command has its own retry key.

## 1. Conditional catalogue revision

Fixture prerequisites: governance tenant `t_demo`; authorized author/reviewer/operator identities; catalogue application `app_permit`, deployment `dep_permit_lab`, environment `env_lab`, WSDs `wsd_portal`/`wsd_data`, domains `sd_oz`/`sd_rz`. The application has current revision `ir_prov_00` and application ETag `"app_permit:1"`.

The author submits complete intent for this deployment. This body demonstrates placement, dependency and service semantics; ADR-013/P01.03 must finalize the complete required field set and vocabulary before implementation.

```http
POST /v1/tenants/t_demo/applications/app_permit/intent-revisions
Content-Type: application/json
If-Match: "app_permit:1"
Idempotency-Key: demo-revise-permit-01
X-Correlation-ID: corr_demo_01

{
  "schema_version": 1,
  "parent_revision_id": "ir_prov_00",
  "deployment_id": "dep_permit_lab",
  "environment_id": "env_lab",
  "workloads": [{"id": "wl_web", "role": "web"}, {"id": "wl_db", "role": "database"}],
  "placements": [
    {
      "workload_id": "wl_web",
      "wsd_id": "wsd_portal",
      "security_domain_id": "sd_oz",
      "guest_profile_ref": "linux_fixture:1",
      "compute": {"vcpus": 2, "memory_mib": 4096},
      "datasets": []
    },
    {
      "workload_id": "wl_db",
      "wsd_id": "wsd_data",
      "security_domain_id": "sd_rz",
      "guest_profile_ref": "linux_fixture:1",
      "compute": {"vcpus": 4, "memory_mib": 8192},
      "datasets": [{"id": "ds_permits", "capacity_gib": 100,
        "consistency_group": "cg_permits", "encryption_required": true}]
    }
  ],
  "startup_dependencies": [{"workload_id": "wl_web", "requires": "wl_db"}],
  "required_flows": [{"source_workload_id": "wl_web", "target_workload_id": "wl_db",
    "protocol": "tcp", "destination_port": 5432, "stateful_reply": true,
    "interface_policy_ref": "zip_oz_rz_fixture:1"}],
  "required_services": ["dns", "identity", "time", "monitoring", "logging", "backup"],
  "acceptance_checks": ["web_health", "database_integrity", "policy_denials", "backup_restore"],
  "recovery_policy_ref": "recovery_permits_fixture:1"
}
```

```http
HTTP/1.1 201 Created
Location: /v1/tenants/t_demo/applications/app_permit/intent-revisions/ir_prov_01
ETag: "app_permit:2"
Content-Type: application/json

{
  "application_id": "app_permit",
  "deployment_id": "dep_permit_lab",
  "intent_revision_id": "ir_prov_01",
  "parent_revision_id": "ir_prov_00",
  "intent_digest": "sha256:1111111111111111111111111111111111111111111111111111111111111111",
  "schema_version": 1,
  "correlation_id": "corr_demo_01"
}
```

Repeating the identical accepted command/key returns this original receipt, after current caller access is checked. It does not fail merely because the application now has ETag `"app_permit:2"`. A *new* command with the old ETag receives `412`; a changed payload under the old key receives `409`. The server atomically persists revision, deployment pointer, receipt and outbox.

## 2. Asynchronous assessment

Planning accepts pinned input references and a requested comparison scope. The example's simulation inputs cannot qualify a native endpoint.

```http
POST /v1/tenants/t_demo/assessments
Content-Type: application/json
Idempotency-Key: demo-assess-permit-01
X-Correlation-ID: corr_demo_01

{
  "application_id": "app_permit",
  "intent_revision_id": "ir_prov_01",
  "intent_digest": "sha256:1111111111111111111111111111111111111111111111111111111111111111",
  "mode": "simulation",
  "operation": "provision",
  "candidate_ids": ["site_openstack_fixture"],
  "observation_generation_ids": ["obs_openstack_fixture_01"],
  "profile_version_refs": ["openstack_fixture:1"],
  "policy_version_ref": "policy_permits_fixture:1"
}
```

```http
HTTP/1.1 202 Accepted
Location: /v1/tenants/t_demo/assessment-jobs/assessment_job_01
Content-Type: application/json

{
  "assessment_id": "as_sim_01",
  "task": {"type": "assessment", "id": "assessment_job_01", "state": "queued"},
  "status_url": "/v1/tenants/t_demo/assessment-jobs/assessment_job_01",
  "result_url": "/v1/tenants/t_demo/assessments/as_sim_01",
  "correlation_id": "corr_demo_01"
}
```

The authorized task read eventually exposes its result reference. An illustrative completed assessment contains:

```json
{
  "id": "as_sim_01",
  "state": "completed",
  "mode": "simulation",
  "intent_revision_id": "ir_prov_01",
  "candidates": [{
    "id": "site_openstack_fixture",
    "assessment": "eligible",
    "eligible_scope": "simulation_only",
    "native_qualification": "not_established",
    "findings": [{"requirement_id": "R20", "result": "simulated_pass",
      "evidence_ref": "fixture_policy_case_01"}]
  }]
}
```

An assessment task has no native effect authority and is not a lifecycle job. Native eligibility would require current exact-tuple evidence, commissioned site facts and the other mandatory inputs; this fixture cannot supply them.

## 3. Immutable plan and exact-digest approval

`POST /v1/tenants/t_demo/plans` compiles the completed assessment, selected candidate and explicit requested operation into a new immutable plan. A minimal command shape is:

```json
{
  "assessment_id": "as_sim_01",
  "selected_candidate_id": "site_openstack_fixture",
  "operation": "provision",
  "mode": "simulation"
}
```

After asynchronous compilation, `GET /plans/plan_sim_01` returns executable content and its digest. The full plan must contain all bindings in the [planning specification](../services/planning.md); this approval example only shows the fields necessary to illustrate exact binding.

```http
POST /v1/tenants/t_demo/approvals
Content-Type: application/json
Idempotency-Key: demo-approve-permit-01
X-Correlation-ID: corr_demo_01

{
  "plan_id": "plan_sim_01",
  "plan_digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "action": "provision",
  "mode": "simulation",
  "scope": {
    "application_id": "app_permit",
    "deployment_id": "dep_permit_lab",
    "site_ids": ["site_openstack_fixture"],
    "workload_ids": ["wl_web", "wl_db"]
  },
  "expires_at": "2030-01-01T02:00:00Z",
  "conditions": {"change_window_ref": "window_fixture_01"},
  "reason": "Review of the synthetic provisioning fixture"
}
```

```http
HTTP/1.1 201 Created
Location: /v1/tenants/t_demo/approvals/ap_sim_01
Content-Type: application/json

{
  "id": "ap_sim_01",
  "plan_id": "plan_sim_01",
  "plan_digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "approver_subject_id": "reviewer_fixture",
  "authorization_policy_version": "approval_policy_fixture:1",
  "mode": "simulation",
  "disposition": "effective",
  "expires_at": "2030-01-01T02:00:00Z"
}
```

The fixture clock is before expiry. Governance derives `approver_subject_id` from authenticated identity, fetches the exact plan and checks independent authority, scope and conditions. No actor field in the request can assign the approver. A changed digest, scope or mode requires a fresh decision; this approval cannot authorize native execution or source retirement.

## 4. Job admission, duplicate and conflict

```http
POST /v1/tenants/t_demo/jobs
Content-Type: application/json
Idempotency-Key: demo-admit-permit-01
X-Correlation-ID: corr_demo_01

{
  "plan_id": "plan_sim_01",
  "plan_digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "approval_id": "ap_sim_01",
  "action": "provision",
  "mode": "simulation",
  "scope": {"application_id": "app_permit", "deployment_id": "dep_permit_lab"}
}
```

The admission scope identifies the deployment and must exactly resolve to the plan's approved effect scope; it cannot add unlisted resources. Lifecycle rechecks current authority and mandatory inputs before acceptance.

```http
HTTP/1.1 202 Accepted
Location: /v1/tenants/t_demo/jobs/job_sim_01
Content-Type: application/json

{
  "job_id": "job_sim_01",
  "admission_id": "adm_sim_01",
  "state_at_acceptance": "accepted",
  "mode": "simulation",
  "plan_id": "plan_sim_01",
  "status_url": "/v1/tenants/t_demo/jobs/job_sim_01",
  "correlation_id": "corr_demo_01"
}
```

An identical retry returns the same `job_sim_01`/`adm_sim_01` receipt and status link. `state_at_acceptance` is historical receipt data; `GET` supplies current progress. Lifecycle commits one durable job/dispatch record, and its dispatcher starts/reconciles one stable Temporal workflow identity. A replay cannot create new execution authority for that existing job.

If the caller changes the plan digest while reusing `demo-admit-permit-01`, return:

```http
HTTP/1.1 409 Conflict
Content-Type: application/problem+json

{
  "type": "urn:portable-hosting:problem:idempotency-key-reused",
  "title": "Command key is already bound to another payload",
  "status": 409,
  "code": "IDEMPOTENCY_PAYLOAD_MISMATCH",
  "detail": "Use the existing job status to inspect the accepted command. A changed plan requires review and a new command.",
  "retryable": false,
  "correlation_id": "corr_demo_01"
}
```

A new key is not a conflict override. Another job for the same owned resources may still fail admission with `RESOURCE_SCOPE_HELD` and an authorized explanation; the original uncertain effect must be reconciled first.

## 5. Outcome unknown is a held job

Suppose a simulated native endpoint accepts an operation but its response is lost. An authorized job read remains `200`; the uncertainty belongs to the recorded operation, not to the HTTP read.

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "job_id": "job_sim_01",
  "mode": "simulation",
  "state": "held",
  "projection_observed_at": "2030-01-01T00:10:00Z",
  "hold": {"code": "NATIVE_OUTCOME_UNKNOWN", "operation_id": "op_create_db_01"},
  "operation": {
    "id": "op_create_db_01",
    "outcome": "outcome_unknown",
    "attempt_id": "attempt_01",
    "native_request_ref": "request_fixture_01",
    "resource_hold": "retained",
    "reconciliation_state": "readback_pending"
  },
  "allowed_actions": ["request_reconciliation", "request_cancellation"],
  "message": "The recorded effect needs observation before execution can continue."
}
```

`request_reconciliation` authorizes the defined bounded readback path, not blind repetition of the write. A cancellation request waits for a safe point and does not claim the already dispatched effect was undone. The fixture exercises the same state rules later required by native Q04 campaigns.

## 6. Event envelope and consumer behavior

The catalogue transaction writes this event to its outbox with the revision. Authentication occurs on transport and consumer identity; the JSON itself is not an access token.

```json
{
  "event_id": "evt_intent_01",
  "type": "catalogue.intent-revision.created",
  "schema_version": 1,
  "occurred_at": "2030-01-01T00:01:00Z",
  "producer": {"service": "catalogue", "artifact_ref": "catalogue_fixture_build_01"},
  "tenant_id": "t_demo",
  "aggregate": {"type": "application", "id": "app_permit", "version": 2},
  "correlation_id": "corr_demo_01",
  "causation_id": "cmd_revise_permit_01",
  "payload": {
    "deployment_id": "dep_permit_lab",
    "intent_revision_id": "ir_prov_01",
    "parent_revision_id": "ir_prov_00",
    "intent_digest": "sha256:1111111111111111111111111111111111111111111111111111111111111111"
  }
}
```

A consumer commits its event-ID inbox record and local projection change together. Duplicate delivery is a no-op. An aggregate-version gap triggers the defined source refresh/replay path; an older event cannot overwrite newer state. A planning consumer may flag a projection for reassessment, but it cannot replace a reviewed plan or grant a native job.

## 7. Stale edit and unavailable authority

```json
{
  "type": "urn:portable-hosting:problem:revision-precondition-failed",
  "title": "Application changed after it was read",
  "status": 412,
  "code": "REVISION_PRECONDITION_FAILED",
  "detail": "Reload the authorized application and compare changes before submitting a new revision.",
  "retryable": false,
  "correlation_id": "corr_demo_01"
}
```

A pre-admission governance outage returns `503` with `AUTHORITY_UNAVAILABLE`, `retryable: true` and safe retry guidance. It creates no accepted job receipt. If the caller lost the response and acceptance is uncertain, it uses its original idempotency key/status reference; it does not mint a second key to guess whether the first request worked. Direct access to another tenant follows the consistent non-disclosing `403`/`404` policy.

## Review cases before schema lock

P01.03 must convert these examples into golden fixtures and tests: accepted retry after ETag change, concurrent first submissions, key/payload mismatch, header/body tenant disagreement, cross-tenant references, unknown enum/schema version, numeric canonicalization, digest binding, async task/job distinction and event duplicate/gap handling. P03/P05/P06 extend them with actual implementations. No example here constitutes test evidence.
