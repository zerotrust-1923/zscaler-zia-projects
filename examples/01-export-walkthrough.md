# Walkthrough 01 — Export DLP Policies

End-to-end guide for exporting Zscaler ZIA DLP policies to CSV and JSON using
the `zia_dlp_export.py` script.

---

## Overview

Export is a **read-only** operation. It pulls the following objects from your
ZIA tenant via OneAPI and writes them to disk:

| Object | API endpoint | Purpose |
|---|---|---|
| DLP Web Rules | `/zia/api/v1/webDlpRules` | The policy rules themselves |
| DLP Engines | `/zia/api/v1/dlpEngines` | Engine definitions referenced by rules |
| DLP Dictionaries | `/zia/api/v1/dlpDictionaries` | Pattern/phrase dictionaries |
| Notification Templates | `/zia/api/v1/dlpNotificationTemplates` | End-user notification templates |
| ICAP Servers | `/zia/api/v1/icapServers` | External ICAP server definitions |
| IDM Profiles | `/zia/api/v1/idmprofile` | Indexed Document Match profiles |

No tenant data is modified.

---

## Prerequisites

- Python 3.9+ installed
- Repo cloned locally (or running in Codespaces)
- Dependencies installed: `pip install -r requirements.txt`
- Valid `.env` file (see Step 1)
- OneAPI client with **read** scopes on the endpoints above

---

## Step 1 — Configure credentials

Copy the template and fill in your tenant values:

```bash
cp .env.example .env
Edit .env:

env
Download
Copy
ZSCALER_CLIENT_ID=abc123-your-client-id
ZSCALER_CLIENT_SECRET=your-client-secret
ZSCALER_VANITY_DOMAIN=acme-prod
ZSCALER_API_BASE_URL=https://api.zsapi.net
EXPORT_FORMAT=both
Variable	Required	Notes
ZSCALER_CLIENT_ID	✅	OneAPI OAuth2 client ID from Zidentity
ZSCALER_CLIENT_SECRET	✅	OneAPI OAuth2 client secret
ZSCALER_VANITY_DOMAIN	✅	Prefix of <vanity>.zslogin.net
ZSCALER_API_BASE_URL	⭕	Default: https://api.zsapi.net
EXPORT_FORMAT	⭕	csv, json, or both (default)

Step 2 — Run the export
bash
Download
Copy
python scripts/zia_dlp_export.py
Choose output format via env var
bash
Download
Copy
EXPORT_FORMAT=csv  python scripts/zia_dlp_export.py
EXPORT_FORMAT=json python scripts/zia_dlp_export.py
EXPORT_FORMAT=both python scripts/zia_dlp_export.py   # default
Or via CLI flag (if supported)
bash
Download
Copy
python scripts/zia_dlp_export.py --format json
Step 3 — Expected output
text
Download
Copy
2026-05-25 11:45:01 | INFO | Authenticating to https://acme-prod.zslogin.net/oauth2/v1/token
2026-05-25 11:45:02 | INFO | Authenticated.
2026-05-25 11:45:02 | INFO | Fetching DLP Web Rules...
2026-05-25 11:45:03 | INFO |   + 137 rules
2026-05-25 11:45:03 | INFO | Fetching DLP Engines...
2026-05-25 11:45:04 | INFO |   + 24 engines
2026-05-25 11:45:04 | INFO | Fetching DLP Dictionaries...
2026-05-25 11:45:05 | INFO |   + 58 dictionaries
2026-05-25 11:45:05 | INFO | Fetching Notification Templates...
2026-05-25 11:45:05 | INFO |   + 6 templates
2026-05-25 11:45:06 | INFO | Fetching ICAP Servers...
2026-05-25 11:45:06 | INFO |   + 2 ICAP servers
2026-05-25 11:45:06 | INFO | Fetching IDM Profiles...
2026-05-25 11:45:07 | INFO |   + 11 IDM profiles
2026-05-25 11:45:07 | INFO | Writing zia_dlp_policies.json...
2026-05-25 11:45:07 | INFO | Writing zia_dlp_policies.csv...
2026-05-25 11:45:07 | INFO | Done. JSON=zia_dlp_policies.json  CSV=zia_dlp_policies.csv
Step 4 — Inspect the artifacts
JSON structure
json
Download
Copy
{
  "exportedAt": "2026-05-25T11:45:07Z",
  "tenant": "acme-prod",
  "data": {
    "DLP Web Rules": [ { "id": 12345, "name": "Block PII Upload", "order": 1, ... } ],
    "DLP Engines": [ ... ],
    "DLP Dictionaries": [ ... ],
    "Notification Templates": [ ... ],
    "ICAP Servers": [ ... ],
    "IDM Profiles": [ ... ]
  }
}
The JSON file is the canonical source consumed by:

scripts/zia_dlp_import.py
scripts/zia_dlp_update.py
scripts/zia_dlp_delete.py (optional reference)
CSV structure
One CSV per object family, written either as separate files or as a single multi-section file (depending on configuration). Useful for spreadsheet review, diff against previous exports, and human audit.

Step 5 — Verify counts
Quick sanity check to confirm the export is complete:

bash
Download
Copy
python -c "import json; d=json.load(open('zia_dlp_policies.json'))['data']; \
[print(f'{k}: {len(v)}') for k,v in d.items()]"
Expected output:

text
Download
Copy
DLP Web Rules: 137
DLP Engines: 24
DLP Dictionaries: 58
Notification Templates: 6
ICAP Servers: 2
IDM Profiles: 11
Common scenarios
Scenario A — Daily backup
Run via cron / Task Scheduler:

bash
Download
Copy
0 2 * * *  cd /opt/zia-dlp-manager && /opt/zia-dlp-manager/.venv/bin/python scripts/zia_dlp_export.py >> /var/log/zia-dlp-export.log 2>&1
Scenario B — Pre-change snapshot
Always run an export immediately before any import/update/delete:

bash
Download
Copy
python scripts/zia_dlp_export.py
cp zia_dlp_policies.json zia_dlp_policies_backup_$(date +%Y%m%d_%H%M%S).json
Scenario C — Cross-tenant migration source
Export from the source tenant, then feed the JSON into import on the target tenant — see 02-import-walkthrough.md.

Troubleshooting
Symptom	Likely cause	Fix
Auth failed [401]	Wrong client ID/secret	Verify .env; rotate credentials in Zidentity
Auth failed [400] invalid_audience	Wrong audience or tenant	Confirm vanity domain spelling
403 Forbidden on an endpoint	Missing API scope	Add the read scope in Zidentity → re-issue token
Empty DLP Web Rules array	New tenant or wrong tenant	Confirm in ZIA Admin UI under Policy → DLP
Connection timeout	Network egress blocked	Allow *.zsapi.net, *.zslogin.net outbound 443


