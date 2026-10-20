# CI and merge gate (GitHub Actions)

Status: workflow written, NOT_VERIFIED. No GitHub repository or remote exists yet, so the
workflow has never run and no branch protection is configured.

## What the workflow does
`.github/workflows/ci.yml` runs on pull requests and pushes to `main` with read-only token
permissions, no secrets, SHA-pinned actions (checkout v7.0.1, setup-uv v10.3.0, resolved
2026-10-20), uv pinned to 0.12.13 and caching disabled. It runs the same real checks as
`.engineering-os-quality.json` directly: locked install, `uv lock --check`, pytest (unit and
contract), compileall, ruff lint and format, mypy, the secret scan (`tools/scan_secrets.py`, a wrapper around detect-secrets), pip-audit. It does not run
`tools/quality_gate.py` because that gate trusts local, forgeable review evidence.

## Settings to apply by hand after the repository exists (not provisioned automatically)
1. Protect `main`: require a pull request, require the `ci / checks` status check, require at
   least one human approval from someone other than the author, block force pushes and deletion.
2. Dismiss stale approvals on new commits so an approval is tied to the exact reviewed commit.
   A local PASS marker is never merge evidence.
3. Restrict who can edit `.github/workflows/`, `.claude/` and `.engineering-os-quality.json`
   (CODEOWNERS plus required review).
4. Update pinned actions and uv deliberately: re-resolve SHAs, never float tags.

## Added later
Docker-based checks (`docker compose config --quiet`, image builds, migration smoke tests,
integration and scenario tests with real PostgreSQL and RabbitMQ) are added with milestone L3
and later. Until then they are NOT_CONFIGURED, not passing.
