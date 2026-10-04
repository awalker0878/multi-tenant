# Architecture and delivery decision register

Date: 2026-10-04. `DIRECTED` records user/source direction. `PROPOSED` is the planning recommendation. `OPEN` requires a recorded P00 decision. None of these statuses means code exists or infrastructure is authorized.

Each resolved ADR must record context, options considered, choice, consequences, owner, date, affected contracts and validation evidence. The register is the starting backlog, not fabricated approval minutes.

| ID | Decision | Status and baseline | Accountable role | Must close before |
| --- | --- | --- | --- | --- |
| ADR-001 | Product reset | DIRECTED: fresh implementation; `greenfield/laravel-product-foundation` is abandoned for this work; previous runtime is reference only | Product | Completed as planning direction; P00 confirms scope |
| ADR-002 | Languages and UI | DIRECTED: Laravel/PHP + Python; Inertia 3, Vue 3, TypeScript, Tailwind 4, Vite 8 | Architecture | P00 dependency spike |
| ADR-003 | Exact runtime versions | PROPOSED: Laravel 13, PHP 8.5 candidate; supported Node/Python minors and all patch versions OPEN | Engineering | P01 scaffolding |
| ADR-004 | Contexts | PROPOSED: console; governance; catalogue; inventory; planning; lifecycle; assurance. Laravel assurance; no generic integrations service | Architecture | P01 contracts |
| ADR-005 | Deployment granularity | PROPOSED: seven principal application deployables plus independently scoped worker pools in one repository | Architecture/SRE | P01 |
| ADR-006 | Data isolation | PROPOSED: database per service with separate roles on an operated PostgreSQL cluster; physical cluster separation follows trust/scale needs | SRE/security | P01 persistence |
| ADR-007 | Durable execution | DIRECTED baseline: Temporal with Python workflows/activities; lifecycle owns admission and native-operation ledger | Infrastructure | P01/P06 |
| ADR-008 | Domain-event broker | OPEN: choose broker supported by the operating team; RabbitMQ is an initial candidate to assess against ordering/replay/HA requirements | Architecture/SRE | P01 outbox transport |
| ADR-009 | Identity and delegated authority | OPEN: enterprise OIDC provider, service identities, token delegation, revocation, break-glass and approval policy | IAM/security | P02 |
| ADR-010 | Secrets, PKI and evidence | OPEN: approved secret/key services, trust bootstrap, protected S3-compatible artifact store, retention and immutable evidence mechanism | Security/SRE | P01/P06 |
| ADR-011 | Central/site topology | PROPOSED: central Kubernetes per approved trust boundary; site-local worker pools; exact distribution/CNI/site runtime and network flows OPEN | SRE/security | P01 infrastructure |
| ADR-012 | API/event compatibility | PROPOSED: OpenAPI + AsyncAPI, schema-first cross-language contracts, at-least-once delivery, outbox/inbox and expand/contract changes | Architecture | P01 |
| ADR-013 | Domain cardinality | OPEN: validate Tenant/WSD/SecurityDomain/DomainInstance/Workload relationships, sharing rules and deletion invariants | Product/architecture | P03 schema |
| ADR-014 | Initial native route | PROPOSED: OpenStack provisioning, VMware→OpenStack cold guest/disk conversion/import, one Linux stateful application; exact method contingent on feasibility | Product/infrastructure | P00/P04 |
| ADR-015 | Platform and service tuples | OPEN: installed versions/backends/network topology, guest image, IPAM/DNS, identity, backup, monitoring and service-owner APIs | Platform/service owners | P04/P07 |
| ADR-016 | Terraform/Ansible ownership | PROPOSED: reviewed saved-plan workflow and explicit field/state ownership; version/toolchain/backend selections OPEN | Infrastructure | P06/P07 |
| ADR-017 | SLO, scale and recovery | PROPOSED targets in phased plan; actual load model, RPO/RTO and application outage objectives OPEN | Product/SRE | P00 baseline; P10 acceptance |
| ADR-018 | Qualification admission | PROPOSED: separate lab campaign authorization for unqualified candidates; supported operational admission requires qualified tuple evidence | Security/quality | P06 native admission design |
| ADR-019 | Frontend runtime | PROPOSED: compiled assets with server sessions and polling first; SSR and live event channel deferred unless justified | Product engineering | P01 console |
| ADR-020 | Restricted-network installation | OPEN: registry/dependency mirrors, signed offline bundles, site disconnection policy and permitted continuation | SRE/security | P01 design, P10 qualification |
| ADR-021 | Retained historical state | OPEN: default clean product data; import/archive only for identified retention or operating needs; never import active workflow authority blindly | Product/records owner | P00 decision, P11 disposition |
| ADR-022 | Release support scope | OPEN: exact P09 tranche included in first release, support ownership, platform qualification expiry and revalidation rules | Product/service owner | P00 scope, P10 release freeze |

Changing a proposed choice is normal design work. Changes to user-directed architecture or release scope require an explicit documented decision; do not silently substitute another stack, reintroduce the previous runtime or label a different migration method as equivalent.
