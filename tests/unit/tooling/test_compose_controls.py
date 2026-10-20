"""Static controls for the Compose skeleton, Dockerfile and secret generator (PROJECT-016/023)."""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[3]
SERVICES = ("order", "payment", "inventory")
INFRA = ("postgres", "rabbitmq")


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _service_block(compose: str, name: str) -> str:
    match = re.search(rf"^  {name}:\n((?:    .*\n|\n)*)", compose, re.MULTILINE)
    assert match, f"service {name} missing"
    return match.group(1)


def _gen_secrets() -> ModuleType:
    spec = importlib.util.spec_from_file_location("gen_secrets", ROOT / "tools" / "gen_secrets.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_images_are_pinned_by_digest_and_never_latest() -> None:
    compose_images = re.findall(r"^\s+image:\s*(\S+)", _text("compose.yaml"), re.MULTILINE)
    from_refs = re.findall(r"^FROM\s+(\S+)", _text("Dockerfile"), re.MULTILINE)
    assert len(compose_images) >= 2
    assert from_refs
    for ref in [*compose_images, *from_refs]:
        if ref.startswith("commerce-lab-"):
            continue  # locally built service images, not pulled
        assert "@sha256:" in ref, ref
        assert ":latest" not in ref, ref


@pytest.mark.parametrize(
    "relative",
    [
        "compose.yaml",
        "Dockerfile",
        "infra/postgres/init-databases.sh",
        "infra/rabbitmq/rabbitmq.conf",
    ],
)
def test_no_privileged_socket_host_network_or_default_credentials(relative: str) -> None:
    text = _text(relative).lower()
    for token in ("privileged", "docker.sock", "network_mode", "guest"):
        assert token not in text, f"{relative} contains {token}"


def test_database_and_broker_are_not_published() -> None:
    compose = _text("compose.yaml")
    for name in INFRA:
        assert "ports:" not in _service_block(compose, name)


def test_service_ports_are_loopback_only() -> None:
    compose = _text("compose.yaml")
    for name in SERVICES:
        published = re.findall(r'ports:\n\s+- "([^"]+)"', _service_block(compose, name))
        assert len(published) == 1, name
        assert re.fullmatch(r"127\.0\.0\.1:\d+:8000", published[0]), published[0]


def test_every_container_is_hardened() -> None:
    compose = _text("compose.yaml")
    for name in (*INFRA, *SERVICES):
        block = _service_block(compose, name)
        assert "no-new-privileges:true" in block, name
        assert "cap_drop:" in block, name
    for name in SERVICES:
        assert "read_only: true" in _service_block(compose, name), name


def test_runtime_services_never_receive_owner_credentials() -> None:
    compose = _text("compose.yaml")
    for name in SERVICES:
        block = _service_block(compose, name)
        assert "owner_password" not in block, name
        assert "superuser" not in block, name
        assert f"{name}_db_app_password" in block, name
        assert f"{name}_amqp_password" in block, name


def test_dockerfile_installs_hashed_dependencies_as_non_root() -> None:
    dockerfile = _text("Dockerfile")
    assert "--require-hashes" in dockerfile
    user = re.findall(r"^USER\s+(\S+)", dockerfile, re.MULTILINE)
    assert user
    assert user[-1] not in {"root", "0"}
    assert re.search(r"order\|payment\|inventory", dockerfile)


def test_secret_generator_creates_without_overwriting(tmp_path: Path) -> None:
    gen = _gen_secrets()
    created = gen.generate(tmp_path)
    assert created
    before = {path.name: path.read_text(encoding="utf-8") for path in tmp_path.iterdir()}
    for name in gen.SECRET_NAMES:
        assert len(before[f"{name}.txt"]) >= 32
    assert len(set(before.values())) == len(before)
    assert gen.generate(tmp_path) == []
    after = {path.name: path.read_text(encoding="utf-8") for path in tmp_path.iterdir()}
    assert after == before


def test_rabbitmq_definitions_hold_only_hashes_and_scoped_service_users(tmp_path: Path) -> None:
    gen = _gen_secrets()
    gen.generate(tmp_path)
    raw = (tmp_path / gen.DEFINITIONS_NAME).read_text(encoding="utf-8")
    definitions = json.loads(raw)
    assert sorted(user["name"] for user in definitions["users"]) == sorted(SERVICES)
    for svc in SERVICES:
        plaintext = (tmp_path / f"{svc}_amqp_password.txt").read_text(encoding="utf-8")
        assert plaintext not in raw
    for permission in definitions["permissions"]:
        assert permission["configure"] == f"^{permission['user']}\\."


def test_secret_generator_never_prints_values(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    gen = _gen_secrets()
    assert gen.main(tmp_path) == 0
    printed = capsys.readouterr().out
    for path in tmp_path.glob("*.txt"):
        assert path.read_text(encoding="utf-8") not in printed


def test_image_tags_and_digests_match_setup_matrix() -> None:
    matrix = _text("docs/SETUP_MATRIX.md")
    refs = [
        *re.findall(r"^\s+image:\s*(\S+@sha256:[0-9a-f]{64})", _text("compose.yaml"), re.MULTILINE),
        *re.findall(r"^FROM\s+(\S+@sha256:[0-9a-f]{64})", _text("Dockerfile"), re.MULTILINE),
    ]
    assert len(refs) == 3
    for ref in refs:
        name_and_tag, digest = ref.split("@", 1)
        assert digest in matrix, ref
        assert name_and_tag.split(":", 1)[1] in matrix, ref


def test_database_and_broker_have_no_outbound_network() -> None:
    compose = _text("compose.yaml")
    assert re.search(r"^  lab:\n(?:    .*\n)*?    internal: true", compose, re.MULTILINE)
    for name in INFRA:
        block = _service_block(compose, name)
        assert "networks: [lab]" in block, name
        assert "edge" not in block, name
    for name in SERVICES:
        assert "networks: [lab, edge]" in _service_block(compose, name), name


def test_init_script_never_puts_passwords_in_arguments() -> None:
    script = _text("infra/postgres/init-databases.sh")
    assert "-v owner_pw" not in script
    assert "-v app_pw" not in script
    assert "\\getenv owner_pw" in script
    assert "\\getenv app_pw" in script
