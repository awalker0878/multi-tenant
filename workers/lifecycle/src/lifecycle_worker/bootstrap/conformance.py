"""One bounded observer poll; schedule at intervals below the 30-second record lifetime."""

import argparse
import time
from collections.abc import Sequence
from pathlib import Path

from lifecycle_worker.application.native import NativeHeld, decode
from lifecycle_worker.infrastructure.capability_conformance import ConformancePublisher
from lifecycle_worker.infrastructure.native_files import protected_read


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lifecycle-worker-conformance", allow_abbrev=False)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    config = decode(protected_read(args.config, 2097152))
    if config.get("schema_version") != 1 or not 1 <= len(config["assignments"]) <= 256:
        raise NativeHeld("conformance_configuration_invalid")
    publisher = ConformancePublisher(Path(config["output_file"]), lambda: int(time.time()))
    for assignment in config["assignments"]:
        publisher.publish(assignment)
    return 0
