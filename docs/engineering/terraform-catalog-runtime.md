# Package-owned Terraform catalog and clean build staging

Reviewed 1 October 2026. This B05 continuation starts at
`7438fb375d95188d1258141f06c2940d9e5d9a31` under the
[existing B01–B50 plan](../product/enterprise-workload-mobility-execution-plan.md).
It relocates the actual Terraform catalog reader and closes its source-input bounds.
It does not implement the remaining admitted provisioning workflow or contact a platform.

## One catalog owner

`provisioner.execution.terraform_catalog.entries` owns the implementation previously
at `provisioner/execution/terraform_catalog.py`. The old file is deleted and its path is prohibited
by the retirement register; no import alias, wrapper or alternate index remains.
The existing Terraform preparation tool, engine verifier, repository checker and all
in-tree test consumers use the package implementation directly. This is an internal
read operation, not another command, API, execution service or approval mechanism.

`terraform/catalog.json` remains the single reviewed scope index, with the existing
`hosting-terraform-catalog/1` format. Valid entries retain their exact values and order;
no fixed number of modules is assumed. The delivered catalog, Terraform configurations,
provider locks, profiles and golden plans are unchanged. The native toolchain verifier
now includes the package reader's source digest in its own verification report.

The default root comes from `hosting_resources.RESOURCE_ROOT`, not the working
directory, a mutable import path or an adjacent checkout. Explicit roots are resolved
once. Missing installed files cannot fall back to a similarly named checkout asset.
The reader imports only standard-library modules and the existing package-owned
resource and component declarations; it never imports a legacy tool or script.

## Validated source boundary

The catalog must be a nonempty, closed object with at most 512 entries. Every entry
has the existing six fields. Scope ID, kind, platform and owner scope are bounded
strings; duplicate IDs and unknown platform families or kinds are refused. Platform
names use the existing compiler-family declaration, not another capability registry.
These checks do not establish actual installed support or the catalog author's authority.

Catalog/module/root JSON files must be regular files, at most 1 MiB each, with UTF-8
encoding, no duplicate keys or non-finite numbers. Oversized, truncated or observed
mid-read changes fail instead of returning a partial catalog. Symlinks and junctions
within the selected tree are rejected, including catalog/configuration files and
ancestor directories. POSIX FIFOs are rejected without waiting for a writer.

Module and root paths must be canonical resource-relative POSIX paths below
`terraform/`, never absolute paths, traversal aliases, URL-like values or provider
cache paths. Each root contains one explicit `owned` module call. Its local source
must resolve to the declared module without leaving the Terraform tree or traversing
a linked directory. Provider declarations must be present and equal between the pair.
This validates the ownership relationship, not all Terraform language semantics or
whether a provider/version/feature is supported by an installed environment.

The registered directories must equal the delivered `main.tf.json` directory set.
The scan rejects unreadable or linked source directories and stops after 20,000
source entries; `.terraform` cache directories are excluded, not promoted into
registered writers. These are finite input/scan bounds, not a hard filesystem deadline,
a hostile-filesystem sandbox, a recursive Terraform module-graph validator or a promise
against concurrent replacement by an administrator. Trusted immutable artifact custody
and current source/approval checks remain the execution tools' responsibilities.

## Incremental build and deployment

Setuptools build staging now reconstructs the four existing Python package trees
alongside their reviewed resources. A deleted owner or orphaned bytecode from an earlier
build cannot survive merely because the build directory was reused. This is cleanup
of disposable build output, not an in-place installation upgrade or state importer.
Build destinations equal to or above the source tree, or inside source package/resource
trees, are refused before cleanup. Linked output directories are still refused.

Installed-distribution tests seed a retired source module, legacy bytecode and cached
bytecode into a reused build directory and require their removal. A fresh installed
interpreter blocks both `tools` and `scripts` imports while loading and evaluating the
new catalog from packaged assets. The installed legacy import must be absent. Separate
disposable-source tests prove unsafe build destinations leave input bytes unchanged.

Deploy a newly built artifact through the approved release process. Existing private
plans, source digests, runtime bundles and signed approvals are not relabelled or
reauthorized. No Terraform state address, schema, native resource or retained execution
journal is converted by this Python ownership change. B05's other runtime owners and
B48's actual state inventory/freeze/reconcile/import obligations remain open.

## Verification and remaining work

Catalog tests cover preserved values/order and variable scope counts, malformed JSON,
closed fields, duplicate IDs/paths, local-source and provider mismatch, path aliases,
links, FIFOs, finite budgets, read failures and import ownership. Existing Terraform
preparation/application/recovery and golden-plan tests retain the original contracts.
Final-revision installed/package, engine and repository CI results must be recorded
separately from local test results and missing dependencies.

B05 is not complete: the source integrity/release verifier, capacity/reservation/IPAM/
DNS evidence owners, execution tools and retained-state conversion still have separate
remaining work. B17/B20 deployment/enrichment, B22 fleet scheduling and the admitted
native provisioning/migration waves remain unchanged. No native capability, production
permission or operating acceptance is added by catalog validation or build success.

## Primary references

The Terraform [module-source contract](https://developer.hashicorp.com/terraform/language/modules/sources)
distinguishes local module paths from remote installation sources. This repository's
explicit local-only owned-root rule is narrower than Terraform's general source support;
no toolchain or provider pin is changed. Python's [pathlib](https://docs.python.org/3.13/library/pathlib.html)
and [OS interfaces](https://docs.python.org/3.13/library/os.html) describe path normalization,
link/junction checks, regular-file descriptors and directory traversal. These references
were consulted on 1 October 2026 and do not constitute deployed-platform qualification.
