# Contextual commissioning qualification

Engineering source `98e528d4b3ed6d1e6a28c81dcfe7dd2df11a7c9f` passes all
39 component commands and **1,336 tests without skips**: Inventory 165, Planning
327, Lifecycle 372, Lifecycle worker 395 and Inventory worker 77. All five browser
commands and five Chromium journeys pass without retries, failures or skips.
The [index](qualification-index.json) retains the original four archives, including
the first browser failure. Reports preserve their original tested PR merge SHAs.
Their source trees match the permanent published heads recorded in the index;
1,023 component and 251 browser file bindings were checked for each run.

Run `python scripts/p08/verify_commissioning_retained.py` from a full checkout to
recheck archived bytes, original logs, report identities and source bindings.
The [desktop](operator-readiness-desktop.png) and
[mobile](operator-readiness-mobile.png) captures are unchanged synthetic browser
observations and were visually inspected. The separate local Console run passed
208 tests and 980 assertions, with seven pre-existing broker-campaign skips.
Pint, PHPStan, Deptrac, TypeScript/build, clean architecture/documentation checks
and 89 documentation tests also passed locally.

The initial browser check looked for a verified field while another section was
selected after the save remounted the form. The correction selects Operating
targets before testing verification/expiry. Its original failure remains in
[the log](reports/initial-console/browser-failure.log). The final increment also
restricts enrolled producers to explicit tenant/site scopes and rejects shared
producer keys; new denial tests pass. No assertion or admission rule was weakened.

These are E2 checks using real PostgreSQL, TLS and a pinned browser with synthetic
native/owner peers. They establish contextual input/evidence handling, bounded AHV
pagination and conditional same-lease export continuation. They establish no native
platform support, concrete guest/service integration or receiving acceptance.
Existing native blockers remain open. See the
[implementation and remaining prerequisites](../../../docs/implementation/contextual-commissioning.md).
