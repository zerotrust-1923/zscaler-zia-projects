"""ZIA DLP Updater - update existing DLP rules from JSON."""
import os, sys, time, logging
from datetime import datetime
from dotenv import load_dotenv

from zia_dlp_update_client import ZscalerOneAPIClient, ZIA_BASE, SLAB_CHOICES
from zia_dlp_update_core import (
    load_rules_json, fetch_existing_rules, build_update_payload,
    select_single, select_multi, select_slab_by_order, write_audit,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("zia-dlp-update")


def update_rule(c, rid, payload):
    return c.put(f"{ZIA_BASE}/webDlpRules/{rid}", body=payload)


def activate(c):
    try:
        log.info("Activating ZIA changes...")
        c.post(f"{ZIA_BASE}/status/activate")
        log.info("Activation submitted.")
    except RuntimeError as e:
        log.warning("Activation failed: %s", e)


def menu():
    print("\n" + "=" * 60)
    print("  ZIA DLP Rule Updater (from JSON)")
    print("=" * 60)
    print("  1) Update single rule by name")
    print("  2) Update multiple rules by name (comma-separated)")
    print("  3) Update slab from starting order (5/10/50/100)")
    print("  q) Quit")
    print("=" * 60)
    return input("Select [1/2/3/q]: ").strip().lower()


def slab_menu():
    print("\nSlab sizes:  1) 5   2) 10   3) 50   4) 100")
    ch = input("Select [1/2/3/4]: ").strip()
    if ch not in SLAB_CHOICES:
        raise ValueError(f"Invalid slab: {ch}")
    return SLAB_CHOICES[ch]


def do_update(c, source_targets, existing_by_name, pause=0.4):
    updated, failed = [], []
    pairs = []
    for src in source_targets:
        nm = str(src.get("name", "")).strip()
        ex = existing_by_name.get(nm)
        if not ex:
            failed.append({"id": None, "name": nm,
                           "error": "no existing rule with this name on target tenant"})
            log.warning("Skip '%s': not on target tenant.", nm)
            continue
        pairs.append((src, ex))

    if not pairs:
        log.info("No matching rules on target tenant.")
        return updated, failed

    print("\nRules to update:")
    print(f"{'ID':<10} {'Order':<6} Name")
    print("-" * 70)
    for _, ex in pairs:
        print(f"{str(ex.get('id','')):<10} {str(ex.get('order','')):<6} {ex.get('name','')}")
    print("-" * 70)
    print(f"Total: {len(pairs)}\n")

    if input("Type 'UPDATE' to confirm: ").strip() != "UPDATE":
        log.info("Cancelled.")
        return updated, failed

    for src, ex in pairs:
        rid = ex["id"]
        nm = ex.get("name")
        try:
            payload = build_update_payload(src, ex)
        except ValueError as e:
            failed.append({"id": rid, "name": nm, "error": str(e)})
            log.error("Skip id=%s: %s", rid, e)
            continue

        log.info("Updating id=%s name='%s'...", rid, nm)
        try:
            resp = update_rule(c, rid, payload)
            if isinstance(resp, dict) and resp.get("id"):
                log.info("    + Updated id=%s", resp.get("id"))
                updated.append(resp)
            else:
                log.info("    + Updated id=%s (no body returned)", rid)
                updated.append({"id": rid, "name": nm,
                                "order": ex.get("order"), "rank": ex.get("rank"),
                                "state": ex.get("state")})
        except RuntimeError as e:
            log.error("    x Failed id=%s: %s", rid, e)
            failed.append({"id": rid, "name": nm, "error": str(e)})
        time.sleep(pause)

    return updated, failed


def main():
    load_dotenv()
    cid = os.getenv("ZSCALER_CLIENT_ID")
    csec = os.getenv("ZSCALER_CLIENT_SECRET")
    vanity = os.getenv("ZSCALER_VANITY_DOMAIN")
    base = os.getenv("ZSCALER_API_BASE_URL", "https://api.zsapi.net")
    json_path = os.getenv("INPUT_JSON", "zia_dlp_policies.json")

    miss = [k for k, v in [("ZSCALER_CLIENT_ID", cid),
                           ("ZSCALER_CLIENT_SECRET", csec),
                           ("ZSCALER_VANITY_DOMAIN", vanity)] if not v]
    if miss:
        log.error("Missing env vars: %s", ", ".join(miss))
        return 2

    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        json_path = sys.argv[1]

    try:
        source_rules = load_rules_json(json_path)
        if not source_rules:
            log.info("No rules in JSON.")
            return 0

        c = ZscalerOneAPIClient(cid, csec, vanity, base)
        c.authenticate()

        log.info("Fetching existing DLP rules from target tenant...")
        existing = fetch_existing_rules(c)
        log.info("Existing rules on target: %d", len(existing))
        existing_by_name = {str(r.get("name", "")).strip(): r for r in existing}

        ch = menu()
        if ch == "1":
            n = input("Enter rule name: ").strip()
            if not n:
                log.error("Empty name."); return 2
            targets = select_single(source_rules, n)
        elif ch == "2":
            ns = input("Enter comma-separated names: ").strip()
            if not ns:
                log.error("Empty names."); return 2
            targets = select_multi(source_rules, ns)
        elif ch == "3":
            try:
                start = int(input("Starting order number (e.g. 1): ").strip())
            except ValueError:
                log.error("Order must be integer."); return 2
            targets = select_slab_by_order(source_rules, start, slab_menu())
        elif ch == "q":
            return 0
        else:
            log.error("Invalid choice: %s", ch); return 2

        if not targets:
            log.info("No matching rules selected.")
            return 0

        updated, failed = do_update(c, targets, existing_by_name)

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        write_audit(updated, failed, f"zia_dlp_update_audit_{ts}.csv")

        if updated:
            if input("\nActivate ZIA changes now? [y/N]: ").strip().lower() == "y":
                activate(c)
            else:
                log.info("Skipped activation. Activate via UI or rerun.")

        log.info("Done. Updated=%d Failed=%d", len(updated), len(failed))
        return 0

    except Exception as e:
        log.error("Update failed: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())

