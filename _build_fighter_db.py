"""Полная сборка fighters_db.json: UFC + Bellator + PFL + ONE.
Run: python3 _build_fighter_db.py [--quick | --no-enrich | --no-sherdog]
"""
import sys, time, json
from pathlib import Path
from fighter_scraper import (
    scrape_ufcstats_all, enrich_with_profiles, scrape_sherdog_roster,
    save_db, load_db, DB_FILE,
)

QUICK = "--quick" in sys.argv
NO_ENRICH = "--no-enrich" in sys.argv or QUICK
NO_SHERDOG = "--no-sherdog" in sys.argv


def progress(i, total, msg):
    pct = (i/total*100) if total else 0
    print(f"  [{i:3}/{total}] {pct:5.1f}% — {msg}", flush=True)


def main():
    t0 = time.time()
    print("=" * 70)
    print("📡 PHASE 1: UFCStats list scraper (A-Z)")
    print("=" * 70)
    ufc = scrape_ufcstats_all(progress_cb=progress)
    print(f"\n✅ UFCStats list: {len(ufc)} fighters in {time.time()-t0:.1f}s")
    save_db(ufc)
    print(f"💾 Saved → {DB_FILE}")

    if not NO_ENRICH:
        print("\n" + "=" * 70)
        print("🔬 PHASE 2: Enrich with deep profiles (SLpM/StrAcc/TDAvg/etc.)")
        print("=" * 70)
        # Фильтр для quick: только активные (with wins+losses>=1)
        targets = [f for f in ufc if (f.get("wins") or 0) + (f.get("losses") or 0) >= 1]
        print(f"   Enriching {len(targets)} of {len(ufc)} fighters with stats...")
        t1 = time.time()
        enrich_with_profiles(targets, max_workers=10, progress_cb=progress)
        print(f"\n✅ Enriched in {time.time()-t1:.1f}s")
        save_db(ufc)

    if not NO_SHERDOG:
        print("\n" + "=" * 70)
        print("🥊 PHASE 3: Sherdog rosters (Bellator/PFL/ONE)")
        print("=" * 70)
        all_others = []
        for org in ("Bellator", "PFL", "ONE"):
            t2 = time.time()
            print(f"\n→ Scraping {org}...")
            rows = scrape_sherdog_roster(org, max_pages=10)
            print(f"   {org}: {len(rows)} fighters in {time.time()-t2:.1f}s")
            all_others.extend(rows)

        # merge by name (UFC priority)
        ufc_names = {f["name"].lower() for f in ufc}
        new = [f for f in all_others if f["name"].lower() not in ufc_names]
        ufc.extend(new)
        save_db(ufc)
        print(f"\n✅ Added {len(new)} non-UFC fighters")

    # Stats
    db = load_db()
    by_org = {}
    for f in db:
        by_org[f.get("org","?")] = by_org.get(f.get("org","?"), 0) + 1
    enriched = sum(1 for f in db if f.get("SLpM") is not None)
    print(f"\n{'=' * 70}\n📊 FINAL DB STATS")
    print(f"{'=' * 70}")
    print(f"   Total fighters: {len(db)}")
    for k, v in sorted(by_org.items()): print(f"   {k}: {v}")
    print(f"   With deep stats (SLpM): {enriched}")
    print(f"   Total time: {time.time()-t0:.1f}s")
    print(f"   File size: {DB_FILE.stat().st_size/1024:.1f} KB")


if __name__ == "__main__":
    main()
