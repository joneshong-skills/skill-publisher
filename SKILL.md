---
name: skill-publisher
description: "publisher, publish, skills, push, github, update, repos"
version: 0.3.0
tools: Read, Write, Edit, Bash, Glob, Grep, WebSearch, sandbox_execute
argument-hint: "[skill-name | --all | --scan]"
---

# Skill Publisher

Publish skills to GitHub with bilingual READMEs, logos, and platform registration.
Handles the full lifecycle: scan status, generate READMEs, create logos, push to GitHub,
and register on DeepWiki and Context7.

## Agent Delegation

Delegate publishing operations to `worker` agent.

## Configuration

| Setting | Value |
|---------|-------|
| GitHub org | `joneshong-skills` |
| Skills dir | `~/.claude/skills/` |
| README languages | English (`README.md`) + Traditional Chinese (`README.zh.md`) |
| Logo path | `logo.png` at repo root (200px width in README) |
| License | MIT (default) |

## Workflow

### Step 1: Scan Status

> **Sandbox acceleration**: Bulk publish status scanning runs in `sandbox_execute` — `~/.claude/` imports are now supported.
>
> Preferred (Sandbox):
> ```python
> import sys, os; sys.path.insert(0, os.path.expanduser('~/.claude/skills/skill-publisher/scripts'))
> import scan_status
> result = scan_status.scan_all()
> output(result)
> ```
>
> Fallback (Bash):
> ```bash
> ~/.local/bin/python3 ~/.claude/skills/skill-publisher/scripts/scan_status.py --json
> ```

Run the scan to identify what needs publishing:

```bash
~/.local/bin/python3 ~/.claude/skills/skill-publisher/scripts/scan_status.py
```

For a single skill: add `--skill <name>`. For JSON output: add `--json`.

Present the results table to the user and confirm which skills to process.

### Step 2: Generate README.md (English)

For each skill, read `SKILL.md` and generate `README.md` using this template:

```html
<h1 align="center">[Skill Display Name]</h1>

<p align="center">
  <a href="README.md"><kbd><strong>English</strong></kbd></a>
  <a href="README.zh.md"><kbd>繁體中文</kbd></a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/joneshong-skills/[REPO]/main/logo.png" alt="[Name] Logo" width="200"/>
</p>

<p align="center">
  <a href="https://github.com/joneshong-skills/[REPO]">
    <img alt="GitHub" src="https://img.shields.io/github/stars/joneshong-skills/[REPO]?style=social">
  </a>
  <a href="https://deepwiki.com/joneshong-skills/[REPO]">
    <img alt="DeepWiki" src="https://img.shields.io/badge/DeepWiki-docs-blue">
  </a>
  <a href="https://github.com/joneshong-skills/[REPO]/blob/main/LICENSE">
    <img alt="License" src="https://img.shields.io/badge/license-MIT-green.svg">
  </a>
</p>

<p align="center">
  <strong>[One-line tagline from SKILL.md first paragraph]</strong>
</p>

<p align="center">
  [Extended description — 1-2 sentences]
</p>
```

After the header, include these sections derived from SKILL.md:

1. **Features** — 4-6 bullet points of key capabilities
2. **Usage** — Trigger phrases and example invocations
3. **Workflow** — Condensed version of the skill's workflow steps
4. **Integration** — Related skills and how they connect
5. **Installation** — How to install the skill in Claude Code
6. **License** — MIT

### Step 3: Generate README.zh.md

Translate the English README to Traditional Chinese. Keep all HTML markup, badge URLs,
and code blocks identical. Translate only prose text and section headings. Use the same
centered template header but swap the language toggle links:

```html
<a href="README.md"><kbd>English</kbd></a>
<a href="README.zh.md"><kbd><strong>繁體中文</strong></kbd></a>
```

### Step 4: Generate Logo

Use the `/image-gen` skill to create a simple, recognizable icon for each skill.

**Prompt formula:**
```
Simple flat icon for a [skill-domain] tool.
[1-2 visual metaphors from the skill's purpose].
Minimal design, solid background, no text, suitable as a small logo/favicon.
Style: flat design, clean lines, 2-3 colors max.
```

Save the generated image to `logo.png` at the skill directory root.
If `/image-gen` is unavailable or the user declines, skip this step and use a
placeholder badge instead of an `<img>` tag in the README.

#### Parallel Logo Generation (Batch Mode)

When processing multiple skills, generate logos in parallel using the Task tool
to dispatch sub-agents. **Limit concurrency to prevent context overflow.**

| Batch size | Condition |
|------------|-----------|
| **3** | Default — safe for most sessions |
| **2** | If conversation is already long or other skills are loaded |
| **1** | If context is near limit or previous batch had issues |

**Execution pattern:**

```
1. Collect all skills needing logos into a queue
2. Pop up to BATCH_SIZE skills from the queue
3. For each skill in the batch, launch a Task sub-agent:
   - subagent_type: "general-purpose"
   - prompt: "Use /image-gen to generate a logo for the [name] skill.
     [prompt formula with skill-specific details].
     Save the result to ~/.claude/skills/[name]/logo.png"
4. Wait for ALL sub-agents in the batch to complete
5. Verify each logo.png was created successfully
6. Repeat from step 2 until the queue is empty
7. Report: X/Y logos generated, list any failures
```

**Important:** Each sub-agent runs `/image-gen` independently — each gets its
own APFS-cloned profile via `mktemp + cp -c` (defined in image-gen's Session
Isolation). Do NOT launch more than 3 concurrent browser sessions —
Playwright resource contention causes failures beyond this limit.

### Step 4.5: Generate CHANGELOG.md

After the version bump in SKILL.md frontmatter, generate a changelog before pushing:

```bash
cd ~/.claude/skills/[name]
git-cliff --output CHANGELOG.md
git add CHANGELOG.md
```

If `git-cliff` is unavailable or the repo has no tags yet, skip this step gracefully
and note it in the lessons.md entry.

### Step 5: Push to GitHub

For each skill, initialize a git repo (if needed) and push:

```bash
cd ~/.claude/skills/[name]

# Init git if not already
git init
git add SKILL.md README.md README.zh.md assets/ scripts/ references/
git add -N . && git diff --name-only --diff-filter=o | grep -v '__pycache__' | xargs git add

# Ignore common patterns
echo -e "__pycache__/\n*.pyc\n.DS_Store\nobservations.md" > .gitignore
git add .gitignore

# Create LICENSE if missing
# (Write MIT license file)

git commit -m "Initial publish" # or "Update README and assets"

# Create GitHub repo if it doesn't exist
gh repo create joneshong-skills/[name] --public --description "[description from SKILL.md]" --source=. --remote=origin --push

# Or push to existing
git remote add origin https://github.com/joneshong-skills/[name].git 2>/dev/null
git push -u origin main
```

**Important:** Always confirm with user before creating repos or pushing.

### Step 6: Register on Platforms

#### DeepWiki

DeepWiki auto-indexes public GitHub repos. Trigger indexing by visiting:
```
https://deepwiki.com/joneshong-skills/[name]
```
Use WebFetch to trigger the initial index. Verify the page loads with content.

#### Context7

Context7 requires submission. Check if the library is already indexed:
```
mcpproxy call_tool_read(server="context7", tool="resolve-library-id", arguments={libraryName: "[name]", query: "[description]"})
```

If not found, inform the user to submit at `https://context7.com/` manually,
or attempt submission via the Context7 MCP tool if available.

## Batch Mode

When the user requests `--all` or "publish all skills":

1. Run scan to show full status
2. Confirm scope with user (all missing items, or specific subset)
3. Generate READMEs sequentially (each needs context from SKILL.md)
4. Generate logos in parallel batches of 3 (see Step 4 § Parallel Logo Generation)
5. Push repos one at a time (requires sequential git operations)
6. Batch-trigger DeepWiki indexing for all new repos
7. Report final status with re-scan

## Quick Reference: Publish Single Skill

```
/skill-publisher smart-search
```

1. Scan → show status for smart-search
2. Generate README.md + README.zh.md
3. Generate logo via /image-gen
4. Push to GitHub (create repo if needed)
5. Trigger DeepWiki indexing
6. Check Context7 registration

## Sandbox Optimization

This skill is **sandbox-optimized**. Batch operations run inside `sandbox_execute`:

- **Publish status scan**: Import `scripts/scan_status.py` in sandbox to batch-check README, logo, GitHub, and git status for all skills in one call
- **Batch status reporting**: Import `scripts/` in sandbox to aggregate scan results across all skills and return structured JSON for pipeline consumption

Fallback (Bash):
- `~/.local/bin/python3 ~/.claude/skills/skill-publisher/scripts/scan_status.py` — run status scan via Bash when sandbox is unavailable

Principle: **Deterministic batch work → sandbox; reasoning/presentation → LLM.**

## Continuous Improvement

This skill evolves with each use. After every invocation:

1. **Reflect** — Identify what worked, what caused friction, and any unexpected issues
2. **Record** — Append a concise lesson to `lessons.md` in this skill's directory
3. **Refine** — When a pattern recurs (2+ times), update SKILL.md directly

### lessons.md Entry Format

```
### YYYY-MM-DD — Brief title
- **Friction**: What went wrong or was suboptimal
- **Fix**: How it was resolved
- **Rule**: Generalizable takeaway for future invocations
```

Accumulated lessons signal when to run `/skill-optimizer` for a deeper structural review.

## Additional Resources

### Scripts
- **`scripts/scan_status.py`** — Scan all skills for publishing status
  (README, zh, logo, GitHub, git). Usage: `~/.local/bin/python3 scan_status.py [--skill NAME] [--json]`
- **`scripts/bootstrap_registry.py`** — 掃描所有 skill 重建 `~/.claude/data/skill-registry/registry.json`
- **`scripts/render_catalog.py`** — 從 registry.json 渲染 catalog 表格到 CATALOG.md（marker 模式）

## Registry Workflow

### 事實源
`~/.claude/data/skill-registry/registry.json` 是少爺自家所有 skill 的集中註冊表。**事實源是 `~/.claude/skills/<slug>/SKILL.md` 的 frontmatter + git 狀態**，registry.json 只是聚合視圖，由 bootstrap 重建，不可手改（要改 lifecycle 例外，archived/draft 標記要手動 commit registry.json）。

### sync_status 語意

| 狀態 | 條件 | 動作 |
|------|------|------|
| `published` | 有 `git remote` + 無 unpushed commit | 維持 |
| `needs-update` | 有 remote + 本地有 unpushed commit | 跑 publish.py 重 push |
| `draft` | 有 .git 但未設 upstream | 設 upstream + push |
| `local-only` | 無 .git | 跑 publish.py 啟動發布 |

### 命令

```bash
# 1. 掃 ~/.claude/skills/ 重建 registry
~/.local/bin/python3 ~/.claude/skills/skill-publisher/scripts/bootstrap_registry.py

# 2. 渲染 catalog 表格到 ~/.claude/skills/skill-catalog/CATALOG.md
~/.local/bin/python3 ~/.claude/skills/skill-publisher/scripts/render_catalog.py

# 3. 渲染到其他 target（任何 .md 加上 marker 後可直接渲染）
~/.local/bin/python3 ~/.claude/skills/skill-publisher/scripts/render_catalog.py --target /path/to/file.md
```

### 何時重跑

- 新增 skill → bootstrap + render
- skill 改動 commit → 不必跑（git status 即時反映）
- skill push 完成 → bootstrap（讓 needs-update → published）
- 想看當前 catalog → render（skill-catalog/CATALOG.md 自動更新）

### Catalog Marker Pattern

蠶食自 yao-open-skills idiom。任何 .md 檔加上：
```markdown
<!-- catalog:start -->
<!-- catalog:end -->
```
跑 `render_catalog.py --target <path>` 就會在 marker 之間插入表格，不影響檔案其他內容。

### 發布前檢查
跑 `publish.py` 前請對照 `~/.claude/rules/skill-publishing-gate.md` 的 9 條規則。

## v0.4 Upgrade Plan (work-in-progress, 2026-05-16)

這版 SKILL.md 是 2026-05-06 archive 還原版（v0.3.0）。`references/` 內 4 份規劃文件是少爺 2026-05-16 蠶食自 `ConardLi/garden-skills` 的 release tooling 升級設計，**尚未實作**：

- [`references/manifest-state-conflict.md`](references/manifest-state-conflict.md) — 發布前比較 `manifest.version` vs 上一個 git tag，分類 synced / ahead / behind 三狀態，防止 double-bump
- [`references/marker-readme-sync.md`](references/marker-readme-sync.md) — README/CATALOG 用 inline marker 自動 re-render「需要 release 時更新的區塊」，user 無需手動維護 tag pinned zip 連結
- [`references/pr-validation-gate.md`](references/pr-validation-gate.md) — 把手動 `scan_status.py` 升級為 PR-time auto smoke-pack + manifest lint + README sync gate
- [`references/readme-standard.md`](references/readme-standard.md) — operonlab 公開 repo 統一 README layout 標準

實作這 4 件升級時，更新 `scripts/` 對應檔，然後砍掉本 v0.4 區段。
