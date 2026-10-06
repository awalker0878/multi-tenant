# P03 qualification corrections

The first hosted PostgreSQL/TLS run at `1544c5f` passed 81 cases and failed two. A create retry incorrectly included an irrelevant inherited `If-Match` header in its command fingerprint; creation now excludes that update-only precondition. Laravel appended default route parameters after explicit identifiers; reference update now selects its kind and identity by route name. Both original failures and the source-bound report are retained in [core-first/report.json](core-first/report.json). Requalification is required; this record does not relabel the failed run.
