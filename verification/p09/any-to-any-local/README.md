# P09-A local engineering evidence

The approved audit baseline is `eda64354816b4884530118f6595c037a5a556807`.
Component source is `b0bc25c7bf6ed2400a26c72485ed4823a9fe3620`;
final browser source is `d676cdfe9a224c6d8c290bad9a477035713f71ad`.
Each report binds its original source files and command logs. Later documentation
and evidence commits do not retroactively change these observed revisions.

| Component | Passed | Database skips |
| --- | ---: | ---: |
| Inventory | 142 | 46 |
| Planning | 359 | 6 |
| Lifecycle | 358 | 67 |
| Inventory worker | 95 | 0 |
| Lifecycle worker | 683 | 27 |
| Total | 1,637 | 146 |

All five Ruff, formatting, strict type and wheel-build checks pass. The final
compiled Console campaign passes all nine browser journeys without skips or
retries using Chromium 153.0.8010.0 and the locked Playwright client. This local
browser substitution is explicit; the pinned CI browser remains unverified.
The source tree also passes architecture validation, 89 documentation tests and
91 build/selection tooling tests.

The contracts campaign records 270 Planning-to-Lifecycle direction/method/mode
scenarios, 3,348 stage boundaries, 1,080 missing/bad qualification denials and
720 partial acceptance denials. Another 126 typed data-owner method operations
validate against the wire/runtime contract. These are synthetic E2 controls, not
native platform qualification.

Original failed browser attempts are retained: `browser-launch-failure` used an
unavailable default browser executable; `browser-alert-ambiguity` exposed an
ambiguous alert test locator. The corrected test deterministically verifies both
controls stay disabled while an outcome is uncertain. Browser output includes
retained trace artifacts; command logs and the reported result identify each run.
Transient unbound Playwright caches are excluded from this evidence package.

PostgreSQL binaries were obtained locally, but the fixture failed while attempting
`os.chown(private, 65534, 65534)` with `OSError: [Errno 22] Invalid argument`.
This workspace cannot create the required unprivileged process identity. The
146 database skips are **not passes**. PHP 8.5 is unavailable, so Console PHP and
full hosted/runtime gates remain unverified. GitHub publication was rejected by
automatic approval review pending explicit destination authorization.

No installed platform, guest image, sealed conversion appliance, application or
storage owner implementation, native E3 direction, operating gate or receiving E4
is established by these results. The phase is not fully closed.

Run `python scripts/p09/verify_any_to_any_retained.py` from the repository to check
historical source blobs, report/log/artifact hashes, pass counts and explicit skips.
