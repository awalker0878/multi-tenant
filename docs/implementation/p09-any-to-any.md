# P09-A — Any-to-any workload migration completion

Approved scope: all nine directed combinations of VMware, OpenStack and Nutanix
AHV, including separate installations of the same platform. Baseline:
`eda64354816b4884530118f6595c037a5a556807`. This tranche completes existing P09
obligations and affected P07/P08 outcomes; P11 remains pilot and supported release.

| Package | Delivery | Engineering | Native qualification |
| --- | --- | --- | --- |
| A01 | Connected directional eligibility and exact support records | In progress | Not started |
| A02 | Role-aware profiles and isolated platform mechanisms | In progress | Not started |
| A03 | Contextual requirements with downstream consumers | Not started | Not started |
| A04 | Copy-only guest preparation and independent health probes | Not started | Not started |
| A05 | Security mapping and individual enterprise-service outcomes | Not started | Not started |
| A06 | OpenStack source and OpenStack → AHV workload path | Not started | Not started |
| A07 | AHV source and composed destination paths | Not started | Not started |
| A08 | VMware destination and all nine composed directions | Not started | Not started |
| A09 | Data consistency, durable continuation and recovery | Not started | Not started |
| A10 | Console, fleet, campaign and measured-progress parity | Not started | Not started |
| A11 | Directional qualification and affected P10 handoff | Not started | Not started |

## Invariants

- Native APIs are authoritative; Terraform is outside the VM data path and VDDK
  is not required. Whole-VM transformations operate on a migration copy.
- Source/destination roles compose through capabilities; native metadata and
  unsupported constraints remain explicit. A method enum is not an implementation.
- Every required guest, security, service and application outcome must be observed
  independently before production activation. Declarations and API receipts are
  not operational acceptance.
- Before possible destination writes, rollback requires target fencing and proof
  of no divergence. After possible writes, preserve changes and reconcile through
  forward recovery or a qualified reverse procedure. Unknown outcomes remain held.
- Test peers are E2 evidence. Each advertised direction/version/guest/method needs
  separate E3 evidence and the applicable E4 receiving acceptance. Missing lab
  access never turns an unimplemented handler into an external-only blocker.

## External qualification inputs

Exact installed platform/API/backend versions, approved guest images and licenses,
application consistency and recovery procedures, platform/service credentials,
network and security mappings, enterprise-service interfaces, conversion artifacts,
measured operating objectives and independent receiving owners are required.
Repository development does not itself authorize operations against a platform.

## Acceptance

Engineering exit requires concrete mechanisms and connected consumers for the
approved scope, compatibility and failure tests, and current architecture/runbooks.
Native exit requires a functioning secured enterprise-integrated workload for an
exact tuple in every direction, plus every additional advertised variant. Include
unsupported combinations, failed prerequisites, lost responses, partial integration,
process interruption, retry/resume, cutover and both recovery boundaries. Retain all
failures and source/artifact identities. P10/P11 own operating release acceptance.
