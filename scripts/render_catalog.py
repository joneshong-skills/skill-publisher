#!/usr/bin/env python3
"""Render skill catalog table from registry.json into a Markdown file with markers.

Marker pattern (蠶食自 yao-open-skills/scripts/render_readme_catalog.py):
    <!-- catalog:start -->
    ...auto-generated table...
    <!-- catalog:end -->

Default target: ~/.claude/skills/skill-catalog/CATALOG.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REGISTRY_PATH = Path.home() / ".claude" / "data" / "skill-registry" / "registry.json"
DEFAULT_TARGET = Path.home() / ".claude" / "skills" / "skill-catalog" / "CATALOG.md"
START = "<!-- catalog:start -->"
END = "<!-- catalog:end -->"

SYNC_BADGE = {
    "published": "✅ published",
    "needs-update": "⚠️ needs-update",
    "draft": "📝 draft",
    "local-only": "🔒 local-only",
}


def render_table(skills: list[dict]) -> str:
    lines = [
        START,
        "",
        f"_Auto-generated from registry.json — total {len(skills)} skills._",
        "",
        "| Skill | Lifecycle | Sync | Tags | GitHub |",
        "| --- | --- | --- | --- | --- |",
    ]
    for s in sorted(skills, key=lambda x: x["slug"]):
        gh = f"[link]({s['github_url']})" if s.get("github_url") else "—"
        tags = ", ".join((s.get("tags") or [])[:3]) or "—"
        sync = SYNC_BADGE.get(s.get("sync_status", "draft"), s.get("sync_status", "?"))
        lines.append(f"| `{s['slug']}` | `{s['lifecycle']}` | {sync} | {tags} | {gh} |")
    lines.append("")
    lines.append(END)
    return "\n".join(lines)


def replace_block(text: str, table: str) -> str:
    if START not in text or END not in text:
        raise SystemExit(f"Markers {START!r} / {END!r} not found in target file.")
    start = text.index(START)
    end = text.index(END) + len(END)
    return text[:start] + table + text[end:]


def main():
    parser = argparse.ArgumentParser(description="Render skill catalog table")
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args()

    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    table = render_table(registry.get("skills", []))

    if not args.target.exists():
        raise SystemExit(f"Target not found: {args.target}. Create scaffold with markers first.")

    text = args.target.read_text(encoding="utf-8")
    updated = replace_block(text, table)
    args.target.write_text(updated, encoding="utf-8")
    print(f"Rendered {len(registry.get('skills', []))} skills to {args.target}")


if __name__ == "__main__":
    main()
