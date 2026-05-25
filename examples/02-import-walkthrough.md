Here's the complete `examples/02-import-walkthrough.md` file.

## `examples/02-import-walkthrough.md` — full contents

```markdown
# Walkthrough 02 — Import (Create) DLP Rules

End-to-end guide for creating new ZIA DLP Web Rules on a target tenant from a
JSON source file, using the `zia_dlp_import.py` script.

---

## Overview

Import **creates brand-new rules** on the target tenant. Each rule is sent via
`POST /zia/api/v1/webDlpRules`. This is a **destructive (write) operation** —
it requires typing `IMPORT` to confirm before any API call is made.

| Mode | Description | Slab sizes |
|---|---|---|
| Single | One rule by exact name match | n/a |
| Multiple | Comma-separated list of rule names | n/a |
| Slab | First N rules from a starting index | 50 / 100 / ALL |

### What gets imported

For each rule, the script sends:

- Core fields: `name`, `description`, `order`, `rank`, `state`, `action`, `severity`
- File / content controls: `fileTypes`, `cloudApplications`, `urlCategories`, `dlpEngines`
- Targeting: `locations`, `locationGroups`, `groups`, `departments`, `users`, `timeWindows`
- Notification & escalation: `notificationTemplate`, `auditor`, `icapServer`
- Flags: `withoutContentInspection`, `zscalerIncidentReceiver`, `externalAuditorEmail`
- Optional: `subRules`, `workloadGroups`, `dlpDownloadScanEnabled`, `excludedDepartments`,
  `excludedGroups`, `excludedUsers`, `userRiskScoreLevels`, etc.

### What is stripped before sending

Read-only / server-managed fields are removed automatically:

- `id`
- `lastModifiedTime`
- `lastModifiedBy`
- `accessControl`
- Any other field outside the create-allow-list

---

## Prerequisites

- A valid source `zia_dlp_policies.json` (typically from `01-export-walkthrough.md`)
- `.env` configured with **target tenant** credentials
- OneAPI client with `webDlpRules:write` scope
- All referenced objects already exist on the target tenant:
  - DLP Engines, DLP Dictionaries, Notification Templates, ICAP Servers
  - Locations, Location Groups, Groups, Departments, Users, Time Windows
- IDs match between source and target — see the [ID remapping](#id-remapping-cross-tenant) section

---

## Step 1 — Confirm the source file

Place the JSON file at the repo root, or point to a custom path:

```bash
ls -lh zia_dlp_policies.json
```

Custom path options:

```bash
# Via env var
INPUT_JSON=/path/to/source.json python scripts/zia_dlp_import.py

# Via CLI argument (overrides env)
python scripts/zia_dlp_import.py /path/to/source.json
```

Quick rule count:

```bash
python -c "import json; d=json.load(open('zia_dlp_policies.json'))['data']; print('Rules:', len(d.get('DLP Web Rules', [])))"
```

---

## Step 2 — (Optional) Set a name suffix to avoid duplicates

If the target tenant may already have rules with the same names, append a
suffix so imports don't collide:

```env
IMPORT_NAME_SUFFIX=_imported_2026Q2
```

A source rule named `Block PII Upload` becomes `Block PII Upload_imported_2026Q2`
on the target.

Leave the variable blank or unset to use the original names verbatim.

---

## Step 3 — Run the importer

```bash
python scripts/zia_dlp_import.py
```

You'll see the interactive menu:

```
============================================================
  ZIA DLP Rule Importer (from JSON)
============================================================
  1) Import single rule by name
  2) Import multiple rules by name (comma-separated)
  3) Import slab from starting index (50/100/ALL)
  q) Quit
============================================================
Select [1/2/3/q]:
```

---

## Step 4 — Choose a mode

### Mode 1 — Single rule

Best for testing, hotfixes, or migrating one rule at a time.

```
Select [1/2/3/q]: 1
Enter rule name: Block PII Upload
```

### Mode 2 — Multiple rules (comma-separated)

Best when you have a known shortlist.

```
Select [1/2/3/q]: 2
Enter comma-separated names: Block PII Upload, Block PCI Upload, Block PHI Upload
```

Whitespace around commas is trimmed automatically.

### Mode 3 — Slab from starting index

Best for bulk migrations. Index is **0-based** and refers to position in the
source JSON's `DLP Web Rules` array (typically already sorted by `order`).

```
Select [1/2/3/q]: 3
Starting index (0-based, e.g. 0 for first rule): 0

Slab sizes:  1) 50   2) 100   3) ALL
Select [1/2/3]: 1
```

| Choice | Effect |
|---|---|
| `1` | Imports rules `[start : start+50]` |
| `2` | Imports rules `[start : start+100]` |
| `3` | Imports rules `[start : end]` (everything from start onward) |

---

## Step 5 — Review and confirm

The script lists every rule it will create, then asks for typed confirmation:

```
Rules to import (3):
Index  Name
-----------------------------------------------
0      Block PII Upload
1      Block PCI Upload
2      Block PHI Upload
-----------------------------------------------

Type 'IMPORT' to confirm:
```

✅ Type `IMPORT` exactly (uppercase) → import proceeds
❌ Anything else → operation is cancelled, no API calls made

---

## Step 6 — Watch the live progress

```
2026-05-25 12:01:14 | INFO | Authenticating to https://acme-prod.zslogin.net/oauth2/v1/token
2026-05-25 12:01:15 | INFO | Authenticated.
2026-05-25 12:01:15 | INFO | Creating rule 'Block PII Upload'...
2026-05-25 12:01:16 | INFO |     + Created id=98765
2026-05-25 12:01:16 | INFO | Creating rule 'Block PCI Upload'...
2026-05-25 12:01:17 | INFO |     + Created id=98766
2026-05-25 12:01:17 | INFO | Creating rule 'Block PHI Upload'...
2026-05-25 12:01:18 | INFO |     + Created id=98767

Activate ZIA changes now? [y/N]:
```

### Pacing

A short delay (default ~0.4s) is added between requests to avoid OneAPI rate
limits. For large slabs (100+ rules), expect ~1 minute per 100 rules.

---

## Step 7 — Activate the changes

ZIA configuration changes are staged until activated. Two options:

### Option A — Activate now (interactive prompt)

```
Activate ZIA changes now? [y/N]: y
2026-05-25 12:01:25 | INFO | Activating ZIA changes...
2026-05-25 12:01:27 | INFO | Activation submitted.
```

### Option B — Activate later (manual)

Skip the prompt (`N`) and activate via:
- ZIA Admin UI → **Activation** button (top-right)
- Or rerun the script and answer `y` next time

---

## Step 8 — Inspect the audit log

Every run produces a CSV at the repo root:

```
zia_dlp_import_audit_20260525_120115.csv
```

### Columns

| Column | Description |
|---|---|
| `status` | `created` or `failed` |
| `id` | New rule ID assigned by ZIA (blank if failed) |
| `name` | Rule name |
| `order` | Order value sent in the create payload |
| `rank` | Rank value sent |
| `state` | `ENABLED` or `DISABLED` |
| `error` | Error message (only for failed entries) |

### Example

```csv
status,id,name,order,rank,state,error
created,98765,Block PII Upload,1,7,ENABLED,
created,98766,Block PCI Upload,2,7,ENABLED,
failed,,Block PHI Upload,3,7,ENABLED,400 Bad Request: dlpEngines[0].id 12345 not found on tenant
```

---

## ID remapping (cross-tenant)

DLP Engine, Dictionary, Template, Location, and Group IDs are **tenant-specific**.
A rule referencing `dlpEngines: [{"id": 12345}]` from tenant A will fail on
tenant B unless engine ID `12345` exists there.

### Manual remapping workflow

1. Export the **source** tenant: produces `source.json`
2. Export the **target** tenant: produces `target.json`
3. Build a name → ID lookup from `target.json` for each object family
4. In `source.json`, replace each referenced ID with the target tenant's
   matching ID (matched by **name**, not ID)
5. Save as `remapped.json` and use it as the import source

A helper script for this is on the roadmap (see `CHANGELOG.md` → `[Unreleased]`).

### Quick manual example

```python
import json

src = json.load(open("source.json"))["data"]
tgt = json.load(open("target.json"))["data"]

# Build name->id maps from target tenant
engine_map = {e["name"]: e["id"] for e in tgt["DLP Engines"]}

# Rewrite engine refs in source rules
for rule in src["DLP Web Rules"]:
    for eng in rule.get("dlpEngines", []):
        # Look up by name (assumes source rule has engine name preserved)
        # If only ID is present, build a source name map first.
        pass

json.dump({"data": src}, open("remapped.json", "w"), indent=2)
```

---

## Common scenarios

### Scenario A — Test a single rule before bulk import

```bash
# 1. Export target tenant
python scripts/zia_dlp_export.py

# 2. Copy backup
cp zia_dlp_policies.json target_backup.json

# 3. Import one rule from source
python scripts/zia_dlp_import.py source.json
# → choose Mode 1, single rule

# 4. Verify in ZIA Admin UI

# 5. If good, run Mode 3 for full slab
```

### Scenario B — Migrate full DLP policy set in slabs of 50

```bash
# First slab
python scripts/zia_dlp_import.py source.json
# → Mode 3, start=0, size=50

# Second slab
python scripts/zia_dlp_import.py source.json
# → Mode 3, start=50, size=50

# ... repeat until done
```

Slabbing keeps each batch reviewable and limits blast radius if something
fails partway through.

### Scenario C — Disaster recovery rebuild

```bash
# Restore everything from last night's export
python scripts/zia_dlp_import.py zia_dlp_policies.json
# → Mode 3, start=0, size=ALL
# → Type IMPORT
# → Activate: y
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `400 Bad Request: dlpEngines[0].id X not found` | Tenant-specific ID mismatch | Remap IDs (see above) |
| `400 Bad Request: name already exists` | Duplicate rule name | Set `IMPORT_NAME_SUFFIX` and retry |
| `403 Forbidden` | Missing `webDlpRules:write` scope | Add scope in Zidentity, re-issue client secret |
| `409 Conflict` | Order collision | Source has same `order` as existing rule
