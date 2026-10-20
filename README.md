# Event-Driven Commerce Learning Lab

Setup stage only: project structure, engineering rules, Claude Code configuration and
verification tooling. No product features are implemented yet; they need explicit approval.

See `project-recipe.md` (governing specification), `docs/SETUP_VERIFICATION.md` (evidence),
`docs/SETUP_MATRIX.md` (dependency and image matrix) and `docs/adr/`.

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
