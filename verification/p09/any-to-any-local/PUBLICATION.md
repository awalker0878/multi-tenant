# Publication and original source history

The original README, qualification index and reports remain unchanged. Their
publication status records the time of the local observation. The user subsequently
authorized publication to `awalker0878/multi-tenant` and creation of a pull request.

The GitHub connector publishes a new commit containing the reviewed working tree.
Its commit identity differs from the original local enhancement history because
the connector supplies publication commit metadata. Hosted qualification must bind
that new published revision; the local reports retain their original source
revisions, results and explicit limitations.

`source-history.bundle` preserves the original incremental Git objects from the
audit baseline through the local evidence handoff. `source-history.json` records
the archive SHA-256, prerequisite commit, archived head/tree and original report
source commit/tree pairs. Neither file replaces the original qualification index.

Run `python scripts/p09/verify_any_to_any_retained.py` to verify the archive and
all original source/log/artifact bindings. The checkout must contain the audit
baseline commit, so use a full-history checkout. The verifier checks the bundle
and reads its commits in a temporary bare repository with the checkout's objects
as read-only prerequisites. It does not add objects or change refs in the checkout.
Run `python -m unittest discover -s scripts/p09 -p 'test_retained.py'` for the
publication archive integrity and isolation regression checks.

Archiving a source revision is not a new test run. Publication does not convert
the 146 local database skips into passes or establish installed native E3/E4
qualification. The current handoff and hosted run records carry subsequent status.
