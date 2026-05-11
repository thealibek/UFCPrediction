"""Real-time UFC данные через публичный ESPN API.
Endpoint: site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard
- Бесплатно, без ключа, обновляется в реальном времени.
- Возвращает текущий/ближайший event со всеми боями: фото, флаги, odds, ранкинги, статус.
"""
from datetime import datetime
import requests
import streamlit as st

ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard"
ESPN_CALENDAR = "https://site.api.espn.com/apis/site/v2/sports/mma/ufc/calendar"


@st.cache_data(ttl=300, show_spinner=False)
def fetch_espn_scoreboard(date: str | None = None) -> dict:
    """Текущий или конкретный (YYYYMMDD) event card с ESPN."""
    params = {"dates": date} if date else {}
    r = requests.get(ESPN_SCOREBOARD, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=600, show_spinner=False)
def fetch_espn_calendar() -> list:
    """Список ближайших UFC событий."""
    try:
        r = requests.get(ESPN_CALENDAR, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []


def _athlete(competitor: dict) -> dict:
    ath = competitor.get("athlete") or {}
    flag = ath.get("flag") or {}
    head = ath.get("headshot") or {}
    photo = head.get("href")
    # Fallback: пробуем стандартный ESPN headshot URL по athlete id
    if not photo and ath.get("id"):
        photo = f"https://a.espncdn.com/i/headshots/mma/players/full/{ath['id']}.png"
    return {
        "id": ath.get("id"),
        "name": ath.get("displayName") or "TBD",
        "short_name": ath.get("shortName") or ath.get("displayName") or "TBD",
        "country": flag.get("alt") or "",
        "flag_url": flag.get("href"),
        "photo": photo,
        "record": ath.get("record"),
        "rank": competitor.get("rank") or ath.get("rank"),
        "winner": competitor.get("winner"),
    }


def _odds(comp: dict) -> tuple[str | None, str | None]:
    """Возвращает moneyline odds для (home, away) если доступны."""
    odds_list = comp.get("odds") or []
    if not odds_list:
        return None, None
    o = odds_list[0]
    home = (o.get("homeTeamOdds") or {}).get("moneyLine")
    away = (o.get("awayTeamOdds") or {}).get("moneyLine")
    home_s = f"{int(home):+d}" if isinstance(home, (int, float)) else None
    away_s = f"{int(away):+d}" if isinstance(away, (int, float)) else None
    return home_s, away_s


def parse_event(ev: dict) -> dict:
    """Парсим один event в удобную структуру."""
    fights = []
    for comp in ev.get("competitions", []):
        cs = comp.get("competitors", [])
        if len(cs) < 2:
            continue
        # ESPN: cs[0] обычно home, cs[1] away — но не критично
        a = _athlete(cs[0])
        b = _athlete(cs[1])
        odds_a, odds_b = _odds(comp)
        wc = (comp.get("type") or {}).get("text") \
            or (comp.get("note") or "") \
            or "Bout"
        status_obj = comp.get("status") or {}
        status_type = status_obj.get("type", {}) or {}
        # Метод финиша (KO/TKO/Sub/Decision) и раунд
        method = (status_type.get("detail")
                  or status_type.get("shortDetail")
                  or status_type.get("description")
                  or "")
        result = (comp.get("status") or {}).get("result") or {}
        if isinstance(result, dict) and result.get("name"):
            # Иногда ESPN возвращает напр. "TKO - Punches" в result.name
            method = result.get("name") or method
        round_num = status_obj.get("period") or 0
        fights.append({
            "weight_class": wc,
            "a": a, "b": b,
            "odds_a": odds_a, "odds_b": odds_b,
            "status": status_type.get("description", ""),
            "completed": status_type.get("completed", False),
            "method": method,
            "round": round_num,
        })
    venue_name = ""
    venues = ev.get("competitions", [{}])
    if venues:
        v = venues[0].get("venue") or {}
        venue_name = v.get("fullName", "") or ""
    return {
        "id": ev.get("id"),
        "name": ev.get("name") or ev.get("shortName") or "UFC Event",
        "date": ev.get("date"),
        "venue": venue_name,
        "fights": fights,
    }


def get_live_events() -> list:
    """Главная функция: возвращает список ближайших event-ов с боями."""
    try:
        data = fetch_espn_scoreboard()
        events = data.get("events", [])
        return [parse_event(e) for e in events]
    except Exception as e:
        raise RuntimeError(f"ESPN API error: {e}")


@st.cache_data(ttl=300, show_spinner=False)
def fetch_espn_range(start_yyyymmdd: str, end_yyyymmdd: str) -> dict:
    """Получаем events за диапазон дат."""
    r = requests.get(
        ESPN_SCOREBOARD,
        params={"dates": f"{start_yyyymmdd}-{end_yyyymmdd}"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def get_events_range(start_yyyymmdd: str, end_yyyymmdd: str) -> list:
    """События за диапазон дат, парсенные."""
    try:
        data = fetch_espn_range(start_yyyymmdd, end_yyyymmdd)
        return [parse_event(e) for e in data.get("events", [])]
    except Exception as e:
        raise RuntimeError(f"ESPN API error: {e}")
