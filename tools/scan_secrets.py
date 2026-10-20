"""Fail when detect-secrets finds a candidate secret in the working tree.

Run through tools/venv_run.py. Prints only file paths, line numbers and detector names,
never secret values. Lock files hold package hashes and are excluded from entropy scans.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE = (
    r"(^|[\\/])(\.git|\.venv|__pycache__|\.engineering-os-review)[\\/]"
    r"|(^|[\\/])(uv\.lock|requirements(-dev)?\.lock)$"
)


def main() -> int:
    completed = subprocess.run(
        [sys.executable, "-m", "detect_secrets", "scan", "--all-files", "--exclude-files", EXCLUDE],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        print("BLOCKED: detect-secrets failed to run", file=sys.stderr)
        return 2
    results = json.loads(completed.stdout).get("results", {})
    for name, hits in sorted(results.items()):
        for hit in hits:
            print(f"potential secret: {name}:{hit['line_number']} ({hit['type']})", file=sys.stderr)
    return 1 if results else 0


if __name__ == "__main__":
    sys.exit(main())
