# Source register and authority

Frozen v1.4 documents are the immediate architecture basis. The original uploaded handbook is historical lineage, not a reason to reintroduce its controller-centric framing or superseded topology assumptions. All new kit record formats, workplans and example delivery IDs are local proposed practices. External sources below support only the stated mechanism/context; they do not qualify an installed platform.

## K01 — Cloud network security zones (ITSP.80.023)

Reviewed sections 1–4; supports scoped cloud-zoning and management considerations, not authorization. Reviewed 2026-09-16.

https://www.cyber.gc.ca/en/guidance/cloud-network-security-zones-itsp80023

## K02 — ITSP.10.033 foreword, overview and introduction

Reviewed supersession statement; preserve exact control edition rather than silently joining legacy IDs. Reviewed 2026-09-16.

https://www.cyber.gc.ca/en/guidance/cyber-security-privacy-risk-management/itsp10033/foreword-overview-introduction

## K03 — Terraform providers within modules

Reviewed provider configuration and module boundaries; actual provider support remains environment-specific. Reviewed 2026-09-16.

https://developer.hashicorp.com/terraform/language/modules/develop/providers

## K04 — Terraform dependency lock file

Reviewed distinction between provider dependency locks and remote module selections. Reviewed 2026-09-16.

https://developer.hashicorp.com/terraform/language/files/dependency-lock

## K05 — Official Nutanix Terraform provider repository

Reviewed README compatibility, feature and lifecycle notes; no provider version selected for a site. Reviewed 2026-09-16.

https://github.com/nutanix/terraform-provider-nutanix

## K06 — OpenStack Neutron networking concepts

Reviewed security-group/port concepts; latest documentation is a development branch, not a production pin. Reviewed 2026-09-16.

https://docs.openstack.org/neutron/latest/admin/intro-os-networking.html

## K07 — OpenStack OVN reference architecture

Reviewed role and routing model; selected distribution/backend must be independently qualified. Reviewed 2026-09-16.

https://docs.openstack.org/neutron/latest/admin/ovn/refarch/refarch.html

## K08 — OpenStack Nova host aggregates

Reviewed scheduling/aggregate controls; labels alone do not establish placement enforcement. Reviewed 2026-09-16.

https://docs.openstack.org/nova/latest/admin/aggregates.html

## K09 — Broadcom KB 442835 — Tier-0 VRF and active-active stateful HA

Official KB reviewed; explicit design limitation warrants a tuple-specific engineering check, not a production reconfiguration instruction. Reviewed 2026-09-16.

https://knowledge.broadcom.com/external/article/442835/cannot-add-tier0-vrf-gateway-to-a-tier0.html

## K10 — Guidance on securely configuring network protocols (ITSP.40.062)

Reviewed protocol-configuration scope; approved site configurations remain required. Reviewed 2026-09-16.

https://www.cyber.gc.ca/en/guidance/guidance-securely-configuring-network-protocols-itsp40062

## K11 — Terraform plan command reference

Reviewed saved-plan handling; plan outputs can contain sensitive infrastructure values. Reviewed 2026-09-16.

https://developer.hashicorp.com/terraform/cli/commands/plan

## Publishing reference

Microsoft Open XML hyperlink class documentation was used to review document-link representation. This is a publishing reference, not an infrastructure requirement.

https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.hyperlink?view=openxml-3.0.1
