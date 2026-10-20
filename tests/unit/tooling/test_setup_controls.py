"""Static checks of the committed setup controls and helper tools."""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.tooling

REPO = Path(__file__).resolve().parents[3]
HOOK_EVENTS = {
    "SessionStart",
    "PreToolUse",
    "PostToolUse",
    "PostToolUseFailure",
    "SubagentStart",
    "SubagentStop",
    "TaskCompleted",
    "Stop",
}
BLOCKING = {"SessionStart", "PreToolUse", "PostToolUse", "PostToolUseFailure", "SubagentStart"}


def test_gitignore_keeps_required_lines() -> None:
    lines = (REPO / ".gitignore").read_text("utf-8").splitlines()
    for required in (
        "/docs/interview/",
        "/.engineering-os-review/",
        ".env",
        ".env.*",
        "!.env.example",
        ".venv/",
    ):
        assert required in lines


def test_security_reviewer_is_read_only() -> None:
    text = (REPO / ".claude" / "agents" / "security-reviewer.md").read_text("utf-8")
    front = text.split("---")[1]
    assert re.search(r"^name: security-reviewer$", front, re.M)
    assert re.search(r"^tools: Read, Glob, Grep$", front, re.M)
    assert not re.search(
        r"Write|Edit|Bash|PowerShell|Agent", re.search(r"^tools:.*$", front, re.M).group(0)
    )  # type: ignore[union-attr]


def test_skills_have_frontmatter() -> None:
    for name in ("tdd", "interview-prep"):
        text = (REPO / ".claude" / "skills" / name / "SKILL.md").read_text("utf-8")
        assert text.startswith("---\n") and f"name: {name}\n" in text and "description:" in text


def test_every_rule_file_is_present_and_unscoped_or_matching_layout() -> None:
    for name in ("core", "fastapi", "postgresql", "web", "project-research"):
        text = (REPO / ".claude" / "rules" / f"{name}.md").read_text("utf-8")
        assert not text.startswith("---"), (
            f"{name}: scoped rules stay off until loading is verified"
        )


def test_quality_config_is_real_and_complete() -> None:
    config = json.loads((REPO / ".engineering-os-quality.json").read_text("utf-8"))
    assert config["configured"] is True
    assert {c["category"] for c in config["checks"]} == {
        "tests",
        "build",
        "static",
        "secrets",
        "dependencies",
    }
    for check in config["checks"]:
        assert isinstance(check["command"], list) and all(
            isinstance(a, str) and a for a in check["command"]
        )


def test_cache_dirs_stay_outside_the_review_snapshot() -> None:
    text = (REPO / "pyproject.toml").read_text("utf-8")
    for tool in ("pytest", "ruff", "mypy"):
        assert (
            f'cache_dir = ".venv/cache/{tool}"' in text
            or f'cache-dir = ".venv/cache/{tool}"' in text
        )


def test_settings_wire_every_hook_with_fixed_wrapper() -> None:
    settings = json.loads((REPO / ".claude" / "settings.json").read_text("utf-8"))
    assert set(settings["hooks"]) == HOOK_EVENTS
    for event, groups in settings["hooks"].items():
        for group in groups:
            for hook in group["hooks"]:
                assert hook["type"] == "command" and hook["command"] == "python"
                assert hook["args"][-2].endswith("/.claude/hooks/security_gate.py")
                assert hook["args"][-1] == "hook"
                assert ("onFailure" in hook) == (event in BLOCKING)
                assert hook.get("onFailure", "block") == "block"
    for event in ("SubagentStart", "SubagentStop"):
        assert settings["hooks"][event][0]["matcher"] == "security-reviewer"


def test_settings_protect_gate_paths_and_secrets() -> None:
    deny = json.loads((REPO / ".claude" / "settings.json").read_text("utf-8"))["permissions"][
        "deny"
    ]
    for path in (
        ".engineering-os-review/**",
        ".claude/hooks/**",
        ".claude/settings.json",
        ".claude/agents/security-reviewer.md",
        ".engineering-os-quality.json",
        "CLAUDE.md",
        "tools/quality_gate.py",
    ):
        # Claude Code 2.1.304 rejects Write(path) rows; Edit(path) rows cover every file-editing
        # tool (see docs/SECURITY_WORKFLOW.md deviation 2). Write rows must stay absent.
        assert f"Edit(./{path})" in deny
        assert f"Write(./{path})" not in deny
    for secret in ("Read(./.env)", "Read(./.env.*)", "Read(./**/*.pem)", "Read(./**/*.key)"):
        assert secret in deny


def test_venv_run_fails_closed_without_venv(tmp_path: Path) -> None:
    (tmp_path / "tools").mkdir()
    shutil.copy(REPO / "tools" / "venv_run.py", tmp_path / "tools")
    result = subprocess.run(
        [sys.executable, str(tmp_path / "tools" / "venv_run.py"), "-c", "pass"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 2


def test_secret_scanner_has_positive_and_negative_control(tmp_path: Path) -> None:
    (tmp_path / "tools").mkdir()
    shutil.copy(REPO / "tools" / "scan_secrets.py", tmp_path / "tools")
    scan = [sys.executable, str(tmp_path / "tools" / "scan_secrets.py")]
    (tmp_path / "clean.py").write_text("value = 1\n", encoding="utf-8")
    clean = subprocess.run(
        scan, cwd=tmp_path, capture_output=True, text=True, timeout=120, check=False
    )
    assert clean.returncode == 0, clean.stderr
    token = "AKIA" + "IOSFODNN7EXAMPLQ"
    (tmp_path / "leak.py").write_text(f'aws_access_key_id = "{token}"\n', encoding="utf-8")
    leak = subprocess.run(
        scan, cwd=tmp_path, capture_output=True, text=True, timeout=120, check=False
    )
    assert leak.returncode == 1
    assert "leak.py" in leak.stderr and token not in leak.stderr + leak.stdout
