"""Run a command with the project's .venv interpreter (no shell, argv passthrough).

Quality checks call this wrapper so they stay portable across Windows and Linux and
never fall back to a global interpreter by accident. Fails closed when .venv is missing.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = (ROOT / ".venv" / "Scripts" / "python.exe", ROOT / ".venv" / "bin" / "python")


def main() -> int:
    interpreter = next((path for path in CANDIDATES if path.is_file()), None)
    if interpreter is None or len(sys.argv) < 2:
        print(
            "BLOCKED: project .venv missing or no arguments; run 'uv sync --frozen'",
            file=sys.stderr,
        )
        return 2
    return subprocess.run([str(interpreter), *sys.argv[1:]], cwd=ROOT, check=False).returncode


if __name__ == "__main__":
    sys.exit(main())
