"""Generated project hook runtime. Python 3.11+, standard library only.

Local evidence is not a hostile-writer trust boundary. Enforce merge/release
approvals in a separately administered CI environment; never trust a local PASS.
"""

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / ".engineering-os-review"
EXCLUDED = {".git", ".engineering-os-review", "node_modules", ".venv", "__pycache__"}
READ_TOOLS = {"Read", "Glob", "Grep", "TaskGet", "TaskList"}
SAFE_COMMANDS = {"python .claude/hooks/security_gate.py report", "python tools/quality_gate.py"}
REQUIRED_CHECKS = {"tests", "build", "static", "secrets", "dependencies"}
SECRET_PATTERNS = [rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", rb"\bAKIA[A-Z0-9]{16}\b",
                   rb"\bsk-[A-Za-z0-9]{24,}\b"]


class Blocked(ValueError):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def is_link(path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def load(path):
    if is_link(path):
        raise Blocked("Refusing linked state/config file")
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    if is_link(path):
        raise Blocked("Refusing linked evidence file")
    temporary = path.with_suffix(path.suffix + ".tmp")
    # A preexisting temp file still requires manual crash recovery. Only clean
    # up a temp created by this call; never discard another writer's evidence.
    with temporary.open("x", encoding="utf-8") as handle:
        try:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        except Exception:
            handle.close()
            temporary.unlink(missing_ok=True)
            raise
    try:
        for attempt in range(8):
            try:
                temporary.replace(path)
                break
            except PermissionError:
                # Windows readers/indexers may briefly prevent replace while
                # a handle is open. Never chmod or bypass a persistent denial.
                if attempt == 7:
                    raise
                time.sleep(0.025 * (attempt + 1))
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def locked():
    if is_link(STATE_DIR):
        raise Blocked("Refusing linked state directory")
    STATE_DIR.mkdir(exist_ok=True)
    lock = STATE_DIR / "lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise Blocked("Concurrent hook or abandoned lock; do not bypass. Inspect before manual recovery") from error
    os.close(descriptor)
    try:
        yield
    finally:
        lock.unlink()


def snapshot():
    files, total = {}, 0
    def onerror(error):
        raise error
    for directory, directories, names in os.walk(ROOT, onerror=onerror, followlinks=False):
        directories[:] = sorted(name for name in directories if name not in EXCLUDED)
        for name in directories:
            if is_link(Path(directory) / name):
                raise Blocked("Linked directories require separate trusted review; snapshot unavailable")
        for name in sorted(names):
            if name.endswith((".pyc", ".pyo")):
                continue
            path = Path(directory) / name
            if is_link(path) or not path.is_file():
                raise Blocked("Linked or special files require separate trusted review")
            size = path.stat().st_size
            total += size
            if size > 10_000_000 or total > 50_000_000 or len(files) >= 5000:
                raise Blocked("Snapshot size limit; define and review a suitable artifact policy before completion")
            files[path.relative_to(ROOT).as_posix()] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                                      "mode": stat.S_IMODE(path.stat().st_mode)}
    return files


def observe(state, files, session=None):
    old = state.get("files", {})
    new_session = session is not None and state.get("session") != session
    if state and new_session and files == old:
        # Re-audit the same content without discarding an unreviewed change ID.
        state.update(session=session, status="PENDING", active_review=None, checks=None, session_audit=True)
        return state
    if files != old or new_session or not state:
        if state.get("status") in {"PENDING", "NOT_VERIFIED"} and files != old:
            state["unreviewed_prior"] = True
        sequence = state.get("sequence", 0) + 1
        changes = {name: {"before": old.get(name), "after": files.get(name)}
                   for name in sorted(old.keys() | files.keys()) if old.get(name) != files.get(name)}
        state.update(schema=1, sequence=sequence, files=files,
                     change_id=digest({"sequence": sequence, "files": files}),
                     changes=changes, status="PENDING", active_review=None, checks=None, session_audit=new_session)
        if new_session:
            state["session"] = session
        state.setdefault("history", []).append({"change_id": state["change_id"], "changes": changes,
                                                 "reason": "session audit" if new_session else "content change"})
    return state


def read_state():
    path = STATE_DIR / "current.json"
    state = load(path) if path.exists() else {}
    if state and (not isinstance(state, dict) or state.get("schema") != 1):
        raise Blocked("Unknown review state schema")
    return state


def secret_findings(files):
    # High-signal complement only. Project-specific dependency/SAST/secret tools
    # are additionally required in quality configuration. Never emit secret text.
    results = []
    for name in files:
        data = (ROOT / name).read_bytes()
        for pattern in SECRET_PATTERNS:
            match = re.search(pattern, data)
            if match:
                results.append({"file": name, "line": data[:match.start()].count(b"\n") + 1,
                                "severity": "HIGH", "check": "potential-secret"})
    return results


def review_ok(state):
    if state.get("unreviewed_prior"):
        raise Blocked("An observed prior change was overwritten before review; recover original evidence and obtain a trusted audit. No automatic reset")
    if state.get("status") != "PASS":
        raise Blocked("Current change needs Security Reviewer evidence: " + state.get("status", "NOT_VERIFIED"))
    reviews = state.get("reviews") or []
    if not reviews or reviews[-1].get("change_id") != state["change_id"] or reviews[-1].get("report", {}).get("status") != "PASS":
        raise Blocked("PASS state has no bound reviewer record")
    if secret_findings(state["files"]):
        raise Blocked("Potential secrets detected; findings contain paths/lines only, never values")


def gate(state):
    review_ok(state)
    checks = state.get("checks") or {}
    if checks.get("change_id") != state["change_id"] or checks.get("status") != "PASS":
        raise Blocked("Current change lacks passing quality checks; run python tools/quality_gate.py")


def parse_review(message, state, event):
    if not isinstance(message, str) or any(re.search(pattern, message.encode()) for pattern in SECRET_PATTERNS):
        raise Blocked("Missing review text or potential secret in review output; result not stored")
    report = json.loads(message)
    if not isinstance(report, dict) or set(report) != {"change_id", "status", "summary", "findings", "evidence"}:
        raise Blocked("Reviewer must return the exact JSON evidence schema")
    if report["change_id"] != state["change_id"] or report["status"] not in {"PASS", "FAIL", "NOT_VERIFIED"}:
        raise Blocked("Stale or invalid review result")
    if not isinstance(report["summary"], str) or not report["summary"].strip():
        raise Blocked("Missing review summary")
    if not isinstance(report["evidence"], list) or not report["evidence"] or not all(isinstance(item, str) and item.strip() for item in report["evidence"]):
        raise Blocked("Missing actual review evidence")
    if not isinstance(report["findings"], list):
        raise Blocked("Findings must be an array")
    for finding in report["findings"]:
        if not isinstance(finding, dict) or set(finding) != {"severity", "location", "threat", "remediation", "standard"}:
            raise Blocked("Malformed finding")
        if finding["severity"] not in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}:
            raise Blocked("Unknown severity")
        if not all(isinstance(value, str) and value.strip() for value in finding.values()):
            raise Blocked("Finding fields must be nonempty text")
        if report["status"] == "PASS" and finding["severity"] in {"CRITICAL", "HIGH", "MEDIUM"}:
            raise Blocked("Blocking findings cannot accompany PASS; this runtime requires remediation for Medium")
    active = state.get("active_review") or {}
    if (active.get("agent_id") != event.get("agent_id") or active.get("session_id") != event.get("session_id")
            or active.get("change_id") != state["change_id"]):
        raise Blocked("Review start/stop binding is absent, stale or mismatched")
    return report


def handle(event):
    if not isinstance(event, dict) or not isinstance(event.get("session_id"), str) or not event["session_id"]:
        raise Blocked("Invalid hook session")
    if not Path(event.get("cwd", "")).resolve().is_relative_to(ROOT):
        raise Blocked("Hook cwd is outside the configured project")
    name = event.get("hook_event_name")
    allowed = {"SessionStart", "PreToolUse", "PostToolUse", "PostToolUseFailure", "SubagentStart", "SubagentStop", "TaskCompleted", "Stop"}
    if name not in allowed:
        raise Blocked("Unknown hook event")
    with locked():
        state = read_state()
        previous_id = state.get("change_id")
        observe(state, snapshot(), event["session_id"] if name == "SessionStart" else None)
        # Persist observed changes even when the requested operation is blocked.
        save(STATE_DIR / "current.json", state)
        feedback = "Invoke security-reviewer with Agent(subagent_type='security-reviewer') before further edits. Read .engineering-os-review/current.json for the change ID and changed paths."
        if name == "PreToolUse":
            tool, args = event.get("tool_name"), event.get("tool_input") or {}
            if tool == "TaskUpdate" and args.get("status") == "completed":
                gate(state)
            reviewer = tool in {"Agent", "Task"} and args.get("subagent_type") == "security-reviewer"
            safe_command = tool in {"Bash", "PowerShell"} and args.get("command", "").strip() in SAFE_COMMANDS
            # Claude Code hands a subagent's result back through the internal SubagentHandback
            # tool and may then send SubagentStop without last_assistant_message. Allow the
            # handback only for the bound, active reviewer (it mutates nothing) and keep its
            # message for SubagentStop, applying the same secret check as reviewer output.
            active = state.get("active_review") or {}
            handback = (tool == "SubagentHandback" and bool(event.get("agent_id"))
                        and active.get("agent_id") == event.get("agent_id"))
            if handback and isinstance(args.get("message"), str) and len(args["message"]) <= 200_000                     and not any(re.search(pattern, args["message"].encode()) for pattern in SECRET_PATTERNS):
                state["active_review"]["handback_message"] = args["message"]
                save(STATE_DIR / "current.json", state)
            if state["status"] not in {"PASS", "FAIL"} and tool not in READ_TOOLS and not reviewer and not safe_command and not handback:
                raise Blocked(feedback)
        elif name == "SubagentStart" and event.get("agent_type") == "security-reviewer":
            if not event.get("agent_id") or state.get("active_review"):
                raise Blocked("Missing reviewer identity or concurrent reviewer; keep one review at a time")
            state["active_review"] = {"agent_id": event["agent_id"], "session_id": event["session_id"], "change_id": state["change_id"]}
            save(STATE_DIR / "current.json", state)
            return {"hookSpecificOutput": {"hookEventName": name, "additionalContext": feedback + " Return only the required JSON schema; no Markdown fences."}}
        elif name == "SubagentStop" and event.get("agent_type") == "security-reviewer":
            # Claude Code can emit a second SubagentStop for the same agent after the handback.
            # An already recorded review for this exact change must not be overwritten.
            if not state.get("active_review") and any(
                    item.get("agent_id") == event.get("agent_id") and item.get("change_id") == state["change_id"]
                    for item in state.get("reviews") or []):
                return {}
            try:
                message = event.get("last_assistant_message") or (state.get("active_review") or {}).get("handback_message", "")
                report = parse_review(message, state, event)
                if state.get("unreviewed_prior"):
                    raise Blocked("Unreviewed historical change cannot be silently covered by current snapshot")
                findings = secret_findings(state["files"])
                if findings and report["status"] == "PASS":
                    raise Blocked("Deterministic secret check failed")
            except (ValueError, TypeError) as error:
                state.update(status="NOT_VERIFIED", active_review=None, checks=None)
                save(STATE_DIR / "current.json", state)
                # Do not recurse the reviewer on invalid output: let the parent retry
                # explicitly, while completion stays blocked by state.
                return {"systemMessage": "Security review NOT_VERIFIED: " + str(error)}
            state.update(status=report["status"], active_review=None, checks=None)
            state.setdefault("reviews", []).append({"change_id": state["change_id"], "agent_id": event["agent_id"],
                                                    "session_id": event["session_id"], "report": report})
            save(STATE_DIR / "current.json", state)
        elif name in {"TaskCompleted", "Stop"}:
            gate(state)  # Never bypass because stop_hook_active is true.
        elif name in {"SessionStart", "PostToolUse", "PostToolUseFailure"}:
            if previous_id != state["change_id"] or state["status"] == "PENDING":
                return {"hookSpecificOutput": {"hookEventName": name, "additionalContext": feedback}}
        return {}


def quality():
    with locked():
        state = read_state()
        observe(state, snapshot())
        state["checks"] = None
        save(STATE_DIR / "current.json", state)
        review_ok(state)
        change_id = state["change_id"]
        config = load(ROOT / ".engineering-os-quality.json")
        if not isinstance(config, dict) or config.get("schema") != 1 or config.get("configured") is not True:
            raise Blocked("Quality configuration is NOT_VERIFIED; configure real checks before setup approval")
        checks = config.get("checks")
        if not isinstance(checks, list) or {item.get("category") for item in checks if isinstance(item, dict)} != REQUIRED_CHECKS:
            raise Blocked("Require tests, build, static, secrets and dependencies checks")
    # Release lock while checks run; bind results to unchanged ID and fresh tree.
    results = []
    for check in checks:
        command = check.get("command")
        if not isinstance(command, list) or not command or not all(isinstance(arg, str) and arg for arg in command):
            raise Blocked("Every required check needs a real argv command; no shell strings or placeholder passes")
        if not isinstance(check.get("name"), str) or not check["name"]:
            raise Blocked("Each check needs a name")
        # stdout/stderr can contain secrets; never persist them in evidence.
        result = subprocess.run(command, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120, shell=False)
        results.append({"name": check["name"], "category": check["category"], "exit_code": result.returncode})
        if result.returncode != 0:
            raise Blocked("Required check failed: " + check["name"] + "; inspect the check directly without exposing secrets")
    with locked():
        state = read_state()
        observe(state, snapshot())
        save(STATE_DIR / "current.json", state)
        if state["change_id"] != change_id:
            raise Blocked("Checks changed project files; a fresh security review and check run are required")
        review_ok(state)
        state["checks"] = {"status": "PASS", "change_id": change_id, "results": results}
        save(STATE_DIR / "current.json", state)
    return {"status": "PASS", "change_id": change_id, "checks": results}


def main():
    try:
        mode = sys.argv[1] if len(sys.argv) > 1 else "hook"
        if mode == "hook":
            result = handle(json.load(sys.stdin))
        elif mode == "report":
            with locked():
                state = read_state()
                observe(state, snapshot())
                save(STATE_DIR / "current.json", state)
                result = {key: state.get(key) for key in ("change_id", "status", "changes", "unreviewed_prior")}
        elif mode == "quality":
            result = quality()
        elif mode == "gate":
            with locked():
                state = read_state()
                observe(state, snapshot())
                save(STATE_DIR / "current.json", state)
                gate(state)
                result = {"status": "PASS", "change_id": state["change_id"]}
        else:
            raise Blocked("Unknown runtime operation")
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
        # Input and subprocess errors may contain sensitive material. Return a
        # generic safe failure; runtime-specific diagnosis is a manual task.
        print("BLOCKED: required security/quality evidence is pending, failed, stale or unavailable. Read the local state; invoke security-reviewer, remediate and rerun checks. Never report DONE or bypass a failed gate.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
