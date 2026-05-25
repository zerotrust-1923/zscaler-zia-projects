"""ZIA DLP Importer - entry point."""
import os, sys, logging
from datetime import datetime
from dotenv import load_dotenv
from zia_dlp_import_core import (
    ZscalerOneAPIClient, SLAB_CHOICES,
    load_rules, by_single, by_multi, by_slab,
    do_import, write_audit, activate,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("zia-dlp-import")


def menu():
    print("\n" + "=" * 60)
    print("  ZIA DLP Rule Importer (from JSON)")
    print("=" * 60)
    print("  1) Import single rule by name")
    print("  2) Import multiple rules by name (comma-separated)")
    print("  3) Import in slabs (50 / 100 / ALL) from start index")
    print("  4) Import ALL rules")
    print("  q) Quit")
    print("=" * 60)
    return input("Select [1/2/3/4/q]: ").strip().lower()


def slab_menu():
    print("\nSlab sizes:  1) 50   2) 100   3) ALL")
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
    json_path = os.getenv("INPUT_JSON", "zia_dlp_policies.json")
    suffix = (os.getenv("IMPORT_NAME_SUFFIX") or "").strip()

    miss = [k for k, v in [("ZSCALER_CLIENT_ID", cid),
                           ("ZSCALER_CLIENT_SECRET", csec),
                           ("ZSCALER_VANITY_DOMAIN", vanity)] if not v]
    if miss:
        log.error("Missing env vars: %s", ", ".join(miss))
        return 2

    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        json_path = sys.argv[1]
    if suffix:
        log.info("Name suffix will be appended: '%s'", suffix)

    try:
        rules = load_rules(json_path)
        if not rules:
            log.info("No rules in JSON.")
            return 0

        c = ZscalerOneAPIClient(cid, csec, vanity, base)
        c.authenticate()

        ch = menu()
        if ch == "1":
            n = input("Enter rule name: ").strip()
            if not n:
                log.error("Empty name."); return 2
            targets = by_single(rules, n)
        elif ch == "2":
            ns = input("Enter comma-separated names: ").strip()
            if not ns:
                log.error("Empty names."); return 2
            targets = by_multi(rules, ns)
        elif ch == "3":
            try:
                start = int(input("Start index (0-based): ").strip())
            except ValueError:
                log.error("Index must be integer."); return 2
            targets = by_slab(rules, start, slab_menu())
        elif ch == "4":
            targets = sorted(rules, key=lambda r: r.get("order", 10**9))
        elif ch == "q":
            return 0
        else:
            log.error("Invalid choice: %s", ch); return 2

        if not targets:
            log.info("No matching rules."); return 0

        created, failed = do_import(c, targets, suffix=suffix)

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        write_audit(created, failed, f"zia_dlp_import_audit_{ts}.csv")

        if created:
            if input("\nActivate ZIA changes now? [y/N]: ").strip().lower() == "y":
                activate(c)
            else:
                log.info("Skipped activation. Activate via UI or rerun.")

        log.info("Done. Created=%d Failed=%d", len(created), len(failed))
        return 0

    except Exception as e:
        log.error("Import failed: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())

