# Setup matrix (PROJECT-023)

Resolved on 2026-10-20 from PyPI JSON metadata and Docker Hub tag listings. Versions are the
latest stable (non-prerelease) at that time. "Support", "license" and "advisory" columns record
only what was actually checked; everything else is NOT_VERIFIED. No compliance or production
readiness is claimed.

## Python packages (pinned in `pyproject.toml`, locked in `uv.lock`)

| Package | Pin | License (package metadata) | Notes |
|---|---|---|---|
| fastapi | 0.156.1 | MIT | |
| uvicorn | 0.54.0 | BSD-3-Clause | |
| pydantic / pydantic-settings | 2.14.1 / 2.16.1 | MIT | |
| SQLAlchemy[asyncio] | 2.1.5 | MIT | Recipe cites 2.0 docs; 2.1 line resolved and imports cleanly with Alembic 1.20.0. Behavior against real PostgreSQL: NOT_VERIFIED until L1. |
| psycopg[binary] | 3.3.6 | LGPL-3.0-only | Dynamic linking via wheel; LGPL obligations reviewed only superficially: NOT_VERIFIED. |
| alembic | 1.20.0 | MIT | |
| aio-pika | 10.1.1 | Apache-2.0 | pulls aiormq 7.2.2 (Apache-2.0) |
| pytest / pytest-asyncio | 9.1.1 / 1.4.0 | MIT / Apache-2.0 | dev |
| httpx | 0.28.1 | BSD-3-Clause | dev |
| ruff / mypy | 0.17.1 / 2.4.0 | MIT / MIT | dev |
| pip-audit | 2.10.1 | license metadata absent: NOT_VERIFIED | dev |
| detect-secrets | 1.5.0 | license metadata absent: NOT_VERIFIED | dev |

73 packages resolved in total (direct and transitive) with hashes in `requirements.lock`
(runtime) and `requirements-dev.lock` (runtime + dev). `uv lock --check` verifies currency.
Advisories: `pip-audit` reported "No known vulnerabilities found" against `requirements-dev.lock`
on 2026-10-20. That is a point-in-time result against one advisory database, not a guarantee.

Interpreter: CPython 3.13 (`requires-python >=3.13,<3.14`). Host has 3.13.15; the container
base below is 3.13.16 (patch mismatch accepted). 3.14 and 3.15 were available but newer than
the development host; revisit deliberately, not by drift.

## Container images (digests are Docker Hub manifest-list digests; pulled and run on 2026-10-20: PASS, see docs/SETUP_VERIFICATION.md)

| Image | Tag | Digest |
|---|---|---|
| python (service base) | 3.13.16-slim-trixie | `sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f` |
| postgres | 18.6 | `sha256:74935e72241653ca55e0414067e6d8763aceb8a810eb51b452253ec3dcfc4336` |
| rabbitmq (broker UI optional) | 4.3.6-management-alpine | `sha256:3505b6096cdbc083bcc363e74366f575ecd0c1a55be4dadcbc60fa08e34647e1` |

RabbitMQ 4.4.0 was published the same day and is deliberately not selected. Compose references
must use tag plus digest, never `latest`. PostgreSQL 18 changed the default data directory
layout; `compose.yaml` mounts the volume at `/var/lib/postgresql` and the container started healthy.

## Host tooling observed

Claude Code 2.1.304 (hook minimum 2.1.295), Python 3.13.15, uv 0.12.13, Git 2.55.0,
Docker 29.7.2 with Compose v5.5.1 (daemon reachable, Linux containers).

## Not yet done (by design at setup stage)

Done in the Compose skeleton change: `compose.yaml`, `Dockerfile`, `docker compose config`, three
image builds, PostgreSQL/RabbitMQ start. Still not done: migration smoke tests, integration/scenario
test checks, `tools/lab.py` and a CI run. See `docs/SETUP_VERIFICATION.md`.
