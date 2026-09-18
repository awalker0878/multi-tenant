# Appendix B — Terraform Root and Module Patterns

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB10:417 BEGIN -->

<!-- SOURCE-BLOCK HB10:417 END -->

<!-- SOURCE-BLOCK HB10:418 BEGIN -->

## B.1 Provider Configuration Pattern

<!-- SOURCE-BLOCK HB10:418 END -->

<!-- SOURCE-BLOCK HB10:419 BEGIN -->


<a id="source-table-419"></a>

| terraform {<br>  required\_providers {<br>    nutanix = {<br>      source  = "nutanix/nutanix"<br>      version = "~&gt; &lt;validated-version&gt;"<br>    }<br>  }<br>}<br><br>provider "nutanix" {<br>  # Endpoint/authentication injected by the execution environment.<br>  # Do not embed secrets in source.<br>}<br><br>module "security\_domain" {<br>  source = "../../modules/nutanix/security-domain"<br><br>  domain\_spec = local.normalized\_domain\_spec<br>  providers = {<br>    nutanix = nutanix<br>  }<br>}<br> |
| --- |

<!-- SOURCE-BLOCK HB10:419 END -->

<!-- SOURCE-BLOCK HB10:420 BEGIN -->

## B.2 Adapter Boundary

<!-- SOURCE-BLOCK HB10:420 END -->

<!-- SOURCE-BLOCK HB10:421 BEGIN -->


<a id="source-table-421"></a>

| # Orchestrator selects one adapter before Terraform execution.<br># Do not build a giant cross-provider child module.<br><br>normalized\_intent.json<br>        \|<br>        +--&gt; adapters/nutanix/root.tf<br>        +--&gt; adapters/nsx/root.tf<br>        +--&gt; adapters/openstack/root.tf<br> |
| --- |

<!-- SOURCE-BLOCK HB10:421 END -->

[Previous chapter](61-appendix-a-canonical-object-model.md) · [Chapter index](README.md) · [Next chapter](63-appendix-c-baseline-policy-matrix.md)
