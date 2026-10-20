# CI and merge gate (GitHub Actions)

Status: workflow ran successfully on GitHub; branch protection partially verified. See
"Applied state" below. Merge and release remain NOT_VERIFIED.

## What the workflow does
`.github/workflows/ci.yml` runs on pull requests and pushes to `main` with read-only token
permissions, no secrets, SHA-pinned actions (checkout v7.0.1, setup-uv v10.3.0, resolved
2026-10-20), uv pinned to 0.12.13 and caching disabled. It runs the same real checks as
`.engineering-os-quality.json` directly: locked install, `uv lock --check`, pytest (unit and
contract), compileall, ruff lint and format, mypy, the secret scan (`tools/scan_secrets.py`, a wrapper around detect-secrets), pip-audit. It does not run
`tools/quality_gate.py` because that gate trusts local, forgeable review evidence.

## Settings to apply by hand after the repository exists (not provisioned automatically)
1. Protect `main`: require a pull request, require the `checks` status check (displayed as `ci / checks` on pull requests), require at
   least one human approval from someone other than the author, block force pushes and deletion.
2. Dismiss stale approvals on new commits so an approval is tied to the exact reviewed commit.
   A local PASS marker is never merge evidence.
3. Restrict who can edit `.github/workflows/`, `.claude/` and `.engineering-os-quality.json`
   (CODEOWNERS plus required review).
4. Update pinned actions and uv deliberately: re-resolve SHAs, never float tags.

## Applied state (recorded 2026-10-21; the observations below were reported by the repository owner)

- CI: the `ci` workflow completed successfully on GitHub for commits `9ff567a` (run #1) and
  `6adf44b` (run #2). The run logs were not read here, so the individual steps are NOT_VERIFIED.
- Repository visibility: public. On the GitHub plan in use, rulesets are not enforced on private
  repositories, so the repository was made public to apply them.
- Ruleset `protect-main` on `main`, observed behaviour:
  - A direct push to `main` was rejected with GH013: "Changes must be made through a pull request"
    and "Required status check "checks" is expected".
  - On a test pull request the merge button was locked while the check ran and became available
    after it passed. The owner reports that the test pull request was closed without merging and
    its branch deleted.
  - The required check is named `checks` in the ruleset and is displayed as `ci / checks` on pull
    requests.
- NOT_VERIFIED: number of required approvals, bypass list, dismissal of stale approvals, the
  force-push and deletion rules, CODEOWNERS (the file does not exist yet) and whether a second human
  reviewer exists. Without an independent approver there is no human review gate, and merge and
  release stay NOT_VERIFIED.

## Added later
Docker-based checks (`docker compose config --quiet`, image builds, migration smoke tests,
integration and scenario tests with real PostgreSQL and RabbitMQ) are added with milestone L3
and later. Until then they are NOT_CONFIGURED, not passing.
