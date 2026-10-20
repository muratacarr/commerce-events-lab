"""Run configured checks and require security evidence for this exact tree."""

import runpy
import sys
from pathlib import Path

try:
    runtime = Path(__file__).resolve().parents[1] / ".claude/hooks/security_gate.py"
    sys.argv = [str(runtime), "quality"]
    runpy.run_path(str(runtime), run_name="__main__")
except Exception:
    print("BLOCKED: quality runtime unavailable; no completion evidence", file=sys.stderr)
    sys.exit(2)
