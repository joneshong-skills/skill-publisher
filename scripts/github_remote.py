"""Parse a GitHub remote URL into (owner, repo).

Shared by publish.py and bootstrap_registry.py so the two cannot disagree
about who owns a skill's repo.
"""

import re
import subprocess

_PATTERN = re.compile(
    r"^(?:https?://(?:[^@/]+@)?github\.com/|git@github\.com:|ssh://git@github\.com/)"
    r"(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$",
    re.IGNORECASE,
)


def parse(url: str) -> tuple[str, str] | None:
    m = _PATTERN.match(url.strip())
    return (m.group("owner"), m.group("repo")) if m else None


def origin_url(repo_dir) -> str:
    """origin as configured, before insteadOf rewrites (`git remote get-url`
    applies them, which turns an org URL into whatever it is mirrored to)."""
    r = subprocess.run(
        ["git", "-C", str(repo_dir), "config", "--get", "remote.origin.url"],
        capture_output=True,
        text=True,
        check=False,
    )
    return r.stdout.strip() if r.returncode == 0 else ""
