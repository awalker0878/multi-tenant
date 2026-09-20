# Repository release controls

The [ruleset request](../../../config/github-main-ruleset.json) is ready for a
repository administrator to review and install. A committed JSON file does not
enable GitHub settings. At the 2026-09-20 review, `main` was unprotected and the
repository had no rulesets. The connected GitHub operations used for this change
do not expose an administration write operation; remote protections remain open.

## Proposed configuration

The request requires a pull request, one independent current approval, code-owner
review, resolved discussions, and successful `repository`, `terraform`, `ansible`
and `routed-families` checks against the latest base. Check origin is bound to
the GitHub Actions integration (`15368`), observed on this repository's actual
check runs. Force pushes and deletion are restricted. No bypass actor is added.
Merge or rebase preserves the small implementation commits.

Before enabling, assign real review coverage. The current CODEOWNERS file names
only the bootstrap owner; an author cannot independently approve their own PR.
Add an authorized second maintainer/team to the relevant ownership entries and
confirm that someone other than the last pusher can approve. Do not invent a
reviewer or weaken the rule to make a test merge pass.

An authenticated repository administrator can create the reviewed ruleset using:

```sh
gh api --method POST repos/awalker0878/multi-tenant/rulesets \
  --input config/github-main-ruleset.json
```

Inspect the returned rule ID and effective rules for `main`; if a rule already
exists, review/update that exact rule instead of creating duplicates. Test that a
PR with a failed required check cannot merge and that new commits invalidate old
approval. GitHub documents the administrator permissions and request fields in
the [ruleset API](https://docs.github.com/en/rest/repos/rules#create-a-repository-ruleset).

## Release sequence

1. Select an exact candidate commit, review its source and declared service scope,
   and retain that revision's complete CI artifacts. A green expected-HOLD fixture
   verifies rejection behavior; it does not establish production readiness.
2. Review provider/dependency updates against the installed tuple before adopting
   them. Pin the actual native execution image and retain its provenance.
3. Merge the reviewed candidate through the protected branch, inspect both
   post-merge workflows and record the resulting source revision.
4. For a native service release, attach its accepted target/campaign, commissioned
   capacity, recovery/operating readiness and change authority. Keep actual
   inventories, credentials, plans, state and native observations in private
   operator systems. Select durable native evidence retention explicitly.
5. Publish a tag/release only for the verified source and its honest scope. A
   repository engineering milestone may be published as a prerelease without
   implying that an installed hosting service is production-ready.

The repository is public. The root description now reflects that fact; sensitive
operator artifacts remain outside Git. This change does not alter repository
visibility, install runners, enable a ruleset, publish a production release or
grant operating authority.
