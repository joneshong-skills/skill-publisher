# README Standard Format

All open-source repos use this layout:

```markdown
# project-name

<p align="center">
  <img src="docs/icon.png" alt="icon" width="200"/>
</p>

<p align="center">
  <strong><a href="...README.md">English</a></strong> | <a href="...README.zh.md">繁體中文</a>
</p>

<p align="center">
  <a href="..."><img alt="badge" src="shields.io/...?style=flat-square"></a>
  ...
</p>

One-line description.

<p align="center">
  <img src="docs/screenshots/..." alt="..." width="700" />
</p>
```

## Rules
- Icon: centered, 200px, from `docs/icon.png`
- Badges: flat-square style, linked to relevant pages
- Common badges: release, language version, license, stars, DeepWiki
- Screenshots: `<p align="center">`, never markdown `![]()` syntax
- Language switch: GitHub URLs (not file paths)
- Both EN and zh-TW READMEs must exist
- DeepWiki badge on all public repos
