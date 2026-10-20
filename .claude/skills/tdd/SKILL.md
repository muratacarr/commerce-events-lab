---
name: tdd
description: Apply project-specific DoR, Red/Green/Refactor and evidence-based completion for implementation and bug fixes.
---

1. Confirm scope, acceptance criteria, affected consumers, dependencies, migration
   impact, threat assumptions and the smallest meaningful test (DoR).
2. RED: write a meaningful failing behavior or regression test. After this edit,
   invoke the read-only security-reviewer before another edit.
3. Verify the failure expresses the intended behavior, not a setup error.
4. GREEN: implement the smallest correct change, with a new security review after
   each actual change. Review relevant negative and authorization-denial paths.
5. REFACTOR with tests green; remediation and refactor edits need new reviews.
6. Run configured project commands and `python tools/quality_gate.py`; require
   current review and check evidence before marking tasks complete (DoD).
7. For non-testable artifacts document justified build, schema, visual or manual
   validation. Never weaken tests just to pass or invent coverage/results.
