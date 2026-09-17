# Security and contribution boundaries

This is a private engineering workspace, not a store for actual secrets or classified
configuration. Keep credential files, accepted native input manifests, state, raw
plans and live observations in approved external storage. Use opaque evidence
references in source and sanitize any approved evidence export.

Automatic CI uses GitHub-hosted ephemeral runners, `contents: read`, no platform
secrets, no OIDC grant and no deployment environment. No job applies Terraform,
runs a DNS update, or enables native readback. Packet tests are manual-only and use
the fixed disconnected lab. Do not run untrusted pull-request code on a privileged
self-hosted runner.

CODEOWNERS is only a bootstrap owner map. Configure branch protection / rulesets,
required reviews and status checks separately. They are not configured by this ZIP.

The static repository scanner catches common high-confidence key/token/state
mistakes, not every possible secret or sensitive document. Human review remains
necessary. Report suspected credential exposure privately; revoke the credential
through its owner and remove it from history using an approved procedure.
