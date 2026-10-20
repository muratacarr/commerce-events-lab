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

## Compose skeleton (change f035f362, recorded 2026-10-20)

Scope: infrastructure and image build definitions only; no application code. Docker checks ran
in a copy outside the repository with freshly generated secrets, under the separate Compose
project `lab-verify`; the copy and that project's containers, volumes, network and images were
removed afterwards. Nothing under `./secrets` was created in this repository.

| Item | Status | Evidence |
|---|---|---|
| Security review of the 8 skeleton files | PASS | fifth attempt; no CRITICAL/HIGH/MEDIUM; 4 LOW (see Residual items) |
| Review delivery under large scope | FAIL then mitigated | four reviewers (16-26 tool calls) ended without `SubagentHandback`, leaving `NOT_VERIFIED`; the fifth, given an explicit budget of 11 `Read` calls, delivered. Cause NOT_VERIFIED |
| `python tools/quality_gate.py` | PASS | 8/8 checks, including `tests/unit/tooling/test_compose_controls.py` |
| TDD Red run for the new tests | NOT_VERIFIED | first attempt used a pytest flag that conflicts with `cache_dir`; the Red state was never captured, only Green |
| `docker compose config --quiet` | PASS | in the repository (no secrets present) and in the copy with `--profile services` |
| Three service images build | PASS | `--require-hashes` install from `requirements.lock`; images run as UID 10001 |
| Default service command | PASS | exits 1 with "no application code yet" by design |
| Invalid `SERVICE` build arg rejected | PASS (weak) | the build fails at the `COPY` stage; the Dockerfile `case` check was not reached |
| PostgreSQL 18.6 and RabbitMQ 4.3.6 pinned digests start healthy | PASS | `up --wait` healthy; volume mounted at `/var/lib/postgresql` |
| One database per service with separate owner and app roles | PASS | 3 databases; `<svc>_owner` owns, `<svc>_app` cannot be superuser; `order_app` can connect to `order` only |
| RabbitMQ has no `guest` user | PASS | `list_users` showed only `order`, `payment`, `inventory` |
| RabbitMQ per-service permissions | PASS | each user limited to `^<svc>\.` on vhost `lab` |
| Database and broker ports unpublished | PASS | `docker ps` shows exposed ports only, no host bindings |
| Runtime privileges of `<svc>_app` on tables | NOT_VERIFIED | no tables exist; grants belong to the migrations |
| Migration smoke tests | NOT_VERIFIED | no migrations yet |

Follow-up change 0908d299 (fixes for three of the four LOW items; verified 2026-10-21 in a
copy outside the repository under the separate Compose project `lab-verify2`, then removed):

| Item | Status | Evidence |
|---|---|---|
| Security review | PASS | no CRITICAL/HIGH/MEDIUM; one new LOW (services keep outbound access) |
| `python tools/quality_gate.py` | PASS | 8/8 checks |
| TDD Red run | PASS | before the fix, `test_database_and_broker_have_no_outbound_network` and `test_init_script_never_puts_passwords_in_arguments` failed; after it, all 16 tests in the file pass |
| Role passwords no longer in `psql` arguments | PASS | init script passes them through the environment of one `psql` process (`\getenv`); roles were created and authenticate |
| Password authentication over the network | PASS | from the `order` container: real app password accepted; wrong password, another database and an owner/app password mix-up rejected |
| `lab` network `internal: true` | PASS | from the postgres container an outbound connection fails with "Network is unreachable"; `order` still reaches `postgres` |
| Service port publishing with the `edge` network | PASS | `docker ps` shows `127.0.0.1:8001->8000/tcp` for a kept-alive `order`; postgres and rabbitmq show exposed ports only |
| Runtime services receive only their own secrets | PASS | `order` container lists `order_db_app_password` and `order_amqp_password` only |
| Image tags and digests match this matrix | PASS | enforced by `test_image_tags_and_digests_match_setup_matrix` |
| Connections from inside the PostgreSQL container | NOT_APPLICABLE as a control | the official image trusts loopback connections made inside the container, so a wrong password was accepted there; only network connections from other containers are password-protected |

Residual items (all LOW, tracked):
1. `tools/gen_secrets.py` keeps default host file permissions so container users can read the
   bind-mounted secrets; a shared host could expose the synthetic credentials. Accepted for the
   single-user lab and documented in the README.
2. The three services join the non-internal `edge` network (needed for loopback port publishing),
   so they keep outbound access. The database and broker do not.
3. The official PostgreSQL image trusts loopback connections inside its own container; anyone who
   can `docker exec` into it bypasses the passwords. Documented in the README.
4. The environment of the init-script `psql` process is readable by the same user or root inside
   the container, and statement logging would show the role statements if it were enabled.

## Remaining scope and superseded items (blocks implementation approval only where stated)

| Item | Status |
|---|---|
| `compose.yaml`, `Dockerfile`, `docker compose config --quiet`, building three images | PASS (see Compose skeleton section) |
| Pull and run of the pinned PostgreSQL/RabbitMQ digests | PASS (see Compose skeleton section) |
| Migration smoke tests per owned database | NOT_VERIFIED (L1/L3) |
| Integration, contract (non-empty), scenario test checks in the gate | NOT_VERIFIED (added as tests appear; trusted config edit) |
| `tools/lab.py` (doctor, scenario, replay --verify, trace) | NOT_VERIFIED (L7) |
| CI provider (GitHub Actions) | PASS (owner-reported) | runs #1 and #2 completed successfully; logs not read here; see docs/CI.md |
| Protected `main` | PARTIAL | ruleset `protect-main` active on the public repository; direct push rejected (GH013) and pull request merge gated by the `checks` status check; approvals, bypass list and force-push/deletion rules NOT_VERIFIED |
| Independent human review gate | NOT_VERIFIED | required approvals and a second reviewer are unconfirmed |
| Interactive workspace trust accepted | NOT_VERIFIED (user action) |
