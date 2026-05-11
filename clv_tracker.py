"""Closing Line Value (CLV) + ROI tracker.

Sharp бетторы измеряют успех не по win/loss, а по **CLV** — побеждаем
ли мы closing line (= коэф в момент закрытия рынка перед боем).

Если ты ставил Strickland @ 4.50, а closing line был 3.50 — твой CLV
положительный (рынок съехал в твою сторону → ты был прав в оценке).
Это **более стабильный sign skill'a** чем единичный win/loss.

Формулы:
- CLV (probability terms) = our_implied_prob_at_bet − closing_implied_prob
- CLV % = (your_odds / closing_odds) − 1
- ROI = (sum of profits) / (sum of stakes)
"""
from __future__ import annotations

from datetime import datetime
from typing import Iterable

from odds_engine import implied_prob


# ---------------------------------------------------------------------------
# Per-record CLV
# ---------------------------------------------------------------------------

def compute_clv(bet_odds: float, closing_odds: float) -> dict:
    """Считаем CLV для одной ставки.

    Returns: {
        "clv_prob": float,      # на сколько п.п. твой implied меньше closing implied (хорошо)
        "clv_pct": float,       # % скачка коэфа в твою пользу
        "verdict": "+CLV" | "-CLV" | "neutral"
    }
    """
    if not bet_odds or not closing_odds or bet_odds <= 1.0 or closing_odds <= 1.0:
        return {"clv_prob": None, "clv_pct": None, "verdict": "n/a"}

    bet_p = implied_prob(bet_odds)
    close_p = implied_prob(closing_odds)
    clv_prob = close_p - bet_p   # положительный = мы взяли по лучшему коэфу
    clv_pct = (bet_odds / closing_odds) - 1.0

    if clv_pct > 0.02:
        v = "+CLV"
    elif clv_pct < -0.02:
        v = "-CLV"
    else:
        v = "neutral"

    return {
        "clv_prob": round(clv_prob, 4),
        "clv_pct": round(clv_pct, 4),
        "bet_implied": round(bet_p, 4),
        "closing_implied": round(close_p, 4),
        "verdict": v,
    }


# ---------------------------------------------------------------------------
# ROI / bankroll metrics для всей истории
# ---------------------------------------------------------------------------

def betting_performance(history: list[dict]) -> dict:
    """Главный анализатор beting performance.

    Считает по всем resolved записям с заполненными `odds` и `stake`:
    - Total bets, won, lost
    - Total stake, total return, profit
    - ROI %
    - CLV stats (sample of records with `closing_odds_snapshot`)
    """
    bets = [h for h in history
            if h.get("status") in ("won", "lost")
            and h.get("odds") and h.get("stake")]

    if not bets:
        return {
            "n_bets": 0, "won": 0, "lost": 0,
            "total_stake": 0.0, "total_return": 0.0, "profit": 0.0,
            "roi": None, "avg_odds": None,
            "clv_n": 0, "clv_avg": None, "clv_positive_rate": None,
            "by_bet_type": {},
        }

    won = sum(1 for b in bets if b["status"] == "won")
    lost = sum(1 for b in bets if b["status"] == "lost")
    total_stake = sum(float(b["stake"]) for b in bets)

    total_return = 0.0
    for b in bets:
        odds = float(b["odds"])
        stake = float(b["stake"])
        if b["status"] == "won":
            total_return += stake * odds  # включая возврат stake
        # losses → 0 returned

    profit = total_return - total_stake
    roi = (profit / total_stake) if total_stake > 0 else None
    avg_odds = sum(float(b["odds"]) for b in bets) / len(bets)

    # CLV stats
    clv_records = []
    for b in bets:
        co = b.get("closing_odds_snapshot") or b.get("closing_odds")
        if co:
            clv = compute_clv(float(b["odds"]), float(co))
            if clv["clv_pct"] is not None:
                clv_records.append(clv["clv_pct"])

    clv_n = len(clv_records)
    clv_avg = (sum(clv_records) / clv_n) if clv_n else None
    clv_positive_rate = (sum(1 for c in clv_records if c > 0) / clv_n) if clv_n else None

    # Breakdown по типам ставок (по predicted method если есть)
    by_type = {}
    for b in bets:
        # Бет тип: пока используем main_bet или просто "moneyline" по дефолту
        bt = (b.get("bet_type") or
              ("ml" if "moneyline" in (b.get("main_bet", "") or "").lower() else "other"))
        d = by_type.setdefault(bt, {"n": 0, "won": 0, "stake": 0.0, "return": 0.0})
        d["n"] += 1
        if b["status"] == "won":
            d["won"] += 1
            d["return"] += float(b["stake"]) * float(b["odds"])
        d["stake"] += float(b["stake"])

    for bt, d in by_type.items():
        d["roi"] = (d["return"] - d["stake"]) / d["stake"] if d["stake"] > 0 else None
        d["acc"] = d["won"] / d["n"] if d["n"] else None

    return {
        "n_bets": len(bets),
        "won": won, "lost": lost,
        "total_stake": round(total_stake, 2),
        "total_return": round(total_return, 2),
        "profit": round(profit, 2),
        "roi": round(roi * 100, 2) if roi is not None else None,
        "avg_odds": round(avg_odds, 3),
        "clv_n": clv_n,
        "clv_avg": round(clv_avg * 100, 2) if clv_avg is not None else None,
        "clv_positive_rate": round(clv_positive_rate * 100, 1) if clv_positive_rate is not None else None,
        "by_bet_type": by_type,
    }


# ---------------------------------------------------------------------------
# Snapshot helper: фиксируем market odds в момент prediction
# ---------------------------------------------------------------------------

def attach_market_odds_snapshot(record: dict, odds_data: dict | None) -> dict:
    """Прикрепляем коэфы букмекеров к prediction record на момент создания.

    odds_data: результат `find_fight_odds()` или None.
    """
    if not odds_data:
        record["market_odds_snapshot"] = None
        return record

    record["market_odds_snapshot"] = {
        "odds_a": odds_data.get("odds_a"),
        "odds_b": odds_data.get("odds_b"),
        "odds_a_avg": odds_data.get("odds_a_avg"),
        "odds_b_avg": odds_data.get("odds_b_avg"),
        "n_books": odds_data.get("n_books"),
        "bookmakers_summary": {
            k: {"odds_a": v["odds_a"], "odds_b": v["odds_b"]}
            for k, v in (odds_data.get("bookmakers") or {}).items()
        },
        "fetched_at": odds_data.get("fetched_at",
            datetime.now().isoformat(timespec="seconds")),
    }
    return record


def attach_closing_odds(record: dict, closing_odds: dict | None) -> dict:
    """Прикрепляем closing line после боя (когда отмечаем результат)."""
    if not closing_odds:
        return record
    record["closing_odds_snapshot"] = {
        "odds_a": closing_odds.get("odds_a"),
        "odds_b": closing_odds.get("odds_b"),
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
    }
    # CLV для основной ставки (если она была — odds + predicted_winner)
    if record.get("odds") and record.get("predicted_winner"):
        from app import _name_match  # might not be importable, fallback below
        try:
            from app import _name_match
            close_o = (closing_odds.get("odds_a")
                       if _name_match(record["predicted_winner"], record.get("fa", ""))
                       else closing_odds.get("odds_b"))
            if close_o:
                record["clv"] = compute_clv(float(record["odds"]), close_o)
        except Exception:
            pass
    return record
