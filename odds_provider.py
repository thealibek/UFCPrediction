"""Real-time UFC odds provider.

Использует TheOddsAPI (https://the-odds-api.com/) — бесплатный тир
500 запросов/мес, поддерживает MMA/UFC.

API key через env var `THE_ODDS_API_KEY`. Если ключа нет — функции
возвращают пустой результат gracefully.

Кеш в `odds_cache.json` (TTL 30 минут по умолчанию) — критично
чтобы не выжигать квоту при каждом rerun Streamlit.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime
from typing import Any

CACHE_FILE = "odds_cache.json"
CACHE_TTL_SEC = 30 * 60  # 30 минут

# TheOddsAPI endpoints
BASE_URL = "https://api.the-odds-api.com/v4"
SPORT_KEY = "mma_mixed_martial_arts"


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def _load_cache() -> dict:
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(data: dict) -> None:
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    except Exception:
        pass


def _get_cached(key: str, ttl: int = CACHE_TTL_SEC) -> Any | None:
    cache = _load_cache()
    entry = cache.get(key)
    if not entry:
        return None
    if time.time() - entry.get("ts", 0) > ttl:
        return None
    return entry.get("data")


def _set_cached(key: str, data: Any) -> None:
    cache = _load_cache()
    cache[key] = {"ts": time.time(), "data": data}
    _save_cache(cache)


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------

def _api_key() -> str:
    return os.environ.get("THE_ODDS_API_KEY", "").strip()


def is_available() -> bool:
    """Доступен ли API (есть ли ключ)."""
    return bool(_api_key())


def _request(path: str, params: dict | None = None) -> dict | list | None:
    """GET-запрос к TheOddsAPI."""
    import urllib.parse
    import urllib.request

    key = _api_key()
    if not key:
        return None

    params = params or {}
    params["apiKey"] = key
    url = f"{BASE_URL}{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[odds_provider] API error: {e}")
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_ufc_events(force_refresh: bool = False) -> list[dict]:
    """Список upcoming MMA событий с moneyline-коэффициентами.

    Returns: list of {
        "id": str, "commence_time": ISO datetime,
        "home_team": str, "away_team": str,
        "bookmakers": [{
            "key": "fanduel", "title": "FanDuel",
            "markets": [{
                "key": "h2h",
                "outcomes": [{"name": str, "price": float}, ...]
            }]
        }, ...]
    }
    """
    if not force_refresh:
        cached = _get_cached("events")
        if cached is not None:
            return cached

    if not is_available():
        return []

    data = _request(
        f"/sports/{SPORT_KEY}/odds",
        params={
            "regions": "us,eu",  # US + EU bookmakers
            "markets": "h2h",     # moneyline only (totals/props доступны только в премиум-тире)
            "oddsFormat": "decimal",
            "dateFormat": "iso",
        },
    )

    if not isinstance(data, list):
        return []

    _set_cached("events", data)
    return data


def get_event_props(event_id: str, force_refresh: bool = False) -> dict | None:
    """Method props (KO/Sub/Dec) и totals для конкретного события.
    Доступно только в премиум-тире TheOddsAPI."""
    cache_key = f"props_{event_id}"
    if not force_refresh:
        cached = _get_cached(cache_key, ttl=60 * 60)
        if cached is not None:
            return cached

    if not is_available():
        return None

    data = _request(
        f"/sports/{SPORT_KEY}/events/{event_id}/odds",
        params={
            "regions": "us,eu",
            "markets": "h2h,totals",
            "oddsFormat": "decimal",
        },
    )
    if data:
        _set_cached(cache_key, data)
    return data


# ---------------------------------------------------------------------------
# Helpers: matchmaking — найти odds для конкретной пары бойцов
# ---------------------------------------------------------------------------

def _norm(s: str) -> str:
    return (s or "").lower().strip().replace(".", "").replace("-", " ")


def find_fight_odds(fighter_a: str, fighter_b: str,
                     events: list[dict] | None = None) -> dict | None:
    """Найти бой по именам бойцов в списке событий.

    Returns: {
        "event_id": str,
        "commence_time": str,
        "fighter_a": str, "fighter_b": str,
        "odds_a": float, "odds_b": float,         # consensus (best odds)
        "odds_a_avg": float, "odds_b_avg": float,  # average across books
        "bookmakers": {key: {"odds_a": float, "odds_b": float}, ...},
    }
    """
    if events is None:
        events = get_ufc_events()
    if not events:
        return None

    na, nb = _norm(fighter_a), _norm(fighter_b)

    for ev in events:
        home = _norm(ev.get("home_team", ""))
        away = _norm(ev.get("away_team", ""))
        # tolerant match: substring in either direction
        match_home_a = (na in home or home in na) if home and na else False
        match_away_b = (nb in away or away in nb) if away and nb else False
        match_home_b = (nb in home or home in nb) if home and nb else False
        match_away_a = (na in away or away in na) if away and na else False

        if not ((match_home_a and match_away_b) or (match_home_b and match_away_a)):
            continue

        # Собираем коэфы по всем букам
        bookmakers = {}
        all_a, all_b = [], []
        for bk in ev.get("bookmakers", []):
            for mk in bk.get("markets", []):
                if mk.get("key") != "h2h":
                    continue
                outs = mk.get("outcomes", [])
                if len(outs) != 2:
                    continue
                # Сопоставляем outcomes с fighter_a / fighter_b
                o_a = o_b = None
                for o in outs:
                    n = _norm(o.get("name", ""))
                    if (n in na or na in n):
                        o_a = float(o.get("price", 0))
                    elif (n in nb or nb in n):
                        o_b = float(o.get("price", 0))
                if o_a and o_b:
                    bookmakers[bk["key"]] = {
                        "title": bk.get("title", bk["key"]),
                        "odds_a": o_a, "odds_b": o_b,
                        "last_update": bk.get("last_update", ""),
                    }
                    all_a.append(o_a)
                    all_b.append(o_b)

        if not bookmakers:
            continue

        return {
            "event_id": ev.get("id"),
            "commence_time": ev.get("commence_time"),
            "fighter_a": fighter_a, "fighter_b": fighter_b,
            "odds_a": max(all_a),     # best odds для bettor'а
            "odds_b": max(all_b),
            "odds_a_avg": sum(all_a) / len(all_a),
            "odds_b_avg": sum(all_b) / len(all_b),
            "bookmakers": bookmakers,
            "n_books": len(bookmakers),
            "fetched_at": datetime.now().isoformat(timespec="seconds"),
        }
    return None


def get_quota_info() -> dict:
    """Возвращает использование квоты API (только если был хотя бы 1 запрос).
    TheOddsAPI возвращает usage в headers, но мы их не сохраняем — функция
    делает «ping» запрос."""
    cache = _load_cache()
    return {
        "configured": is_available(),
        "cache_size": len(cache),
        "last_event_fetch": (cache.get("events", {}).get("ts", 0)
                              if cache.get("events") else 0),
    }


def clear_cache() -> None:
    """Сбросить кеш — например, перед важным карой."""
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
