# Security and quality workflow

Requires Python 3.11+ and Claude Code with exec-form command hooks and
`onFailure: block` support (documented from 2.1.295). Engineering OS checks its
installed version separately; verify the actual target version and hook events.

Inspect the target first. Merge the recipe's files without overwriting user work.
Prepare reviewer/skills/rules/scripts and actual check commands first; install
active `.claude/settings.json` last, then restart into a fresh audit. Installing
the policy earlier can correctly block the remaining protected setup writes.
Project allow rules may be ignored until the folder is trusted. Complete the
normal interactive trust step for the target; never edit global trust state
silently. A controlled test may grant exact fixture-only commands through CLI
flags instead of modifying user trust settings. Initial setup/config upgrades
are trusted manual operations outside the running workflow; protected gate and
state paths deny ordinary Write/Edit. Restart and re-audit after such upgrades.
Configure real tests/build/static/secret/dependency argv commands in
`.engineering-os-quality.json` before setting `configured` to true. The initial
false/empty configuration intentionally fails. Candidate commands are not proof
of installed packages or configured scripts. Configure CI against the actual
provider; no provider or branch protection is silently provisioned.

Restart Claude after setup. SessionStart audits all current files, then all tool
boundaries rehash the tree. After a change invoke `security-reviewer` explicitly
with the Agent tool. PreToolUse blocks another mutation while review is pending;
Read/Glob/Grep, the reviewer and the two exact report/quality commands remain
available. A recorded FAIL permits remediation; the next change needs a new
review. A failed/missing reviewer never counts as PASS. A prior unreviewed
revision overwritten externally blocks completion until its evidence can be
recovered and a trusted human audit handles recovery; there is no automatic reset.

SubagentStart binds agent/session/change IDs. SubagentStop accepts only the
reviewer's exact JSON schema for that unchanged revision. Invalid/unavailable
output records NOT_VERIFIED and lets the reviewer stop; the parent must retry
explicitly, avoiding recursive reviewer hooks. Evidence writes are separate
from project changes. LOW findings remain in the ledger; CRITICAL/HIGH block.
This small runtime also requires MEDIUM remediation and offers no risk-approval
bypass. Never expose secrets in review output.

After PASS, run `python tools/quality_gate.py`. All five configured check
categories must execute successfully. Results bind to the same tree and change
ID; generated files or remediation edits invalidate them. Stop, TaskCompleted
and completing TaskUpdate require both current review and checks. The Stop
handler never bypasses checks because `stop_hook_active` is true. A runtime
exception/missing script is mapped to exit 2 by a fixed exec-form wrapper.
Unrecoverable gates must be reported as blocked, not weakened to escape a loop.

## Scope and trust limits

- This is a cooperative local workflow, not a tamper-resistant sandbox. A writer
  can alter scripts, settings or local evidence. A disabled hook, absent Python,
  process timeout, user interruption, API failure or Claude continuation cap
  cannot guarantee an active session stays open. Never interpret exit/stop as
  security success. Independently administered CI, protected branches and human
  review must reject missing/forged local evidence before merge/release.
- Do not upload or trust local review markers as CI approval. CI must run actual
  checks and require a protected review/attestation tied to the exact commit from
  a separate trusted reviewer. This generic recipe does not provision that service;
  merge/release remains NOT_VERIFIED until configured and tested.
- Snapshots cover content and basic mode bits (including untracked and ignored interview notes) at tool,
  session and completion boundaries. They cannot see transient writes reverted
  inside a single command or external edits between observations. Do not claim
  filesystem-event-level enforcement. Stop other writers; fresh session audits
  and independent full-diff release reviews are required.
  OS ACLs, registry state, file ownership and external services are not captured;
  assess these separately when deployment or permission changes affect them.
- Excluded directories: `.git`, `.engineering-os-review`, `node_modules`, `.venv`,
  `__pycache__`; `.pyc`/`.pyo` caches are excluded. Never store product source in
  these paths. Dependencies are checked separately. Large trees (>5000 files,
  >10 MB/file or >50 MB total) and links fail instead of silently reducing scope.
- State contains paths and hashes, not file contents or diff text. Deleted or
  inaccessible original content requires a trusted read-only diff audit; the
  reviewer must return NOT_VERIFIED if evidence cannot be recovered. Secret
  checks emit no values; narrow built-in patterns complement a configured scanner.
- Configured commands are reviewed trusted local code, run without a shell and
  with a timeout; their captured output is not stored. Review commands before
  enabling them. Windows `.cmd` wrappers need a reviewed executable entry point.
- An abandoned lock or incomplete atomic-write temp file fails closed. Confirm
  no hook/check/reviewer is active, preserve state for diagnosis and obtain human
  recovery review before removing only the known lock/temp file. Never delete
  evidence to manufacture a clean pass or reset an unreviewed history.
  Transient Windows replace denials use bounded retries; a failed write removes
  only its own temporary file and preserves the prior state, so later attempts
  can recover without bypassing a gate. Persistent denials remain blocked.

## Smoke tests before setup approval

Use an isolated disposable configuration fixture, not product features. Verify
actual Write/Edit, shell-created change, nonmutating reads, reviewer PASS, FAIL,
NOT_VERIFIED/unavailable, malformed output, remediation, concurrent/external edits,
stale/reverted evidence, missing scripts, missing check executable, failing check,
TaskCompleted and attempted Stop without review. Confirm reviewer has only
Read/Glob/Grep and skills/rule frontmatter load correctly. Hooks must appear in
actual Claude hook events; direct script tests alone do not prove event wiring.
Do not mock an LLM review as real runtime evidence. Record any unavailable test
as NOT_VERIFIED and block setup/merge/release accordingly.
If path-scoped rule loading cannot be verified on the installed version, keep
the selected rule files unscoped as a documented conservative fallback until
loading is verified; preserve every applicable requirement. Do not remove rules
or claim automatic path loading based only on valid YAML.

Before notes, verify `/docs/interview/` with Git ignore and tracked-file checks.
Do not alter tracked notes/index without user approval. At meaningful milestones
update development state, honest English interview notes and consequential ADRs.

## Deviations from the generated recipe (installed-version findings, 2026-10-20)

Found by live smoke tests on Claude Code 2.1.304. Each keeps every required control and was
covered by tests in `tests/unit/tooling/`. Re-verify after any Claude Code upgrade.

1. `security_gate.py`: Claude Code 2.1.304 returns a subagent's result through the internal
   `SubagentHandback` tool and may then emit a second `SubagentStop` with an empty
   `last_assistant_message`. The generated runtime blocked the handback while a review was
   pending and then let the empty second stop overwrite a recorded `PASS`/`FAIL` with
   `NOT_VERIFIED`, so `PASS` could never be reached (fail-closed, but unusable). Changes:
   (a) `SubagentHandback` is allowed only for the bound, active reviewer, and its message
   (after the same secret-pattern check) is kept for `SubagentStop`; (b) a duplicate
   `SubagentStop` for an agent whose review for the same change is already recorded is a
   no-op. A stop with no recorded review and no handback still records `NOT_VERIFIED`.
2. `.claude/settings.json`: 2.1.304 reports `Write(path)` deny rules as invalid ("only
   Edit(path) rules are matched; Edit rules cover all file-editing tools"). The seven
   redundant `Write(...)` rows were removed; the matching `Edit(...)` rows remain and were
   shown to deny Write-tool calls on protected paths. `Read` denies are unchanged.
3. Workspace trust: project `permissions.allow` entries are ignored until the folder is
   trusted. Accept the trust dialog interactively once; never edit trust state silently.
4. Tool caches (`.pytest_cache`, `.mypy_cache`, `.ruff_cache`) would change the snapshot after
   every quality run and invalidate the evidence. They are redirected under `.venv/cache/`
   (excluded from the snapshot) in `pyproject.toml`.
5. Rule files for FastAPI and PostgreSQL are kept unscoped (path-scoped loading NOT_VERIFIED),
   with the intended scope recorded in an HTML comment.
6. CI/branch protection are not provisioned: no remote or provider exists yet.
