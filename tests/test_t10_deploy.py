"""T10: `cms deploy` pushes the export to the Pages branch, tested without GitHub.

Seam 3 (the `cms` command). The "remote" is a bare Git repository in a temporary
folder, and Git is limited to the `file` protocol, so nothing here can reach the
network. The tests run the real `cms publish` and then the real `cms deploy` from a
working repository, with the site where the real command puts it (`<repo>/site`).
"""
import os
import subprocess
from types import SimpleNamespace

import pytest

from app import posts, settings
from app.cli import main
from tests.test_t03_publish import add_post

GIT_ISOLATION = {"GIT_ALLOW_PROTOCOL": "file", "GIT_CONFIG_GLOBAL": os.devnull,
                 "GIT_CONFIG_SYSTEM": os.devnull, "GIT_TERMINAL_PROMPT": "0",
                 "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
                 "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com"}
# Set when pytest is run from a Git hook; they would point every git call at the developer's repository.
GIT_REDIRECTS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
                 "GIT_COMMON_DIR", "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_COUNT")


def git(*args, cwd=None, git_dir=None, binary=False):
    command = ["git"] + (["--git-dir", str(git_dir)] if git_dir else []) + list(args)
    return subprocess.run(command, cwd=cwd, capture_output=True, check=True,
                          text=not binary).stdout


@pytest.fixture
def remote(tmp_path, monkeypatch, db_path):
    """A working repository whose `origin` is a local bare repository (`.bare`), site at `.work/site`."""
    for name in GIT_REDIRECTS:
        monkeypatch.delenv(name, raising=False)
    for name, value in GIT_ISOLATION.items():
        monkeypatch.setenv(name, value)
    bare, work = tmp_path / "pages-remote.git", tmp_path / "work"
    git("init", "--bare", "-q", str(bare))
    work.mkdir()
    git("init", "-q", cwd=work)
    git("remote", "add", "origin", str(bare), cwd=work)
    (work / "README").write_text("the project, not the site")
    git("add", ".", cwd=work)
    git("commit", "-qm", "initial", cwd=work)
    monkeypatch.chdir(work)
    # The only place anything can be pushed is a folder on this machine.
    assert git("remote", "get-url", "origin", cwd=work).strip() == str(bare)
    monkeypatch.setattr(settings, "SITE", work / "site")
    monkeypatch.setattr(settings, "DATABASE_PATH", db_path)
    return SimpleNamespace(bare=bare, work=work, site=work / "site", db=db_path)


def pages_files(remote):
    return set(git("ls-tree", "-r", "--name-only", "gh-pages", git_dir=remote.bare).split())


def publish_and_deploy(remote, capsys):
    assert main(["publish"]) == 0
    capsys.readouterr()
    code = main(["deploy", "--message", "Publish test"])
    return code, capsys.readouterr().out


def test_deploy_pushes_every_exported_file_to_gh_pages_and_nothing_else(remote, capsys):
    add_post(remote.db, "Afrobeat Night", "What: music")

    code, out = publish_and_deploy(remote, capsys)

    assert code == 0 and "Pushed to gh-pages" in out
    exported = {str(p.relative_to(remote.site)) for p in remote.site.rglob("*") if p.is_file()}
    assert pages_files(remote) - exported == {".nojekyll"}        # the only extra file
    assert exported <= pages_files(remote)
    for name in exported:                                          # byte for byte
        assert git("show", f"gh-pages:{name}", git_dir=remote.bare, binary=True) == \
            (remote.site / name).read_bytes(), name
    assert "posts/afrobeat-night.html" in pages_files(remote)
    assert git("branch", "--list", git_dir=remote.bare).split() == ["gh-pages"]    # no main pushed
    assert "README" not in pages_files(remote)                      # the project is not the site


def test_a_draft_never_reaches_the_pages_branch_even_on_a_second_deploy(remote, capsys):
    add_post(remote.db, "Afrobeat Night", "What: music")
    add_post(remote.db, "Quiet Draft", "not for the public", published=False)

    def nothing_of_the_draft():
        files = pages_files(remote)
        assert not any("quiet-draft" in name for name in files)
        text = "".join(git("show", f"gh-pages:{name}", git_dir=remote.bare)
                       for name in files if name.endswith((".html", ".css")))
        assert "Quiet Draft" not in text and "not for the public" not in text

    publish_and_deploy(remote, capsys)
    nothing_of_the_draft()
    publish_and_deploy(remote, capsys)                              # a second deploy, draft still there
    nothing_of_the_draft()


def test_a_second_deploy_replaces_the_branch_so_an_unpublished_post_is_gone(remote, capsys):
    post_id = add_post(remote.db, "Afrobeat Night", "What: music")
    add_post(remote.db, "Movie Evening", "What: film")
    publish_and_deploy(remote, capsys)
    assert {"posts/afrobeat-night.html", "posts/movie-evening.html"} <= pages_files(remote)

    posts.unpublish(remote.db, post_id)
    code, _ = publish_and_deploy(remote, capsys)

    assert code == 0
    files = pages_files(remote)
    assert "posts/afrobeat-night.html" not in files and "posts/movie-evening.html" in files
    announcements = git("show", "gh-pages:announcements.html", git_dir=remote.bare)
    assert "Afrobeat Night" not in announcements and "Movie Evening" in announcements
    assert len(git("rev-list", "gh-pages", git_dir=remote.bare).split()) == 2     # a new commit


def test_deploy_leaves_the_remote_s_other_branches_alone(remote, capsys):
    git("push", "-q", "origin", "HEAD:refs/heads/main", cwd=remote.work)
    before = git("rev-parse", "main", git_dir=remote.bare).strip()
    add_post(remote.db, "Afrobeat Night", "What: music")

    publish_and_deploy(remote, capsys)

    assert git("rev-parse", "main", git_dir=remote.bare).strip() == before
    assert sorted(git("branch", "--list", "--format=%(refname:short)",
                      git_dir=remote.bare).split()) == ["gh-pages", "main"]
    assert "README" not in pages_files(remote)


def test_deploy_refuses_when_there_is_no_site_and_pushes_nothing(remote, capsys):
    assert not remote.site.exists()
    assert main(["deploy"]) == 1
    assert "cms publish" in capsys.readouterr().out
    assert git("branch", "--list", git_dir=remote.bare).strip() == ""


def test_the_safety_net_blocks_a_network_remote_for_the_right_reason(remote, capfd):
    """The net the other tests rely on: with only `file` allowed, an https remote is refused by git."""
    add_post(remote.db, "Afrobeat Night", "What: music")
    assert main(["publish"]) == 0
    git("remote", "set-url", "origin", "https://github.com/example/never-contacted.git", cwd=remote.work)
    capfd.readouterr()

    assert main(["deploy"]) != 0

    assert "transport 'https' not allowed" in capfd.readouterr().err
