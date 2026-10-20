"""Logic tests for the review/quality gate, driven through its real command interface.

These run the actual hook script against a disposable copy of the project skeleton with
synthetic hook events. They prove the gate logic only; they do NOT prove that Claude Code
delivers these events (that needs a live session, see docs/SETUP_VERIFICATION.md).
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.tooling

REPO = Path(__file__).resolve().parents[3]
SESSION = "session-1"


class Project:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.gate = root / ".claude" / "hooks" / "security_gate.py"

    def run(self, *args: str, stdin: str = "") -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.gate), *args],
            cwd=self.root,
            input=stdin,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    def event(self, name: str, **extra: object) -> subprocess.CompletedProcess[str]:
        payload = {"session_id": SESSION, "cwd": str(self.root), "hook_event_name": name, **extra}
        return self.run("hook", stdin=json.dumps(payload))

    def state(self) -> dict[str, object]:
        return json.loads(
            (self.root / ".engineering-os-review" / "current.json").read_text("utf-8")
        )

    def write(self, name: str, text: str = "x\n") -> None:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def configure(self, *checks: tuple[str, str, list[str]]) -> None:
        config = {
            "schema": 1,
            "configured": True,
            "checks": [{"name": n, "category": c, "command": argv} for n, c, argv in checks],
        }
        (self.root / ".engineering-os-quality.json").write_text(
            json.dumps(config), encoding="utf-8"
        )

    def review(
        self,
        status: str = "PASS",
        findings: list[dict[str, str]] | None = None,
        change_id: str | None = None,
        agent: str = "agent-1",
    ) -> subprocess.CompletedProcess[str]:
        """Run SubagentStart + SubagentStop for the current change and return the Stop result."""
        start = self.event("SubagentStart", agent_type="security-reviewer", agent_id=agent)
        assert start.returncode == 0, start.stderr
        report = {
            "change_id": change_id or self.state()["change_id"],
            "status": status,
            "summary": "synthetic review",
            "findings": findings or [],
            "evidence": ["read files"],
        }
        return self.event(
            "SubagentStop",
            agent_type="security-reviewer",
            agent_id=agent,
            last_assistant_message=json.dumps(report),
        )


PASSING = ("tests", "tests", [sys.executable, "-c", "pass"])


def full_checks() -> list[tuple[str, str, list[str]]]:
    return [
        (c, c, [sys.executable, "-c", "pass"])
        for c in ("tests", "build", "static", "secrets", "dependencies")
    ]


@pytest.fixture
def project(tmp_path: Path) -> Project:
    (tmp_path / ".claude" / "hooks").mkdir(parents=True)
    (tmp_path / "tools").mkdir()
    shutil.copy(REPO / ".claude" / "hooks" / "security_gate.py", tmp_path / ".claude" / "hooks")
    shutil.copy(REPO / "tools" / "quality_gate.py", tmp_path / "tools")
    (tmp_path / "app.py").write_text("print('hi')\n", encoding="utf-8")
    p = Project(tmp_path)
    p.configure(*full_checks())
    assert p.event("SessionStart").returncode == 0
    return p


def test_mutation_blocked_while_review_pending(project: Project) -> None:
    result = project.event("PreToolUse", tool_name="Write", tool_input={"file_path": "a.py"})
    assert result.returncode == 2


def test_reads_and_reviewer_and_report_allowed_while_pending(project: Project) -> None:
    for tool, args in [
        ("Read", {}),
        ("Grep", {}),
        ("Agent", {"subagent_type": "security-reviewer"}),
        ("Bash", {"command": "python tools/quality_gate.py"}),
    ]:
        assert project.event("PreToolUse", tool_name=tool, tool_input=args).returncode == 0, tool


def test_arbitrary_shell_blocked_while_pending(project: Project) -> None:
    result = project.event("PreToolUse", tool_name="Bash", tool_input={"command": "echo hi > x.py"})
    assert result.returncode == 2


def test_pass_review_unlocks_edits_and_new_change_relocks(project: Project) -> None:
    assert project.review("PASS").returncode == 0
    assert project.state()["status"] == "PASS"
    assert project.event("PreToolUse", tool_name="Write", tool_input={}).returncode == 0
    project.write("app.py", "print('changed')\n")
    assert project.event("PostToolUse", tool_name="Write").returncode == 0
    assert project.state()["status"] == "PENDING"
    assert project.event("PreToolUse", tool_name="Write", tool_input={}).returncode == 2


def test_shell_generated_change_is_detected(project: Project) -> None:
    project.write("generated/new_file.py")
    project.event("PostToolUse", tool_name="Bash")
    state = project.state()
    assert state["status"] == "PENDING"
    assert "generated/new_file.py" in state["changes"]  # type: ignore[operator]


def test_fail_review_permits_remediation_but_blocks_completion(project: Project) -> None:
    finding = {
        "severity": "HIGH",
        "location": "app.py:1",
        "threat": "t",
        "remediation": "r",
        "standard": "NOT_AVAILABLE",
    }
    assert project.review("FAIL", [finding]).returncode == 0
    assert project.state()["status"] == "FAIL"
    assert project.event("PreToolUse", tool_name="Edit", tool_input={}).returncode == 0
    assert project.event("Stop").returncode == 2


def test_not_verified_review_blocks_stop_and_edits(project: Project) -> None:
    assert project.review("NOT_VERIFIED").returncode == 0
    assert project.event("Stop").returncode == 2
    assert project.event("PreToolUse", tool_name="Write", tool_input={}).returncode == 2


@pytest.mark.parametrize("message", ["not json", "{}", json.dumps({"status": "PASS"})])
def test_malformed_reviewer_output_is_not_a_pass(project: Project, message: str) -> None:
    project.event("SubagentStart", agent_type="security-reviewer", agent_id="agent-1")
    result = project.event(
        "SubagentStop",
        agent_type="security-reviewer",
        agent_id="agent-1",
        last_assistant_message=message,
    )
    assert result.returncode in (0, 2)
    assert project.state()["status"] != "PASS"
    assert project.event("Stop").returncode == 2


def test_stale_change_id_is_rejected(project: Project) -> None:
    result = project.review("PASS", change_id="0" * 64)
    assert "NOT_VERIFIED" in result.stdout
    assert project.state()["status"] == "NOT_VERIFIED"


def test_pass_with_medium_finding_is_rejected(project: Project) -> None:
    finding = {
        "severity": "MEDIUM",
        "location": "a",
        "threat": "t",
        "remediation": "r",
        "standard": "X",
    }
    project.review("PASS", [finding])
    assert project.state()["status"] == "NOT_VERIFIED"


def test_review_without_start_binding_is_rejected(project: Project) -> None:
    report = {
        "change_id": project.state()["change_id"],
        "status": "PASS",
        "summary": "s",
        "findings": [],
        "evidence": ["e"],
    }
    project.event(
        "SubagentStop",
        agent_type="security-reviewer",
        agent_id="ghost",
        last_assistant_message=json.dumps(report),
    )
    assert project.state()["status"] == "NOT_VERIFIED"


def test_second_concurrent_reviewer_is_blocked(project: Project) -> None:
    assert (
        project.event("SubagentStart", agent_type="security-reviewer", agent_id="a").returncode == 0
    )
    assert (
        project.event("SubagentStart", agent_type="security-reviewer", agent_id="b").returncode == 2
    )


def test_stop_and_task_completed_without_review_fail_closed(project: Project) -> None:
    assert project.event("Stop").returncode == 2
    assert project.event("TaskCompleted").returncode == 2
    done = project.event("PreToolUse", tool_name="TaskUpdate", tool_input={"status": "completed"})
    assert done.returncode == 2


def test_completion_requires_quality_evidence_even_after_pass(project: Project) -> None:
    project.review("PASS")
    assert project.event("Stop").returncode == 2
    quality = project.run("quality")
    assert quality.returncode == 0, quality.stderr
    assert project.event("Stop").returncode == 0
    assert project.event("TaskCompleted").returncode == 0


def test_change_after_quality_pass_invalidates_evidence(project: Project) -> None:
    project.review("PASS")
    assert project.run("quality").returncode == 0
    project.write("app.py", "print('late edit')\n")
    assert project.event("Stop").returncode == 2


def test_quality_requires_current_review(project: Project) -> None:
    assert project.run("quality").returncode == 2


def test_unconfigured_quality_fails_closed(project: Project) -> None:
    project.review("PASS")
    (project.root / ".engineering-os-quality.json").write_text(
        json.dumps({"schema": 1, "configured": False, "checks": []}), encoding="utf-8"
    )
    assert project.run("quality").returncode == 2


def test_missing_required_category_fails_closed(project: Project) -> None:
    project.review("PASS")
    project.configure(PASSING)
    assert project.run("quality").returncode == 2


def test_failing_check_fails_quality(project: Project) -> None:
    project.review("PASS")
    project.configure(
        *[
            (n, c, [sys.executable, "-c", "raise SystemExit(1)"] if c == "static" else a)
            for n, c, a in full_checks()
        ]
    )
    assert project.run("quality").returncode == 2
    assert project.event("Stop").returncode == 2


def test_missing_check_executable_fails_quality(project: Project) -> None:
    project.review("PASS")
    project.configure(
        *[
            (n, c, ["definitely-not-an-executable-xyz"] if c == "build" else a)
            for n, c, a in full_checks()
        ]
    )
    assert project.run("quality").returncode == 2


def test_check_that_modifies_the_tree_is_rejected(project: Project) -> None:
    project.review("PASS")
    writer = [sys.executable, "-c", "open('side_effect.txt','w').write('x')"]
    project.configure(*[(n, c, writer if c == "tests" else a) for n, c, a in full_checks()])
    assert project.run("quality").returncode == 2


def test_abandoned_lock_blocks_everything(project: Project) -> None:
    (project.root / ".engineering-os-review" / "lock").write_text("", encoding="utf-8")
    assert project.event("PreToolUse", tool_name="Read").returncode == 2
    assert project.run("report").returncode == 2


def test_external_edit_between_sessions_is_audited(project: Project) -> None:
    project.review("PASS")
    project.write("app.py", "print('external')\n")
    assert project.event("SessionStart").returncode == 0
    assert project.state()["status"] == "PENDING"


def test_potential_secret_blocks_pass(project: Project) -> None:
    token = "AKIA" + "ABCDEFGHIJKLMNOP"
    project.write("leak.txt", f"key={token}\n")
    project.event("PostToolUse", tool_name="Write")
    project.review("PASS")
    assert project.state()["status"] != "PASS"
    assert token not in json.dumps(project.state())


def test_unknown_hook_event_is_blocked(project: Project) -> None:
    assert project.event("SomethingElse").returncode == 2


def test_cwd_outside_project_is_blocked(
    project: Project, tmp_path_factory: pytest.TempPathFactory
) -> None:
    other = tmp_path_factory.mktemp("elsewhere")
    payload = {
        "session_id": SESSION,
        "cwd": str(other),
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
    }
    assert project.run("hook", stdin=json.dumps(payload)).returncode == 2


def test_quality_gate_wrapper_maps_missing_runtime_to_exit_2(tmp_path: Path) -> None:
    (tmp_path / "tools").mkdir()
    shutil.copy(REPO / "tools" / "quality_gate.py", tmp_path / "tools")
    result = subprocess.run(
        [sys.executable, str(tmp_path / "tools" / "quality_gate.py")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 2


def _handback(project: Project, agent: str, message: str) -> subprocess.CompletedProcess[str]:
    return project.event(
        "PreToolUse", tool_name="SubagentHandback", agent_id=agent, tool_input={"message": message}
    )


def _report(project: Project, status: str = "PASS") -> str:
    return json.dumps(
        {
            "change_id": project.state()["change_id"],
            "status": status,
            "summary": "synthetic review",
            "findings": [],
            "evidence": ["read files"],
        }
    )


def test_handback_is_allowed_only_for_the_bound_active_reviewer(project: Project) -> None:
    assert _handback(project, "agent-1", _report(project)).returncode == 2  # no active review
    project.event("SubagentStart", agent_type="security-reviewer", agent_id="agent-1")
    assert _handback(project, "agent-2", _report(project)).returncode == 2  # different agent
    assert _handback(project, "agent-1", _report(project)).returncode == 0


def test_review_delivered_via_handback_with_empty_stop_message_is_recorded(
    project: Project,
) -> None:
    project.event("SubagentStart", agent_type="security-reviewer", agent_id="agent-1")
    assert _handback(project, "agent-1", _report(project)).returncode == 0
    stop = project.event("SubagentStop", agent_type="security-reviewer", agent_id="agent-1")
    assert stop.returncode == 0
    assert project.state()["status"] == "PASS"


def test_duplicate_subagent_stop_does_not_overwrite_a_recorded_review(project: Project) -> None:
    assert project.review("PASS").returncode == 0
    again = project.event("SubagentStop", agent_type="security-reviewer", agent_id="agent-1")
    assert again.returncode == 0
    assert project.state()["status"] == "PASS"
    assert len(project.state()["reviews"]) == 1  # type: ignore[arg-type]


def test_empty_stop_without_any_recorded_review_still_fails_closed(project: Project) -> None:
    project.event("SubagentStart", agent_type="security-reviewer", agent_id="agent-1")
    project.event("SubagentStop", agent_type="security-reviewer", agent_id="agent-1")
    assert project.state()["status"] == "NOT_VERIFIED"


def test_handback_message_containing_a_secret_is_not_stored(project: Project) -> None:
    token = "AKIA" + "ABCDEFGHIJKLMNOP"
    project.event("SubagentStart", agent_type="security-reviewer", agent_id="agent-1")
    _handback(project, "agent-1", _report(project) + token)
    assert token not in json.dumps(project.state())
    project.event("SubagentStop", agent_type="security-reviewer", agent_id="agent-1")
    assert project.state()["status"] == "NOT_VERIFIED"
