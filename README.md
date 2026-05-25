# zia-dlp-manager
Create, update, import, export, and delete Zscaler ZIA DLP policies via OneAPI


---

## File 2 — `README.md`

```markdown
# Zscaler ZIA DLP Manager

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![Zscaler OneAPI](https://img.shields.io/badge/Zscaler-OneAPI-00B5E2)](https://help.zscaler.com/oneapi)

A production-grade toolkit and agent skill for the **complete lifecycle
management of Zscaler Internet Access (ZIA) Data Loss Prevention policies**
via the OneAPI (Zidentity OAuth2) interface.

> **Create · Read · Update · Delete · Import · Export** — with audit logs and
> explicit confirmations for every write operation.

---

## Table of contents

- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Operation modes](#operation-modes)
- [Outputs and audit logs](#outputs-and-audit-logs)
- [Security model](#security-model)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- ✅ **Export** DLP rules, engines, dictionaries, notification templates, ICAP servers, and IDM profiles to CSV and/or JSON
- ✅ **Import** rules from JSON in single, multiple, or slab (50/100/ALL) modes
- ✅ **Update** existing rules with field-level allow-listing in slabs of 5/10/50/100
- ✅ **Delete** rules safely with double confirmation and audit logging
- ✅ **OneAPI** native — Zidentity OAuth2 client_credentials grant
- ✅ **Audit CSV** generated for every write operation
- ✅ **Idempotent updates** — preserves existing fields not present in the source
- ✅ **MCP Marketplace ready** — ships with `SKILL.md` manifest and `mcp.json`

---

## Architecture

┌─────────────────────┐ ┌────────────────────────┐ │ Source JSON file │────────▶│ zia_dlp_import.py │──┐ └─────────────────────┘ └────────────────────────┘ │ │ ┌─────────────────────┐ ┌────────────────────────┐ ├──▶ Zscaler OneAPI │ Source JSON file │────────▶│ zia_dlp_update.py │──┤ (Zidentity └─────────────────────┘ └────────────────────────┘ │ OAuth2) │ ┌─────────────────────┐ ┌────────────────────────┐ │ │ Interactive menu │────────▶│ zia_dlp_delete.py │──┤ └─────────────────────┘ └────────────────────────┘ │ │ ┌────────────────────────┐ │ │ zia_dlp_export.py │◀─┘ └────────────────────────┘ │ ▼ CSV + JSON backup



---

## Installation

### Requirements

- Python 3.9 or newer
- Zscaler OneAPI client (Zidentity OAuth2)
- API scopes:
  - `webDlpRules:read`, `webDlpRules:write`
  - `dlpEngines:read`, `dlpDictionaries:read`
  - `dlpNotificationTemplates:read`
  - `icapServers:read`, `idmprofile:read`
  - `status:write` (for activation)

### Steps

```bash
git clone https://github.com/<your-org>/zia-dlp-manager.git
cd zia-dlp-manager
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env with your tenant values
