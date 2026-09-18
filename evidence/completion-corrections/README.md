# Connected engine evidence and corrective verification

The initial corrected run [35294495699](https://github.com/awalker0878/multi-tenant/actions/runs/35294495699) tested head `2bb69be80f58304bb39cbaefd85935da2d2eba7a`. It passed actual Terraform 1.13.5 module/root validation, all ten plan-only provider-mock suites, and actual local Ansible syntax/idempotence/check-mode/negative checks. No root apply, native platform contact or authorization was performed.

[Actual Terraform report](initial_terraform_engine.json) · [Actual Ansible report](initial_ansible_engine.json) · [Artifact/source/schema/lock provenance](initial_engine_provenance.json)

Actual exported provider schemas are stored as unchanged JSON under `schemas/`, deduplicated by SHA-256. Root and module provider locks are committed under their exact source paths. They are actual initialization outputs, not fabricated selections. The recorded pins match the intended versions; supplier provenance/security and platform qualification remain separate.

The corrected final source must pass CI again with source locks read-only. The final run is recorded separately rather than relabelling this initial run as evidence for every later edit. Maintained docs, scope acceptance and native assertions have their own owner/evidence obligations.

[Corrective finding dispositions](../../docs/assurance/completion-corrections.md)
