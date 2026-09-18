#!/usr/bin/env python3
"""Read-only SHA-256 release check; integrity consistency is not signer trust.

Run before commands that refresh quality reports. Such refreshes intentionally change
recorded hashes. The manifest excludes itself; keep the outer archive's checksum
through an independently trusted delivery channel when provenance matters.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify(root: Path) -> dict:
    root = root.resolve()
    issues = []
    count = 0
    try:
        manifest = json.loads((root / 'sources/release_manifest.json').read_text())
        expected = manifest['file_sha256']
        if not isinstance(expected, dict) or not expected:
            raise ValueError('Nonempty file digest map required')
        for relative, digest in expected.items():
            if not isinstance(relative, str) or not isinstance(digest, str):
                raise ValueError('Invalid manifest entry')
            candidate = root / relative
            path = candidate.resolve()
            if not path.is_relative_to(root) or candidate.is_symlink():
                issues.append({'kind': 'UNSAFE_PATH', 'file': relative})
                continue
            count += 1
            if not path.is_file():
                issues.append({'kind': 'MISSING_FILE', 'file': relative})
            elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                issues.append({'kind': 'DIGEST_MISMATCH', 'file': relative})
    except (KeyError, ValueError, TypeError, OSError):
        issues.append({'kind': 'MANIFEST_UNREADABLE_OR_INVALID'})
    return {
        'status': 'HASHES_MATCH' if not issues else 'FAILED_INTEGRITY_CHECK',
        'files_checked': count,
        'issues': issues,
        'scope': 'Listed release file bytes only; not signature, authorization or infrastructure validation.',
    }


if __name__ == '__main__':
    report = verify(ROOT)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if not report['issues'] else 1)
