#!/usr/bin/env python3
"""Compatibility command for the canonical assurance-index builder.

No alternate 370-row allocation or verification-family format is generated. The
540-row implementation_assertions record and original procedure sources remain
owned by the maintained builder. Historical proposal records are never overwritten.
"""
import json
from build_assurance_indexes import ROOT, build

if __name__=='__main__':
    print(json.dumps(build(ROOT), indent=2))
