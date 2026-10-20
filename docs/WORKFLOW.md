# Change workflow, gates and terms

This page explains how a change moves through this repository and what the words used in the
status reports mean. It describes the working method of this project; it is not an industry
standard (see the last section).

## Two layers of control

| Layer | What | Strength |
|---|---|---|
| Local | Security gate and quality gate (hooks and scripts in this repository) | Cooperative: a writer with local access can alter scripts or local evidence |
| Independent | GitHub Actions workflow and the ruleset on `main` | Enforced by the hosting service, not by local files |

A local `PASS` is never merge evidence. Merge and release stay `NOT_VERIFIED` until the
independent layer, including a human approval from someone other than the author, is configured
and tested (see `docs/CI.md`).

## Security gate

Parts:
- **Hook runtime** (`.claude/hooks/security_gate.py`): runs on Claude Code events, hashes the file
  tree after each tool call and keeps its state in `.engineering-os-review/current.json`
  (git-ignored).
- **Reviewer agent** (`.claude/agents/security-reviewer.md`): can use only `Read`, `Glob` and
  `Grep`. It reads the changed files and returns one JSON report.

States:

    PASS ──(a file changes)──► PENDING ──(valid PASS report)──► PASS
                                   │
                                   ├──(valid FAIL report)──► FAIL      remediation edits allowed
                                   └──(no or invalid report)► NOT_VERIFIED   a new review is needed

Lifecycle of one change:
1. A file is created or edited. The tree is hashed again and a new **change identifier** is
   derived from the changed paths and their before/after hashes. The state becomes `PENDING`.
2. While `PENDING`, tools that mutate files are blocked. Still allowed: the read tools, the
   reviewer agent and two exact commands (`python .claude/hooks/security_gate.py report` and
   `python tools/quality_gate.py`).
3. The reviewer agent is started. The hook binds that agent to the session and the change
   identifier.
4. The reviewer reads the change and returns a report with exactly these keys: `change_id`,
   `status`, `summary`, `findings`, `evidence`. A finding has `severity`, `location`, `threat`,
   `remediation` and `standard`. The report is rejected if the identifier does not match, the
   evidence is empty, a `PASS` carries a `CRITICAL`, `HIGH` or `MEDIUM` finding, or it contains a
   secret-like pattern.
5. When the reviewer stops, the hook records the result. A valid report sets the state; anything
   else sets `NOT_VERIFIED` and the parent must retry explicitly.
6. After a `PASS`, run `python tools/quality_gate.py`. Its result is bound to the same change
   identifier, so any later edit invalidates it.
7. A task cannot be completed (Stop and TaskCompleted hooks) without both a current review and
   passing checks. `LOW` findings stay in the ledger; `CRITICAL` and `HIGH` block; this runtime
   also requires `MEDIUM` findings to be fixed.

## Quality gate

`python tools/quality_gate.py` runs eight checks defined in `.engineering-os-quality.json`:
unit and contract tests, `compileall`, `ruff` lint, `ruff` format check, `mypy`, the secret scan
(`tools/scan_secrets.py`, a wrapper around detect-secrets), the lock-file currency check and
`pip-audit`. A missing or failing check fails the gate; nothing is reported as passing that did not
run. Integration, scenario and Compose-based checks are added as those artifacts appear.

## Independent controls (GitHub)

- The workflow `ci` (`.github/workflows/ci.yml`) re-runs the same real checks on every pull
  request and push to `main`, with read-only token permissions and no secrets.
- A ruleset on `main` rejects direct pushes and requires a pull request and the `checks` status
  check. This was observed working; the number of required approvals, the bypass list and a second
  human reviewer are `NOT_VERIFIED`.
- Private repositories do not enforce rulesets on the GitHub plan in use, so the repository is public.

## Working rules that avoid known problems

- Run one reviewer at a time. A late, report-less stop of an older reviewer can overwrite a newer
  `PASS` with `NOT_VERIFIED`.
- Keep each change small. Reviews of large changes (many files) often ended without a report;
  reviews of one to three files were delivered in seconds. The cause is not established.
- If a reviewer read is blocked by the hook while a review is pending, repeating the same read
  succeeds; give reviewers room for those retries.
- Never edit `.engineering-os-review/` or the gate files to obtain a `PASS`. Protected paths are
  denied for ordinary edits on purpose.
- Record the outcome as `PASS`, `FAIL`, `NOT_VERIFIED` or `NOT_APPLICABLE` with the evidence;
  results reported by a person rather than observed are labelled as such.

## Known limitations

- The local gate hashes the tree at tool, session and completion boundaries. It cannot see writes
  that are reverted within a single command or edits made between observations.
- A disabled hook, a missing Python, a timeout or an interruption cannot guarantee that an active
  session stays blocked. Stopping is never security success.
- A reviewer report is model output. It is one more piece of evidence, not proof; the independent
  controls and human review remain the authority for merge and release.
- More detail and recovery steps: `docs/SECURITY_WORKFLOW.md`.

## Glossary

| Term | Meaning here |
|---|---|
| Hook | A script Claude Code runs on an event (before or after a tool call, when an agent starts or stops, when a turn ends) |
| Security gate | The hook runtime plus the reviewer agent, which together require recorded review evidence for every change |
| Quality gate | `tools/quality_gate.py`, the automated checks bound to the same change |
| Change identifier | A hash-derived ID of the current set of changed files; reviews and checks are valid only for the identifier they were recorded against |
| `PASS` / `FAIL` | A recorded result with no blocking findings / with blocking findings |
| `NOT_VERIFIED` | No usable evidence; this never counts as success |
| `NOT_APPLICABLE` | A control that does not apply, with a stated reason |
| Finding severities | `CRITICAL` and `HIGH` block; `MEDIUM` must be fixed in this runtime; `LOW` is tracked |
| CI | Continuous integration: the GitHub Actions workflow that re-runs the checks on GitHub |
| Ruleset | A GitHub rule for `main` (pull request required, status check required, no force push) |
| DoR / DoD | Definition of Ready (scope, risks and test plan clear before work starts) and Definition of Done (verified with real evidence) |
| TDD | Test-driven development: write a failing test (Red), make it pass (Green), then clean up (Refactor) |
| ADR | Architecture decision record: a short note of a decision, its reasons and rejected alternatives (`docs/adr/`) |
| Digest | The immutable content hash of a container image; images are pinned by tag plus digest, never `latest` |
| Smoke test | A quick, shallow check that the basics work |

## Is this a standard?

Partly, and the difference matters.

- **Common practice:** test-first development, continuous integration, required status checks
  and pull requests on the main branch, architecture decision records, least privilege, secret and
  dependency scanning, definitions of ready and done, and the Event Sourcing, CQRS, saga and
  transactional outbox/inbox patterns the lab teaches.
- **Referenced standard:** the rules cite OWASP ASVS and select requirements by risk. No
  compliance, certification or production readiness is claimed.
- **Specific to this project:** the hook-driven reviewer gate, the change identifier mechanism, the
  reviewer agent, and the rule identifiers (such as `PROJECT-016`) in `.claude/rules/`. These are
  this repository's working method, not an industry standard.
