"""ZIA DLP Policy Exporter — exports to CSV and/or JSON via Zscaler OneAPI."""
import os, sys, csv, json, logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import requests
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("zia-dlp-export")

ZIA_BASE = "/zia/api/v1"
VALID_FORMATS = {"csv", "json", "both"}


class ZscalerOneAPIClient:
    def __init__(self, client_id, client_secret, vanity, base_url="https://api.zsapi.net"):
        if not all([client_id, client_secret, vanity]):
            raise ValueError("client_id, client_secret, and vanity are required.")
        self.cid, self.csec, self.vanity = client_id, client_secret, vanity
        self.base_url = base_url.rstrip("/")
        self.token_url = f"https://{vanity}.zslogin.net/oauth2/v1/token"
        self.s = requests.Session()

    def authenticate(self):
        log.info("Authenticating to %s", self.token_url)
        r = self.s.post(self.token_url,
            data={"grant_type": "client_credentials", "client_id": self.cid,
                  "client_secret": self.csec, "audience": "https://api.zscaler.com"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30)
        if r.status_code != 200:
            raise RuntimeError(f"Auth failed [{r.status_code}]: {r.text}")
        token = r.json().get("access_token")
        if not token:
            raise RuntimeError("No access_token in response")
        self.s.headers.update({"Authorization": f"Bearer {token}",
                               "Accept": "application/json", "Content-Type": "application/json"})
        log.info("Authenticated successfully.")

    def get(self, path, params=None):
        url = f"{self.base_url}{path}"
        r = self.s.get(url, params=params, timeout=60)
        if r.status_code == 401:
            self.authenticate()
            r = self.s.get(url, params=params, timeout=60)
        if r.status_code >= 400:
            raise RuntimeError(f"GET {path} [{r.status_code}]: {r.text}")
        if not r.content:
            return []
        try:
            return r.json()
        except json.JSONDecodeError:
            return r.text


def safe_fetch(label, fn):
    try:
        result = fn() or []
        if not isinstance(result, list):
            result = [result]
        log.info("  -> %s: %d records", label, len(result))
        return result
    except RuntimeError as e:
        log.warning("  -> %s: skipped (%s)", label, e)
        return []


def fetch_rules(c):    return c.get(f"{ZIA_BASE}/webDlpRules") or []
def fetch_engines(c):  return c.get(f"{ZIA_BASE}/dlpEngines") or []
def fetch_dicts(c):    return c.get(f"{ZIA_BASE}/dlpDictionaries") or []
def fetch_tmpls(c):    return c.get(f"{ZIA_BASE}/dlpNotificationTemplates") or []
def fetch_icap(c):     return c.get(f"{ZIA_BASE}/icapServers") or []
def fetch_idm(c):      return c.get(f"{ZIA_BASE}/idmprofile") or []


# -------------------- CSV --------------------
def flatten(v):
    if v is None:
        return ""
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def write_section(w, title, records):
    w.writerow([])
    w.writerow([f"=== {title} (count={len(records)}) ==="])
    if not records:
        w.writerow(["No records found."])
        return
    keys, seen = [], set()
    for r in records:
        if isinstance(r, dict):
            for k in r.keys():
                if k not in seen:
                    seen.add(k)
                    keys.append(k)
    if not keys:
        w.writerow(["value"])
        for r in records:
            w.writerow([flatten(r)])
        return
    w.writerow(keys)
    for r in records:
        if not isinstance(r, dict):
            w.writerow([flatten(r)])
        else:
            w.writerow([flatten(r.get(k)) for k in keys])


def export_csv(path, sections):
    log.info("Writing CSV: %s", path)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([f"ZIA DLP Policy Export - {datetime.utcnow().isoformat()}Z"])
        for title, records in sections.items():
            write_section(w, title, records)
    log.info("CSV done: %s", os.path.abspath(path))


# -------------------- JSON --------------------
def export_json(path, sections):
    log.info("Writing JSON: %s", path)
    payload = {
        "exported_at_utc": datetime.utcnow().isoformat() + "Z",
        "source": "Zscaler OneAPI - ZIA DLP",
        "summary": {t: len(r) for t, r in sections.items()},
        "data": sections,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    log.info("JSON done: %s", os.path.abspath(path))


# -------------------- Format selection --------------------
def resolve_format():
    # 1. CLI arg --format / -f
    for i, a in enumerate(sys.argv):
        if a in ("--format", "-f") and i + 1 < len(sys.argv):
            fmt = sys.argv[i + 1].strip().lower()
            if fmt in VALID_FORMATS:
                log.info("Format from CLI: %s", fmt)
                return fmt
    # 2. Env var
    env_fmt = (os.getenv("EXPORT_FORMAT") or "").strip().lower()
    if env_fmt in VALID_FORMATS:
        log.info("Format from EXPORT_FORMAT env: %s", env_fmt)
        return env_fmt
    # 3. Menu
    print("\n" + "=" * 50)
    print("  Select Export Format")
    print("=" * 50)
    print("  1) CSV only")
    print("  2) JSON only")
    print("  3) Both CSV and JSON")
    print("=" * 50)
    ch = input("Select [1/2/3] (default 1): ").strip() or "1"
    mapping = {"1": "csv", "2": "json", "3": "both"}
    fmt = mapping.get(ch, "csv")
    log.info("Format selected: %s", fmt)
    return fmt


# -------------------- Main --------------------
def main():
    load_dotenv()
    cid = os.getenv("ZSCALER_CLIENT_ID")
    csec = os.getenv("ZSCALER_CLIENT_SECRET")
    vanity = os.getenv("ZSCALER_VANITY_DOMAIN")
    base = os.getenv("ZSCALER_API_BASE_URL", "https://api.zsapi.net")
    out_csv = os.getenv("OUTPUT_CSV", "zia_dlp_policies.csv")
    out_json = os.getenv("OUTPUT_JSON", "zia_dlp_policies.json")

    miss = [k for k, v in [("ZSCALER_CLIENT_ID", cid), ("ZSCALER_CLIENT_SECRET", csec),
                            ("ZSCALER_VANITY_DOMAIN", vanity)] if not v]
    if miss:
        log.error("Missing env vars: %s", ", ".join(miss))
        return 2

    fmt = resolve_format()

    try:
        c = ZscalerOneAPIClient(cid, csec, vanity, base)
        c.authenticate()

        sections = {
            "DLP Web Rules":              safe_fetch("DLP Web Rules", lambda: fetch_rules(c)),
            "DLP Engines":                safe_fetch("DLP Engines", lambda: fetch_engines(c)),
            "DLP Dictionaries":           safe_fetch("DLP Dictionaries", lambda: fetch_dicts(c)),
            "DLP Notification Templates": safe_fetch("DLP Notification Templates", lambda: fetch_tmpls(c)),
            "ICAP Servers":               safe_fetch("ICAP Servers", lambda: fetch_icap(c)),
            "IDM Profiles":               safe_fetch("IDM Profiles", lambda: fetch_idm(c)),
        }

        if fmt in ("csv", "both"):
            export_csv(out_csv, sections)
        if fmt in ("json", "both"):
            export_json(out_json, sections)

        log.info("---- Summary ----")
        for t, r in sections.items():
            log.info("%s: %d", t, len(r))
        if fmt in ("csv", "both"):
            log.info("CSV  : %s", os.path.abspath(out_csv))
        if fmt in ("json", "both"):
            log.info("JSON : %s", os.path.abspath(out_json))
        return 0

    except Exception as e:
        log.error("Export failed: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())

