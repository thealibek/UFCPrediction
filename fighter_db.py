"""Lookup-слой над fighters_db.json. Используется в prediction pipeline."""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

DB_FILE = Path("fighters_db.json")


def _norm(s: str) -> str:
    """Нормализация имени для матчинга (lowercase, без диакритики)."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9 ]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


@lru_cache(maxsize=1)
def _load() -> tuple[dict, dict]:
    """Загружает БД и строит два индекса:
    - exact: full normalized name → fighter
    - by_last: last_name → list of fighters (для disambiguation)
    """
    if not DB_FILE.exists():
        return {}, {}
    db = json.loads(DB_FILE.read_text())
    exact = {}
    by_last = {}
    for f in db:
        name = f.get("name")
        if not name:
            continue
        k = _norm(name)
        exact[k] = f
        parts = k.split()
        if len(parts) >= 2:
            by_last.setdefault(parts[-1], []).append(f)
    return exact, by_last


def lookup(name: str) -> dict | None:
    """Возвращает запись из БД или None. Точный матч приоритет,
    last-name fallback только если first initial совпадает И ровно один кандидат.
    """
    if not name:
        return None
    exact, by_last = _load()
    k = _norm(name)
    if k in exact:
        return exact[k]
    parts = k.split()
    if len(parts) >= 2:
        last = parts[-1]
        first_initial = parts[0][:1]
        candidates = by_last.get(last, [])
        # фильтр: первый initial совпадает
        matching = [c for c in candidates
                    if _norm(c["name"]).split()[0][:1] == first_initial]
        if len(matching) == 1:
            return matching[0]
    return None


def enrich_fighter(fa: dict) -> dict:
    """Берёт минимум {name} и дозаполняет полями из БД."""
    if not isinstance(fa, dict) or not fa.get("name"):
        return fa
    rec = lookup(fa["name"])
    if not rec:
        return fa
    merged = dict(fa)
    # дозаполняем только пустые поля (UI-данные имеют приоритет)
    for k, v in rec.items():
        if v in (None, "", [], {}):
            continue
        if merged.get(k) in (None, "", [], {}):
            merged[k] = v
    merged["_db_match"] = rec.get("name")
    return merged


def db_size() -> int:
    exact, _ = _load()
    return len(exact)


def stats_summary() -> dict:
    exact, _ = _load()
    db_list = list(exact.values())
    enriched = sum(1 for f in db_list if f.get("SLpM") is not None)
    by_org = {}
    for f in db_list:
        o = f.get("org", "?")
        by_org[o] = by_org.get(o, 0) + 1
    return {
        "total": len(db_list),
        "enriched_with_stats": enriched,
        "by_org": by_org,
    }
