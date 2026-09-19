# Qualification campaign evidence assurance

**Purpose:** validate the exported evidence packet produced by an externally authorized native qualification campaign without running the campaign, issuing the qualification decision, or granting production authority.

The repository now records the actual target separately from native qualification. Between those two points, the source procedures require a governed campaign that preserves applicability, every material attempt, healthy positive controls for negative observations, artifact provenance, evidence freshness, defects and residual gaps. This gate makes that evidence boundary machine-checkable while keeping the independent qualification decision outside CI.

## Source obligations

- QCP §1 binds qualification to a named service, topology, version, address-family and failure scope.
- QCP §6 requires evidence to match target, scope, time and observation method, with protected artifact identity and an explicit disposition.
- QCP §8 requires retained defects/retests, remaining limits and a separately controlled qualification decision.
- QUAL §5 requires exact component/API/provider releases, topology, applicable assertions, preconditions, observed results, artifacts and reviewer identity; not-run or unknown outcomes cannot satisfy a mandatory service promise.
- ADR-0017 separates reference adoption, technical qualification and production authorization.

## Active evidence index

The active index is \`sources/capabilities/qualification_campaign_evidence_index.json\` and is intentionally empty.

Every active record must bind to one reviewed target-selection record for the same:

- selection ID;
- site and cell;
- restricted campaign scope;
- platform family; and
- exact product-tuple ID.

The packet also carries the exact authorization references selected for the native campaign: change/contact/stop authority, qualification-campaign identity, native API/observer/writer scopes, credential custody, evidence workspace, data restrictions, permitted/prohibited operations, cleanup and contact-window reference. Those references must match the target-selection record, and the governed evidence workspace must equal the authorized workspace.

A campaign packet cannot float free of the target or the restricted authority under which its observations were made.

## Contact-window semantics

Target-contact authority controls **new target interaction**, not the historical validity of observations already collected under that authority. A completed evidence packet may therefore remain current after the contact window expires when:

- the target selection itself remains reviewed and has no open/uncertain scope gap;
- the packet records an authorized contact expiry no later than the target-selection expiry;
- the campaign began after the target selection became effective; and
- every native attempt occurred on or before the recorded authorized expiry.

A target-selection state of `CONTACT_AUTHORITY_DUE` can support retained campaign evidence under those conditions, but it still grants **no permission to reconnect, retrieve credentials, rerun tests or refresh evidence**. `REVIEW_DUE`, `GAPS_OPEN` and `UNCERTAIN` target selections cannot support a current campaign packet.

## Campaign scope and applicability

The scope additionally records the service scope, topology generation, offered address families, failure scope, campaign start and review date.

\`required_assertions\` lists the assertions that the adopted campaign says must be addressed. An assertion may be excluded only through an explicit \`not_applicable\` record carrying a controlled decision, rationale, reviewer and review date. Absence of an attempt is not silently converted to not-applicable.

The gate does not decide what assertions are mandatory. That remains a design/assurance decision made before the campaign.

## Retain attempts instead of overwriting history

Each attempt records:

- a unique attempt ID and assertion ID;
- procedure and variant references;
- observation class;
- result: \`PASSED\`, \`FAILED\`, \`BLOCKED\` or \`NOT_RUN\`;
- the healthy positive-control attempt when required;
- controlled evidence reference and SHA-256;
- observation and freshness timestamps; and
- reviewer reference.

Multiple attempts for one assertion are expected. Earlier failed or blocked attempts remain in history; the latest attempt determines current mechanical coverage. A later pass does not erase the earlier result.

For \`NEGATIVE_CONTROL\`, the packet must explicitly reference a retained \`PASSED\` \`POSITIVE_CONTROL\` attempt that was still healthy when the negative observation ran. A timeout without that control cannot be promoted into a security success by this gate.

## Evidence freshness and residual gaps

\`CURRENT_EVIDENCE_COMPLETE\` requires:

- a current matching target selection;
- all required assertions either covered by a current latest \`PASSED\` attempt or explicitly reviewed not-applicable;
- no stale latest passing evidence;
- no due campaign/applicability/gap review; and
- no \`OPEN\` residual gaps.

Other states are:

- \`REVIEW_DUE\` — evidence, applicability or campaign review is due and no open gap is being represented as closed;
- \`GAPS_OPEN\` — current review exists but at least one residual gap remains open;
- \`UNCERTAIN\` — authoritative scope, provenance, attempt or review state requires reconciliation.

The checker retains evidence references and hashes but does not prove that a controlled evidence store, collector identity, signature or custody process is authentic. Those remain review obligations.

## Readiness preflight

\`scripts/check_qualification_campaign_readiness.py\` evaluates one exact campaign packet.

A successful result is:

\`QUALIFICATION_CAMPAIGN_EVIDENCE_CURRENT_DECISION_NOT_ISSUED\`

That means only that the exported packet is mechanically current and review-ready. It still keeps all of the following false:

- target contact;
- credential retrieval;
- native test execution;
- qualification decision issuance;
- publication of a native-qualified platform profile/capability;
- infrastructure apply; and
- production activation.

Current repository state remains held because no actual native campaign evidence has been exported:

\`\`\`sh
python scripts/check_qualification_campaign_readiness.py examples/qualification_campaign_readiness_intent.json.example --as-of 2026-09-19T16:30:00Z --expected-status HOLD_NO_CURRENT_QUALIFICATION_CAMPAIGN_EVIDENCE
\`\`\`

## Relationship to PlatformProfile qualification

A current evidence packet is input to an accountable independent qualification review. It does **not** write \`sources/capabilities/qualification_index.json\`, change the platform capability registry to \`NATIVE_QUALIFIED\`, satisfy site/capacity/operational acceptance, or authorize G3 production activation.

If the independent authority accepts a scope, the separately governed PlatformProfile qualification dossier records that decision, tested limits, evidence set, owners, validity and exclusions. The dossier validator now cross-checks every native evidence reference, digest and observation time against current latest-passing evidence from this gate, and it refuses to extend evidence validity beyond the campaign freshness window. If evidence is incomplete, stale, failed, blocked or uncertain, the campaign remains held rather than manufacturing a qualified state.

[Native campaign procedure](../implementation/native-reference/campaign.md) · [QCP §6 evidence packet](../assurance/qualification-campaign/6-build-an-evidence-packet-a-reviewer-can-challenge.md) · [QCP §8 disposition](../assurance/qualification-campaign/8-close-defects-and-issue-a-scoped-campaign-disposition.md) · [PlatformProfile qualification](platform-native-qualification.md)
