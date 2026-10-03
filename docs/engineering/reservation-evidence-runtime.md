# Package-owned exported reservation evidence

Reviewed 2 October 2026. Continue B05 from
`73731f7e6432e5adc44e11a89c0b5ddd5f3578e9` under the
[existing B01–B50 plan](../product/enterprise-workload-mobility-execution-plan.md).
This moves an existing read-only contract into the installed package. It does not
implement a live reservation service, allocate capacity or complete B23.

## One implementation, all callers migrated

`provisioner.allocations.reservation_evidence` owns the implementation formerly at
`provisioner/allocations/reservation_evidence.py`. The old module is deleted and prohibited by
the retirement register. Repository access, reservation preflight, IPAM parent-binding
checks, test consumers, generated documentation, implementation metadata and the
existing CI command now use the package owner. There is no forwarding module or
second record representation. Other preflight and allocation owners still require
separate B05 migration.

The supported command is:

```sh
python -m provisioner.allocations.reservation_evidence --as-of 2026-10-02T00:00:00Z
```

The timestamp is an explicit historical inspection example, not an authority grant.
Omit it to inspect at current UTC. Supply `--index` for a separately obtained export.
The default index comes from the installed resource root, never the working directory.
A missing installed index is an error, not permission to load another file with the
same name. The package imports no `tools` or `scripts` module and does not mutate
`sys.path`.

## Preserved evidence and refusal semantics

The contract remains `portable-hosting-reservation-record-index/2`. Valid record
values, canonical digests, owner fields, immutable operation/generation/spec/envelope
bindings and chronological checks retain their existing meaning. HELD, CONSUMED,
RELEASED, EXPIRED and UNCERTAIN are unchanged. An expired HELD record still requires
reconciliation; it does not become available capacity automatically. Uncertain
dependency handoffs remain unresolved, and downstream IPAM must still match the exact
parent reservation and normalized spec.

The committed export remains empty. The reader does not authenticate a file's external
issuer or prove current capacity, even when its format and references are valid.
Trusted export custody, authoritative current reads, concurrent reservations and
native qualification remain separate obligations. All CLI mutation/activation flags
remain false. Historical record bytes and private reservation state are not rewritten.

## Bounded inputs and exact source references

The index must be a nonempty regular file of at most 1 MiB. Reads reject symlink or
junction paths, non-regular files and observed size/time/inode changes. On POSIX,
nonblocking opens allow a FIFO to be rejected without waiting for a writer. Descriptors
are closed on success and refusal. Existing JSON encoding support is retained;
duplicate properties, malformed content, explicit non-finite values and floating-point
overflow are refused. Excessive parser nesting becomes a handled validation failure,
not a command traceback. This is not a hard I/O deadline or a hostile-filesystem sandbox.

Artifact-relative references must retain their exact normalized POSIX spelling and
identify regular files within the selected resource root. Traversal, alias spellings,
linked members, directories and missing references are refused. The selected root is
resolved once; its custody and stability are deployment responsibilities. Existence
checks do not authenticate document contents. Do not silently relabel a retained or
signed record to repair an invalid reference; obtain a corrected export through its
owner and preserve the original evidence.

The filesystem checks do not lock ancestors against concurrent privileged changes,
verify digital signatures or confer owner privileges. Input hardlinks are not rejected
solely for being hardlinks; this is a read-only evidence reader, not private-key custody.

## Installed and regression verification

Boundary tests cover encodings, unchanged digests, every existing record state,
expired holds, duplicate/non-finite JSON, byte limits, deep nesting, missing inputs,
links, FIFOs, path aliases, observed replacement and descriptor cleanup. Existing
reservation, capacity-owner and IPAM/address-owner suites use the new owner directly.

The actual installed-wheel test blocks `scripts` and `tools` imports, executes the
module command outside the checkout, and refuses a forged working-directory fallback
when the packaged index is absent. Reused build staging is seeded with the retired
script and its bytecode; neither may survive in the new wheel. The independent
retirement expectation is advanced with the register, retaining negative reintroduction
tests. Final-commit CI and any unavailable local integrations are reported separately.

No Terraform configuration, provider lock, capability/profile catalog, golden plan,
database schema, native privilege or reservation record format changes. B05, remaining
Wave 2 work and the later provisioning/migration waves stay open.

## Primary implementation references

Consulted 2 October 2026: Python 3.13 [JSON decoding](https://docs.python.org/3.13/library/json.html),
[OS file descriptors](https://docs.python.org/3.13/library/os.html) and
[path handling](https://docs.python.org/3.13/library/pathlib.html). The reader uses
separate duplicate, constant and floating-point checks; JSON decoding alone is not
semantic evidence validation. These references do not qualify deployed file custody
or change the repository's pinned dependencies.
