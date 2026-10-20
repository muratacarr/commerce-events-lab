# Setup verification ledger

Recorded 2026-10-20 on Windows 11, Claude Code 2.1.304, Python 3.13.15, uv 0.12.13,
Docker 29.7.2 / Compose v5.5.1, Git 2.55.0. Statuses: PASS, FAIL, NOT_VERIFIED, NOT_APPLICABLE.
Direct script tests prove gate logic only; "live" means an actual `claude -p` session in a
disposable fixture directory outside this repository. The final live run in this repository and
the final `python tools/quality_gate.py` result are kept in the ignored local state
(`.engineering-os-review/current.json`) and reported in the setup summary; they are not recorded
here because recording them would itself be a new change.

## Runtime and hooks

| Item | Status | Evidence |
|---|---|---|
| Claude Code >= 2.1.295 with exec-form hooks and `onFailure` | PASS | 2.1.304 accepted the generated settings; hooks fired |
| Python >= 3.11 for hook runtime | PASS | 3.13.15 |
| SessionStart audit fires | PASS (live) | state created with `session_audit: true` |
| PreToolUse blocks mutation while review pending | PASS (live) | Write blocked, file not created |
| Reviewer start/stop binding (agent, session, change) | PASS (live) | review record with agent_id/session_id/change_id |
| Real reviewer returns schema-valid JSON, recorded by SubagentStop | PASS (live) | recorded `FAIL` with MEDIUM+LOW findings for a placeholder-check fixture |
| Real reviewer returns `PASS` on a clean tree | NOT_VERIFIED here | see final run in the setup summary |
| `SubagentHandback` / duplicate `SubagentStop` incompatibility | FAIL then fixed | see SECURITY_WORKFLOW.md deviation 1; live rerun recorded `FAIL` correctly; 5 regression tests |
| Stop / TaskCompleted blocked without review | PASS (live + logic) | Stop looped blocked until max turns; unit tests |
| FAIL permits remediation edits | PASS (logic); live NOT_VERIFIED | hook passed the Write; headless `ask` permission stopped it |
| Quality gate fail-closed (unconfigured, missing category, failing check, missing executable, tree-mutating check, no review) | PASS (logic) | unit tests |
| Concurrent/abandoned lock, external edit, stale/forged change_id, secret in tree | PASS (logic) | unit tests |
| Transient-write revert between observations, filesystem-event enforcement | NOT_APPLICABLE | documented limit of the snapshot design |
| Hostile-writer resistance of local evidence | NOT_VERIFIED | by design requires independent CI |

## Reviewer, permissions, rules, skills

| Item | Status | Evidence |
|---|---|---|
| Reviewer tools are only Read, Glob, Grep | PASS | frontmatter test; live session reports read-only; reviewer made only Read calls |
| Deny rules block protected paths and secrets | PASS (live) | CLAUDE.md, tools/quality_gate.py, quality config writes denied with "deny" message; `.env` read denied |
| Allowed write of an unprotected path under `ask` | NOT_VERIFIED | headless mode cannot answer `ask` |
| Project allow rules active | NOT_VERIFIED | workspace untrusted in headless runs; needs interactive trust |
| Five rule files, `tdd` and `interview-prep` skills, reviewer agent load | PASS (live) | session listed one rule ID per file |
| Path-scoped rule loading | NOT_VERIFIED | rules kept unscoped on purpose |
| Language policy (Turkish interaction, English artifacts) in CLAUDE.md | PASS (live) | session restated it correctly |

## Git

| Item | Status | Evidence |
|---|---|---|
| `/docs/interview/` ignored, nothing tracked there | PASS | `git check-ignore --no-index`, `git ls-files` |
| `.env`, `.env.*` ignored; `.env.example` not ignored | PASS | probe files |
| `.engineering-os-review/`, `.venv/`, caches, `/secrets/` ignored | PASS | probe files |
| Lock files and sources not ignored | PASS | probe files |

## Dependencies and checks (each run directly during setup)

| Check | Status | Evidence |
|---|---|---|
| `uv lock --check`, 73 packages, hashes exported | PASS | |
| `pip-audit -r requirements-dev.lock` | PASS | "No known vulnerabilities found" (point in time) |
| Imports of pinned stack (SQLAlchemy 2.1.5, Alembic 1.20.0, psycopg 3.3.6, aio-pika 10.1.1) | PASS | import only; real-DB/broker behavior NOT_VERIFIED |
| `pytest tests/unit` (tooling tests) | PASS | 42 passed excluding the 2 settings tests; settings tests run after install |
| `ruff check` / `ruff format --check` / `mypy src` / `compileall` | PASS | |
| `detect-secrets` scan with positive and negative control | PASS | |
| Package licenses | PARTIAL | pip-audit and detect-secrets license metadata absent: NOT_VERIFIED; psycopg is LGPL-3.0 |

## Not done by design (blocks implementation approval only where stated)

| Item | Status |
|---|---|
| `compose.yaml`, Dockerfiles, `docker compose config --quiet`, building three images | NOT_VERIFIED (milestone L3) |
| Pull and run of the pinned PostgreSQL/RabbitMQ digests | NOT_VERIFIED |
| Migration smoke tests per owned database | NOT_VERIFIED (L1/L3) |
| Integration, contract (non-empty), scenario test checks in the gate | NOT_VERIFIED (added as tests appear; trusted config edit) |
| `tools/lab.py` (doctor, scenario, replay --verify, trace) | NOT_VERIFIED (L7) |
| CI provider, protected branches, independent review gate | NOT_VERIFIED (provider undecided) |
| Interactive workspace trust accepted | NOT_VERIFIED (user action) |
