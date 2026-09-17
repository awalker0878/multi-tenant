# Disabled DNS illustrations

[dns_job.json.example](dns_job.json.example) and [dns_scope.json.example](dns_scope.json.example)
show one A/AAAA record group with explicit before/after values. They are disabled and
contain documentation names, addresses and non-approval references. They intentionally
fail actual-target screening, even if someone toggles the enabled fields alone.

Create actual inputs only from accepted name/address assignments and authorized
management endpoints. The secret is not part of either file. Replace the illustrative
validity with an approved current operation interval. Reuse the operation ID only to
reconcile the same intended operation; a new desired state has a new ID and the exact
previous marker. The record group's member names/types are immutable for its lifetime.

Forward and reverse jobs target distinct zones and are not one transaction. Delete
uses after=null plus the exact previous marker and before values; it retains owner
markers, not permission to reuse a name or address. Read the full
[DNS procedure](../docs/DNS_LIFECYCLE.md) before native use.
