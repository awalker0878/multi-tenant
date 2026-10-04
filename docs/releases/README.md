# Release documentation

The release set connects deployable artifacts to qualified capabilities, operating acceptance and the instructions needed to install and support them.

| Document | Responsibility |
| --- | --- |
| [Release process](release-process.md) | Candidate creation, promotion, acceptance, publication and withdrawal |
| [Release manifest](release-manifest.md) | Exact artifact, configuration, contract and evidence bindings |
| [Release readiness](release-readiness.md) | Required technical and operating review before release |
| [Release notes](release-notes.md) | User/operator communication of behavior, supported scope, changes and limitations |

Actual release records are grouped under `docs/releases/<release-id>/` when a candidate is assembled. Each record identifies its immutable manifest and protected evidence references. The current implementation state remains in the [delivery register](../implementation/delivery-register.yaml); these procedures do not create a released version.

Release owners use the [promotion runbook](../operations/runbooks/promote-release.md), the [support matrix](../implementation/support-matrix.md), and G10/G11 [gate criteria](../implementation/gates.md). Runtime authorization still requires the approved operation scope and current native qualification.
