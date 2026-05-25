"""ZIA DLP Rule Deleter — Zscaler OneAPI."""
import os, sys, csv, json, time, logging
from datetime import datetime
import requests
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("zia-dlp-delete")

ZIA_BASE = "/zia/api/v1"
SLAB_CHOICES = {"1": 10, "2": 50, "3": 100}


class ZscalerOneAPIClient:
    def __init__(self, client_id, client_secret, vanity, base_url="https://api.zsapi.net"):
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
        log.info("Authenticated.")

    def _req(self, method, path):
        url = f"{self.base_url}{path}"
        r = self.s.request(method, url, timeout=60)
        if r.status_code == 401:
            self.authenticate()
            r = self.s.request(method, url, timeout=60)
        if r.status_code >= 400:
            raise RuntimeError(f"{method} {path} [{r.status_code}]: {r.text}")
        if not r.content:
            return None
        try:
            return r.json()
        except json.JSONDecodeError:
            return r.text

    def get(self, path): return self._req("GET", path)
    def delete(self, path): return self._req("DELETE", path)
    def post(self, path): return self._req("POST", path)


def list_rules(c):
    r = c.get(f"{ZIA_BASE}/webDlpRules") or []
    return r if isinstance(r, list) else []


def del_rule(c, rid):
    try:
        c.delete(f"{ZIA_BASE}/webDlpRules/{rid}")
        return True
    except RuntimeError as e:
        log.error("    x delete id=%s: %s", rid, e)
        return False


def activate(c):
    try:
        log.info("Activating changes...")
        c.post(f"{ZIA_BASE}/status/activate")
        log.info("Activation submitted.")
    except RuntimeError as e:
        log.warning("Activation failed: %s", e)


def by_single(rules, name):
    name = name.strip()
    m = [r for r in rules if str(r.get("name", "")).strip() == name]
    log.info("Match for '%s': %d", name, len(m))
    return m


def by_multi(rules, csv_names):
    want = {n.strip() for n in csv_names.split(",") if n.strip()}
    m = [r for r in rules if str(r.get("name", "")).strip() in want]
    found = {str(r.get("name", "")).strip() for r in m}
    miss = want - found
    log.info("Matched %d/%d.", len(found), len(want))
    if miss:
        log.warning("Not found: %s", ", ".join(sorted(miss)))
    return m


def by_slab(rules, start, size):
    s = sorted(rules, key=lambda r: r.get("order", 10**9))
    elig = [r for r in s if int(r.get("order", 0)) >= start]
    sel = elig[:size]
    log.info("Slab start=%d size=%d -> selected=%d (eligible=%d)", start, size, len(sel), len(elig))
    return sel


def write_audit(deleted, failed, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([f"ZIA DLP Deletion Audit - {datetime.utcnow().isoformat()}Z"])
        w.writerow([])
        w.writerow([f"=== Deleted ({len(deleted)}) ==="])
        w.writerow(["id", "name", "order", "rank", "state"])
        for r in deleted:
            w.writerow([r.get("id"), r.get("name"), r.get("order"), r.get("rank"), r.get("state")])
        w.writerow([])
        w.writerow([f"=== Failed ({len(failed)}) ==="])
        w.writerow(["id", "name", "order", "error"])
        for r in failed:
            w.writerow([r.get("id"), r.get("name"), r.get("order"), r.get("error")])
    log.info("Audit saved: %s", os.path.abspath(path))


def do_delete(c, targets, pause=0.3):
    deleted, failed = [], []
    if not targets:
        log.info("Nothing to delete.")
        return deleted, failed
    print("\nRules selected for deletion:")
    print(f"{'ID':<10} {'Order':<6} Name")
    print("-" * 70)
    for r in targets:
        print(f"{str(r.get('id','')):<10} {str(r.get('order','')):<6} {r.get('name','')}")
    print("-" * 70)
    print(f"Total: {len(targets)}\n")
    if input("Type 'DELETE' to confirm: ").strip() != "DELETE":
        log.info("Cancelled.")
        return deleted, failed
    for r in targets:
        rid = r.get("id")
        log.info("Deleting id=%s name='%s' order=%s", rid, r.get("name"), r.get("order"))
        if del_rule(c, rid):
            deleted.append(r)
            log.info("    + Deleted")
        else:
            failed.append({**r, "error": "delete failed"})
        time.sleep(pause)
    return deleted, failed


def menu():
    print("\n" + "=" * 60)
    print("  ZIA DLP Rule Deletion")
    print("=" * 60)
    print("  1) Delete by single policy name")
    print("  2) Delete by multiple policy names (comma-separated)")
    print("  3) Delete in slabs (10/50/100) from starting order")
    print("  q) Quit")
    print("=" * 60)
    return input("Select [1/2/3/q]: ").strip().lower()


def slab_size():
    print("\nSlab sizes:  1) 10   2) 50   3) 100")
    ch = input("Select [1/2/3]: ").strip()
    if ch not in SLAB_CHOICES:
        raise ValueError(f"Invalid slab: {ch}")
    return SLAB_CHOICES[ch]


def main():
    load_dotenv()
    cid = os.getenv("ZSCALER_CLIENT_ID")
    csec = os.getenv("ZSCALER_CLIENT_SECRET")
    vanity = os.getenv("ZSCALER_VANITY_DOMAIN")
    base = os.getenv("ZSCALER_API_BASE_URL", "https://api.zsapi.net")
    miss = [k for k, v in [("ZSCALER_CLIENT_ID", cid), ("ZSCALER_CLIENT_SECRET", csec),
                            ("ZSCALER_VANITY_DOMAIN", vanity)] if not v]
    if miss:
        log.error("Missing env vars: %s", ", ".join(miss))
        return 2
    try:
        c = ZscalerOneAPIClient(cid, csec, vanity, base)
        c.authenticate()
        log.info("Fetching DLP Web Rules...")
        rules = list_rules(c)
        log.info("Total rules: %d", len(rules))
        if not rules:
            return 0
        ch = menu()
        if ch == "1":
            name = input("Enter policy name: ").strip()
            if not name:
                log.error("Empty name.")
                return 2
            targets = by_single(rules, name)
        elif ch == "2":
            names = input("Enter comma-separated names: ").strip()
            if not names:
                log.error("Empty names.")
                return 2
            targets = by_multi(rules, names)
        elif ch == "3":
            try:
                start = int(input("Starting order number (e.g. 1): ").strip())
            except ValueError:
                log.error("Order must be integer.")
                return 2
            targets = by_slab(rules, start, slab_size())
        elif ch == "q":
            return 0
        else:
            log.error("Invalid: %s", ch)
            return 2
        if not targets:
            log.info("No matching rules.")
            return 0
        deleted, failed = do_delete(c, targets)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        write_audit(deleted, failed, f"zia_dlp_delete_audit_{ts}.csv")
        if deleted:
            if input("\nActivate ZIA changes now? [y/N]: ").strip().lower() == "y":
                activate(c)
            else:
                log.info("Skipped activation. Activate via UI or rerun.")
        log.info("Done. Deleted=%d Failed=%d", len(deleted), len(failed))
        return 0
    except Exception as e:
        log.error("Failed: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())

