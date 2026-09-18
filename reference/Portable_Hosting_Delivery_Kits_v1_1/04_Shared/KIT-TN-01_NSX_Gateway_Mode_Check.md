# KIT-TN-01 — Verify NSX parent-gateway mode before selecting Tier-0 VRF

**Status:** additional engineering review check; not an amendment to the frozen architecture and not a production change instruction.

The v1.4 architecture treats an isolated Tier-0 VRF as one candidate upstream realization and requires exact release/feature qualification. Broadcom KB 442835 describes a restriction when the parent Tier-0 uses active-active stateful mode. Therefore the engineering record must name the parent mode, VRF functions, Edge placement, installed releases and supported feature combination rather than accepting the words “Tier-0 VRF” as a complete design.

Review the current applicable vendor documentation and actual installed tuple. A required different mode or topology is an architecture-impacting change with service interruption, routing, stateful inspection and recovery consequences to assess. Do not reconfigure a live parent gateway to satisfy this checklist without a separate approved design/change and qualification.

**Owner:** VMware/NSX platform and network/security engineering. **Blocking point:** selecting/qualifying the affected native realization. **Record:** engineering Stack_Tuples and Operation_Coverage; LLD §8; Vendor Realization Card §3. **Actual disposition:** unresolved until the site supplies support evidence.

Official source (reviewed 16 September 2026): https://knowledge.broadcom.com/external/article/442835/cannot-add-tier0-vrf-gateway-to-a-tier0.html

[Parent architecture](../05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Vendor cards](../02_Engineering/Vendor_Realization_Cards.docx)
