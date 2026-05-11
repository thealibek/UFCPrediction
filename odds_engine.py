"""Odds-aware bet recommendation engine.

Принимает:
  - наши вероятности (win_prob, ko_prob, sub_prob, dec_prob)
  - рыночные коэффициенты (decimal): moneyline, method props, total rounds

Выдаёт:
  - implied probabilities из рынка (с de-vig)
  - Expected Value (EV) для каждой возможной ставки
  - Kelly fraction (рекомендованный размер банка)
  - structured recommendations: какие ставки имеют +EV, какие skip

Главная идея: высокая уверенность ≠ хорошая ставка. Если модель даёт 62%,
а рынок 1.2 (implied 83%) — moneyline это −EV. Но есть value в methods,
total rounds, или контр-ставке.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Probability ↔ Odds conversions
# ---------------------------------------------------------------------------

def implied_prob(decimal_odds: float) -> float:
    """Decimal odds → raw implied probability (с букмекерским vig'ом)."""
    if not decimal_odds or decimal_odds <= 1.0:
        return 0.0
    return 1.0 / decimal_odds


def remove_vig_two_way(odds_a: float, odds_b: float) -> tuple[float, float]:
    """Убираем vig из двусторонней линии (moneyline). Возвращаем чистые
    вероятности, которые в сумме дают 1.0."""
    pa = implied_prob(odds_a)
    pb = implied_prob(odds_b)
    total = pa + pb
    if total <= 0:
        return 0.5, 0.5
    return pa / total, pb / total


def remove_vig_three_way(odds_ko: float, odds_sub: float, odds_dec: float
                          ) -> tuple[float, float, float]:
    """De-vig для метода (KO/Sub/Dec)."""
    pk = implied_prob(odds_ko)
    ps = implied_prob(odds_sub)
    pd = implied_prob(odds_dec)
    total = pk + ps + pd
    if total <= 0:
        return 0.33, 0.33, 0.34
    return pk / total, ps / total, pd / total


def expected_value(our_prob: float, decimal_odds: float, stake: float = 100.0
                   ) -> float:
    """EV ставки: our_prob × (odds−1) × stake − (1−our_prob) × stake."""
    if decimal_odds <= 1.0:
        return 0.0
    return our_prob * (decimal_odds - 1.0) * stake - (1.0 - our_prob) * stake


def ev_percent(our_prob: float, decimal_odds: float) -> float:
    """EV как % от ставки (= edge per $100)."""
    return expected_value(our_prob, decimal_odds, 100.0)


def kelly_fraction(our_prob: float, decimal_odds: float,
                    fraction: float = 0.25) -> float:
    """Kelly criterion для размера ставки. fraction=0.25 = квартер-Kelly
    (более консервативно, рекомендуется для prediction models)."""
    if decimal_odds <= 1.0 or our_prob <= 0:
        return 0.0
    b = decimal_odds - 1.0
    q = 1.0 - our_prob
    kelly = (b * our_prob - q) / b
    return max(0.0, min(0.25, kelly * fraction))  # cap 25%


# ---------------------------------------------------------------------------
# Bet evaluation: одна ставка
# ---------------------------------------------------------------------------

def evaluate_bet(our_prob: float, market_odds: float,
                  bet_label: str = "") -> dict:
    """Полная оценка ставки. Возвращает рекомендацию + EV + Kelly."""
    if not market_odds or market_odds <= 1.0:
        return {
            "label": bet_label, "verdict": "no_odds",
            "our_prob": our_prob, "market_odds": market_odds,
            "implied": None, "edge": None, "ev_per_100": None,
            "kelly": 0.0, "recommendation": "Введи коэффициент.",
        }

    impl = implied_prob(market_odds)
    edge = our_prob - impl  # положительный = value у нас
    ev100 = ev_percent(our_prob, market_odds)
    kelly = kelly_fraction(our_prob, market_odds, fraction=0.25)

    if edge >= 0.05:
        verdict = "strong_value"
        rec = f"💰 STRONG VALUE — bet {kelly*100:.1f}% bankroll (¼-Kelly)"
    elif edge >= 0.02:
        verdict = "lean_value"
        rec = f"✅ Lean value — small bet {kelly*100:.1f}% bankroll"
    elif edge >= -0.02:
        verdict = "fair"
        rec = "🟡 Fair priced — coin flip, skip unless live edge"
    elif edge >= -0.05:
        verdict = "lean_against"
        rec = "🟠 Lean against — рынок чуть переоценивает"
    else:
        verdict = "strong_against"
        rec = (f"❌ STRONG NEGATIVE EV — рынок переоценивает на "
               f"{abs(edge)*100:.1f}%. Ищи value в method / total / другом исходе.")

    return {
        "label": bet_label, "verdict": verdict,
        "our_prob": round(our_prob, 4),
        "market_odds": round(market_odds, 3),
        "implied": round(impl, 4),
        "edge": round(edge, 4),
        "ev_per_100": round(ev100, 2),
        "kelly": round(kelly, 4),
        "recommendation": rec,
    }


# ---------------------------------------------------------------------------
# Полный анализ боя: moneyline + methods + totals
# ---------------------------------------------------------------------------

def analyze_fight_odds(our_probs: dict, market_odds: dict) -> dict:
    """Главный анализатор. Принимает наши probs и market odds, выдаёт
    structured рекомендации.

    our_probs = {
        'win_prob_a': 0.62, 'win_prob_b': 0.38,
        'ko_prob_winner': 0.45, 'sub_prob_winner': 0.20,
        'dec_prob_winner': 0.35,
        'fa_name': 'Khamzat', 'fb_name': 'Strickland',
    }
    market_odds = {
        'ml_a': 1.20, 'ml_b': 4.50,         # moneyline
        'ko_winner': 2.80, 'sub_winner': 5.50, 'dec_winner': 2.20,
        'over_2_5': 1.85, 'under_2_5': 1.95,  # totals
    }

    Returns: {
        'bets': [list of evaluated bets sorted by EV desc],
        'top_pick': бой #1 пик,
        'avoid': список ставок с −EV,
        'summary': короткий вердикт,
    }
    """
    fa = our_probs.get("fa_name", "A")
    fb = our_probs.get("fb_name", "B")
    win_a = our_probs.get("win_prob_a", 0.5)
    win_b = our_probs.get("win_prob_b", 1.0 - win_a)

    # Method probs у нас по победителю — расщепим на фаворита/андердога
    ko_w = our_probs.get("ko_prob_winner", 0.0) or 0.0
    sub_w = our_probs.get("sub_prob_winner", 0.0) or 0.0
    dec_w = our_probs.get("dec_prob_winner", 0.0) or 0.0

    # Кто наш предсказанный winner?
    winner_is_a = win_a >= 0.5
    winner_name = fa if winner_is_a else fb
    winner_prob = max(win_a, win_b)

    bets = []

    # --- Moneyline ---
    if market_odds.get("ml_a"):
        bets.append(evaluate_bet(win_a, market_odds["ml_a"], f"ML — {fa}"))
    if market_odds.get("ml_b"):
        bets.append(evaluate_bet(win_b, market_odds["ml_b"], f"ML — {fb}"))

    # --- Method (для нашего winner'а) ---
    # P(Winner by KO) = P(Winner) × P(KO | Winner)
    if market_odds.get("ko_winner"):
        bets.append(evaluate_bet(
            winner_prob * ko_w, market_odds["ko_winner"],
            f"{winner_name} by KO/TKO",
        ))
    if market_odds.get("sub_winner"):
        bets.append(evaluate_bet(
            winner_prob * sub_w, market_odds["sub_winner"],
            f"{winner_name} by Submission",
        ))
    if market_odds.get("dec_winner"):
        bets.append(evaluate_bet(
            winner_prob * dec_w, market_odds["dec_winner"],
            f"{winner_name} by Decision",
        ))

    # --- Totals (over/under round bands) ---
    # Если KO/Sub раннние = under, Decision = over (приближение)
    # Точнее можно через round-distribution prediction, но для MVP так:
    early_finish_prob = (winner_prob * (ko_w + sub_w) * 0.6
                          + (1 - winner_prob) * 0.3)  # rough estimate
    distance_prob = 1.0 - early_finish_prob
    if market_odds.get("over_2_5"):
        bets.append(evaluate_bet(
            distance_prob, market_odds["over_2_5"], "Over 2.5 rounds",
        ))
    if market_odds.get("under_2_5"):
        bets.append(evaluate_bet(
            early_finish_prob, market_odds["under_2_5"], "Under 2.5 rounds",
        ))

    # Сортируем по edge desc
    bets.sort(key=lambda b: b.get("edge") or -1, reverse=True)

    value_bets = [b for b in bets if b["verdict"] in ("strong_value", "lean_value")]
    avoid = [b for b in bets if b["verdict"] == "strong_against"]

    # Summary
    if value_bets:
        top = value_bets[0]
        summary = (
            f"🎯 **Top pick:** {top['label']} @ {top['market_odds']} · "
            f"edge {top['edge']*100:+.1f}% · EV ${top['ev_per_100']:+.1f}/100"
        )
    elif bets:
        summary = (
            "🟡 **No clear value found.** Рынок более-менее правильно оценил бой. "
            "Skip moneyline, look for live edges или другой бой."
        )
    else:
        summary = "Введи рыночные коэффициенты для анализа value."

    return {
        "bets": bets,
        "value_bets": value_bets,
        "avoid": avoid,
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# Heavy-favorite warning
# ---------------------------------------------------------------------------

def heavy_favorite_warning(market_odds_favorite: float,
                            our_prob_favorite: float) -> dict | None:
    """Особое предупреждение если рынок видит heavy favorite (odds < 1.3)."""
    if market_odds_favorite >= 1.30:
        return None
    impl = implied_prob(market_odds_favorite)
    edge = our_prob_favorite - impl
    return {
        "trigger": True,
        "market_odds": market_odds_favorite,
        "implied": round(impl, 3),
        "our_prob": round(our_prob_favorite, 3),
        "edge": round(edge, 3),
        "message": (
            f"⚠️ **HEAVY FAVORITE WARNING** — рынок ставит {market_odds_favorite:.2f} "
            f"(implied {impl*100:.0f}%). Наша prob {our_prob_favorite*100:.0f}%. "
            + (f"Edge {edge*100:+.1f}% — moneyline даёт мало value. "
               "Лучше: method props (KO/Sub/Dec) или round totals — там часто "
               "есть value на heavy favorite карточках."
               if edge > -0.1 else
               f"Мы ниже рынка на {abs(edge)*100:.1f}% → значит модель видит value "
               "**на underdog'e** (или альтернативном проп'е). Не ставь "
               "moneyline на фаворита.")
        ),
    }
