#!/usr/bin/env python3
"""Bootstrap ~/.claude/data/skill-registry/registry.json from ~/.claude/skills/*.

事實源：~/.claude/skills/<slug>/SKILL.md (frontmatter)
輸出：~/.claude/data/skill-registry/registry.json

蠶食自 yao-open-skills 的 registry pattern，移除 source_local_path 雙寫。
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import date, datetime
from pathlib import Path

import yaml

SKILLS_DIR = Path.home() / ".claude" / "skills"
REGISTRY_PATH = Path.home() / ".claude" / "data" / "skill-registry" / "registry.json"
GITHUB_ORG = "joneshong-skills"


def parse_frontmatter(skill_md: Path) -> dict:
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    body = text[3:end].strip()
    try:
        data = yaml.safe_load(body) or {}
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError:
        return {}


def first_sentence(text: str) -> str:
    if not text:
        return ""
    text = " ".join(text.split())
    for sep in ["。", ". ", "; "]:
        idx = text.find(sep)
        if 30 <= idx <= 200:
            return text[: idx + 1].strip()
    return text[:200].strip()


def detect_license(skill_dir: Path) -> str | None:
    lic = skill_dir / "LICENSE"
    if not lic.exists():
        return None
    head = lic.read_text(encoding="utf-8", errors="replace")[:500].upper()
    for token, name in [
        ("MIT LICENSE", "MIT"),
        ("APACHE LICENSE", "Apache-2.0"),
        ("BSD ", "BSD"),
        ("GNU GENERAL PUBLIC", "GPL"),
    ]:
        if token in head:
            return name
    return "custom"


def git_status(skill_dir: Path) -> dict:
    git_dir = skill_dir / ".git"
    if not git_dir.exists():
        return {
            "has_git": False,
            "remote_url": None,
            "github_url": None,
            "sync_status": "local-only",
            "last_synced_at": None,
            "last_commit_date": None,
        }

    def run(args: list[str]) -> str:
        try:
            r = subprocess.run(
                ["git", "-C", str(skill_dir)] + args, capture_output=True, text=True, timeout=10
            )
            return r.stdout.strip() if r.returncode == 0 else ""
        except Exception:
            return ""

    remote = run(["remote", "get-url", "origin"])
    last_commit = run(["log", "-1", "--format=%cI"])
    unpushed = run(["log", "@{u}..HEAD", "--oneline"])
    upstream_check = run(["rev-parse", "--abbrev-ref", "@{u}"])

    github_url = None
    if remote:
        m = re.search(r"github\.com[:/]([^/]+/[^/.]+)", remote)
        if m:
            github_url = f"https://github.com/{m.group(1)}"

    if not upstream_check:
        sync = "draft"
    elif unpushed:
        sync = "needs-update"
    else:
        sync = "published"

    return {
        "has_git": True,
        "remote_url": remote or None,
        "github_url": github_url,
        "sync_status": sync,
        "last_synced_at": last_commit[:10] if (sync == "published" and last_commit) else None,
        "last_commit_date": last_commit[:10] if last_commit else None,
    }


def list_org_repos() -> set[str]:
    try:
        r = subprocess.run(
            [
                "gh",
                "repo",
                "list",
                GITHUB_ORG,
                "--limit",
                "300",
                "--json",
                "name",
                "--jq",
                ".[].name",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if r.returncode == 0:
            return set(r.stdout.strip().split("\n")) - {""}
    except Exception:
        pass
    return set()


def build_entry(skill_dir: Path, org_repos: set[str]) -> dict | None:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return None
    fm = parse_frontmatter(skill_md)
    name = fm.get("name") or skill_dir.name
    desc = fm.get("description") or ""
    if isinstance(desc, list):
        desc = " ".join(str(x) for x in desc)
    summary = first_sentence(str(desc).strip())
    tags = fm.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    git = git_status(skill_dir)
    if not git["github_url"] and skill_dir.name in org_repos:
        git["github_url"] = f"https://github.com/{GITHUB_ORG}/{skill_dir.name}"

    mtime = datetime.fromtimestamp(skill_md.stat().st_mtime).date().isoformat()
    updated_at = git.get("last_commit_date") or mtime

    return {
        "slug": skill_dir.name,
        "title": name.replace("-", " ").title() if name == skill_dir.name else name,
        "summary": summary,
        "skill_path": f"~/.claude/skills/{skill_dir.name}",
        "lifecycle": "active",
        "sync_status": git["sync_status"],
        "github_url": git["github_url"],
        "remote_url": git["remote_url"],
        "license": detect_license(skill_dir),
        "tags": tags,
        "last_synced_at": git["last_synced_at"],
        "updated_at": updated_at,
    }


def main():
    parser = argparse.ArgumentParser(description="Bootstrap skill registry")
    parser.add_argument("--output", type=Path, default=REGISTRY_PATH)
    parser.add_argument("--no-gh", action="store_true", help="Skip gh org repo lookup")
    args = parser.parse_args()

    org_repos = set() if args.no_gh else list_org_repos()
    entries = []
    for d in sorted(SKILLS_DIR.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        entry = build_entry(d, org_repos)
        if entry:
            entries.append(entry)

    counts = {}
    for e in entries:
        counts[e["sync_status"]] = counts.get(e["sync_status"], 0) + 1

    registry = {
        "updated_at": date.today().isoformat(),
        "schema_version": 1,
        "github_org": GITHUB_ORG,
        "totals": {"skills": len(entries), **counts},
        "skills": entries,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(entries)} skills to {args.output}")
    print(f"Sync status: {counts}")


if __name__ == "__main__":
    main()
