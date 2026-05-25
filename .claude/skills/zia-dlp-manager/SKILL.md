---
name: zia-dlp-manager
display_name: Zscaler ZIA DLP Manager
version: 1.0.0
description: Create, read, update, delete, import, and export Zscaler Internet Access (ZIA) DLP policies via OneAPI.
author: Ramesh Mani
license: MIT
homepage: https://github.com/zerotrust-1923/zia-dlp-manager
repository: https://github.com/zerotrust-1923/zia-dlp-manager
issues: https://github.com/zerotrust-1923/zia-dlp-manager/issues
categories:
  - security
  - policy-management
  - data-loss-prevention
tags:
  - zscaler
  - zia
  - dlp
  - oneapi
  - zidentity
  - policy
  - migration
runtime: python>=3.9
entrypoints:
  - id: export
    file: scripts/zia_dlp_export.py
    description: Export DLP policies (rules, engines, dictionaries, templates, ICAP, IDM) to CSV and/or JSON.
  - id: import
    file: scripts/zia_dlp_import.py
    description: Create DLP rules from a JSON source. Supports single, multiple, and slab modes (50/100/ALL).
  - id: update
    file: scripts/zia_dlp_update.py
    description: Update existing DLP rules with only allowed fields. Supports single, multiple, and slab modes (5/10/50/100).
  - id: delete
    file: scripts/zia_dlp_delete.py
    description: Delete DLP rules safely. Supports single, multiple, and slab modes with double confirmation.
inputs:
  - name: ZSCALER_CLIENT_ID
    type: secret
    required: true
    description: OneAPI OAuth2 client ID (from Zidentity).
  - name: ZSCALER_CLIENT_SECRET
    type: secret
    required: true
    description: OneAPI OAuth2 client secret.
  - name: ZSCALER_VANITY_DOMAIN
    type: string
    required: true
    description: Tenant vanity domain (the prefix in <vanity>.zslogin.net).
  - name: ZSCALER_API_BASE_URL
    type: string
    required: false
    default: https://api.zsapi.net
  - name: INPUT_JSON
    type: file
    required: false
    description: JSON file used by import/update/delete operations.
  - name: EXPORT_FORMAT
    type: enum
    values: [csv, json, both]
    required: false
    default: both
permissions:
  network:
    - "*.zsapi.net"
    - "*.zslogin.net"
  filesystem: read-write
  secrets: required
safety:
  destructive_operations: [import, update, delete]
  confirmation_required: true
  audit_log: true
  dry_run_supported: true
---

# Zscaler ZIA DLP Manager

A production-grade skill for managing the full lifecycle of Zscaler Internet
Access (ZIA) Data Loss Prevention policies through the OneAPI (Zidentity
OAuth2) interface.

## When to invoke this skill

Trigger this skill when the user asks to:

- Back up or export DLP policies (rules, engines, dictionaries, templates, ICAP, IDM)
- Migrate DLP rules between tenants
- Bulk-create new DLP rules from a JSON source
- Bulk-update existing DLP rules from a JSON source
- Delete DLP rules in single, multiple, or slab batches
- Audit changes via CSV reports

## Capabilities

| Action | Entrypoint | Modes | Confirmation |
|---|---|---|---|
| Export | `scripts/zia_dlp_export.py` | csv / json / both | none (read-only) |
| Import | `scripts/zia_dlp_import.py` | single / multi / slab(50,100,ALL) | type `IMPORT` |
| Update | `scripts/zia_dlp_update.py` | single / multi / slab(5,10,50,100) | type `UPDATE` |
| Delete | `scripts/zia_dlp_delete.py` | single / multi / slab(5,10,50,100) | type `DELETE` + name echo |

## Prerequisites

1. Zscaler OneAPI client credentials (Zidentity OAuth2 client_credentials grant)
2. Python 3.9+ with packages from `requirements.txt`
3. A populated `.env` file (see `.env.example`)
4. Required API scopes: `webDlpRules:read`, `webDlpRules:write`, `dlpEngines:read`,
   `dlpDictionaries:read`, `dlpNotificationTemplates:read`, `icapServers:read`,
   `idmprofile:read`, `status:write`

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure credentials
cp .env.example .env
# edit .env with your tenant values

# 3. Run any operation
python scripts/zia_dlp_export.py --format both
python scripts/zia_dlp_import.py zia_dlp_policies.json
python scripts/zia_dlp_update.py zia_dlp_policies.json
python scripts/zia_dlp_delete.py


Safety guarantees
Read-only export — no mutations during backup
Explicit confirmation for every write operation (typed token, not just y/N)
Audit CSV generated for every import / update / delete run
Field allow-listing — update payloads send only updatable fields
Reference normalization — IDs are reduced to {"id": N} form
No silent overwrites — duplicate-name handling via optional suffix
Operational modes
Single
Operate on one rule by exact name match.

Multiple
Operate on a comma-separated list of rule names.

Slab
Operate on N rules starting from a given order value, sorted ascending. Slab sizes: 5, 10, 50, 100, or ALL (import only).

Outputs
File	Produced by	Purpose
zia_dlp_policies.csv	export	Tabular backup
zia_dlp_policies.json	export	Structured backup, used as input by other ops
zia_dlp_import_audit_<ts>.csv	import	Per-rule create result
zia_dlp_update_audit_<ts>.csv	update	Per-rule update result
zia_dlp_delete_audit_<ts>.csv	delete	Per-rule delete result

Limitations
DLP engine, dictionary, template, location, and group IDs are tenant-specific. Cross-tenant import/update requires ID remapping.
The OneAPI activation step is optional and prompted at the end of write ops.
Sub-rules and workload groups are passed through as-is; deep validation is not performed.

