#!/usr/bin/env python3
"""Exercise the actual tools against temporary faults, then restore a clean tree.

This is spike-level tool evidence. It does not assert deployed service isolation.
The PHP source, manifests, and configuration are never relaxed for a failing case.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(arguments, cwd=ROOT, text=True, capture_output=True, check=False)


def require_success(result: subprocess.CompletedProcess[str], label: str) -> None:
    if result.returncode != 0:
        raise AssertionError(f"{label} failed ({result.returncode})\n{result.stdout}\n{result.stderr}")


def source(namespace: str, body: str) -> str:
    return f"<?php\n\ndeclare(strict_types=1);\n\nnamespace {namespace};\n\n{body}\n"


def main() -> None:
    created: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="p00-quality-") as temporary:
        report_path = Path(temporary) / "deptrac.json"

        def write(relative: str, content: str) -> Path:
            path = ROOT / relative
            if path.exists():
                raise AssertionError(f"Refusing to overwrite existing canary path: {path}")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            created.append(path)
            return path

        def deptrac() -> tuple[subprocess.CompletedProcess[str], dict]:
            report_path.unlink(missing_ok=True)
            result = run("php", "vendor/bin/deptrac", "analyse", "--no-cache", "--no-ansi",
                         "--fail-on-uncovered", "--formatter=json", f"--output={report_path}")
            if not report_path.exists():
                raise AssertionError(f"Deptrac produced no JSON report\n{result.stdout}\n{result.stderr}")
            return result, json.loads(report_path.read_text())

        try:
            clean, _ = deptrac()
            require_success(clean, "Unmodified Deptrac baseline")

            # Contract names are parser fixtures, not a claim that generated clients exist.
            legal = write("app/Infrastructure/QualityCanary.php", source("App\\Infrastructure", """final class QualityCanary
{
    public function __construct(public \\Product\\Contracts\\Readiness $contract) {}
}
"""))
            positive, _ = deptrac()
            require_success(positive, "Published contract positive control")
            legal.unlink()

            cases = [
                ("Domain", "Application", "App\\Application\\QualityTarget"),
                ("Domain", "Infrastructure", "App\\Infrastructure\\QualityTarget"),
                ("Domain", "Delivery", "App\\Http\\QualityTarget"),
                ("Application", "Infrastructure", "App\\Infrastructure\\QualityTarget"),
                ("Application", "Delivery", "App\\Http\\QualityTarget"),
                ("Application", "ForeignPrivate", "Product\\Services\\Governance\\PrivateModel"),
                ("Domain", "Transport", "Illuminate\\Http\\Request"),
                ("Application", "Transport", "Illuminate\\Support\\Facades\\Http"),
                ("Domain", "Transport", "Inertia\\Response"),
                ("Application", "Transport", "Inertia\\Response"),
                ("Application", "PublishedContracts", "Product\\Contracts\\Readiness"),
            ]
            for origin, destination, target in cases:
                name = f"App\\{origin}\\QualityCanary"
                fault = write(f"app/{origin}/QualityCanary.php", source(f"App\\{origin}", f"""final class QualityCanary
{{
    public function __construct(public \\{target} $dependency) {{}}
}}
"""))
                result, report = deptrac()
                expected = f"{name} must not depend on {target} ({origin} on {destination})"
                messages = [entry["message"] for file in report["files"].values()
                            for entry in file["messages"]]
                summary = report["Report"]
                if (result.returncode != 1 or not messages or
                        any(message != expected for message in messages) or
                        summary["Violations"] != len(messages) or
                        any(summary.get(key, 0) for key in ["Skipped violations", "Uncovered", "Warnings", "Errors"])):
                    raise AssertionError(f"Wrong failure for {origin} -> {destination}: {report}\n{result.stderr}")
                fault.unlink()
                print(f"PASS Deptrac canary: {origin} -> {destination}")

            bad_type = write("app/Domain/QualityCanary.php", source("App\\Domain", """final class QualityCanary
{
    public function count(): int
    {
        return 'not-an-integer';
    }
}
"""))
            result = run("php", "vendor/bin/phpstan", "analyse", "--no-progress", "--error-format=json", str(bad_type))
            report = json.loads(result.stdout)
            messages = [message for file in report["files"].values() for message in file["messages"]]
            if result.returncode != 1 or len(messages) != 1 or messages[0].get("identifier") != "return.type":
                raise AssertionError(f"Wrong PHPStan negative control failure: {report}\n{result.stderr}")
            bad_type.unlink()
            print("PASS PHPStan canary: return.type")

            bad_format = write("app/Domain/QualityCanary.php", "<?php namespace App\\Domain;final class QualityCanary{public function count():int{return 1;}}\n")
            result = run("php", "vendor/bin/pint", "--test", str(bad_format), "--format=json")
            if result.returncode != 1 or "QualityCanary.php" not in result.stdout:
                raise AssertionError(f"Wrong Pint formatting failure\n{result.stdout}\n{result.stderr}")
            require_success(run("php", "vendor/bin/pint", str(bad_format)), "Pint canary repair")
            require_success(run("php", "vendor/bin/pint", "--test", str(bad_format)), "Pint repaired positive control")
            bad_format.unlink()
            print("PASS Pint canary: formatting fault and repaired positive control")

            private_action = write("app/Application/Quality/Actions/QualityCanary.php", source("App\\Application\\Quality\\Actions", """final class QualityCanary
{
    private function handle(): void {}
}
"""))
            result = run("php", "vendor/bin/pest", "tests/Architecture/PragmaticBoundariesTest.php", "--filter=actions expose", "--colors=never")
            if result.returncode != 1 or "Action handle must be public: App\\Application\\Quality\\Actions\\QualityCanary" not in result.stdout:
                raise AssertionError(f"Wrong Action visibility failure\n{result.stdout}\n{result.stderr}")
            private_action.unlink()
            print("PASS Pest canary: private Action handle")

            clean, _ = deptrac()
            require_success(clean, "Restored Deptrac baseline")
            require_success(run("php", "vendor/bin/pest", "tests/Architecture", "--colors=never"), "Restored Pest architecture baseline")
            print(f"PASS: {len(cases)} dependency faults, 1 type fault, 1 formatting fault, 1 Action visibility fault; source restored")
        finally:
            for path in created:
                path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
