[English](README.md) | [繁體中文](README.zh.md)

# skill-publisher

Publish skills to GitHub with bilingual READMEs and platform registration.

## Description

Skill Publisher handles the full skill publishing lifecycle: scanning status, generating bilingual READMEs (English + Traditional Chinese), pushing to the `joneshong-skills` GitHub org, and registering on documentation platforms.

## Features

- Scans all skills and reports README, logo, and GitHub status
- Generates bilingual README.md and README.zh.md from SKILL.md
- Initializes git repos and pushes to `joneshong-skills` GitHub org
- Creates GitHub repositories automatically for new skills
- Skips CLI-specific and internal skills automatically
- Batch mode (`--all`) for publishing all pending skills at once

## Usage

Invoke by asking Claude Code with trigger phrases such as:

- "publish skills"
- "push skill to GitHub"
- "update skill repos"
- "generate skill README"
- "發布 skill"
- "skill 上架"

## Related Skills

- [`skill-lifecycle`](https://github.com/joneshong-skills/skill-lifecycle)
- [`readme-gen`](https://github.com/joneshong-skills/readme-gen)
- [`create-skill`](https://github.com/joneshong-skills/create-skill)

## Install

Copy the skill directory into your Claude Code skills folder:

```
cp -r skill-publisher ~/.claude/skills/
```

Skills placed in `~/.claude/skills/` are auto-discovered by Claude Code. No additional registration is needed.
