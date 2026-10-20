"""Generate local lab secrets under ./secrets (PROJECT-016).

Writes one random value per file, never overwrites an existing file and never prints a value.
The RabbitMQ definitions file stores only salted password hashes for the three service users.
Files keep the host's default permissions so bind-mounted container users can read them; the
directory is git-ignored and holds synthetic lab credentials only.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import sys
from pathlib import Path

SERVICES = ("order", "payment", "inventory")
SECRET_NAMES = (
    "postgres_superuser_password",
    *(f"{svc}_db_{role}_password" for svc in SERVICES for role in ("owner", "app")),
    *(f"{svc}_amqp_password" for svc in SERVICES),
)
DEFINITIONS_NAME = "rabbitmq_definitions.json"
VHOST = "lab"


def _rabbit_hash(password: str) -> str:
    salt = os.urandom(4)
    return base64.b64encode(salt + hashlib.sha256(salt + password.encode()).digest()).decode()


def _write_new(path: Path, content: str) -> bool:
    try:
        with path.open("x", encoding="utf-8", newline="") as handle:
            handle.write(content)
    except FileExistsError:
        return False
    return True


def _definitions(secrets_dir: Path) -> str:
    users = []
    permissions = []
    for svc in SERVICES:
        password = (secrets_dir / f"{svc}_amqp_password.txt").read_text(encoding="utf-8")
        users.append(
            {
                "name": svc,
                "password_hash": _rabbit_hash(password),
                "hashing_algorithm": "rabbit_password_hashing_sha256",
                "tags": [],
            }
        )
        scope = f"^{svc}\\."
        permissions.append(
            {"user": svc, "vhost": VHOST, "configure": scope, "write": scope, "read": scope}
        )
    return json.dumps(
        {"users": users, "vhosts": [{"name": VHOST}], "permissions": permissions}, indent=2
    )


def generate(secrets_dir: Path) -> list[str]:
    """Create missing secret files and return the names that were created."""
    secrets_dir.mkdir(parents=True, exist_ok=True)
    created = [
        name
        for name in SECRET_NAMES
        if _write_new(secrets_dir / f"{name}.txt", secrets.token_urlsafe(32))
    ]
    definitions = secrets_dir / DEFINITIONS_NAME
    if not definitions.exists() and _write_new(definitions, _definitions(secrets_dir)):
        created.append(DEFINITIONS_NAME)
    return created


def main(secrets_dir: Path | None = None) -> int:
    target = secrets_dir or Path(__file__).resolve().parent.parent / "secrets"
    created = generate(target)
    print(f"created {len(created)} secret file(s); existing files were left untouched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
