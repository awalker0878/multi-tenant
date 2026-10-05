# P02 browser quota-save synchronization

Owner: Console/quality. Package P02.05; requirement R03; criterion G02.04.

The WebKit campaign at `b13996d13db9b54736667a04be23c53f74269424`
completed the bootstrap journey but failed the federation journey because an
uncaught quota request network error remained. The test reloaded immediately
after submitting quota and also checked an already-filled input as evidence of
another completed save. Either check could continue before the request finished.

The campaign now waits for the actual redirected GET response, verifies the
owner-backed returned quota and waits for form processing to finish before
reload or further navigation. Network exceptions are still failures. No retry,
browser exclusion, timeout increase or product authorization change was added.

The [original report](../../verification/p02/identity/run-37371858388/webkit/report.json)
and archive retain the failure. Its 284 source hashes and eight artifact hashes
match the recorded commit and original downloaded bytes. Local discovery of the
corrected two-journey suite passes; hosted execution must establish the correction
independently for each browser. This does not establish a gate or supported
managed-browser floor.
