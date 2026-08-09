#!/usr/bin/env python3
"""Pre-deploy check for infrastructure/parameters/*.json.

Validates that each parameter file follows the per-environment naming
convention so that deployed resources are reachable by the IAM team policy
(policies/iam-team-policy.json) and by the SAM template defaults.

Convention:
  DynamoDBJobsTable     = emip-jobs-<Environment>
  DynamoDBAnalysisTable = emip-analysis-<Environment>

Exits non-zero on any violation.
"""

import json
import re
import sys
from pathlib import Path

PARAMETERS_DIR = Path(__file__).resolve().parent.parent / "parameters"
ALLOWED_ENVIRONMENTS = {"dev", "staging", "prod"}
BARE_LEGACY = {"emip-jobs", "emip-analysis"}


def check_file(path: Path) -> list[str]:
    problems: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return [f"{path.name}: cannot read JSON: {exc}"]

    params = data.get("Parameters", {})
    env = params.get("Environment")
    if env not in ALLOWED_ENVIRONMENTS:
        problems.append(
            f"{path.name}: Environment must be one of "
            f"{sorted(ALLOWED_ENVIRONMENTS)}, got {env!r}"
        )
        return problems

    jobs = params.get("DynamoDBJobsTable")
    analysis = params.get("DynamoDBAnalysisTable")

    if jobs != f"emip-jobs-{env}":
        problems.append(
            f"{path.name}: DynamoDBJobsTable={jobs!r}, expected "
            f"'emip-jobs-{env}' (bare legacy names like 'emip-jobs' do not exist)"
        )
    if analysis != f"emip-analysis-{env}":
        problems.append(
            f"{path.name}: DynamoDBAnalysisTable={analysis!r}, expected "
            f"'emip-analysis-{env}' (bare legacy names like 'emip-analysis' do not exist)"
        )

    for value in [jobs, analysis]:
        if value in BARE_LEGACY:
            problems.append(f"{path.name}: bare legacy table name {value!r}")

    return problems


def main() -> int:
    files = sorted(PARAMETERS_DIR.glob("*.json"))
    if not files:
        print(f"No parameter files found in {PARAMETERS_DIR}")
        return 1

    all_problems: list[str] = []
    for path in files:
        all_problems.extend(check_file(path))

    for problem in all_problems:
        print(f"  ERROR: {problem}")

    if all_problems:
        print(f"\n{len(all_problems)} parameter problem(s) found — fix before deploying.")
        return 1
    print(f"OK: {len(files)} parameter file(s) follow the per-environment naming convention.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
