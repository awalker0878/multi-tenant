# Package-owned operator artifacts and readback primitives

Reviewed 3 October 2026, continuing B05 from
`32d0f77002a549302ed8149c575bcad64d3b71db`.

| Owner | Installed module | Boundary |
|---|---|---|
| Shared GET-only observation transport/comparison | `provisioner.execution.readback_core` | Bounded responses, exact scope, sanitized status and digests |
| Exact-ID Neutron reader | `provisioner.execution.neutron_observe` | Explicit read-only contact opt-in, pinned HTTPS origin, no redirects or discovery |
| Durable private operator files | `provisioner.execution.run_files` | Existing owner-only files, create-only starts, fsync and immutable digest formats |
| Exact route record reviewer | `provisioner.execution.route_record_review` | Offline field, time, attachment and scope matching; no signer or IPAM authority |

Implementations and consumers moved together. Old paths are prohibited, with no
forwarding modules or working-directory imports. Use `python -m` with the installed
module for commands. Wheel verification exercises these owners with `tools` and
`scripts` imports blocked, from an unrelated directory. Existing loopback readback,
interrupted-operation, file/ledger and route tests retain their original contracts.

No native endpoint is contacted by installation checks. Existing explicit contact
authority remains required for observations; a match grants no activation authority.
This increment changes no retained record, native operation, approval or state schema.
Actual retained-state conversion, distributed ownership, deployed service composition
and native qualification remain separate open obligations.
