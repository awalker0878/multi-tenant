# ADR-0001 — Architecture-first repository with preserved artifact paths

Status: Proposed repository organization, not organizational architecture approval.

## Decision

Expose architecture, engineering and implementation navigation under `docs/`, keep
Terraform and Ansible execution scopes separately visible at the root, and preserve
the complete `reference/` subtree at its existing paths. Use an indexed catalogue
instead of copying the same Word file into three folders. Existing relative links
continue to address their original files.

Native Terraform paths are deliberately unchanged. Moving them to a new layout would
need module-source, tests, README and historical-tool changes without improving
resource ownership. Ten existing root/module pairs are retained as owned scopes.
New Ansible roles are separate, localhost-only staging/validation work; native
installers and external service owners remain explicitly outside that default path.

Historical `quality/` reports remain available for the unchanged implementation
guide. Active checks write `build/reports/`; a repository snapshot under `evidence/`
records this import's actual results. Historical success never satisfies a new gate.

## Alternatives considered

A folder per increment duplicates active code and invites competing owners. Moving
all binaries immediately breaks cross-document links. Putting all work into one
Terraform module conflates lifecycle and privilege. A new portal/controller is not
needed for repository organization.

## Consequences

Use the artifact catalogue and role indexes to find authoritative files. The frozen
library contains historical generators; they are not CI entrypoints. Native execution
requires actual site decisions and separate acceptance. The next architecture
revision may adopt new artifact paths only through an explicit link migration.
