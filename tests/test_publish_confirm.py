"""A publish that stops at the confirmation prompt must not exit 0.

publish_skill() runs against a real local bare repo as origin; only `gh` and
the two preflight gates are replaced, so "was it pushed" is read from the
remote itself.
"""

import builtins
import importlib.util
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "publish.py"


def load_publish():
    spec = importlib.util.spec_from_file_location("publish_under_test", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def env(tmp_path, monkeypatch):
    publish = load_publish()
    skills = tmp_path / "skills"
    skill = skills / "demo"
    skill.mkdir(parents=True)
    for name in ("SKILL.md", "README.md", "README.zh.md", ".gitignore", "LICENSE"):
        (skill / name).write_text(f"{name}\n")
    remote = tmp_path / "remote.git"
    git("init", "-q", "--bare", str(remote), cwd=tmp_path)
    git("init", "-q", "-b", "main", cwd=skill)
    git("-c", "user.email=t@t", "-c", "user.name=t", "add", ".", cwd=skill)
    git(
        "-c",
        "user.email=t@t",
        "-c",
        "user.name=t",
        "commit",
        "-q",
        "-m",
        "init",
        cwd=skill,
    )
    git("remote", "add", "origin", str(remote), cwd=skill)

    monkeypatch.setattr(publish, "SKILLS_DIR", skills)
    monkeypatch.setattr(publish, "preflight_secrets_pii", lambda d: None)
    monkeypatch.setattr(publish, "preflight_structure", lambda d: None)

    state = {"repo_exists": True, "gh_calls": []}
    real_run = subprocess.run

    def fake_run(cmd, *a, **kw):
        if cmd and cmd[0] == "gh":
            state["gh_calls"].append(cmd[1:3])
            if cmd[1:3] == ["repo", "view"]:
                rc = 0 if state["repo_exists"] else 1
            else:
                rc = 0 if cmd[1:3] == ["repo", "create"] else 1
            return subprocess.CompletedProcess(cmd, rc, stdout="", stderr="")
        return real_run(cmd, *a, **kw)

    monkeypatch.setattr(publish.subprocess, "run", fake_run)

    def remote_has_main():
        r = real_run(
            ["git", "-C", str(remote), "rev-parse", "--verify", "-q", "main"],
            capture_output=True,
        )
        return r.returncode == 0

    return publish, state, remote_has_main


def run_publish(publish, **kw):
    kwargs = {"skill_name": "demo", "dry_run": False, "skip_logo": True, "register_note": False}
    kwargs.update(kw)
    publish.publish_skill(**kwargs)


def answer(monkeypatch, reply):
    def fake_input(prompt=""):
        if reply is EOFError:
            raise EOFError
        return reply

    monkeypatch.setattr(builtins, "input", fake_input)


@pytest.mark.parametrize("reply", [EOFError, "n", ""])
def test_declined_push_exits_nonzero_and_pushes_nothing(env, monkeypatch, reply):
    publish, _, remote_has_main = env
    answer(monkeypatch, reply)
    with pytest.raises(SystemExit) as exc:
        run_publish(publish)
    assert exc.value.code == 3
    assert not remote_has_main()


def test_declined_repo_creation_exits_nonzero(env, monkeypatch):
    publish, state, _ = env
    state["repo_exists"] = False
    answer(monkeypatch, EOFError)
    with pytest.raises(SystemExit) as exc:
        run_publish(publish)
    assert exc.value.code == 3
    assert ["repo", "create"] not in state["gh_calls"]


def test_confirmed_repo_creation_finishes_with_exit_0(env, monkeypatch):
    publish, state, _ = env
    state["repo_exists"] = False
    answer(monkeypatch, "y")
    run_publish(publish)
    assert ["repo", "create"] in state["gh_calls"]


def test_assume_yes_pushes_without_prompting(env, monkeypatch):
    publish, _, remote_has_main = env

    def no_prompt(prompt=""):
        raise AssertionError("--yes must not prompt")

    monkeypatch.setattr(builtins, "input", no_prompt)
    run_publish(publish, assume_yes=True)
    assert remote_has_main()


def test_yes_flag_reaches_publish_skill(monkeypatch):
    publish = load_publish()
    seen = {}
    monkeypatch.setattr(publish, "publish_skill", lambda **kw: seen.update(kw))
    monkeypatch.setattr("sys.argv", ["publish.py", "demo", "--yes"])
    publish.main()
    assert seen["assume_yes"] is True
