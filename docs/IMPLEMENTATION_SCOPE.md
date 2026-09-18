# Implementation Increment 04 — scope and evidence boundary

## New executed code

- GET-only HTTPS transport with exact origins/paths, strict JSON/framing and bounded reads.
- NSX Local Manager selected-object/configuration and intent-realization observation.
- Nutanix networking/prism v4.3 selected VPC/subnet and known-single-task observation.
- Offline interrupted-change history/binding/freshness and hold-point review.
- Disposable HTTPS scripted native-readback fault campaign and additional regressions.

These are reusable implementation tools tied to existing infrastructure work packages,
not a new hosting application, service API, scheduler or authorization engine.

## Existing capabilities retained

The ten native Terraform module/root pairs are unchanged candidate source. The
Neutron GET-only reader, exact route/plan/input checks, scoped RFC2136 DNS client and
fixed IPv4 routing/mTLS lab retain their documented scopes. All 139 reference files
and 50 Terraform source files remain byte-for-byte unchanged.

The new Nutanix reader does not inspect VM, route or Flow-policy resources. The NSX
reader does not establish complete hierarchy, transport-node enforcement, Global
Manager/project-root variants or packet-path correctness. The existing Neutron
reader is not silently promoted into the new two-platform task-triage profile.

## Not implemented or not executed

No native hosting change, firewall/context selection, state import/unlock, task
cancel/replay, readback-triggered repair, production activation or data deletion was
performed. Native target selection, actual read privileges, expected tokens, full
inventory selection and qualification remain implementation obligations.

Terraform is still unavailable; no engine validation, provider schema, dependency
lock or mock-plan pass is asserted. A retry of the official binary download failed
at runtime DNS resolution. The quality records state that blocker independently
from the passing local code and packet checks.

Hashes and private journals support consistency, not authorizer authenticity or
immutable custody. Record-only fencing does not fence a native writer. Selected
configuration match is not a security certification or operating authorization.
