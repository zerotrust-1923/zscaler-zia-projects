Here's the complete `examples/04-delete-walkthrough.md` file.

## `examples/04-delete-walkthrough.md` — full contents

```markdown
# Walkthrough 04 — Delete DLP Rules

End-to-end guide for safely deleting ZIA DLP Web Rules using the
`zia_dlp_delete.py` script.

---

## Overview

Delete **permanently removes rules** from the target tenant. Each rule is
removed via `DELETE /zia/api/v1/webDlpRules/{id}`. This is the **most
destructive operation** in this skill — it requires:

1. Typed `DELETE` confirmation
2. Echo of the rule name (for single-rule mode)
3. Activation to take full effect

| Mode | Description | Slab sizes |
|---|---|---|
| Single | One rule by exact name match | n/a |
| Multiple | Comma-separated list of rule names | n/a |
| Slab | First N rules from a starting `order` value | 5 / 10 / 50 / 100 |

> ⚠️ **There is no undo.** Once activated, deleted rules cannot be recovered
> from the tenant — only restored from a prior export via the import script.

---

## Prerequisites

- A **fresh export** of the target tenant (mandatory rollback artifact)
- `.env` configured with **target tenant** credentials
- OneAPI client with `webDlpRules:read` AND `webDlpRules:write` scopes
- Confirmed list of rules to delete (cross-checked with stakeholders)
- Change ticket / approval per your organization's change-control process

---

## Step 1 — Take a mandatory pre-delete snapshot

**This is non-negotiable.** Without a snapshot, recovery is impossible.

```bash
python scripts/zia_dlp_export.py
cp zia_dlp_policies.json zia_dlp_pre_delete_$(date +%Y%m%d_%H%M%S).json
```

Verify the snapshot file:

```bash
ls -lh zia_dlp_pre_delete_*.json
python -c "import json; d=json.load(open('zia_dlp_policies.json'))['data']; print('Rules in snapshot:', len(d.get('DLP Web Rules', [])))"
```

Store this file outside the repo (e.g., S3, secure share, ticket attachment)
in addition to the local copy.

---

## Step 2 — Identify the rules to delete

### Option A — Browse the export CSV

Open `zia_dlp_policies.csv` in a spreadsheet and filter the `DLP Web Rules`
section by name, state, last-modified date, or order range. Copy the exact
names you intend to delete.

### Option B — Quick CLI list

```bash
python -c "
import json
rules = json.load(open('zia_dlp_policies.json'))['data']['DLP Web Rules']
for r in sorted(rules, key=lambda x: x.get('order', 0)):
    print(f\"{r.get('order'):>4}  {r.get('state','?'):<8}  {r['name']}\")
" | less
```

### Option C — Find disabled rules (typical cleanup target)

```bash
python -c "
import json
rules = json.load(open('zia_dlp_policies.json'))['data']['DLP Web Rules']
disabled = [r for r in rules if r.get('state') == 'DISABLED']
print('Disabled rules:', len(disabled))
for r in disabled:
    print(f\"  - {r['name']}\")
"
```

---

## Step 3 — Run the deleter

```bash
python scripts/zia_dlp_delete.py
```

You'll see the interactive menu:

```
============================================================
  ZIA DLP Rule Deleter
============================================================
  ⚠  Deletion is permanent. Ensure you have a fresh export.
============================================================
  1) Delete single rule by name
  2) Delete multiple rules by name (comma-separated)
  3) Delete slab from starting order (5/10/50/100)
  q) Quit
============================================================
Select [1/2/3/q]:
```

---

## Step 4 — Choose a mode

### Mode 1 — Single rule (with name echo)

The safest mode — requires you to retype the rule name as a second confirmation.

```
Select [1/2/3/q]: 1
Enter rule name: Block Legacy SaaS Upload
```

### Mode 2 — Multiple rules

```
Select [1/2/3/q]: 2
Enter comma-separated names: Old PII Test, Old PCI Test, Old PHI Test
```

Whitespace around commas is trimmed automatically.

### Mode 3 — Slab from starting order

The starting value refers to the rule's **`order`** field (1-based, ascending).

```
Select [1/2/3/q]: 3
Starting order (1-based): 200

Slab sizes:  1) 5   2) 10   3) 50   4) 100
Select [1/2/3/4]: 1
```

| Choice | Effect |
|---|---|
| `1` | Deletes rules with order `[start ... start+4]` (5 rules) |
| `2` | Deletes rules with order `[start ... start+9]` (10 rules) |
| `3` | Deletes rules with order `[start ... start+49]` (50 rules) |
| `4` | Deletes rules with order `[start ... start+99]` (100 rules) |

> 💡 **Best practice:** Start with size `5` for first-time use. Move to larger
> slabs only after several successful runs.

---

## Step 5 — Review the kill list

The script shows every rule that will be deleted:

```
Rules to DELETE (3):
Order  ID       State      Name
------------------------------------------------------------
200    98123    DISABLED   Old PII Test
201    98124    DISABLED   Old PCI Test
202    98125    DISABLED   Old PHI Test
------------------------------------------------------------

⚠  This action is permanent.
Type 'DELETE' to confirm:
```

### Confirmation flow

1. **Type `DELETE` exactly** (uppercase) → proceeds
2. **Single-rule mode adds a second prompt** — re-type the exact rule name:
   ```
   Re-type the rule name to confirm: Block Legacy SaaS Upload
   ```
3. **Anything else** → operation is cancelled, no API calls made

---

## Step 6 — Watch the live progress

```
2026-05-25 13:05:14 | INFO | Authenticating to https://acme-prod.zslogin.net/oauth2/v1/token
2026-05-25 13:05:15 | INFO | Authenticated.
2026-05-25 13:05:15 | INFO | DELETE /zia/api/v1/webDlpRules/98123 ('Old PII Test')
2026-05-25 13:05:16 | INFO |     - Deleted id=98123
2026-05-25 13:05:16 | INFO | DELETE /zia/api/v1/webDlpRules/98124 ('Old PCI Test')
2026-05-25 13:05:17 | INFO |     - Deleted id=98124
2026-05-25 13:05:17 | INFO | DELETE /zia/api/v1/webDlpRules/98125 ('Old PHI Test')
2026-05-25 13:05:18 | INFO |     - Deleted id=98125

Activate ZIA changes now? [y/N]:
```

### Pacing

A short delay (~0.4s default) between deletes avoids OneAPI rate limits and
keeps the audit log readable.

---

## Step 7 — Activate the changes

ZIA configuration changes are staged until activated. Until activation, the
rules are removed from the configuration but may still be enforced from the
last-activated policy snapshot.

### Activate now

```
Activate ZIA changes now? [y/N]: y
2026-05-25 13:05:25 | INFO | Activating ZIA changes...
2026-05-25 13:05:27 | INFO | Activation submitted.
```

### Activate later

Answer `N` to defer. Useful when:
- Multiple change scripts are being run in sequence (activate once at the end)
- A change-window window is upcoming and you want to stage now, activate then
- You want a peer to review the staged config in the ZIA Admin UI first

---

## Step 8 — Inspect the audit log

Every run produces a CSV at the repo root:

```
zia_dlp_delete_audit_20260525_130514.csv
```

### Columns

| Column | Description |
|---|---|
| `status` | `deleted` or `failed` |
| `id` | Rule ID that was targeted |
| `name` | Rule name at deletion time |
| `order` | Order value at deletion time |
| `state` | `ENABLED` or `DISABLED` at deletion time |
| `error` | Error message (only for failed entries) |

### Example

```csv
status,id,name,order,state,error
deleted,98123,Old PII Test,200,DISABLED,
deleted,98124,Old PCI Test,201,DISABLED,
failed,98125,Old PHI Test,202,DISABLED,409 Conflict: rule referenced by sub-rule chain
```

Keep audit CSVs alongside the pre-delete snapshot for compliance / SOX /
ISO 27001 evidence.

---

## Rollback procedure

If a wrong rule was deleted, recovery requires the pre-delete snapshot taken
in Step 1.

### If NOT yet activated

```
1. Open ZIA Admin UI → Activation panel
2. Click "Discard pending changes"
3. The deletion is undone — no further action required
```

### If already activated

```bash
# 1. Locate the snapshot
ls -lh zia_dlp_pre_delete_*.json

# 2. Re-import the deleted rule(s)
python scripts/zia_dlp_import.py zia_dlp_pre_delete_20260525_125900.json
#    → Mode 1 (single) or Mode 2 (multiple) — pick the deleted rule names
#    → Type IMPORT
#    → Activate: y

# 3. Verify in ZIA Admin UI that the rule reappears with correct settings
```

> ⚠️ The new rule will receive a **new tenant-side ID**. Any external system
> referencing the old ID (SIEM, ticketing, automation) must be updated.

---

## Common scenarios

### Scenario A — Decommission a deprecated policy

```bash
# 1. Verify the rule has been disabled for ≥30 days
# 2. Snapshot
python scripts/zia_dlp_export.py
cp zia_dlp_policies.json zia_dlp_pre_delete_$(date +%Y%m%d_%H%M%S).json

# 3. Delete
python scripts/zia_dlp_delete.py
# → Mode 1, name: 'Legacy 2024 PII Block'
# → Type DELETE, re-type name
# → Activate: y
```

### Scenario B — Bulk cleanup of disabled rules

```bash
# 1. Identify disabled rules (Step 2, Option C)
# 2. Take snapshot
# 3. Run deleter

python scripts/zia_dlp_delete.py
# → Mode 2, paste comma-separated names
# → Type DELETE
# → Activate: y
```

### Scenario C — Tenant cleanup before re-import (DR rebuild)

```bash
# 1. Export
python scripts/zia_dlp_export.py

# 2. Delete in slabs of 100 until empty
python scripts/zia_dlp_delete.py
# → Mode 3, start=1, size=100   (repeat until 'no rules found')
# → Activate after each slab OR once at the end

# 3. Re-import from a known-good source
python scripts/zia_dlp_import.py known_good.json
# → Mode 3, start=0, size=ALL
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `404 Not Found` | Rule already deleted or name typo | Refresh export and re-check
