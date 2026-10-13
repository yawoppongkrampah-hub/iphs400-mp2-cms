"""T09: the rubric's clean-setup commands work without `--env-file`.

Seam 3 (the `cms` command and scripts). Each test builds a clean copy of the
project (the code, templates, images and `.env.example`, never the real `.env` or
database), does `cp .env.example .env` in it, and runs the script there.
"""
import os
import re
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import csrf_token

ROOT = Path(__file__).resolve().parents[1]
COPIED = ("app", "scripts", "templates", "images")


@pytest.fixture
def clean_copy(tmp_path):
    """A clean checkout in a temp folder, with `.env` copied from `.env.example`."""
    repo = tmp_path / "repo"
    repo.mkdir()
    for name in COPIED:
        shutil.copytree(ROOT / name, repo / name,
                        ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(ROOT / ".env.example", repo / ".env.example")
    shutil.copy(repo / ".env.example", repo / ".env")        # the rubric's `cp .env.example .env`
    return repo


def env_without_cms(repo, **extra):
    """The shell a grader has: no CMS_* variables, the clean copy's code first on the path."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("CMS_")}
    env["PYTHONPATH"] = str(repo)
    env.update(extra)
    return env


def run_python(repo, *args, **extra_env):
    return subprocess.run([sys.executable, *args], cwd=repo, capture_output=True, text=True,
                          env=env_without_cms(repo, **extra_env))


def example(name):
    for line in (ROOT / ".env.example").read_text().splitlines():
        if line.startswith(f"{name}="):
            return line.partition("=")[2].strip().strip('"')


def sign_in(db, username, password):
    client = TestClient(create_app(database=db))
    response = client.post("/login", data={"username": username, "password": password,
                                           "csrf_token": csrf_token(client)},
                           follow_redirects=False)
    return response.status_code == 303


def rewrite_env(repo, **values):
    text = (repo / ".env").read_text()
    for name, value in values.items():
        text = re.sub(rf"(?m)^{name}=.*$", f"{name}={value}", text)
    (repo / ".env").write_text(text)


# -- the rubric's commands ---------------------------------------------------------

def test_seed_works_after_copying_env_example_with_no_env_file_flag(clean_copy):
    result = run_python(clean_copy, "scripts/seed_demo.py")
    assert result.returncode == 0, result.stdout + result.stderr
    db = clean_copy / "cms.db"
    assert db.exists()
    assert sign_in(db, "admin", example("CMS_ADMIN_PASSWORD"))
    assert sign_in(db, "editor", example("CMS_EDITOR_PASSWORD"))


def test_create_admin_works_with_no_env_file_flag(clean_copy):
    result = run_python(clean_copy, "-m", "app.cli", "create-admin", "--username", "boss",
                        "--display-name", "ASA Leadership")
    assert result.returncode == 0, result.stdout + result.stderr
    assert sign_in(clean_copy / "cms.db", "boss", example("CMS_ADMIN_PASSWORD"))


def test_other_settings_come_from_dotenv_too(clean_copy):
    rewrite_env(clean_copy, CMS_SITE_TITLE='"A Title From The File"')
    result = run_python(clean_copy, "-c", "from app import settings; print(settings.SITE_TITLE)")
    assert result.stdout.strip() == "A Title From The File"


def test_a_clone_with_no_dotenv_still_starts_with_the_defaults(clean_copy):
    (clean_copy / ".env").unlink()
    result = run_python(clean_copy, "-c", "from app import settings; print(settings.SITE_TITLE)")
    assert result.returncode == 0 and result.stdout.strip() == "African Student Association"


# -- environment wins, secrets stay quiet --------------------------------------------

def test_a_variable_in_the_real_environment_wins_over_dotenv(clean_copy):
    rewrite_env(clean_copy, CMS_ADMIN_PASSWORD="password-from-the-file-1")
    result = run_python(clean_copy, "scripts/seed_demo.py",
                        CMS_ADMIN_PASSWORD="password-from-the-environment-2")
    assert result.returncode == 0, result.stdout + result.stderr
    db = clean_copy / "cms.db"
    assert sign_in(db, "admin", "password-from-the-environment-2")
    assert not sign_in(db, "admin", "password-from-the-file-1")


def test_the_environment_can_point_at_another_database(clean_copy, tmp_path):
    elsewhere = tmp_path / "elsewhere.db"
    result = run_python(clean_copy, "scripts/seed_demo.py", CMS_DATABASE=str(elsewhere))
    assert result.returncode == 0, result.stdout + result.stderr
    assert elsewhere.exists() and not (clean_copy / "cms.db").exists()


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def serve(repo, port):
    """`cms serve` as a grader runs it: from the repo folder, with no flags for the .env file."""
    return subprocess.Popen(
        [sys.executable, "-m", "app.cli", "serve", "--port", str(port)], cwd=repo,
        env=env_without_cms(repo), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        start_new_session=True)


def stop(process):
    os.killpg(process.pid, signal.SIGTERM)
    output, _ = process.communicate(timeout=30)
    return output


def test_cms_serve_reads_dotenv_signs_in_and_prints_no_secret(clean_copy):
    secrets = {"CMS_SECRET_KEY": "a-very-secret-signing-key-0123456789",
               "CMS_ADMIN_PASSWORD": "admin-secret-passphrase-1",
               "CMS_EDITOR_PASSWORD": "editor-secret-passphrase-2"}
    rewrite_env(clean_copy, **secrets)
    seed = run_python(clean_copy, "scripts/seed_demo.py")
    assert seed.returncode == 0, seed.stdout + seed.stderr

    port = free_port()
    process = serve(clean_copy, port)
    try:
        client = httpx.Client(base_url=f"http://127.0.0.1:{port}")
        for _ in range(100):
            try:
                page = client.get("/login")
                break
            except httpx.TransportError:
                time.sleep(0.2)
        else:
            pytest.fail("cms serve did not start")
        token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        response = client.post("/login", data={"username": "admin", "csrf_token": token,
                                               "password": secrets["CMS_ADMIN_PASSWORD"]},
                               follow_redirects=False)
        assert response.status_code == 303 and response.headers["location"] == "/admin"
        assert client.get("/admin").status_code == 200
    finally:
        output = stop(process)
    seed_output = seed.stdout + seed.stderr
    for secret in secrets.values():
        assert secret not in output and secret not in seed_output
    assert b"admin-secret-passphrase-1" not in (clean_copy / "cms.db").read_bytes()


def test_a_dollar_sign_in_a_password_stays_literal(clean_copy):
    rewrite_env(clean_copy, CMS_ADMIN_PASSWORD="'pass-${HOME}-x1'")
    assert run_python(clean_copy, "scripts/seed_demo.py").returncode == 0
    assert sign_in(clean_copy / "cms.db", "admin", "pass-${HOME}-x1")


def test_the_env_file_can_be_somewhere_else(clean_copy, tmp_path):
    other = tmp_path / "other.env"
    other.write_text('CMS_SITE_TITLE="Title From Another File"\n')
    result = run_python(clean_copy, "-c", "from app import settings; print(settings.SITE_TITLE)",
                        CMS_ENV_FILE=str(other))
    assert result.stdout.strip() == "Title From Another File"


def test_the_loader_is_a_declared_and_locked_dependency():
    """app/settings.py imports dotenv directly, so pyproject.toml must declare it."""
    import tomllib
    declared = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["dependencies"]
    assert any(re.match(r"python-dotenv\b", requirement) for requirement in declared)
    lock = (ROOT / "uv.lock").read_text()
    assert 'name = "python-dotenv"' in lock
    assert '{ name = "python-dotenv", specifier = ">=1.0" }' in lock          # the direct edge
