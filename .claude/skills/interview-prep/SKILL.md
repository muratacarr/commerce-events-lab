---
name: interview-prep
description: Update concise factual English interview notes at completed milestones after validating Git ignore and tracked status.
---

At a completed milestone or project completion, inspect real implementation,
ADRs and development state. Ensure root `.gitignore` contains `/docs/interview/`
before generating notes. Use `git check-ignore --no-index` and `git ls-files --
docs/interview/` separately. If tracked, report it and request approval before a
safe index-only removal that preserves local files. Never rewrite history silently.

Create/update these English files, roughly 300-500 words maximum each:

- `docs/interview/01-project-overview.md`: 30-second/2-minute pitches, problem,
  architecture, honest contribution, 1-2 CV statements and a short B1 English pitch.
- `docs/interview/02-technical-interview.md`: 8-10 questions and answers tied to
  actual architecture, alternatives, security/TDD/data and scalability/failure cases.
- `docs/interview/03-challenges-and-lessons.md`: 2-3 authentic challenges and lessons;
  STAR stories only if recorded experience supports them.

Do not invent metrics, teamwork, features, vulnerabilities or outcomes. Use
NOT_MEASURED/NOT_AVAILABLE for missing facts. Update only at milestones. Every
note change still requires its scoped security review; ignored is not unreviewed.
