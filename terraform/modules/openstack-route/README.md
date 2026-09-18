# openstack-route — exact native IPv4 route

Candidate source using `openstack_networking_router_route_v2`. One invocation owns one route, **not** the
gateway, interface, external attachment, route table, firewall or data.

## Preconditions
The isolated target context and directly reachable attachment already exist and
have accepted path/return-path evidence. The route owner is the single writer for
this target's extra routes. Parent/interface removal is blocked until dependants
are retired. Never combine an aggregate route owner with competing route resources.

`prevent_destroy` deliberately blocks replacements/removal until a separately
reviewed retirement change handles dependencies. In particular OpenStack next-hop
changes replace this resource. Do not work around this with an unreviewed destroy.

Run the original input screen **and** `tools/route_record_review.py` against the
actual engineering route record before planning. A matching record is not signature
verification or permission to apply. No default route, tenant exposure or allow
policy is installed. A complete network remains unavailable until independently
owned attachments and controls are accepted. The Increment01 quarantine remains.

## Validation status
Native engine/provider and mocked-plan qualification are not run in this runtime.
The tagged primary-source resource interface was reviewed. Shipped examples are
disabled documentation values, not accepted allocations or approvals.
