# Zscaler ZIA DLP Manager

A Claude Skill for managing Zscaler Internet Access (ZIA) Data Loss Prevention
policies via OneAPI.

## 📦 Skill location

The skill lives at:

**[`.claude/skills/zia-dlp-manager/`](./.claude/skills/zia-dlp-manager/)**

See its [README](./.claude/skills/zia-dlp-manager/README.md) and
[SKILL.md](./.claude/skills/zia-dlp-manager/SKILL.md) for full documentation.

## ✨ Capabilities

- **Export** — DLP rules, engines, dictionaries, templates, ICAP, IDM profiles → CSV/JSON
- **Import** — Create rules from JSON (single / multi / slab modes)
- **Update** — Modify existing rules with field-level allow-listing
- **Delete** — Remove rules safely with double confirmation

## 🚀 Install

\`\`\`bash
git clone https://github.com/zerotrust-1923/zia-dlp-manager.git
cd zia-dlp-manager/.claude/skills/zia-dlp-manager
pip install -r requirements.txt
cp .env.example .env   # edit with your OneAPI credentials
\`\`\`

## 📜 License

[MIT](./LICENSE)
