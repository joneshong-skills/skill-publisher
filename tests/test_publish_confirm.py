"""publish_skill() must publish to the repo origin names and must not exit 0
when it stopped at a confirmation prompt.

Runs against a real local bare repo: origin carries the GitHub URL publish.py
reads, and git's pushInsteadOf sends the actual push to the bare repo. Only
`gh` and the two preflight gates are replaced, so "was it pushed" is read from
the remote itself.
"""

import builtins
import importlib.util
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "publish.py"
ORG_URL = "https://github.com/joneshong-skills/"


def load_publish():
    spec = importlib.util.spec_from_file_location("publish_under_test", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git(*args, cwd):
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )


def build(tmp_path, monkeypatch, origin: str | None = ORG_URL + "demo.git"):
    publish = load_publish()
    skill = tmp_path / "skills" / "demo"
    skill.mkdir(parents=True)
    for name in ("SKILL.md", "README.md", "README.zh.md", ".gitignore", "LICENSE"):
        (skill / name).write_text(f"{name}\n")
    remote = tmp_path / "remote.git"
    git("init", "-q", "--bare", str(remote), cwd=tmp_path)
    git("init", "-q", "-b", "main", cwd=skill)
    ident = ("-c", "user.email=t@t", "-c", "user.name=t")
    git(*ident, "add", ".", cwd=skill)
    git(*ident, "commit", "-q", "-m", "init", cwd=skill)
    if origin:
        git("remote", "add", "origin", origin, cwd=skill)
        git("config", f"url.{remote}.pushInsteadOf", origin, cwd=skill)

    monkeypatch.setattr(publish, "SKILLS_DIR", skill.parent)
    monkeypatch.setattr(publish, "preflight_secrets_pii", lambda d: None)
    monkeypatch.setattr(publish, "preflight_structure", lambda d: None)

    state = {"existing": {"joneshong-skills/demo"}, "gh_calls": [], "viewed": []}
    real_run = subprocess.run

    def fake_run(cmd, *a, **kw):
        if cmd and cmd[0] == "gh":
            state["gh_calls"].append(cmd[1:3])
            if cmd[1:3] == ["repo", "view"]:
                state["viewed"].append(cmd[3])
                rc = 0 if cmd[3] in state["existing"] else 1
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

    return publish, state, remote_has_main, skill


@pytest.fixture
def env(tmp_path, monkeypatch):
    publish, state, remote_has_main, _ = build(tmp_path, monkeypatch)
    return publish, state, remote_has_main


def run_publish(publish, **kw):
    kwargs = {
        "skill_name": "demo",
        "dry_run": False,
        "skip_logo": True,
        "register_note": False,
    }
    kwargs.update(kw)
    publish.publish_skill(**kwargs)


def answer(monkeypatch, reply):
    def fake_input(prompt=""):
        if reply is EOFError:
            raise EOFError
        return reply

    monkeypatch.setattr(builtins, "input", fake_input)


def no_prompt(monkeypatch):
    def fail(prompt=""):
        raise AssertionError("--yes must not prompt")

    monkeypatch.setattr(builtins, "input", fail)


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
    state["existing"] = set()
    answer(monkeypatch, EOFError)
    with pytest.raises(SystemExit) as exc:
        run_publish(publish)
    assert exc.value.code == 3
    assert ["repo", "create"] not in state["gh_calls"]


def test_confirmed_repo_creation_finishes_with_exit_0(env, monkeypatch):
    publish, state, _ = env
    state["existing"] = set()
    answer(monkeypatch, "y")
    run_publish(publish)
    assert ["repo", "create"] in state["gh_calls"]


def test_assume_yes_pushes_without_prompting(env, monkeypatch):
    publish, _, remote_has_main = env
    no_prompt(monkeypatch)
    run_publish(publish, assume_yes=True)
    assert remote_has_main()


def test_yes_flag_reaches_publish_skill(monkeypatch):
    publish = load_publish()
    seen = {}
    monkeypatch.setattr(publish, "publish_skill", lambda **kw: seen.update(kw))
    monkeypatch.setattr("sys.argv", ["publish.py", "demo", "--yes"])
    publish.main()
    assert seen["assume_yes"] is True


def test_origin_repo_name_wins_over_the_slug(tmp_path, monkeypatch):
    publish, state, remote_has_main, _ = build(
        tmp_path, monkeypatch, origin=ORG_URL + "cc-skill-demo.git"
    )
    state["existing"] = {"joneshong-skills/cc-skill-demo"}
    no_prompt(monkeypatch)
    run_publish(publish, assume_yes=True)
    assert state["viewed"] == ["joneshong-skills/cc-skill-demo"]
    assert ["repo", "create"] not in state["gh_calls"]
    assert remote_has_main()


def test_origin_outside_the_org_is_refused_before_touching_the_repo(
    tmp_path, monkeypatch
):
    publish, state, _, skill = build(
        tmp_path, monkeypatch, origin="https://github.com/browser-use/demo.git"
    )
    (skill / "LICENSE").unlink()
    (skill / ".gitignore").unlink()
    head = git("rev-parse", "HEAD", cwd=skill).stdout
    no_prompt(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        run_publish(publish, assume_yes=True)
    assert exc.value.code == 1
    assert not (skill / "LICENSE").exists()
    assert not (skill / ".gitignore").exists()
    assert git("rev-parse", "HEAD", cwd=skill).stdout == head
    assert state["gh_calls"] == []


def test_no_origin_falls_back_to_the_slug(tmp_path, monkeypatch):
    publish, state, _, _ = build(tmp_path, monkeypatch, origin=None)
    state["existing"] = set()
    answer(monkeypatch, EOFError)
    with pytest.raises(SystemExit):
        run_publish(publish)
    assert state["viewed"] == ["joneshong-skills/demo"]


def test_a_look_alike_host_is_refused(tmp_path, monkeypatch):
    publish, state, _, _ = build(
        tmp_path, monkeypatch, origin="https://evil.example/github.com/joneshong-skills/demo.git")
    no_prompt(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        run_publish(publish, assume_yes=True)
    assert exc.value.code == 1
    assert state["gh_calls"] == []


def test_an_insteadof_rewrite_does_not_hide_the_org_origin(tmp_path, monkeypatch):
    publish, state, remote_has_main, skill = build(tmp_path, monkeypatch)
    bare = tmp_path / "remote.git"
    git("config", f"url.{bare}.insteadOf", ORG_URL + "demo.git", cwd=skill)
    no_prompt(monkeypatch)
    run_publish(publish, assume_yes=True)
    assert state["viewed"] == ["joneshong-skills/demo"]
    assert remote_has_main()


def test_the_org_name_is_case_insensitive(tmp_path, monkeypatch):
    publish, state, remote_has_main, _ = build(
        tmp_path, monkeypatch, origin="https://github.com/JonesHong-Skills/demo.git")
    no_prompt(monkeypatch)
    run_publish(publish, assume_yes=True)
    assert state["viewed"] == ["joneshong-skills/demo"]
    assert remote_has_main()
