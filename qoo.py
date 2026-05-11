"""Quality of Opposition (QoO) module.

Считает ELO-рейтинг бойцов на основании их прошлых боёв (из data_seed
recent_fights и rag_seed HISTORICAL_FIGHTS) и выдаёт метрики качества
оппозиции для использования в ML-фичах и LLM-промпте.

Ключевая идея: чем сильнее были побеждённые соперники, тем выше уровень бойца.
И наоборот — рекорд 18-0 против региональных бойцов слабый сигнал.

Не требует внешних зависимостей. Кеш в `qoo_cache.json` (опционально).
"""
from __future__ import annotations

import json
import math
import os
from datetime import datetime
from typing import Iterable

CACHE_FILE = "qoo_cache.json"
SEED_ELO = 1500.0
K_FACTOR = 32.0
DECAY_LAMBDA = 0.04  # per month — recency weight = exp(-λ·months_ago)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(s: str) -> datetime:
    """Parse 'YYYY-MM' / 'YYYY-MM-DD' → datetime. Default = epoch start."""
    if not s:
        return datetime(2000, 1, 1)
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return datetime(2000, 1, 1)


def _months_between(a: datetime, b: datetime) -> float:
    return (b - a).days / 30.4375


def _normalize_elo(elo: float) -> float:
    """Map ELO 1300..1900 → [0, 1]. Below 1300 → 0, above 1900 → 1."""
    return max(0.0, min(1.0, (elo - 1300.0) / 600.0))


# ---------------------------------------------------------------------------
# ELO computation across all known fights
# ---------------------------------------------------------------------------

def _gather_events(fighters_db: list[dict],
                    historical_fights: list[dict] | None = None,
                    resolved_history: list[dict] | None = None) -> list[dict]:
    """Собираем все события (бои) из доступных источников в единый список.
    Каждое событие: {date, a, b, winner, method}.
    Дедуп по (sorted names, date_yyyy_mm).
    """
    events: list[dict] = []

    for f in fighters_db or []:
        name = f.get("name")
        if not name:
            continue
        for rf in f.get("recent_fights", []) or []:
            opp = rf.get("opponent")
            if not opp:
                continue
            events.append({
                "date": rf.get("date", "2020-01"),
                "a": name, "b": opp,
                "winner": name if rf.get("result") == "W" else opp,
                "method": rf.get("method", ""),
            })

    for hf in historical_fights or []:
        a = hf.get("fighter_a"); b = hf.get("fighter_b")
        if not a or not b:
            continue
        events.append({
            "date": hf.get("date", "2020-01"),
            "a": a, "b": b,
            "winner": hf.get("winner", a),
            "method": hf.get("method", ""),
        })

    # Resolved history (наши собственные предсказания с реальным исходом)
    for h in resolved_history or []:
        if h.get("status") not in ("won", "lost"):
            continue
        a, b = h.get("fa"), h.get("fb")
        actual = h.get("actual_winner")
        if not (a and b and actual):
            continue
        events.append({
            "date": (h.get("ts") or "2020-01")[:10],
            "a": a, "b": b,
            "winner": actual,
            "method": h.get("actual_method", ""),
        })

    # Dedup: одно и то же событие могло попасть из нескольких источников
    seen = set()
    unique = []
    for e in events:
        key = (tuple(sorted([e["a"].lower(), e["b"].lower()])),
               (e["date"] or "")[:7])
        if key in seen:
            continue
        seen.add(key)
        unique.append(e)
    unique.sort(key=lambda x: _parse_date(x["date"]))
    return unique


def compute_elos(fighters_db: list[dict],
                  historical_fights: list[dict] | None = None,
                  resolved_history: list[dict] | None = None
                  ) -> tuple[dict[str, float], dict[str, list]]:
    """Прогоняет ELO по всем известным боям в хронологическом порядке.

    Returns:
        elos: {fighter_name: current_elo}
        per_fighter_history: {fighter_name: [{date, opponent, opp_elo_then,
                                              result: 'W'|'L', method}]}
    """
    events = _gather_events(fighters_db, historical_fights, resolved_history)
    elos: dict[str, float] = {}
    history: dict[str, list] = {}

    for e in events:
        a, b = e["a"], e["b"]
        elos.setdefault(a, SEED_ELO)
        elos.setdefault(b, SEED_ELO)

        ea = 1.0 / (1.0 + 10 ** ((elos[b] - elos[a]) / 400.0))
        a_won = (e["winner"] or "").lower() == a.lower()
        sa = 1.0 if a_won else 0.0

        # snapshot ELO opponent на момент боя — сохраняем ДО апдейта
        history.setdefault(a, []).append({
            "date": e["date"], "opponent": b,
            "opp_elo_then": round(elos[b], 1),
            "result": "W" if a_won else "L",
            "method": e["method"],
        })
        history.setdefault(b, []).append({
            "date": e["date"], "opponent": a,
            "opp_elo_then": round(elos[a], 1),
            "result": "L" if a_won else "W",
            "method": e["method"],
        })

        elos[a] += K_FACTOR * (sa - ea)
        elos[b] += K_FACTOR * ((1.0 - sa) - (1.0 - ea))

    return elos, history


# ---------------------------------------------------------------------------
# Per-fighter QoO metrics
# ---------------------------------------------------------------------------

def build_qoo(fighter_name: str,
              elos: dict[str, float],
              per_fighter_history: dict[str, list],
              as_of: datetime | None = None) -> dict:
    """Считаем метрики качества оппозиции для одного бойца.

    Returns dict со следующими ключами:
        elo, opp_quality_score, recent_opp_strength,
        ufc_fights_count, rookie_penalty,
        top15_wins, loss_quality_score,
        opponents (список),
        tier_distribution
    """
    opps = per_fighter_history.get(fighter_name, []) or []
    now = as_of or datetime.now()

    if not opps:
        return {
            "fighter": fighter_name,
            "elo": SEED_ELO,
            "opp_quality_score": 0.5,
            "recent_opp_strength": 0.5,
            "ufc_fights_count": 0,
            "rookie_penalty": 1.0,
            "top15_wins": 0,
            "loss_quality_score": 0.5,
            "opponents": [],
            "tier_distribution": {"top5": 0, "top15": 0, "ranked": 0, "unranked": 0},
        }

    # Weighted avg opp ELO с recency decay
    weights, weighted_elos = [], []
    for o in opps:
        d = _parse_date(o.get("date", ""))
        months_ago = max(0.0, _months_between(d, now))
        w = math.exp(-DECAY_LAMBDA * months_ago)
        weights.append(w)
        weighted_elos.append(o["opp_elo_then"] * w)
    avg_opp_elo = sum(weighted_elos) / sum(weights) if sum(weights) > 0 else SEED_ELO
    opp_quality_score = _normalize_elo(avg_opp_elo)

    # Recent: последние 3 боя, более жёсткий decay
    recent_3 = opps[-3:]
    if recent_3:
        rweights, relos = [], []
        for o in recent_3:
            d = _parse_date(o.get("date", ""))
            months_ago = max(0.0, _months_between(d, now))
            w = math.exp(-DECAY_LAMBDA * 2.0 * months_ago)
            rweights.append(w)
            relos.append(o["opp_elo_then"] * w)
        recent_opp_strength = _normalize_elo(
            sum(relos) / sum(rweights) if sum(rweights) > 0 else SEED_ELO
        )
    else:
        recent_opp_strength = 0.5

    # Tiers
    tier = {"top5": 0, "top15": 0, "ranked": 0, "unranked": 0}
    top15_wins = 0
    losses_quality = []
    for o in opps:
        e_then = o.get("opp_elo_then", SEED_ELO)
        if e_then >= 1750:
            tier["top5"] += 1
            if o["result"] == "W":
                top15_wins += 1
        elif e_then >= 1650:
            tier["top15"] += 1
            if o["result"] == "W":
                top15_wins += 1
        elif e_then >= 1550:
            tier["ranked"] += 1
        else:
            tier["unranked"] += 1
        if o["result"] == "L":
            losses_quality.append(e_then)

    loss_quality_score = (_normalize_elo(sum(losses_quality) / len(losses_quality))
                          if losses_quality else 0.5)

    # Rookie penalty: <3 UFC fights → 1.0, >=8 → 0
    n = len(opps)
    if n >= 8:
        rookie_penalty = 0.0
    elif n < 3:
        rookie_penalty = 1.0
    else:
        rookie_penalty = (8 - n) / 5.0  # 3→1.0, 8→0

    return {
        "fighter": fighter_name,
        "elo": round(elos.get(fighter_name, SEED_ELO), 1),
        "opp_quality_score": round(opp_quality_score, 3),
        "recent_opp_strength": round(recent_opp_strength, 3),
        "ufc_fights_count": n,
        "rookie_penalty": round(rookie_penalty, 3),
        "top15_wins": top15_wins,
        "loss_quality_score": round(loss_quality_score, 3),
        "opponents": opps[-10:],  # последние 10 для контекста
        "tier_distribution": tier,
    }


# ---------------------------------------------------------------------------
# Convenience: build QoO для пары бойцов одним вызовом
# ---------------------------------------------------------------------------

def build_qoo_pair(fa_name: str, fb_name: str,
                    fighters_db: list[dict],
                    historical_fights: list[dict] | None = None,
                    resolved_history: list[dict] | None = None,
                    as_of: datetime | None = None) -> tuple[dict, dict]:
    elos, history = compute_elos(fighters_db, historical_fights, resolved_history)
    qoo_a = build_qoo(fa_name, elos, history, as_of=as_of)
    qoo_b = build_qoo(fb_name, elos, history, as_of=as_of)
    return qoo_a, qoo_b


# ---------------------------------------------------------------------------
# Cache (optional)
# ---------------------------------------------------------------------------

def save_cache(cache_data: dict, path: str = CACHE_FILE) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2, default=str)
    except Exception:
        pass


def load_cache(path: str = CACHE_FILE) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Prompt formatting — для инжекта в LLM
# ---------------------------------------------------------------------------

def format_qoo_for_prompt(qoo_a: dict, qoo_b: dict) -> str:
    """Возвращает форматированный блок === QOO === для вставки в LLM-промпт."""
    def _fmt_one(q: dict) -> str:
        name = q.get("fighter", "?")
        td = q.get("tier_distribution", {})
        opps = q.get("opponents", [])
        opps_str = "\n".join(
            f"      - {o['date']} · {o['result']} vs {o['opponent']} "
            f"(opp ELO ~{int(o['opp_elo_then'])}) · {o.get('method','')}"
            for o in opps[-6:]
        ) or "      (no recorded UFC opponents)"
        return (
            f"  ▸ {name}\n"
            f"      ELO ~{int(q['elo'])} · "
            f"opp_quality_score={q['opp_quality_score']:.2f} · "
            f"recent_opp_strength={q['recent_opp_strength']:.2f}\n"
            f"      UFC fights: {q['ufc_fights_count']} · "
            f"rookie_penalty={q['rookie_penalty']:.2f} · "
            f"top15_wins={q['top15_wins']}\n"
            f"      Tiers: top5={td.get('top5',0)}, top15={td.get('top15',0)}, "
            f"ranked={td.get('ranked',0)}, unranked={td.get('unranked',0)}\n"
            f"      Loss quality: {q['loss_quality_score']:.2f} "
            f"(higher = lost only to top opponents)\n"
            f"      Recent opponents:\n{opps_str}"
        )

    return (
        "=== QOO (Quality of Opposition) ===\n"
        "Используй эти данные для оценки УРОВНЯ соперников каждого бойца.\n"
        "Высокий opp_quality_score (>0.7) = бил топов. Низкий (<0.4) = слабая оппозиция.\n"
        "rookie_penalty > 0.5 = малая UFC-выборка, снижай уверенность на 5-8%.\n\n"
        f"{_fmt_one(qoo_a)}\n\n"
        f"{_fmt_one(qoo_b)}\n"
        "=== END QOO ===\n"
    )


# ---------------------------------------------------------------------------
# Rookie dampening — применяется к final_prob после combine_hybrid
# ---------------------------------------------------------------------------

def apply_rookie_dampening(final_prob_a: float | None,
                            qoo_a: dict, qoo_b: dict) -> tuple[float | None, dict]:
    """Если хотя бы один из бойцов rookie — стягиваем prob к 0.5."""
    if final_prob_a is None:
        return None, {"applied": False, "reason": "no_prob"}
    rp_a = qoo_a.get("rookie_penalty", 0.0)
    rp_b = qoo_b.get("rookie_penalty", 0.0)
    rookie_factor = max(rp_a, rp_b)
    if rookie_factor <= 0.5:
        return final_prob_a, {"applied": False, "rookie_factor": rookie_factor}

    # Стягиваем к 0.5 на 30% от расстояния, скейлим по rookie_factor
    pull = 0.3 * rookie_factor
    new_prob = 0.5 + (final_prob_a - 0.5) * (1 - pull)
    new_prob = max(0.05, min(0.95, new_prob))
    return new_prob, {
        "applied": True,
        "rookie_factor": round(rookie_factor, 3),
        "pull": round(pull, 3),
        "before": round(final_prob_a, 4),
        "after": round(new_prob, 4),
    }
