# RAD-M01 — Reference adoption and deviation design

**Version:** 0.1 · **Status:** Proposed · **Accountable role:** Architecture authority.

## Scope and authority

Reference adoption for a portable infrastructure service; no site-specific control assessment is implied.

This is a newly authored maintained Markdown record, not a reconstruction of an unavailable Word original. Its creation date is not an acceptance date. Source basis: [RA §1](../architecture/reference/1-purpose-scope-and-architectural-authority.md) · [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) · [RA §29](../architecture/reference/29-architecture-decisions-and-alternatives.md).

## Design content

The available proposed baseline is the v1.4 infrastructure reference and linked delivery-kit v1.1 engineering. Adopt its physical/logical views as a versioned set, then identify service demand, independent information impacts, eligible locations, assurance sharing and required native platform profiles. Do not equate Tenant Namespace, WSD, security-domain intent and native domain instance.

Every variation names the original requirement/decision, requested scope, competing options, route/data/management consequences and accountable authority. Existing proposed ADRs explain why the base design uses commissioned cells, local overlays, explicit ZIP mediation, scoped services and separated administration. Acceptance must record actual applicability and exceptions, not rewrite source history.

The source-scope inventory records previously described but unavailable originals. This newly identified record covers adoption guidance without asserting that the missing RAD file was recovered. Unresolved file recovery and organizational adoption are different conditions.

## Engineering and implementation handoff

The TAD and selected solution inherit the approved baseline version, topology boundaries, sharing choices and service constraints. They identify which fields need actual supported values and which require architecture/security decisions. Independent controls such as physical OOB and key recovery need real owners and design artifacts, not references to an API reader.

## Acceptance and open work

Review the explicit scope inventory, current risks and unresolved values. Choose whether this new maintained record meets the service’s documentation need. That owner decision remains open; the repository can validate its completeness of structure, not supply authority.

Adopting authority and approval evidence: **not recorded**. Link the actual design review and its conditions when they exist; a code merge does not authorize a site or service. Keep sensitive site parameters and private credentials in their approved systems.

[Maintained design register](README.md) · [Decision register](../adr/README.md)
