# Q08: VMware → AHV Linux cold-export destination

This is an executable campaign specification for the
[AHV destination implementation](../../implementation/ahv-destination.md).
It is not a completed campaign, acceptance certificate or E3 record.
Use the Q08 route-selection/admission machinery and ADR-018 isolated lab authority.
Inherit Q02 and Q04–Q07 evidence obligations; do not bypass current custody, approval
or stage boundaries merely to obtain native evidence.

Record exact VMware release/API, Prism Central, AOS, AHV, each namespace version,
cluster/project/storage/network/security configuration, guest/kernel/initramfs,
firmware, all source disk/NIC identities, driver profile, converter/rootfs digests,
worker image and source commit. Initially select Linux cold export, BIOS, raw,
SCSI disks and VirtIO NICs. The namespace pin is v4.3; unsupported namespaces hold.
Every distinct guest, firmware, device, platform version and route is separate scope.

| Case | Required original observation and pass condition |
| --- | --- |
| Accounts and scope | Separate collector/writer/observer creation receipts; current IAM/key/policy reads; permitted native actions and actual denial outside the project and selected cluster. Verify read-only identities cannot create or delete. |
| Discovery | API identities and installed versions match the enrollment. Expiry/revocation invalidates selection. Missing permissions, mixed/unknown versions and partial lists remain held. No returned URL changes the native origin. |
| Source fence | Verify application quiescence, last-write boundary, source shutdown and all-writer fencing before capture. The source remains stopped/fenced throughout cold export/import. |
| All-disk capture | Compare every disk/NIC and dataset to the reviewed source. Test at least a boot disk plus data disk, different sizes, and multiple NICs. Retain exact snapshot/clone/OVF and per-file digests. |
| Converted copy | Native source remains unchanged. Pinned conversion and copy-only offline driver preparation succeed; sector comparison and whole-file receipts match before any target write. |
| Image transfer | The real native downloader trusts and reaches the private HTTPS listener. Invalid CA, foreign peer, expired/revoked grant, changed file and symlink fail. Verify all native image bytes/checksums and placement; no public sharing or credential leakage. |
| VM and quarantine | Native task succeeds and independently read-back IDs match the journal. Check project/cluster, CPU/RAM, BIOS, boot order, every disk/image/container and every disconnected quarantine NIC/category. No production network or application writes are admitted. |
| Guest and data | Separately authorized quarantine boot: drivers, initramfs, OS/filesystems, disk UUIDs/order, mountpoints, metadata and all dataset hashes/application checks succeed. Native image creation alone cannot satisfy this case. |
| Network/security | Actual allowed and denied flows across same-host subnet, different hosts and edge, forward and return, plus applicable IPv4/IPv6. Validate Flow policy/category effect, DNS/IPAM, routes and enterprise service attachments. |
| Activation | Current review, support record, approval, ownership and independent results gate production mapping and writes. Record the first possible target write. Confirm source stays fenced. |
| Interrupted API | Kill worker after POST before reply, after accepted task, mid-download and mid-poll. Rotate/revoke credentials and change authority. Reconcile tasks/objects without another POST; no duplicate images/VMs or released custody. |
| Pre-write recovery | Fence target, prove no divergence, then restore source under separate approval. Verify application/data and retained snapshots/artifacts. |
| Post-write recovery | After actual or uncertain target writes, preserve target changes; prove approved forward recovery or qualified reverse synchronization. Starting the old source without this proof must fail. |
| Cleanup | Reconcile every native task, delete only owned temporary objects under separate scoped authority, verify image/VM absence and source snapshot consolidation, revoke grants/credentials and enforce retention. Successful migration never implicitly retires source. |

Retain native request/task/object IDs, timestamps, independent observations, exact
selection/artifact digests, raw test output and failures. A reset/retry must use a
new independently approved operation only after the prior outcome and custody are
resolved. Feed original, source-bound results through Q08's existing exact-tuple
qualification mechanism; E3 may be issued only after all required cases pass.
Receiving acceptance and tenant plan approval remain separate. E2 fixtures,
manual checkmarks, SDK field coverage and this document cannot promote a tuple.
