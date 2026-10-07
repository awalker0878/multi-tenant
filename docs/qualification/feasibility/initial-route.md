# Initial native export/import route feasibility

The selected method in [ADR-014](../../decisions/adr-014-first-native-provisioning-and-migration-slice.md)
is `native_api_export_import` for the VMware → OpenStack Linux application route.
This procedure prepares P00.04/G00.04; native acceptance belongs to
[Q07](../campaigns/q07-first-offline-migration.md) and G08.

## Required inputs

Discover source VM identity/configuration, every disk and backing chain, firmware,
controllers, encryption/key requirements, guest agents/drivers and source APIs.
Discover destination image schemas/import methods, compute/storage support, quotas,
service/network topology and approved transfer endpoints. Console records the
administrator's validation and undiscoverable references. Unknown compatibility
blocks the route; image-format acceptance alone does not prove bootability.

## Bounded native procedure

1. Approve preparation of the migration copy through isolated guest operations, consistency checks,
   shutdown, writer fencing, disk mapping, custody and outage/recovery objectives.
2. Recheck the exact powered-off source and configuration. Persist export intent,
   call `ExportVm` once, record its `HttpNfcLease`, and wait for lease readiness.
3. Transfer every approved disk through verified, allowlisted HTTPS. Maintain lease
   progress and bounded byte/deadline checks. Verify the native manifest's inventory,
   capacity, length and secure checksum before completing the lease.
4. Use Glance's discovered `glance-direct` method: private image create, staging and
   import. Verify the imported object and byte digest using a separate identity.
5. Create the target through the approved native volume/port/compute plan in
   quarantine. Verify boot, all application data, service owners and policy paths.
6. Recheck source fencing independently of the completed export lease. Separately
   authorize target writes and traffic. Retain source disks until retirement approval.

Use only the method and copy-only conversion steps selected in the immutable P08 plan. No automatic alternate path is available. A lost reply,
partial transfer, expired authority or unsupported native operation retains custody
and enters reconciliation. A second export/import is never an automatic retry.

## Required negative and recovery observations

Exercise powered-on or changed sources, extra/missing disks, unapproved transfer
origins, corrupt manifests, wrong project, lost export/import responses, revocation,
partial targets, failed boot and denied policy/service checks. Rehearse both sides
of the target-first-write boundary with independently observed single-writer state.
Report actual outage components and data results; synthetic peers establish E2
software evidence only, not installed-platform support.
