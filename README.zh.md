[English](README.md) | [繁體中文](README.zh.md)

# skill-publisher

Publish skills to GitHub with bilingual READMEs and platform registration.

## 說明

Skill Publisher handles the full skill publishing lifecycle: scanning status, generating bilingual READMEs (English + Traditional Chinese), pushing to the `joneshong-skills` GitHub org, and registering on documentation platforms.

## 功能特色

- Scans all skills and reports README, logo, and GitHub status
- Generates bilingual README.md and README.zh.md from SKILL.md
- Initializes git repos and pushes to `joneshong-skills` GitHub org
- Creates GitHub repositories automatically for new skills
- Skips CLI-specific and internal skills automatically
- Batch mode (`--all`) for publishing all pending skills at once

## 使用方式

透過以下觸發語句呼叫 Claude Code 來使用此技能：

- "publish skills"
- "push skill to GitHub"
- "update skill repos"
- "generate skill README"
- "發布 skill"
- "skill 上架"

## 相關技能

- [`skill-lifecycle`](https://github.com/joneshong-skills/skill-lifecycle)
- [`readme-gen`](https://github.com/joneshong-skills/readme-gen)
- [`create-skill`](https://github.com/joneshong-skills/create-skill)

## 安裝

將技能目錄複製到 Claude Code 技能資料夾：

```
cp -r skill-publisher ~/.claude/skills/
```

放置在 `~/.claude/skills/` 的技能會被 Claude Code 自動發現，無需額外註冊。
