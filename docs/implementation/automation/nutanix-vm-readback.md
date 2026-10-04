# Nutanix AHV VM snapshot readback

`provisioner/execution/nutanix_vm_observe.py` reads only explicitly enumerated VM UUIDs from
`GET /api/vmm/v4.2/ahv/config/vms/{extId}`. Its wire profile follows the
[vmm-go-client/v4.2.2 SDK](https://github.com/nutanix/ntnx-api-golang-clients/tree/vmm-go-client/v4.2.2/vmm-go-client),
pinned by the Nutanix 2.4.2 Terraform provider. There is no API negotiation,
list/discovery request, write, task inference or redirect following.

Use profile `nutanix-ahv-v4.2-vm-snapshot` in the native-reader manifest format:
`platform`, `profile`, canonical HTTPS `origin`, `operation_id`, portable
`tenant_id`, `scope_id`, `engineering_record_ref`, `target_binding_ref`, Boolean
`contact_enabled`, and `resources`. Each resource has `kind: vm`, `ext_id`, an
independently accepted strong `expected_etag`, and `expected`. Do not include
`task`: this observer cannot determine task completion.

For independently recorded VM task IDs, use the separate
[AHV VM/task profile](nutanix-vm-task-readback.md). It adds bounded Prism task
witnesses and recovery review; this snapshot profile retains its original semantics.

The expected wire fields include actual native tenant UUID, VM UUID/type/name,
host, cluster, project, complete category membership, ON/OFF power, CPU/memory,
cross-cluster migration flag, exact NIC identities/connections/MACs/subnets/IPv4,
and disk identities, slots, sizes, containers and migration flags. The schema in
`validate()` is deliberately restricted to normal emulated subnet NICs and VM
disks. NICs use `nicBackingInfo` and `nicNetworkInfo`, the current v4.2 union
fields. Deprecated `backingInfo`/`networkInfo` NIC shapes do not substitute for
them. A missing host for a powered-off VM, omitted Boolean, missing ETag or
unsupported shape produces a hold; never invent defaults to obtain a match.

Use the successful execution receipt's VM IDs, then independently accept expected
native placement, project/category, disk and NIC identities for that exact scope.
The portable tenant label alone does not prove native ownership. Guest IP fields
in the API do not establish actual guest addressing or service reachability.

Offline validation performs no network contact:

```sh
python -m provisioner.execution.nutanix_vm_observe /private/ahv-manifest.json
```

For an authorized observation, inject scoped read-only `NUTANIX_USERNAME` and
`NUTANIX_PASSWORD` into the process environment through the site's secret system,
set `contact_enabled: true`, and provide the accepted origin and CA explicitly:

```sh
python -m provisioner.execution.nutanix_vm_observe /private/ahv-manifest.json \
  --read-authorized-target --expected-origin https://actual-prism-host \
  --ca-file /private/prism-ca.pem --output /private/new-ahv-observation.json
```

The output is a new owner-only file with selected-field hashes and mismatch paths.
Two consecutive matching snapshots are required. Extra collection members,
changed identities/configuration and changed ETags hold. Unselected dictionary
fields remain outside coverage; guest initialization material is not recorded.
`READBACK_MATCH_NOT_QUALIFIED` describes configuration only. Every resource state
explicitly records `task_completion_observed: false`. It cannot resolve an
uncertain Terraform apply, authorize replay, prove Flow enforcement, establish
HA placement/failover, or qualify a recovery. Use actual task evidence and the
[commissioning procedure](site-commissioning.md) separately.

This snapshot supplements [restricted lifecycle transitions](platform-lifecycle.md)
and is integrated before and after guest probes in [campaign v3](target-qualification.md).
Keep the readback, effective Flow/DFW, guest probes and recovery evidence together
under the accepted site record; none of these implementation tests closes live
platform qualification.
