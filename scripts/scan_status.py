#!/usr/bin/env python3
"""Scan all skills and report publishing status."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

SKILLS_DIR = Path.home() / ".claude" / "skills"
GITHUB_ORG = "joneshong-skills"


def get_github_repos():
    """Fetch existing repos from the GitHub org."""
    try:
        result = subprocess.run(
            ["gh", "repo", "list", GITHUB_ORG, "--limit", "100",
             "--json", "name", "--jq", ".[].name"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            return set(result.stdout.strip().split("\n")) - {""}
        return set()
    except Exception:
        return set()


def scan_skill(skill_dir: Path, github_repos: set):
    """Check a single skill's publishing status."""
    name = skill_dir.name
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return None

    return {
        "name": name,
        "has_readme": (skill_dir / "README.md").exists(),
        "has_readme_zh": (skill_dir / "README.zh.md").exists(),
        "has_logo": (skill_dir / "logo.png").exists(),
        "has_github": name in github_repos,
        "has_git": (skill_dir / ".git").exists(),
    }


def main():
    parser = argparse.ArgumentParser(description="Scan skill publishing status")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--skill", type=str, help="Check single skill by name")
    parser.add_argument("--skills-dir", type=str, default=str(SKILLS_DIR))
    args = parser.parse_args()

    skills_dir = Path(args.skills_dir)
    github_repos = get_github_repos()

    results = []
    for d in sorted(skills_dir.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        if args.skill and d.name != args.skill:
            continue
        status = scan_skill(d, github_repos)
        if status:
            results.append(status)

    if args.json:
        print(json.dumps(results, indent=2))
        return

    # Summary
    total = len(results)
    readme_count = sum(1 for r in results if r["has_readme"])
    zh_count = sum(1 for r in results if r["has_readme_zh"])
    logo_count = sum(1 for r in results if r["has_logo"])
    github_count = sum(1 for r in results if r["has_github"])

    print(f"\n{'Skill':<28} {'README':>6} {'  zh':>6} {'Logo':>6} {'GitHub':>6} {'Git':>4}")
    print("-" * 62)
    for r in results:
        check = lambda v: "  OK" if v else "MISS"
        print(f"{r['name']:<28} {check(r['has_readme']):>6} {check(r['has_readme_zh']):>6} "
              f"{check(r['has_logo']):>6} {check(r['has_github']):>6} {check(r['has_git']):>4}")

    print("-" * 62)
    print(f"{'TOTAL':<28} {readme_count:>3}/{total:<2} {zh_count:>3}/{total:<2} "
          f"{logo_count:>3}/{total:<2} {github_count:>3}/{total:<2}")

    # Missing lists
    missing_readme = [r["name"] for r in results if not r["has_readme"]]
    missing_zh = [r["name"] for r in results if not r["has_readme_zh"]]
    missing_logo = [r["name"] for r in results if not r["has_logo"]]
    missing_github = [r["name"] for r in results if not r["has_github"]]

    if missing_readme:
        print(f"\nMissing README.md ({len(missing_readme)}):")
        for n in missing_readme:
            print(f"  - {n}")
    if missing_zh:
        print(f"\nMissing README.zh.md ({len(missing_zh)}):")
        for n in missing_zh:
            print(f"  - {n}")
    if missing_github:
        print(f"\nMissing GitHub repo ({len(missing_github)}):")
        for n in missing_github:
            print(f"  - {n}")


if __name__ == "__main__":
    main()
