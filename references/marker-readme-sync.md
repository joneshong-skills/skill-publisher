# Marker-Based README Sync — Per-Skill Download Block Auto-Update

蠶食自 ConardLi/garden-skills `scripts/release/update-readme.mjs:2-92`（2026-05-16）。

**用途**：在 README.md / CATALOG.md 用 inline marker 圍出「需要每次 release 更新的區塊」，release 工具自動 re-render markers 內容，**永遠指向最新 tag pinned zip**，user 無需手動維護連結。

## 為何重要

`skill-catalog/CATALOG.md` 目前用單一 `<!-- catalog:start --> ... <!-- catalog:end -->` 整段重 render，無法 per-skill 細粒度更新。ConardLi 的 per-skill marker 模式讓單個 skill release 只更新它自己那段，**不會誤動其他 skill 的內容**。

## Marker 約定

每個 skill 在 README/CATALOG 各占一個 marker block：

```markdown
<!-- DOWNLOAD:cannibalize:start -->
**cannibalize** v0.2.1 — [Download zip](https://github.com/joneshong-skills/cannibalize/releases/download/v0.2.1/cannibalize-v0.2.1.zip)
<!-- DOWNLOAD:cannibalize:end -->

<!-- DOWNLOAD:frontend-design:start -->
**frontend-design** v2.2.0 — [Download zip](https://github.com/joneshong-skills/frontend-design/releases/download/v2.2.0/frontend-design-v2.2.0.zip)
<!-- DOWNLOAD:frontend-design:end -->
```

Release pipeline 只 rewrite 對應的 marker，其他 markers 不動。

## Reference Implementation (Python)

```python
#!/usr/bin/env python3
"""Per-skill marker README sync — replaces single-block catalog:start pattern."""
import re
import sys
from pathlib import Path

# Multi-language support: list all README files to sync
README_FILES = [
    {"path": Path("README.md"), "lang": "en"},
    {"path": Path("README.zh.md"), "lang": "zh"},
]

COPY = {
    "en": {"label": "Download v{v} .zip", "unreleased": "_(no release yet)_"},
    "zh": {"label": "下載 v{v} .zip", "unreleased": "_(尚未發布)_"},
}

REPO_BASE = "https://github.com/joneshong-skills"  # change per org

def render_block(skill: str, version: str | None, lang: str) -> str:
    """Return the inner content for a marker block."""
    copy = COPY[lang]
    if version is None:
        return f"\n**{skill}** — {copy['unreleased']}\n"
    label = copy["label"].format(v=version)
    url = f"{REPO_BASE}/{skill}/releases/download/v{version}/{skill}-v{version}.zip"
    return f"\n**{skill}** v{version} — [{label}]({url})\n"

def rewrite_readme(content: str, blocks: dict[str, str]) -> str:
    """Replace each <!-- DOWNLOAD:<skill>:start --> ... :end --> block."""
    out = content
    for skill, body in blocks.items():
        # Note: escape skill name for regex
        skill_esc = re.escape(skill)
        pattern = re.compile(
            rf"(<!--\s*DOWNLOAD:{skill_esc}:start\s*-->)([\s\S]*?)(<!--\s*DOWNLOAD:{skill_esc}:end\s*-->)",
            re.MULTILINE,
        )

        def _replace(m):
            return f"{m.group(1)}{body}{m.group(3)}"
        out = pattern.sub(_replace, out)
    return out

def main():
    # Read registry to get all skills + their latest tag versions
    registry = load_registry()  # returns {slug: latest_version}

    for cfg in README_FILES:
        if not cfg["path"].exists():
            continue
        content = cfg["path"].read_text()
        blocks = {
            slug: render_block(slug, version, cfg["lang"])
            for slug, version in registry.items()
        }
        new = rewrite_readme(content, blocks)
        if new != content:
            cfg["path"].write_text(new)
            print(f"✅ updated {cfg['path']}")

if __name__ == "__main__":
    main()
```

## Idempotency 保證

Marker 是 invariant — 多次重跑同樣 input → 同樣 output。`render_catalog.py` 現用單一 `catalog:start` 整段重 render 的問題：誤改動 user 在 marker 內手寫的補充內容。Per-skill marker 把更新範圍縮到最小，**降低意外覆蓋風險**。

## Migration from `catalog:start` 單 marker

`skill-catalog/CATALOG.md` 目前長這樣：

```markdown
<!-- catalog:start -->
| skill | version | description |
...
<!-- catalog:end -->
```

升級為 per-skill marker：

```markdown
<!-- catalog:start -->
<!-- DOWNLOAD:cannibalize:start -->
<!-- DOWNLOAD:cannibalize:end -->

<!-- DOWNLOAD:frontend-design:start -->
<!-- DOWNLOAD:frontend-design:end -->
...
<!-- catalog:end -->
```

外層 `catalog:start` 仍包覆全表（讓「初次 scaffold」工具能定位）；內層 per-skill markers 處理每行細粒度更新。

## 多語言 README 自動同步

少爺場景：`README.md` (en) + `README.zh.md` (zh) 並存時，per-skill marker 在兩個檔案都 rewrite，無需手動翻譯下載連結（連結結構跨語言一致）。

`COPY` 字典只翻譯按鈕文字 + unreleased placeholder，downland URL 不翻譯。

## 為何沒整合到 render_catalog.py

`skill-publisher` 已 archive。本檔留 reference implementation；若 publisher 復活或 skill-catalog 升級採用，照本檔直接抄錄。Marker 約定本身（`<!-- DOWNLOAD:<slug>:start/end -->`）可以**現在就在任何 README 預埋**，等 tool 來填即可。

## 相關 patterns

- 版號管理：[manifest-state-conflict.md](manifest-state-conflict.md)
- CI 驗證：[pr-validation-gate.md](pr-validation-gate.md)
