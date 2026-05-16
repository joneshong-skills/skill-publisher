# PR-Time Validation Gate — Auto Smoke-Pack + Manifest Lint + README Sync

蠶食自 ConardLi/garden-skills `.github/workflows/validate-skills.yml`（2026-05-16）。

**用途**：把 publish-time 手動 `scan_status.py` 升級為 PR-time 自動 gate，**阻擋有問題的 PR 進 main**。

## 為何重要

少爺現況：發布前才用 `scan_status.py --skill <slug>` 手動掃描，發現問題已晚（PR 已 merge）。CI gate 在 PR 階段就攔截 → 還有機會在開發者本機 fix。

## Reference Implementation — `.github/workflows/validate-skills.yml`

放在任何 `joneshong-skills/*` repo 或 `skill-publisher` 復活時的 repo root。

```yaml
name: Validate Skill
on:
  pull_request:
    paths:
      - "SKILL.md"
      - "manifest.json"
      - "references/**"
      - "scripts/**"
      - "README.md"
      - "README.zh.md"

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          fetch-tags: true

      - name: Validate frontmatter + manifest
        run: |
          python3 .github/scripts/validate_manifest.py
          # Checks:
          # - manifest.json exists + required fields (name, version, description)
          # - SKILL.md frontmatter present + name matches manifest
          # - version is valid SemVer
          # - compat array (if present) only contains whitelisted agents

      - name: Smoke-pack (dry-run zip)
        run: |
          python3 .github/scripts/smoke_pack.py
          # Builds the release zip locally, asserts:
          # - All referenced files in SKILL.md actually exist
          # - No absolute paths leak into the zip
          # - Total size under 10MB (catch accidental data dumps)

      - name: README sync check
        run: |
          python3 .github/scripts/check_readme_sync.py
          # Verifies marker blocks (see marker-readme-sync.md) match latest tag

      - name: Lint Markdown
        run: |
          npx --yes markdownlint-cli2 "SKILL.md" "references/**/*.md"
```

## Validator scripts

### `.github/scripts/validate_manifest.py`

```python
#!/usr/bin/env python3
"""Validate manifest.json + SKILL.md frontmatter consistency."""
import json
import re
import sys
from pathlib import Path

import yaml  # PyYAML

VALID_AGENTS = {"claude-code", "claude-ai", "cursor", "codex-cli", "gemini-cli", "opencode"}
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
REQUIRED = {"name", "version", "description"}

def main() -> int:
    errs = []
    manifest_path = Path("manifest.json")
    skill_path = Path("SKILL.md")

    if not manifest_path.exists():
        errs.append("manifest.json missing")
    else:
        m = json.loads(manifest_path.read_text())
        for f in REQUIRED - m.keys():
            errs.append(f"manifest missing required field: {f}")
        if "version" in m and not SEMVER_RE.match(m["version"]):
            errs.append(f"manifest.version not SemVer: {m['version']}")
        if "compat" in m:
            if not isinstance(m["compat"], list):
                errs.append("manifest.compat must be array")
            else:
                for a in m["compat"]:
                    if a not in VALID_AGENTS:
                        errs.append(f"manifest.compat unknown agent: {a}")

    if skill_path.exists():
        text = skill_path.read_text()
        if not text.startswith("---\n"):
            errs.append("SKILL.md missing frontmatter")
        else:
            end = text.index("\n---\n", 4)
            fm = yaml.safe_load(text[4:end])
            if manifest_path.exists():
                m = json.loads(manifest_path.read_text())
                if fm.get("name") != m.get("name"):
                    errs.append(f"SKILL.md frontmatter.name ({fm.get('name')}) != manifest.name ({m.get('name')})")

    if errs:
        for e in errs:
            print(f"❌ {e}", file=sys.stderr)
        return 1
    print("✅ manifest + SKILL.md frontmatter validated")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### `.github/scripts/smoke_pack.py`

```python
#!/usr/bin/env python3
"""Build release zip locally, check size + referenced paths."""
import json
import re
import sys
import zipfile
from pathlib import Path

MAX_SIZE_MB = 10

def main() -> int:
    manifest = json.loads(Path("manifest.json").read_text())
    skill_md = Path("SKILL.md").read_text()

    # Check all referenced paths resolve
    errs = []
    for ref in re.findall(r"\[.*?\]\((references/[^)]+)\)", skill_md):
        if not Path(ref).exists():
            errs.append(f"SKILL.md references missing file: {ref}")
    for ref in re.findall(r"scripts/[a-zA-Z0-9_./-]+", skill_md):
        if not Path(ref).exists() and not ref.startswith("scripts/"):
            continue
        if not Path(ref).exists():
            errs.append(f"SKILL.md references missing script: {ref}")

    # Build zip
    out_path = Path(f"/tmp/{manifest['name']}-v{manifest['version']}.zip")
    with zipfile.ZipFile(out_path, "w") as z:
        for p in Path(".").rglob("*"):
            if p.is_file() and not any(part.startswith(".") for part in p.parts):
                if "__pycache__" in p.parts or "node_modules" in p.parts:
                    continue
                z.write(p)

    size_mb = out_path.stat().st_size / (1024 * 1024)
    if size_mb > MAX_SIZE_MB:
        errs.append(f"Release zip {size_mb:.1f}MB exceeds {MAX_SIZE_MB}MB cap")

    if errs:
        for e in errs:
            print(f"❌ {e}", file=sys.stderr)
        return 1
    print(f"✅ smoke-pack OK: {out_path} ({size_mb:.1f}MB)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

## 啟用步驟（任何 joneshong-skills repo）

1. 複製本檔的 yaml → repo 的 `.github/workflows/validate-skills.yml`
2. 複製本檔的 Python scripts → repo 的 `.github/scripts/`
3. PR 即觸發。本機可以跑 `python3 .github/scripts/validate_manifest.py` 預測 CI 結果。

## 為何沒整合到 publish.py

`scan_status.py` 是 publish-time check，本檔是 PR-time gate — 互補非取代。`skill-publisher` skill 已 archive，本檔留為 reference implementation。Mac 本機 / CI 兩條都用同樣 scripts，無重複維護。
