# Manifest-State Conflict Detection — synced / ahead / behind

蠶食自 ConardLi/garden-skills `scripts/release/cut-release.mjs:184-210`（2026-05-16）。

**用途**：發布 skill 前比較 `manifest.version` vs 上一個 git tag 的 version，分類三種狀態，防止 publish 階段意外 double-bump 版號。

## 三種狀態

| 狀態 | 條件 | 動作 |
|---|---|---|
| **synced** | manifest.version == last_tag.version | bump 一次（patch/minor/major） |
| **ahead** | manifest.version > last_tag.version | 開發者已預先 bump，**honour manifest，不重複 bump** |
| **behind** | manifest.version < last_tag.version | manifest 比 published 還舊，**raise error 強制 user 確認** |

## 為何重要

少爺場景：開發 skill 時改了 version 但忘了 publish，下次 publish 流程若無腦 bump → 變雙倍 bump，造成 version 跳號。`ahead` 狀態正是這個情境。

## Reference Implementation (Python)

```python
# scripts/publish.py 加入此檢測

import re
import subprocess
from pathlib import Path

SEMVER_RE = re.compile(r'^(\d+)\.(\d+)\.(\d+)(?:-[0-9A-Za-z.-]+)?$')

def parse_semver(v: str) -> tuple[int, int, int]:
    m = SEMVER_RE.match(v)
    if not m:
        raise ValueError(f"Invalid SemVer: {v}")
    return tuple(int(x) for x in m.groups()[:3])

def get_last_tag_version(skill_slug: str) -> str | None:
    """Tag format: <slug>-v<X.Y.Z>"""
    try:
        out = subprocess.check_output(
            ["git", "tag", "-l", f"{skill_slug}-v*", "--sort=-version:refname"],
            text=True,
        )
        tags = [t.strip() for t in out.splitlines() if t.strip()]
        if not tags:
            return None
        return tags[0].removeprefix(f"{skill_slug}-v")
    except subprocess.CalledProcessError:
        return None

def detect_manifest_state(manifest_version: str, skill_slug: str) -> tuple[str, str | None]:
    """Returns (state, last_tag_version)."""
    last = get_last_tag_version(skill_slug)
    if last is None:
        return ("initial", None)  # never published
    cmp = (parse_semver(manifest_version) > parse_semver(last)) - (
        parse_semver(manifest_version) < parse_semver(last)
    )
    if cmp == 0:
        return ("synced", last)
    if cmp > 0:
        return ("ahead", last)
    return ("behind", last)

# Usage at publish entry point:
state, last_v = detect_manifest_state(manifest["version"], slug)
if state == "ahead":
    print(f"⚠️ manifest.version {manifest['version']} > last tag {last_v} — honouring manifest, skipping bump")
    next_version = manifest["version"]
elif state == "behind":
    raise SystemExit(
        f"❌ manifest.version {manifest['version']} < last tag {last_v}. "
        f"Bump manifest or pass --force-rollback."
    )
elif state == "synced":
    next_version = bump_version(last_v, args.bump)  # patch/minor/major
elif state == "initial":
    next_version = manifest["version"]  # first release
```

## CLI 整合

```bash
publish.py --skill <slug> --bump patch
# Auto-detects state. ahead → uses manifest as-is. behind → errors out.

publish.py --skill <slug> --bump patch --force-rollback
# Override "behind" check (rare, e.g. after botched release).
```

## 為何沒直接 implement 到 publish.py

`skill-publisher` skill 已 archive 到 `skills-archive/skill-publisher-20260506/`。本 pattern 留為 reference implementation，未來 publisher 復活或新 publish 流程採用時，照本檔直接抄錄。

## 範例 git tag layout

```
cannibalize-v0.2.0
cannibalize-v0.2.1
frontend-design-v2.1.0
frontend-design-v2.2.0
image-prompt-v0.1.0
```

Tag format `<slug>-v<semver>`，每個 skill 獨立版號。詳見 [`pr-validation-gate.md`](pr-validation-gate.md) 的 tag-as-contract pattern。
