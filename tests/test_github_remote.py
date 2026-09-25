"""The one parser both scripts trust to say who owns a skill's repo."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "github_remote", Path(__file__).resolve().parent.parent / "scripts" / "github_remote.py")
assert spec and spec.loader
github_remote = importlib.util.module_from_spec(spec)
spec.loader.exec_module(github_remote)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://github.com/joneshong-skills/cc-skill-demo.git", ("joneshong-skills", "cc-skill-demo")),
        ("https://github.com/joneshong-skills/demo", ("joneshong-skills", "demo")),
        ("https://github.com/joneshong-skills/demo/", ("joneshong-skills", "demo")),
        ("git@github.com:joneshong-skills/demo.git", ("joneshong-skills", "demo")),
        ("ssh://git@github.com/joneshong-skills/demo.git", ("joneshong-skills", "demo")),
        ("https://github.com/JonesHong-Skills/demo.git", ("JonesHong-Skills", "demo")),
        ("https://github.com/joneshong-skills/foo.bar.git", ("joneshong-skills", "foo.bar")),
        ("https://evil.example/github.com/joneshong-skills/demo.git", None),
        ("https://evil.example/?next=https://github.com/joneshong-skills/demo.git", None),
        ("https://gitlab.com/joneshong-skills/demo.git", None),
        ("/tmp/some/local/bare.git", None),
    ],
)
def test_parse(url, expected):
    assert github_remote.parse(url) == expected
