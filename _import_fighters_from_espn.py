"""Импорт участников ESPN-ивента в fighters.json (базовый профиль).
Имя, страна, country_code, photo URL, ESPN id, record. Остальное (height,
reach, SLpM и т.п.) останется null — пользователь дозаполняет через UI.
"""
import json, os, sys, types
from pathlib import Path

_st = types.ModuleType("streamlit")
def _noop(*a, **kw):
    def deco(fn): return fn
    if a and callable(a[0]): return a[0]
    return deco
_st.cache_data = _noop
sys.modules["streamlit"] = _st

from live_data import fetch_espn_range, parse_event

EVENT_ID = sys.argv[1] if len(sys.argv) > 1 else "600058807"
DATE_RANGE = ("20260420", "20260520")

FIGHTERS_FILE = Path("fighters.json")

def _slug_country(name):
    return (name or "").lower()


def main():
    raw = fetch_espn_range(*DATE_RANGE)
    target = None
    for e in raw.get("events", []):
        if str(e.get("id")) == EVENT_ID:
            target = parse_event(e); break
    if not target:
        print(f"❌ event {EVENT_ID} not found"); sys.exit(1)

    existing = json.loads(FIGHTERS_FILE.read_text()) if FIGHTERS_FILE.exists() else []
    by_name = {f["name"]: f for f in existing}

    added, updated = 0, 0
    for fight in target["fights"]:
        for side in ("a", "b"):
            ath = fight.get(side) or {}
            name = ath.get("name")
            if not name or name == "TBD":
                continue
            base = {
                "name": name,
                "country": ath.get("country") or "",
                "photo": ath.get("photo"),
                "espn_id": ath.get("id"),
                "record": ath.get("record"),
                # placeholders for enrichment
                "age": None, "height_cm": None, "reach_cm": None,
                "stance": None, "division": fight.get("weight_class"),
                "style": None,
                "SLpM": None, "SApM": None,
                "StrAcc": None, "StrDef": None,
                "TDAvg": None, "TDDef": None, "SubAvg": None,
                "strengths": [], "weaknesses": [],
                "weight_cut_difficulty": None,
                "needs_enrichment": True,
                "source": "espn_blind_import",
            }
            if name in by_name:
                # обновляем только поля которые пустые
                existing_rec = by_name[name]
                for k, v in base.items():
                    if existing_rec.get(k) in (None, "", [], {}) and v not in (None, "", [], {}):
                        existing_rec[k] = v
                updated += 1
            else:
                existing.append(base)
                by_name[name] = base
                added += 1

    FIGHTERS_FILE.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
    print(f"✅ Added {added}, updated {updated}. Total fighters: {len(existing)}")


if __name__ == "__main__":
    main()
