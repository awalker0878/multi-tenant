# Package-owned implementation input review

Reviewed 3 October 2026. This B05 continuation moves the read-only implementation
input validator from `tools/input_review.py` to
`provisioner.execution.input_review`. The old path is deleted and registered as
retired; live callers and active documentation use the package owner directly and
no forwarding module remains.

The validator still performs offline shape checks only. It validates required and
unexpected Terraform root inputs, primitive types, placeholders, documentation
addresses, logical identifiers, restricted-build opt-in and gateway usability. It
uses the already package-owned route-audit documentation prefixes. It does not read
credentials, allocate addresses, select a site, validate external approvals, contact
a platform, execute Terraform or authorize production.

Installed-package tests require the package module in the wheel and require the old
`tools.input_review` import to be absent. Existing input, route-record and Increment02
regressions exercise the same behavior after relocation. This changes implementation
ownership only; input formats, error codes, address rules and native acceptance are
unchanged.

B05 remains open for mutation/orchestration owners, installed service composition and
retained-state conversion. B23 live reservation/IPAM composition and later native
provisioning/migration gates are unaffected.
