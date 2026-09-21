# Reference service implementation decisions

This implementation selects concrete interfaces from the existing architecture.
These are engineering choices for a deployable reference profile, not claims that
an installed site has been selected, commissioned or accepted. Actual endpoints,
native IDs, installed versions, credentials and data-owner objectives are private
deployment inputs. The architecture remains portable across all three VM stacks.

| Concern | Selected reference implementation | Architecture basis and boundary |
| --- | --- | --- |
| First qualification path | OpenStack, internal IPv4 two-tenant OZ/RZ fixture, Ubuntu 24.04 guests | [Delivery order](README.md#scope-of-all-environments); existing Neutron exact-ID observations and domain/workload roots provide the first vertical path. VMware/NSX and Nutanix remain required follow-on targets; no installed site or release tuple is invented |
| Terraform state | GitLab-managed HTTP state, separate projects at the required credential boundary, one state per environment/site/platform/tenant/WSD/phase | [Writer ownership](../provisioning-strategy/5-concurrency-ownership-and-failed-execution.md); backend locks serialize Terraform, while native task fencing remains separate |
| Address ownership | NetBox REST IPAM, exact tenant/VRF/prefix and reserved address; bounded token, operation identity and lost-response reconciliation | [Service interfaces](../native-reference/service-interfaces.md); IPAM is not a compute-capacity reservation service |
| Authoritative DNS | Existing RFC 2136 client with TSIG; [NetBox handoff](netbox-dns.md) binds initial A/PTR registration to current confirmed IPv4 ownership | Same service interface schedule; forward/reverse and recursive/secondary observations remain separate gates |
| Guest | Existing Ubuntu 24.04 systemd/Python image profile, extended with explicitly owned hardening and service files | [Guest runbook](native-guests.md); image packages and actual installed versions are qualified before use |
| Guest execution | Source-bound private Ansible bundle, certificate-only SSH, fixed serial playbook, exact mode approval and durable per-scope attempt ledger | [Reviewed guest execution](guest-execution.md); implements the existing guest ownership boundary and keeps native fencing/acceptance separate |
| Administrator identity | OpenSSH user certificates from an external issuing authority, explicit per-account principals and revocation data | [Identity and independent recovery](../../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md); signing keys stay outside workloads and Terraform state |
| Guest audit transport | rsyslog over authenticated TLS to explicit collectors, persistent local journal and disk queue | [Service interfaces](../native-reference/service-interfaces.md); ingestion credentials do not grant collector administration or deletion |
| Workload data backup | restic client and a TLS REST repository with append-only server authority; separate retention administrator and restore custodian | [Backup and isolated restore](../../architecture/shared-services/5-backup-capture-independent-protection-and-isolated-restore.md); file backup is not application-consistent VM snapshot protection |
| Activation | Adopted provider-owned Linux/nftables IPv4 edge: exact service tuples, expiring kernel allows, explicit bootstrap/active/withdraw operations | [Edge adapter](edge-activation.md); requires commissioned routes, native attachments, mandatory platform policy and independently verified boot/HA containment |
| Qualification | Bound native API readback before/after certificate-SSH guest health and denial probes | [Target runner](target-qualification.md) feeds the [native campaign](../native-reference/campaign.md); no local fixture populates accepted qualification indexes |

## State service setup

Use an independently recoverable GitLab instance. State access is a project-level
authorization boundary: separate projects where different tenants or operators
must not read one another's state. Restrict the runner token to its intended state
project and retain GitLab encryption secrets, database and object storage through
the independently tested service backup. Restoring an old state is not a native
resource rollback.

`tools/state_backend.py` compiles `backend.json` consumed by the
[reviewed executor](terraform-execution.md). It takes `--origin`, `--project-id`,
`--environment-key`, `--site-key`, `--platform`, `--tenant-key`, `--wsd-key`,
`--phase` and `--output`. The output parent must already be private. It performs
no service contact. Inject `TF_HTTP_USERNAME` and `TF_HTTP_PASSWORD` through the
executor's private credential file. A state project's access, actual lock
behavior, retention and independent recovery must be exercised at commissioning.

Implementation references: [GitLab state](https://docs.gitlab.com/user/infrastructure/iac/terraform_state/),
[NetBox REST API](https://netbox.readthedocs.io/en/stable/integrations/rest-api/),
[OpenSSH server configuration](https://man.openbsd.org/sshd_config),
[restic restore](https://restic.readthedocs.io/en/stable/050_restore.html).

This record selects implementations for the existing boundaries. It does not
select a physical site, assert supported platform tuples, change architecture
approval, grant production exposure, or replace an already adopted enterprise
service without its owner's migration decision.
