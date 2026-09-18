# Import or update the local repository

## Documentation-first update

The new ZIP is a complete repository snapshot. Its Markdown chapters, ADRs and source maps are intended for review and a local commit. It contains no `.git` directory and performs no remote changes.

For an already imported checkout, use the companion documentation-update ZIP and its `apply_update.py` helper. Dry-run is the default. The helper compares every changed destination against the previous package hash or the new hash, refuses unexpected collisions/symlinks, and never stages, commits, pushes or deletes files. A pre-existing local edit must be reconciled rather than force-overwritten. It requires a clean worktree so unrelated changes are not mixed into this update.

```sh
# From the extracted documentation-update directory:
python apply_update.py /path/to/your/multi-tenant
python apply_update.py /path/to/your/multi-tenant --copy-reviewed-update

cd /path/to/your/multi-tenant
git switch -c docs/markdown-architecture-and-decisions
python scripts/check_documentation.py
python scripts/check_repository.py
git status --short
git add .
git diff --cached --stat
git diff --cached --check
git commit -m "Convert architecture and engineering sources to Markdown and add decision records"
git push -u origin docs/markdown-architecture-and-decisions
```

For a new empty/initialization checkout, the original procedure below still applies using the **full** repository ZIP. It is deliberately not a general updater.

---

# Import into the private repository

The observed target is `awalker0878/multi-tenant`, private, branch `main`, with only
its initialization README. [The recorded observation](../sources/repository_observation.json)
is a read-only snapshot, not a promise that nobody has changed the repository since.
No commit or push was made while preparing this package.

## Recommended path: clean clone and dry-run copy

Extract the ZIP outside the destination checkout. Its `multi-tenant/` directory is
an import source, not a Git checkout. The helper does not remove any file and refuses
unknown collisions. A new or changed remote repository must be reconciled manually;
it is never force-overwritten. No GitHub token is included or requested by the helper.

```sh
# Use your normal GitHub authentication. This runs on your computer.
git clone git@github.com:awalker0878/multi-tenant.git /path/to/checkout

# Review the import without copying anything.
python /path/to/extracted/multi-tenant/scripts/import_into_checkout.py /path/to/checkout

# This copies working-tree files only; it is NOT a Terraform apply.
python /path/to/extracted/multi-tenant/scripts/import_into_checkout.py /path/to/checkout --apply

cd /path/to/checkout
git switch -c chore/import-hosting-architecture-and-automation
git status --short
git diff -- README.md
```

On Windows, use quoted absolute Windows paths for the helper. Use Linux or WSL2 for
Ansible and the complete protocol/namespace suite. Do not copy over the checkout's
`.git` directory; the ZIP contains no `.git` metadata. Do not use `git clean`, a
force push, or a bulk destructive synchronization to import this release.

## Test and commit

Follow [TESTING.md](TESTING.md). The repository and protocol tests can be run without
Terraform or Ansible. Their engine gates remain failed/blocked until the required
executables and trusted packages are available. A candidate-source commit is not
production approval; the included CI does not deploy infrastructure.

```sh
python scripts/check_repository.py
python tools/check_local.py
python scripts/verify_ansible.py
python tools/verify_terraform.py --mock-tests

git add .
git diff --cached --stat
git diff --cached --check
git commit -m "Organize hosting architecture and add guarded automation validation"
git push -u origin chore/import-hosting-architecture-and-automation
```

Inspect the staged files before committing. The attributes preserve original CSV/reference line endings so Git staging does not invalidate their source hashes. The ignore rules exclude state, plans,
private keys, local input values, live inventories, generated output and credentials;
they are a safeguard, not an exhaustive secret detector. Real provider lockfiles are
not ignored. Obtain and review them from successful connected engine validation.

## Existing work and subsequent imports

The helper requires a clean `main` checkout with the expected origin. It accepts
identical files, new files and replacement of the exact initialization README only.
It refuses edits, other collisions and symlink destinations. Make a separate clean
clone when the working checkout contains changes. Use a reviewed branch/merge for
later increments instead of treating this one-time import helper as a release updater.

Repository branch protection, required checks, reviewers, retention and access are
administrative decisions. This package includes suggested ownership and CI files but
does not claim to configure those repository settings.
