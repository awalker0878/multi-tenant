# Read-only local checks

These utilities do not connect to infrastructure, apply configuration, allocate resources or authorize operation. They use the Python standard library.

## Package check

From the extracted root:

```console
python 06_Tools/check_package.py
```

This checks the declared release files, hashes, reference fingerprints, document hyperlink/bookmark targets, response tags and catalogue counts. Editing a project copy will deliberately invalidate release hashes. Keep the original release separate from the working project.

## Optional Terraform saved-plan metadata screen

Use only an authorized protected JSON export of an already generated saved plan. The JSON may contain secrets even when normal display output redacts them. The kit does not generate a plan, initialize a provider or execute any apply. Supply a controlled local file:

```console
python 06_Tools/review_tfplan.py protected-plan.json
```

The tool reports deletion/replacement, state-forgetting, moved addresses, unknown values, drift, deferred changes and an explicitly incomplete/errored plan when present. It never includes resource before/after values in output. Resource addresses themselves may still be sensitive. Keep both input and output protected.

Exit 0 means no selected metadata trigger, not approval. Exit 1 means explicit review triggers. Exit 2 means input is unsupported or malformed. A missing resource_changes array is not treated as evidence of an empty plan. The screen does not evaluate topology, policy, provider compatibility, privileges, current evidence or operating authority. Always use the architecture/engineering/implementation review and current actual approval.

## Local synthetic tests

```console
python -m unittest discover -s 06_Tools/tests -v
```

These exercise the offline parser and non-disclosure behaviour using fabricated non-production metadata. They do not execute the inherited infrastructure test procedures.

Source context: https://developer.hashicorp.com/terraform/cli/commands/plan . Source/API compatibility still needs review when using a newer JSON format or new actions.
