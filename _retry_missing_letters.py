"""Повторный прогон пропущенных букв с долгими паузами против rate-limit.
Inkremental: добавляет к существующей fighters_db.json, не удаляет."""
import time, json, string
from collections import Counter
from fighter_scraper import (
    scrape_ufcstats_list, scrape_ufcstats_profile, save_db, load_db,
)
import requests

db = load_db()
c = Counter(f["name"][0].lower() for f in db if f.get("name"))

# Считаем недобранные. UFCStats реально имеет 100+ на каждую активную букву.
THRESHOLD = 50
missing = [l for l in string.ascii_lowercase
           if c.get(l, 0) < THRESHOLD and l not in ("q","u","x")]  # Q/U/X реально маленькие
print(f"Letters to retry ({len(missing)}): {missing}")

sess = requests.Session()
total_added = 0
existing_ids = {f.get("ufcstats_id") for f in db if f.get("ufcstats_id")}

for li, letter in enumerate(missing, 1):
    print(f"\n[{li}/{len(missing)}] Letter {letter.upper()} (had {c.get(letter,0)})...")
    delay = 4.0  # стартовый большой
    rows = []
    for attempt in range(6):
        try:
            rows = scrape_ufcstats_list(letter, sess)
            print(f"  ✓ got {len(rows)} fighters")
            break
        except Exception as e:
            wait = delay * (1.6 ** attempt)
            print(f"  ✗ attempt {attempt+1}: {e} (wait {wait:.0f}s)")
            time.sleep(wait)
    # Добавляем новых
    added = 0
    for r in rows:
        if r.get("ufcstats_id") not in existing_ids:
            db.append(r); existing_ids.add(r.get("ufcstats_id"))
            added += 1
    total_added += added
    print(f"  +{added} new (total db: {len(db)})")
    save_db(db)
    # межбуквенная пауза побольше
    time.sleep(3.5)

print(f"\n✅ Phase 1 retry: +{total_added} fighters. Total: {len(db)}")

# Enrich новых
new_unenriched = [f for f in db if not f.get("SLpM") and f.get("ufcstats_url")]
print(f"\n🔬 Phase 2: enriching {len(new_unenriched)} fighters (serial, 0.5s delay)...")
for i, f in enumerate(new_unenriched, 1):
    try:
        prof = scrape_ufcstats_profile(f["ufcstats_url"], sess)
        f.update(prof)
        if i % 50 == 0:
            print(f"  [{i}/{len(new_unenriched)}] enriched"); save_db(db)
    except Exception as e:
        f["_profile_err"] = str(e)[:80]
    time.sleep(0.5)
save_db(db)

# Finalize
enriched = sum(1 for f in db if f.get("SLpM") is not None)
print(f"\n📊 FINAL: {len(db)} fighters, {enriched} with deep stats")
