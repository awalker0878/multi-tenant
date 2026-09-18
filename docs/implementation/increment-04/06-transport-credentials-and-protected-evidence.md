# Transport, credentials and protected evidence

[Documentation home](../../README.md) · [Source document](../../../Implementation_Execution_Guide.docx) · [Chapter index](README.md)

> **Source:** IMP04 — Implementation Increment 04. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 9ca5c85333dcb51137ca694aea7b034e393fa8927831f0b475b3b88e842418f7 -->
<a id="chapter_6"></a>

[Contents and release status](01-implementation-increment-04.md#chapter_1)

The new clients perform only enumerated HTTPS GETs. The caller supplies an exact expected origin; the transport accepts only generated resource/status paths. It does not follow redirects or response links, use environment proxies, discover resources, refresh credentials or issue native mutations.


<a id="source-table-66"></a>

| Protection | Implemented behavior / remaining prerequisite |
| --- | --- |
| Server trust and credentials | Verified certificate/hostname, strict SSL context, no ambient TLS keylogging. Scoped Basic credentials injected through NSXT\_\* or NUTANIX\_\* environment variables. |
| Response validation | HTTP 200 JSON object only; duplicate keys/nonfinite numbers, malformed framing, unsupported encoding, oversized/truncated bodies and ambiguous ETags are rejected. |
| Bounded collection | Default 20-resource limit, 3 rounds, 5-second socket timeout, 60-second cooperative budget, 400-GET ceiling and 2 MiB body limit. These are tool bounds, not service guarantees. |
| Timeout limitation | Response reads use remaining budget on the live TLS socket. OS hostname resolution is not forcibly interrupted; native execution needs an external deadline and accepted DNS. |
| Private journal | New exclusive non-symlink file, mode 0600; incomplete record before contact, flush/fsync on write. Parent directory and durable evidence custody remain external. |
| Data minimization | Safe error codes and selected-state hashes; no raw credential/service exception text echoed. Hashes are not signatures or immutable retention. |

## No-contact checks and explicit read-only contact

```text
python tools/nsx_observe.py examples/nsx_observation.json.example
python tools/nutanix_observe.py examples/nutanix_observation.json.example
python tools/nsx_observe.py /secure/nsx-expected.json \
  --read-authorized-target --expected-origin https://nsx.site.invalid \
  --ca-file /secure/approved-ca.pem --output /secure/new-readback.json
```

The .invalid endpoint is intentionally unusable. Actual reads require an enabled accepted manifest, matching real origin and injected credentials. NSXT\_USERNAME/NSXT\_PASSWORD and NUTANIX\_USERNAME/NUTANIX\_PASSWORD are variable names, not values to paste in chat or source. No-contact validation and matching readback can both exit 0; neither authorizes a change.

[Previous chapter](05-interrupted-change-decision-procedure.md) · [Chapter index](README.md) · [Next chapter](07-local-execution-and-observed-results.md)
