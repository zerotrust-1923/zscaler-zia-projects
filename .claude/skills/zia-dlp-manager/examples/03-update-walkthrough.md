Here's the complete `examples/03-update-walkthrough.md` file.

## `examples/03-update-walkthrough.md` — full contents

```markdown
# Walkthrough 03 — Update DLP Rules

End-to-end guide for updating existing ZIA DLP Web Rules from a JSON source
file using the `zia_dlp_update.py` script.

---

## Overview

Update **modifies existing rules** on the target tenant. Each rule is sent via
`PUT /zia/api/v1/webDlpRules/{id}`. This is a **destructive (write) operation** —
it requires typing `UPDATE` to confirm before any API call is made.

| Mode | Description | Slab sizes |
|---|---|---|
| Single | One rule by exact name match | n/a |
| Multiple | Comma-separated list of rule names | n/a |
| Slab | First N rules from a starting `order` value | 5 / 10 / 50 / 100 |

### Key behaviors

- **Field-level allow-listing** — only updatable fields are sent; everything
  else (read-only / server-managed) is stripped automatically
- **Idempotent merge** — fields not present in the source JSON are preserved
  on the target by reading the current rule first and merging
- **Reference normalization** — all object/list references (engines,
  dictionaries, locations, groups, etc.) are reduced to `{"id": N}` form
- **Match by name** — rules are located on the target tenant by exact name
  match, then updated by their existing tenant-side `id`

### What can be updated

| Category | Fields |
|---|---|
| Core | `description`, `order`, `rank`, `state`, `action`, `severity` |
| Content | `fileTypes`, `cloudApplications`, `urlCategories`, `dlpEngines` |
| Targeting | `locations`, `locationGroups`, `groups`, `departments`, `users`, `timeWindows` |
| Notification | `notificationTemplate`, `auditor`, `icapServer`, `externalAuditorEmail` |
| Flags | `withoutContentInspection`, `zscalerIncidentReceiver`, `dlpDownloadScanEnabled` |
| Exclusions | `excludedDepartments`, `excludedGroups`, `excludedUsers` |
| Risk | `userRiskScoreLevels` |
| Sub-rules | `subRules`, `workloadGroups` |

### What is NEVER updated

These are stripped before the PUT request:

- `id` (used in URL only)
- `name` (use a separate rename workflow if needed)
- `lastModifiedTime`
- `lastModifiedBy`
- `accessControl`
- Any field outside the update-allow-list

---

## Prerequisites

- A valid source `zia_dlp_policies.json` containing the desired field values
- `.env` configured with **target tenant** credentials
- OneAPI client with `webDlpRules:read` AND `webDlpRules:write` scopes
- Rules to be updated **already exist** on the target tenant (matched by name)
- All referenced objects (engines, dictionaries, locations, etc.) exist on
  the target tenant — IDs are tenant-specific

---

## Step 1 — Prepare the source JSON

The simplest workflow:

```bash
# 1. Export current target state
python scripts/zia_dlp_export.py

# 2. Edit zia_dlp_policies.json — change only the fields you want to update
#    (e.g., bump severity, add a dictionary, change action, etc.)

# 3. Save the edited file
```

You can also feed in a JSON from another source (e.g., a hand-crafted change
set or a cross-tenant export after ID remapping).

Custom path options:

```bash
# Via env var
INPUT_JSON=/path/to/changes.json python scripts/zia_dlp_update.py

# Via CLI argument (overrides env)
python scripts/zia_dlp_update.py /path/to/changes.json
```

---

## Step 2 — Snapshot before changing anything

**Always take a fresh export immediately before running update.** This gives
you a known-good rollback point.

```bash
python scripts/zia_dlp_export.py
cp zia_dlp_policies.json zia_dlp_pre_update_$(date +%Y%m%d_%H%M%S).json
```

---

## Step 3 — Run the updater

```bash
python scripts/zia_dlp_update.py
```

You'll see the interactive menu:

```
============================================================
  ZIA DLP Rule Updater (from JSON)
============================================================
  1) Update single rule by name
  2) Update multiple rules by name (comma-separated)
  3) Update slab from starting order (5/10/50/100)
  q) Quit
============================================================
Select [1/2/3/q]:
```

---

## Step 4 — Choose a mode

### Mode 1 — Single rule

Best for hotfixes, targeted changes, or one-off corrections.

```
Select [1/2/3/q]: 1
Enter rule name: Block PII Upload
```

### Mode 2 — Multiple rules

Best when you have a known shortlist.

```
Select [1/2/3/q]: 2
Enter comma-separated names: Block PII Upload, Block PCI Upload, Block PHI Upload
```

Whitespace around commas is trimmed automatically.

### Mode 3 — Slab from starting order

Best for sweeping changes (e.g., "increase severity on all rules from order 50–60").
The starting value refers to the rule's **`order`** field (1-based, ascending).

```
Select [1/2/3/q]: 3
Starting order (1-based, e.g. 1 for first rule): 50

Slab sizes:  1) 5   2) 10   3) 50   4) 100
Select [1/2/3/4]: 1
```

| Choice | Effect |
|---|---|
| `1` | Updates rules with order `[start ... start+4]` (5 rules) |
| `2` | Updates rules with order `[start ... start+9]` (10 rules) |
| `3` | Updates rules with order `[start ... start+49]` (50 rules) |
| `4` | Updates rules with order `[start ... start+99]` (100 rules) |

---

## Step 5 — Review and confirm

The script lists every rule it will update, then asks for typed confirmation:

```
Rules to update (3):
Order  ID       Name
-----------------------------------------------------
1      98765    Block PII Upload
2      98766    Block PCI Upload
3      98767    Block PHI Upload
-----------------------------------------------------

Type 'UPDATE' to confirm:
```

✅ Type `UPDATE` exactly (uppercase) → update proceeds
❌ Anything else → operation is cancelled, no API calls made

---

## Step 6 — Watch the live progress

```
2026-05-25 12:30:14 | INFO | Authenticating to https://acme-prod.zslogin.net/oauth2/v1/token
2026-05-25 12:30:15 | INFO | Authenticated.
2026-05-25 12:30:15 | INFO | Fetching current state for 'Block PII Upload' (id=98765)...
2026-05-25 12:30:16 | INFO | Merging source fields into current rule...
2026-05-25 12:30:16 | INFO | PUT /zia/api/v1/webDlpRules/98765
2026-05-25 12:30:17 | INFO |     + Updated id=98765
2026-05-25 12:30:17 | INFO | Fetching current state for 'Block PCI Upload' (id=98766)...
2026-05-25 12:30:18 | INFO |     + Updated id=98766
2026-05-25 12:30:18 | INFO | Fetching current state for 'Block PHI Upload' (id=98767)...
2026-05-25 12:30:19 | INFO |     + Updated id=98767

Activate ZIA changes now? [y/N]:
```

### How merge works

For each rule, the updater:

1. **GETs** the current state from the target tenant
2. **Reads** the matching rule from your source JSON (by name)
3. **Allow-lists** updatable fields only
4. **Normalizes** all references to `{"id": N}` form
5. **Merges** — source fields overwrite; absent fields keep current values
6. **PUTs** the merged payload back

This guarantees you don't accidentally blank a field by omitting it from the
source JSON.

---

## Step 7 — Activate the changes

```
Activate ZIA changes now? [y/N]: y
2026-05-25 12:30:25 | INFO | Activating ZIA changes...
2026-05-25 12:30:27 | INFO | Activation submitted.
```

Same activation behavior as import — answer `N` to defer and activate later
via the ZIA Admin UI.

---

## Step 8 — Inspect the audit log

Every run produces a CSV at the repo root:

```
zia_dlp_update_audit_20260525_123014.csv
```

### Columns

| Column | Description |
|---|---|
| `status` | `updated` or `failed` |
| `id` | Rule ID on the target tenant |
| `name` | Rule name |
| `order` | Order value after update |
| `rank` | Rank value after update |
| `state` | `ENABLED` or `DISABLED` |
| `fields_changed` | Comma-separated list of field names that differed from current |
| `error` | Error message (only for failed entries) |

### Example

```csv
status,id,name,order,rank,state,fields_changed,error
updated,98765,Block PII Upload,1,7,ENABLED,"severity,dlpEngines",
updated,98766,Block PCI Upload,2,7,ENABLED,"action",
failed,98767,Block PHI Upload,3,7,ENABLED,,400 Bad Request: dlpEngines[0].id 12345 not found
```

The `fields_changed` column is invaluable for post-change reviews and
compliance reporting.

---

## Common scenarios

### Scenario A — Bump severity on a single rule

1. Export: `python scripts/zia_dlp_export.py`
2. Edit `zia_dlp_policies.json`:
   ```json
   { "name": "Block PII Upload", "severity": "RULE_SEVERITY_HIGH", ... }
   ```
3. Run: `python scripts/zia_dlp_update.py`
4. Mode 1 → name: `Block PII Upload` → confirm `UPDATE`

### Scenario B — Disable a batch of rules

1. Edit JSON: set `"state": "DISABLED"` on the target rules
2. Run updater in Mode 2 (comma-separated names) or Mode 3 (slab)
3. Confirm and activate

### Scenario C — Add a new DLP engine reference to many rules

1. Export and find the engine ID on the target tenant
2. Edit JSON: append `{"id": <engine_id>}` to each target rule's `dlpEngines` list
3. Run updater in Mode 3 (slab) covering the affected rules
4. Verify in `fields_changed` column of the audit CSV

### Scenario D — Cross-tenant policy sync

1. Export source tenant
2. Export target tenant (as snapshot)
3. Remap IDs in source JSON to match target tenant (engines, dictionaries, etc.)
4. Run updater against target — Mode 3, ALL slab if every rule should sync
5. Review the audit CSV's `fields_changed` column to confirm what drifted

---

## Rollback procedure

If an update produces unwanted results:

```bash
# 1. Stop activations from going through (if not yet activated)
#    → Discard changes in ZIA Admin UI → Activation panel

# 2. If already activated, restore from the pre-update snapshot
#    Use the snapshot saved in Step 2:
ls -lh zia_dlp_pre_update_*.json

# 3. Run updater again with the snapshot as source
python scripts/zia_dlp_update.py zia_dlp_pre_update_20260525_122900.json
#    → Mode 
