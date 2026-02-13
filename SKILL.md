---
name: skill-publisher
description: >-
  This skill should be used when the user asks to "publish skills", "push skill to GitHub",
  "update skill repos", "generate skill README", "add skill to DeepWiki", "register on Context7",
  "generate skill logo", "發布 skill", "推送 skill", "skill 上架", "更新 skill repo",
  "產生 skill logo", mentions skill publishing, or discusses pushing skills to GitHub,
  generating bilingual READMEs, creating logos, or registering skills on documentation platforms.
version: 0.2.0
tools: Read, Write, Edit, Bash, Glob, Grep, WebSearch
argument-hint: "[skill-name | --all | --scan]"
---

# Skill Publisher

Publish skills to GitHub with bilingual READMEs, logos, and platform registration.
Handles the full lifecycle: scan status, generate READMEs, create logos, push to GitHub,
and register on DeepWiki and Context7.

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

Run the scan to identify what needs publishing:

```bash
python3 ~/.claude/skills/skill-publisher/scripts/scan_status.py
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

**Important:** Each sub-agent runs `/image-gen` independently (opens its own
browser session). Do NOT launch more than 3 concurrent browser sessions —
Playwright resource contention causes failures beyond this limit.

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
mcp__context7__resolve-library-id with libraryName="[name]" and query="[description]"
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
  (README, zh, logo, GitHub, git). Usage: `python3 scan_status.py [--skill NAME] [--json]`
