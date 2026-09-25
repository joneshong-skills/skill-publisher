"""A skill whose origin is someone else's repo is tracked upstream, not
waiting to be published to the org."""

import importlib.util
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "bootstrap_registry.py"


def load():
    spec = importlib.util.spec_from_file_location("registry_under_test", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def skill_with_unpushed_commit(tmp_path, origin_url):
    skill = tmp_path / "demo"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nname: demo\n---\n")
    bare = tmp_path / "bare.git"
    git("init", "-q", "--bare", str(bare), cwd=tmp_path)
    ident = ("-c", "user.email=t@t", "-c", "user.name=t")
    git("init", "-q", "-b", "main", cwd=skill)
    git(*ident, "add", ".", cwd=skill)
    git(*ident, "commit", "-q", "-m", "one", cwd=skill)
    git("remote", "add", "origin", str(bare), cwd=skill)
    git("push", "-q", "-u", "origin", "main", cwd=skill)
    git("remote", "set-url", "origin", origin_url, cwd=skill)
    (skill / "SKILL.md").write_text("---\nname: demo\n---\nmore\n")
    git(*ident, "commit", "-q", "-am", "two", cwd=skill)
    return skill


@pytest.mark.parametrize(
    ("origin", "expected"),
    [
        ("https://github.com/browser-use/video-use.git", "upstream"),
        ("https://github.com/joneshong-skills/cc-skill-demo.git", "needs-update"),
    ],
)
def test_sync_status_follows_the_origin_owner(tmp_path, origin, expected):
    registry = load()
    skill = skill_with_unpushed_commit(tmp_path, origin)
    assert registry.git_status(skill)["sync_status"] == expected
