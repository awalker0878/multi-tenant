# P10 engineering observations

Source: `eb8805ff74fa780b6ab0ba021322253c62a7d37f`.
[Hosted run 37700591172](https://github.com/awalker0878/multi-tenant/actions/runs/37700591172)
passes all nine campaign commands. The full Planning/Lifecycle/worker conformance
runner rejects skipped database cases. Local qualification-tool tests, published
native contracts, both compiler/resolver compositions, real Cosign controls and
foundation regressions also pass.

The original decoded job log and GitHub artifact metadata are retained alongside
`observations.json`. The original ZIP remains in GitHub artifact `11517127973`,
with expiry 2027-01-05 and GitHub-reported SHA-256
`c6f719fb66981a5f918787c49686e7cbad49c99d2378be38e4f5a64e137e0a54`.
The signed download returned HTTP 403 in this workspace; the archive was not
independently downloaded or rehashed. The index states that limitation explicitly.

The actual synthetic scheduler workload completes 48 operations across twelve
tenants with eight dispatchers and a four-slot shared endpoint. Every tenant
completes four operations; Jain fairness is 1.0. Boundary-through-reconciliation
p95 is 18.6622 ms; total workload time is 3.394591451 seconds. These are observations
of a small disposable integration workload, not native throughput or a promised SLO.

Actual PostgreSQL dump/restore of the Lifecycle database rejects the restored old
grant after its synthetic independent custody owner advances. One synthetic effect
remains accepted; it is not repeated. Restore-and-denial time is 285.988129 ms;
this does not measure full control-plane RTO.

The runner reports `PASSED_ENGINEERING_CHECKS`, `g10_status: HELD` and
`release_authorized: false`. No real native environment, receiving alert recipient,
restricted install or G10 acceptance is supplied by this evidence.
