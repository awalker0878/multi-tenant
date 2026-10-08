# P07 native product control

The product path now composes provisioning and retirement recipes into new immutable
Planning proposals and admits their independently approved references through
Lifecycle. It retains the single-use stage journal, current custody checks,
independent readback, and terminal stop behavior of the native workflow.

`POST /v1/tenants/{tenant}/applications/{application}/environments/{environment}/native-plans`
accepts only `site_id`, `base_plan_id`, and `recipe_id`, with workload authentication,
current delegated `plan.create` authority and an idempotency key. The protected
`PLANNING_NATIVE_RECIPES_FILE` uses the same scoped registry format as migration
recipes. Each recipe binds the exact base content hash, purpose, every ordered
stage intent, custody generation, configuration, tuple and policy matrix. Retirement
also identifies its original provisioning job. The provision/retire intent must
match the qualified base native operation plan. Recipe expiry or removal holds
unattended execution as well as interactive validity reads. Composition creates a
new plan requiring its own approval; retry returns the original durable receipt.

`POST /v1/tenants/{tenant}/native-jobs` accepts only immutable plan and approval
references. Lifecycle resolves Planning and Governance itself, restricts the purpose
to provision/retire, checks the delegated executor and admits through the durable
native workflow. `GET .../native-jobs/{job}` returns tenant-scoped state;
`POST .../native-jobs/{job}/stop` requires `expected_revision` and current delegated
control authority. Migration stays under the separate campaign controller.

The explicit worker `native_owner_protocol` stage kind supports reservation, guest,
service, activation, retirement and release owner protocols. Provision remains the
reviewed OpenStack API adapter. Owner writes and observations use distinct mounted
credentials. Effects recheck credentials and current authority during requests;
read clients reject write routes. Rotated or shared credentials hold the operation.
These mechanisms do not implement the external enterprise owner or native fence.

The worker rechecks writer/observer credential separation before inspection and
at every effect boundary, including after the current-authority callback. Rotation
cannot defer detection until after a native request. Independently enrolled owner
observers can use a different origin from vCenter or the service writer; their
own pinned address and TLS policy still apply. Direct VMware/AHV lifecycle
readback continues to require the same enrolled provider origin.

The direct OpenStack worker now checks mounted runtime identity and distinct
writer/observer tokens before inspection and at native request boundaries. Both
identities use the same enrolled service URLs and address pins. A runtime edit,
missing observer token, credential collision, in-flight rotation or token expiry
holds the attempt. Scope is retained only after a complete Keystone response.
Native JSON transports also reject truncated bodies, conflicting length/chunk
framing and incomplete chunks; a valid JSON prefix cannot establish acceptance.

Published additive interfaces are in `contracts/openapi/planning-native-v1.json`
and `contracts/openapi/lifecycle-native-jobs-v1.json`. The compiler/resolver
composition check is `scripts/p07/check_composition.py`; PostgreSQL persistence,
revocation, HTTP authority and owner-adapter regressions run in component CI.

Native qualification still requires the actual N01–N15 records and the owner
implementations identified in [the completion packet](p07-completion-review.md).
P08 still requires its selected copied-guest/delta/continuation/recovery methods and
native campaigns. No provision, retirement or migration support claim follows from
synthetic owner responses or a local passing test.
