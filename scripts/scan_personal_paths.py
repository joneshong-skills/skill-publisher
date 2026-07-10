#!/usr/bin/env python3
"""scan_personal_paths.py — Scan publishable skill files for personal paths, emails, private IPs.

Ported and extended from affaan-m/ECC scripts/ci/validate-no-personal-paths.js.

Usage:
  scan_personal_paths.py <skill-dir-path-or-slug> [--json]

Exits 1 if any finding, 0 otherwise. Used as a fail-closed publish gate.
"""

import argparse
import json
import re
import sys
from pathlib import Path

SKILLS_DIR = Path.home() / ".claude" / "skills"

ALLOWED_EXT = {
    ".md",
    ".py",
    ".sh",
    ".js",
    ".ts",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".txt",
    ".css",
    ".html",
}

# Usernames that are documentation placeholders, not real leaks.
PLACEHOLDER_USERNAMES = {
    "example",
    "me",
    "user",
    "username",
    "you",
    "yourname",
    "yourusername",
    "your-username",
}

POSIX_USER_RE = re.compile(r"/Users/([a-zA-Z][a-zA-Z0-9._-]*)/")
WIN_USER_RE = re.compile(r"C:\\Users\\([a-zA-Z][a-zA-Z0-9._-]*)", re.IGNORECASE)
EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+-]+@(?:gmail|yahoo|outlook|icloud|protonmail)\.com"
)
PRIVATE_IP_RE = re.compile(
    r"\b(?:"
    r"192\.168\.\d{1,3}\.\d{1,3}"
    r"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
    r"|100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}"  # Tailscale CGNAT
    r")\b"
)


def truncate(s, n=80):
    s = s.strip()
    return s if len(s) <= n else s[:n] + "…"


def scan_line(text):
    hits = []
    for m in POSIX_USER_RE.finditer(text):
        if m.group(1).lower() not in PLACEHOLDER_USERNAMES:
            hits.append(m.group(0))
    for m in WIN_USER_RE.finditer(text):
        if m.group(1).lower() not in PLACEHOLDER_USERNAMES:
            hits.append(m.group(0))
    for m in EMAIL_RE.finditer(text):
        hits.append(m.group(0))
    for m in PRIVATE_IP_RE.finditer(text):
        hits.append(m.group(0))
    return hits


def collect_files(skill_dir):
    files = []
    for name in ["SKILL.md", "LICENSE"]:
        p = skill_dir / name
        if p.is_file():
            files.append(p)
    for p in sorted(skill_dir.glob("README*.md")):
        if p.is_file():
            files.append(p)
    for sub in ["scripts", "references", "assets"]:
        d = skill_dir / sub
        if d.is_dir():
            for p in sorted(d.rglob("*")):
                if p.is_file() and p.suffix.lower() in ALLOWED_EXT:
                    files.append(p)
    return files


def scan_skill_dir(skill_dir):
    findings = []
    for p in collect_files(skill_dir):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for hit in scan_line(line):
                findings.append({"path": str(p), "line": i, "match": hit})
    return findings


def resolve_target(arg):
    p = Path(arg).expanduser()
    if p.is_dir():
        return p
    return SKILLS_DIR / arg


def main():
    parser = argparse.ArgumentParser(
        prog="scan_personal_paths.py",
        description="Scan publishable skill files for personal paths, emails, private IPs.",
    )
    parser.add_argument(
        "target", help="Skill directory path or slug under ~/.claude/skills"
    )
    parser.add_argument("--json", action="store_true", help="Output findings as JSON")
    args = parser.parse_args()

    skill_dir = resolve_target(args.target)
    if not skill_dir.is_dir():
        print(f"error: skill directory not found: {skill_dir}", file=sys.stderr)
        sys.exit(2)

    findings = scan_skill_dir(skill_dir)

    if args.json:
        print(json.dumps(findings, indent=2, ensure_ascii=False))
    else:
        for f in findings:
            print(f"{f['path']}:{f['line']}: {truncate(f['match'])}")
        if not findings:
            print(f"[OK] no personal paths / emails / private IPs found in {skill_dir}")

    sys.exit(1 if findings else 0)


if __name__ == "__main__":
    main()
