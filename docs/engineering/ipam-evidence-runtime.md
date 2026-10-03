# Package-owned IPAM allocation evidence

Reviewed 2 October 2026. This B05 continuation moves the exported IPAM allocation
evidence reader into `provisioner.allocations.ipam_evidence` and removes the former
script owner without an alias. It validates retained external-service evidence; it is
not IPAM, does not disclose assigned addresses or prefixes, and cannot reserve, confirm,
release, reuse, write DNS, apply infrastructure or activate service.

## Preserved contract

`portable-hosting-ipam-allocation-index/1` remains unchanged. Allocation, operation,
reservation and request identities, generation, intent digest, family/kind, requested
prefix length, allocation policy, overlap exception, owner roles, lifecycle times,
cleanup evidence and opaque authoritative-system references keep their existing
semantics. Confirmed-allocation digests remain stable across release lifecycle and are
still the exact binding consumed by DNS registration. No existing index is rewritten.

The authoritative IPAM remains external. Repository records deliberately omit actual
allocation values; an opaque reference must not contain an IPv4/IPv6 literal. Missing,
expired, uncertain, quarantined or incompletely cleaned state remains a hold. Release
never implies reuse before all dependent cleanup and the recorded quarantine boundary.

## Installed read boundary

The default index resolves from `hosting_resources.RESOURCE_ROOT`, not the process
working directory. A missing packaged index cannot fall back to a similarly named local
file. Explicit alternate paths are supported only as the caller-selected evidence file.

Index reads require a nonempty regular file no larger than 1 MiB. Final and ancestor
links/junctions, FIFOs/devices, oversize input, observed replacement/change during the
read, duplicate JSON properties, non-finite numbers, malformed encodings and excessive
nesting fail closed. Repository source references are canonical relative POSIX paths to
contained unlinked regular files. These checks assume trusted artifact-directory custody;
they are not a lock against a privileged concurrent filesystem writer.

The reader mutates no file and opens no network connection. It parses a fresh value per
call; returned objects are not a shared cache. The package owner imports no `scripts` or
`tools` module.

## Ownership and deployment

All runtime/preflight/DNS consumers and current CI invocation use the package owner.
`scripts/check_ipam_allocation_records.py` is retired and prohibited; there is no
forwarding module. Installed-wheel tests require the package module, the absence of the
old import, packaged-resource resolution outside the checkout and refusal of a forged
working-directory fallback. Reused build staging cannot preserve the retired script or
bytecode.

Deploy through the normal package release process. This code-owner move does not
reauthorize prior intents, migrate private IPAM state, contact NetBox, establish a live
reservation, change a DNS registration or qualify a native platform. B23 transactional
reservation/IPAM composition and B48 retained-state conversion remain separate work.

## Verification boundary

Regression coverage retains reservation→IPAM→DNS ordering, stable confirmation digests,
uncertain outcomes, release cleanup/quarantine, overlap exceptions and refusal of caller-
supplied allocation values. New boundary tests cover installed ownership, finite regular
files, duplicate/non-finite JSON, links/FIFOs, concurrent observed replacement and exact
repository references. Final-revision CI and deployed owner/service acceptance remain
separate evidence classes.
