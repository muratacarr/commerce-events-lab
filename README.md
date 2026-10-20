# Event-Driven Commerce Learning Lab

A deliberately small, local, three-service Python lab (Order, Payment, Inventory) that teaches
Event Sourcing, CQRS and distributed failure recovery through observable order, simulated
payment and inventory workflows. All data is synthetic. There is no browser UI, no customer login
and no real payment provider.

## Status

Setup stage only. **No product code exists yet**; implementing it needs explicit approval.
Overall setup is `NOT_VERIFIED`; the evidence ledger is `docs/SETUP_VERIFICATION.md` and the short
current state is `docs/DEVELOPMENT_STATE.md`.

Verified so far (see the ledger for how each item was checked):
- Local review and quality gates, and the hook runtime behind them.
- The Compose skeleton: configuration, three image builds, PostgreSQL and RabbitMQ start, one
  database and role pair per service, per-service RabbitMQ users, no published database or
  broker ports, internal network for the database and broker.
- The GitHub Actions workflow ran, and a ruleset on `main` rejected a direct push and gated a
  pull request on the `checks` status check (both reported by the repository owner).

Not verified yet: number of required approvals and the bypass list of the ruleset, interactive
workspace trust, CODEOWNERS, a second human reviewer (so merge and release are not claimed),
migration smoke tests, integration and scenario tests, and `tools/lab.py`.

## Planned milestones

Seven small steps, each built test-first with a security review per change and direct evidence
against a real database or broker where one is involved (rule `PROJECT-020`):

| Step | Content |
|---|---|
| L1 | Pure Order aggregate, replay and optimistic append |
| L2 | Idempotent HTTP command, query projection, visible lag |
| L3 | RabbitMQ, outbox and inbox delivery between one service pair |
| L4 | Payment, Inventory and the durable happy-path saga |
| L5 | Rejection, refund, pending timeout and restart recovery |
| L6 | Snapshots, projection rebuild and event schema evolution |
| L7 | Repeatable failure lab and documentation |

## Repository map

| Path | Purpose |
|---|---|
| `src/` | Service packages (`order`, `payment`, `inventory`, `contracts`); empty stubs for now |
| `migrations/` | One folder per service database; empty for now |
| `infra/` | PostgreSQL initialisation script and RabbitMQ configuration |
| `tests/` | Unit tests (currently the tooling tests); contract, integration and scenario folders are empty |
| `tools/` | Quality gate, secret scanner wrapper, secret generator |
| `docs/` | Evidence ledger, dependency matrix, CI notes, ADRs, workflow guide |
| `.claude/` | Rules, skills, the security reviewer agent and the gate hooks |
| `.github/workflows/` | The CI workflow |
| `compose.yaml`, `Dockerfile` | Local infrastructure and the shared service image definition |

## Local infrastructure (Compose skeleton)

Synthetic data only; the lab assumes a single-user host. Only the three service ports are
published, on `127.0.0.1` (8001-8003), and the services contain no application yet.

    python tools/gen_secrets.py            # once; writes git-ignored files under ./secrets
    docker compose up -d --wait postgres rabbitmq
    docker compose --profile services build

Security notes:
- `./secrets` keeps default host permissions so container users can read the bind-mounted files.
  On a shared host, anyone who can read the directory can read the lab credentials. Do not use
  this setup on a shared or untrusted host (PROJECT-017).
- The official PostgreSQL image trusts connections made from inside its own container, so a user
  who can `docker exec` into it bypasses the passwords. Connections from other containers do
  require them.
- The database and broker sit on an internal network without outbound access. The services also
  join an `edge` network so loopback port publishing works, which gives them outbound access.
- Stop with `docker compose down`. Add `-v` only if you intend to delete the lab volumes.

## How changes are made

Every change goes through two local gates and then through GitHub:

1. **Security gate:** a read-only reviewer agent must record a `PASS` for the exact change.
2. **Quality gate:** `python tools/quality_gate.py` runs tests, build, static, secret and
   dependency checks for that same change.
3. **GitHub:** the change reaches `main` only through a pull request whose `checks` status check
   passes.

The local gates are cooperative, not tamper-resistant; the GitHub controls are the independent
part. Details, the state diagram, the glossary and a plain statement of what is and is not an
industry standard are in [`docs/WORKFLOW.md`](docs/WORKFLOW.md).

## Documentation index

- `project-recipe.md`: governing specification.
- `docs/WORKFLOW.md`: change workflow, gates, glossary, standards statement.
- `docs/SETUP_VERIFICATION.md`: evidence ledger. `docs/DEVELOPMENT_STATE.md`: short current state.
- `docs/SETUP_MATRIX.md`: dependency and image versions. `docs/CI.md`: CI and merge controls.
- `docs/SECURITY_WORKFLOW.md`: gate limits, deviations and failure recovery.
- `docs/adr/`: architecture decision records.
