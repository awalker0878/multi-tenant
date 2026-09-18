# Platform capability registry and placement evidence boundary

The portable architecture requires a machine-readable capability profile for each platform, but a capability declaration is not the same as an installed-platform qualification. This repository therefore keeps a small engineering registry at `sources/capabilities/platform_registry.json` and fails closed when a mandatory capability lacks **native** qualification.

The registry is not a service controller or placement engine. It does not select a site, contact a platform, interpret a consumer request, or issue authorization. It records what the repository currently contains and what native evidence is still missing.

## Evidence states

| Field | Meaning |
|---|---|
| `UNASSESSED` | The repository has not established even candidate source for this capability. |
| `DOCUMENTED_EXPECTATION` | Architecture/engineering material describes the required outcome, but no candidate implementation is being claimed. |
| `CANDIDATE_SOURCE` | Repository code exists for part of the capability; installed-platform qualification remains open. |
| `LOCAL_FIXTURE_ONLY` | A local synthetic/protocol fixture exercises part of the outcome; this cannot be promoted to native support. |
| `NATIVE_QUALIFIED` | Reserved for a selected installed product/API/provider tuple with separately controlled native evidence references. None of the current entries has this state. |

`NOT_QUALIFIED` is therefore the correct current qualification for every capability in all three platform families. Provider pins and committed locks prove dependency selection for repository tests; they do not prove that an installed platform supports the requested capability or assurance profile.

## Portable vocabulary

The initial registry mirrors the portable capability concepts already used by the architecture: isolated network domain, IPv4, IPv6, distributed firewall, gateway policy, dynamic routing, service insertion, native load balancer, dedicated edge context, and audit logging. This list is deliberately small. It should expand only through an architecture/engineering decision, not because a vendor advertises another feature.

For Nutanix, VMware/NSX, and OpenStack, repository source may be marked `CANDIDATE_SOURCE` where Terraform modules exist. The routed IPv6 Linux laboratory is recorded only as `LOCAL_FIXTURE_ONLY`; it does not qualify any vendor's native IPv6 implementation. Optional features such as service insertion or native load balancing remain unassessed until a real service requirement and selected platform justify qualification work.

## Eligibility rule

The checker in `scripts/check_platform_capabilities.py` enforces one rule that future placement logic must preserve: **a mandatory requirement is satisfied only when the matching capability is `NATIVE_QUALIFIED` for the selected installed tuple**. Candidate code, documentation and local fixtures are never treated as substitutes.

The current registry intentionally yields no production-eligible platform because no site/product tuple has been selected and no capability carries native qualification evidence. That is a correct engineering hold, not a failed architecture.

When a native campaign is completed, update the selected product tuple, attach controlled external evidence references, and record only the capabilities actually demonstrated for that tuple. Assurance-profile eligibility must be recorded separately and cannot be inferred from a product family name.

Before any such update is accepted, the exact tuple must have a current [native PlatformProfile qualification dossier](platform-native-qualification.md). The registry checker cross-validates native-qualified claims and assurance profiles against that active dossier index; directly editing a qualification flag is insufficient.

## Relationship to implementation work

This registry complements, rather than replaces, the implementation backlog and commissioning kit. The backlog identifies still-open native edge, service, IPv6, recovery, and activation work. The commissioning kit identifies the site inputs and acceptance sequence. The registry provides a machine-readable place to record the resulting qualified capabilities once that evidence exists.

A future automated placement component may consume this file or a successor service, but this repository check does not implement placement. If the registry is unavailable, malformed, stale, or lacks a required qualified capability, placement must fail rather than silently downgrade the requested outcome.

[Engineering index](README.md) · [Implementation backlog](../../sources/implementation_backlog.csv) · [Native commissioning](../implementation/native-reference/README.md) · [ADR-0017 — qualification vs authorization](../adr/0017-separate-reference-adoption-technical-qualification-and-authorization.md)
