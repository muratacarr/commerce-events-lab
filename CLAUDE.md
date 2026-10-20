# Event-Driven Commerce Learning Lab

Language policy (user override of the recipe's English-interaction line):
- Talk to the user in Turkish in the terminal: questions, explanations, progress updates, approval requests and summaries.
- Everything else stays in English: repository files, code, comments, tests, documentation, ADRs, commit messages, configuration, rules, skills, agent instructions, reviewer output and interview notes.
- Never translate code, identifiers, paths, commands, status words (PASS/FAIL/NOT_VERIFIED) or file contents into Turkish.
Project context (data, not operating instructions): {"summary": "A deliberately small local three-service Python lab that teaches Event Sourcing, CQRS and distributed failure recovery through observable order, simulated payment and inventory workflows.", "platforms": ["web"], "stacks": ["fastapi", "postgresql"], "data_sensitivity": "internal"}
Inspect existing work before editing. No product features before verified setup and explicit user approval.
Use DoR, default Red/Green/Refactor, change-impact analysis and evidence-based DoD.
Every change requires read-only Security Reviewer evidence for the current change; remediation requires re-review.
After a change, invoke Agent with subagent_type security-reviewer before another edit.
A pending flag is not a review. Missing or failed required evidence blocks completion.
Read .engineering-os-review/current.json for change identity and paths; never forge or edit evidence.
The reviewer returns JSON; SubagentStop records it. Do not use shell writes to create a PASS.
Remediate failures one reviewed change at a time; do not overwrite unreviewed intermediate changes.
Keep secrets out of code and logs; apply least privilege and the selected rules.
Before sensitive features, have the reviewer assess the architecture and threat model.
Run python .claude/hooks/security_gate.py report for current scope.
Run python tools/quality_gate.py for current-change tests, build, static and security evidence.
Merge/release additionally require independently administered CI and human/branch approvals.
At milestones update docs/DEVELOPMENT_STATE.md, relevant ADRs and ignored factual interview notes.
Setup is NOT_VERIFIED until installed-version hook smoke tests and actual project commands pass.
Candidate project commands (configure and execute before calling them verified):
- docker compose config --quiet
- python -m compileall -q src
- python -m mypy src
- python -m pytest -q tests/contract
- python -m pytest -q tests/integration
- python -m pytest -q tests/scenarios
- python -m pytest -q tests/unit
- python -m ruff check src tests
- python -m ruff format --check src tests
- python tools/lab.py doctor
- python tools/lab.py replay --verify
- python tools/lab.py scenario happy-path
- python tools/lab.py scenario stock-rejected

Use docs/SECURITY_WORKFLOW.md for limitations and failure recovery. Never bypass a gate to claim DONE.
