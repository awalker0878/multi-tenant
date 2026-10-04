# Actual installed identity before native admission

`provisioner.controlplane.workflow.installed_identity.InstalledApplicationIdentity`
binds the service to the actual accepted application wheel, sealed runtime tree,
running interpreter and current protected source checkout. Configuration supplies
only the original protected runtime-build configuration path. Environment version
labels or supplied digests cannot identify the installation.

The worker may set `HOSTING_APPLICATION_RUNTIME_CONFIG` to that existing private
configuration. The owner reuses the actual `runtime_build` validators to compare
the accepted wheel with the selected source bytes, rehash the sealed installed
files and modes, and check `sys.executable` against the exact
`output/env/bin/python`. Verification creates no installation and repairs no
changed file. Every later operating write admission rechecks the original
configuration and installation.

The concrete operating instance gate must match this source commit and artifact
digest and independently authenticate its actual instance report and operating
handover. Missing installation identity or handover keeps native effects held.
Scoped observation remains available under its own custody gate. Retained-state
conversion handover and native owner epochs are separately checked; accepting an
operating instance cannot clear an imported unknown operation.

`test_installed_identity.py` covers actual protected-configuration drift,
interpreter mismatch, source/receipt mismatch and linked configuration. The
existing hosted offline runtime-build campaign additionally runs this owner with
the actual sealed interpreter and wheel inside an empty network namespace. That
campaign verifies installation behavior. Production commissioning still needs
independent service custody, the selected native estate and signed acceptance of
the final artifact.
