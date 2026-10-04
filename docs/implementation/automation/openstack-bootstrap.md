# Controlled OpenStack bootstrap and withdrawal

The OpenStack domain and workload modules now expose a separate execution
`lifecycle_stage`: `prepared` (default, network/router/port down and VM stopped)
or `bootstrap` (enabled). Neither stage changes the delivery/qualification state.
Use the saved-plan executor and exact transition contract below. A reference
string or successful apply does not establish native acceptance.

## Prepare the site and guest image

Commission the chosen OpenStack distribution using the existing platform-build
runbooks. Record actual Keystone endpoints, project credentials, placement hosts,
storage encryption/key custody, OVN/Neutron enforcement and delegated mutation
boundaries. Accept the provider edge, service endpoints and exact routes. This
implementation adds no external network, SNAT, floating IP or Internet path.

The reference Ubuntu image must already consume config-drive static network data
and trust the operator SSH CA. Select `config_drive: true` **at initial prepared
creation**. Turning it on for an existing VM can require replacement, which
`prevent_destroy` and lifecycle plan review reject. Do not remove these guards to
recover an old VM; commission a separate replacement and reviewed data migration.

Apply domain and workload prepared scopes with the documented
[saved-plan process](terraform-execution.md). Keep the successful private bundles,
receipts and outputs. Confirm native identities and stopped/isolated state using
Neutron and [workload readback](openstack-readback.md). Install and independently
accept the narrow provider-edge bootstrap policy before enabling native links.

## Build and execute an exact transition

Copy the previous scope's inputs into a new private input file. Preserve all
members and resource inputs; change each member's `lifecycle_stage` to `bootstrap`
and supply `bootstrap_acceptance_ref`. Domain members may additionally specify
`bootstrap_rules`: a map of stable rule names to `{direction, protocol, port,
remote_ipv4}`. Only ingress/egress TCP or UDP, one port and one unicast IPv4 /32
per rule are supported. At most 32 rules per domain are permitted. All members
share the provider-owned group for their domain, so shared rules must be accepted
for every attached port. Security groups are stateful and additive; acceptance
must cover native bypass paths, other groups and tenant write permissions.

Create an owner-only acceptance record with `valid_from`, `valid_until` (at most
one hour) and `acceptance_refs` containing `native_boundary`, `service_paths`,
`image_bootstrap`, `withdrawal`. These reference independently accepted evidence
in the site's change system. The helper binds native IDs from a successful prior
execution completed within 24 hours; it cannot authenticate those external
acceptances, refresh stale receipts, or freeze native concurrent writers.

```sh
python -m provisioner.execution.openstack_transition --prior-run /private/prepared-domain-run \
  --inputs /private/bootstrap-domain-inputs.json \
  --acceptance /private/bootstrap-acceptance.json --stage bootstrap \
  --output /private/domain-transition.json
```

Prepare the next exact saved plan with `provisioner/execution/terraform_run.py`, passing the new
inputs, fresh contact authority and `--transition /private/domain-transition.json`
along with the normal backend, cloud, CA and other arguments. The transition is
sealed into the bundle and revalidated before apply. Obtain approval of that
exact bundle and all findings, then use `provisioner/execution/terraform_apply.py`. Repeat for
the workload scope using its own prior outputs and transition file.

Only updates to existing network/router/port administrative state and VM power
are permitted, plus creation of precisely described bootstrap service rules.
Unrelated updates, replacement, deletion, adoption, unresolved mutation fields,
native drift, missing members or changed native IDs block the transition.
Existing service rules must remain unchanged. Terraform still owns these objects;
no secondary command writes Nova/Neutron/Cinder lifecycle state.

## Qualify, activate, and withdraw

Run readback again, construct pinned guest access, apply guest hardening/services,
then collect controlled service and isolation observations. Complete the accepted
HA, delegated security, storage and application-recovery exercises. The existing
edge activation process still requires separate exact evidence and approval.
Bootstrap is not tenant-service activation.

If verification fails or becomes unknown, withdraw the edge policy first. A
fresh Terraform transition to `prepared` stops workloads and disables owned
ports, then disables domain links. Retain the same bootstrap rule map and its
acceptance reference during withdrawal; rules and volumes have `prevent_destroy`.
Plan/apply each scope separately and read back the resulting state. Terraform
ordering is not an atomic cross-scope withdrawal, and a timeout must remain held
for reconciliation. Never roll Terraform state back as a substitute for restoring
data. Retirement of retained disks/rules is a separate reviewed operation.

The operator must provide actual site inventory, service trust, native credentials
and authorized fault-test windows. Local fixtures and provider mocks do not
commission a site or qualify production HA/security/recovery.
