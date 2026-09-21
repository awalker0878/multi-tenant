# OpenStack workload observations

`tools/openstack_observe.py` performs bounded GET-only readback of explicitly
enumerated Nova servers, Cinder volumes and Glance images. This complements the
Neutron collector; it does not establish platform qualification or native RBAC.

Create an owner-only `hosting-openstack-readback/1` manifest outside the checkout.
It contains the five-part WSD `scope`, exact `project_id`, accepted catalog
`endpoints` for each used service and 1–30 `resources`. Every resource has `kind`
(`server`, `volume`, `image`), UUID `id`, and an `expected` object. The required
fields are defined in `KINDS` in the collector. The synthetic test manifest in
`tests/test_openstack_observe.py` illustrates the shape, not installed inventory.

Use full HTTPS catalog endpoints: compute ending in `/v2.1` or
`/v2.1/<project>`, volume ending in `/v3/<project>`, image ending in `/v2`.
Deployment-specific path prefixes are preserved. Discovery, redirects, proxy
inheritance and writes are unavailable. Nova uses microversion 2.79 and Cinder
3.60; an unsupported or missing negotiated version holds the observation.

The manifest must name actual compute hosts and hypervisor names, availability
zones, flavor shape, retained boot/data attachments, volume encryption and type,
and the protected image's strong content hash. The operator must compare these
against the accepted placement, storage and image records. Nova administrative
host fields and Cinder project fields require suitable read privileges; missing
fields remain unknown. A read token must never be handed to a guest or tenant.

Two consecutive reads must match the expectations and one another. Selected
dictionary fields are compared recursively; lists require exact membership and
order. Unselected dictionary fields are outside coverage. These reads are not an
atomic cross-service snapshot, a scheduler/aggregate isolation proof, or a
concurrent-mutation fence. Native writes must remain frozen by the operator
during acceptance. Metadata/body values and credentials are not emitted in the
report; it contains mismatch paths and observation hashes.

Validate without network contact:

```sh
python tools/openstack_observe.py /private/workloads.json
```

For actual contact, provide owner-only token, CA and authority files. Authority
contains exact `manifest_sha256`, `token_sha256`, `ca_sha256` byte hashes,
`valid_from`, `valid_until` (at most one hour), and external `change_ref`.

```sh
python tools/openstack_observe.py /private/workloads.json \
  --token /private/read-token --ca /private/site-ca.pem \
  --authority /private/read-authority.json --output /private/new-observation \
  --execute
```

`OBSERVED_MATCH_NOT_QUALIFIED` is an observation only. Attach its manifest and
result to commissioning evidence before and after bootstrap, guest hardening,
activation, each authorized HA/security/recovery exercise and withdrawal. Combine
it with Neutron readback, healthy-control traffic tests, delegated negative
mutation tests, application recovery checks and an independently accepted site
record. Never manufacture actual host IDs or accepted evidence from these tests.

API contracts: [Nova compute](https://docs.openstack.org/api-ref/compute/),
[Cinder v3](https://docs.openstack.org/api-ref/block-storage/v3/), and
[Glance v2](https://docs.openstack.org/api-ref/image/v2/).
