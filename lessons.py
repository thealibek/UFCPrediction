"""Lessons Memory — персистентная память ошибок модели.

После каждого blind-test или промаха пользователь (или автомат) записывает
урок в `lessons.json`. Перед следующим прогнозом релевантные lessons
автоматически инжектятся в промпт.

Каждый lesson имеет тэги (chin / age / opposition / home_bias / proton / ...)
и срабатывает если фактор присутствует в контексте боя.

Структура:
{
  "id": "...", "title": "...", "body": "...",
  "tags": ["chin","age_decline"],
  "trigger_keywords": ["35+","chin","KO loss"],
  "created_at": "...", "source": "blind_test:<file>:<fight_idx>",
  "active": true
}
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

LESSONS_FILE = Path("lessons.json")

DEFAULT_LESSONS = [
    {
        "id": "lsn_anthro_vs_record",
        "title": "Антропометрия + KO power > раздутый рекорд против слабой оппозиции",
        "body": (
            "Если у бойца A reach/height/power значительно выше, а у B рекорд "
            "набит против низко-ранкованной оппозиции — A фаворит вопреки "
            "рекорду B. Признаки 'раздутого рекорда': все победы по решению, "
            "или нокаут-победы только над неранкованными. Проверяй quality of "
            "opposition (QoO ELO ниже 1500 у всей оппозиции = красный флаг). "
            "Пример: Prates (нокаутер, всех финишировал, проиграл одно решение "
            "Гарри который его потряс) vs JDM (рекорд против слабой оппозиции, "
            "проиграл Брэди как только встретил топ-бойца)."
        ),
        "tags": ["anthropometry", "opposition_quality", "ko_power"],
        "trigger_keywords": ["reach", "ko/tko", "нокаутер", "decision",
                             "opposition", "weak opposition", "raised record"],
        "active": True,
    },
    {
        "id": "lsn_chin_age_decline",
        "title": "Старый ветеран (35+) с хрустальной челюстью vs молодой нокаутёр-проспект",
        "body": (
            "Если фаворит 33+, имеет ≥2 KO/TKO поражений в карьере или ≥1 KO "
            "поражение за последние 3 боя — его 'chin' деградирует. Молодой "
            "(<29) нокаутёр-проспект на восхождении против такого ветерана = "
            "сильная ставка на underdog с финишем. НЕ ставь heavy favorite "
            "на ветерана только по имени. Пример: Beneil Dariush (старый, "
            "недавние KO losses) vs Salkilld (молодой нокаутёр) — апсет был "
            "предсказуем."
        ),
        "tags": ["chin", "age_decline", "prospect_vs_veteran"],
        "trigger_keywords": ["35+", "33+", "veteran", "chin", "ko loss",
                             "хрустальная", "prospect", "проспект", "молодой"],
        "active": True,
    },
    {
        "id": "lsn_home_decision_bias",
        "title": "Home-country judge bias: бои в Австралии/UK/Бразилии",
        "body": (
            "Если бой проходит в Австралии (Perth/Sydney) → австралийцы "
            "получают примерно +5-10% к шансу на decision в близких боях. "
            "Те же правила: UK для англичан, Бразилия для бразильцев. Это "
            "НЕ повод флипать прогноз, но если ты колеблешься между Decision "
            "split и финиш — наклоняй к decision в пользу домашнего бойца. "
            "Не работает если финиш очевиден."
        ),
        "tags": ["home_bias", "judge_bias", "decision"],
        "trigger_keywords": ["perth", "sydney", "australia", "london", "rio",
                             "brazil", "австрал", "home", "venue"],
        "active": True,
    },
    {
        "id": "lsn_finisher_vs_inactive",
        "title": "Pure finisher (high finish rate) vs decision-fighter",
        "body": (
            "Если у одного бойца finish rate >70%, а у другого только "
            "decisions — finisher выигрывает 'fight IQ' матчей: один good "
            "punch меняет всё. Не ставь decision-prop в такой матчап. "
            "Если favourite-decision fighter не доминирует stylistically, "
            "underdog-finisher имеет реальный path to victory через KO."
        ),
        "tags": ["finish_rate", "ko_power"],
        "trigger_keywords": ["finish rate", "нокаутер", "decision fighter",
                             "ko рейт", "финиш"],
        "active": True,
    },
    {
        "id": "lsn_unknown_fighter_fallback",
        "title": "Неизвестный дебютант: не угадывай 50/50",
        "body": (
            "Если у бойца меньше 2 боёв в UFC и нет публичных данных о его "
            "стиле — НЕ давай уверенность выше 55%. В таких случаях явно "
            "пиши 'недостаточно данных' и ставь win_prob 0.50-0.55. "
            "Brier штрафует overconfidence жёстче чем underconfidence."
        ),
        "tags": ["debutant", "low_data", "calibration"],
        "trigger_keywords": ["debut", "дебют", "rookie", "0-0", "1-0", "newcomer"],
        "active": True,
    },
]


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load_lessons() -> list[dict]:
    if not LESSONS_FILE.exists():
        save_lessons(DEFAULT_LESSONS)
        return list(DEFAULT_LESSONS)
    try:
        return json.loads(LESSONS_FILE.read_text())
    except Exception:
        return list(DEFAULT_LESSONS)


def save_lessons(lessons: list[dict]) -> None:
    LESSONS_FILE.write_text(json.dumps(lessons, indent=2, ensure_ascii=False))


def add_lesson(title: str, body: str,
               tags: list[str] | None = None,
               trigger_keywords: list[str] | None = None,
               source: str = "manual") -> dict:
    lessons = load_lessons()
    rec = {
        "id": f"lsn_{uuid.uuid4().hex[:8]}",
        "title": title.strip(),
        "body": body.strip(),
        "tags": tags or [],
        "trigger_keywords": [k.lower() for k in (trigger_keywords or [])],
        "created_at": _now(),
        "source": source,
        "active": True,
    }
    lessons.append(rec)
    save_lessons(lessons)
    return rec


def remove_lesson(lesson_id: str) -> bool:
    lessons = load_lessons()
    new = [l for l in lessons if l["id"] != lesson_id]
    if len(new) != len(lessons):
        save_lessons(new); return True
    return False


def toggle_lesson(lesson_id: str) -> bool:
    lessons = load_lessons()
    for l in lessons:
        if l["id"] == lesson_id:
            l["active"] = not l.get("active", True)
            save_lessons(lessons); return l["active"]
    return False


# ---------------------------------------------------------------------------
# Relevance matching
# ---------------------------------------------------------------------------

def relevant_lessons(context: str, max_n: int = 5) -> list[dict]:
    """Возвращает lessons чьи trigger_keywords нашлись в context.
    Если ни один не сработал — возвращает топ-2 универсальных (chin/QoO).
    """
    ctx = (context or "").lower()
    matched = []
    for l in load_lessons():
        if not l.get("active", True):
            continue
        triggers = [k.lower() for k in l.get("trigger_keywords", [])]
        if not triggers:
            continue
        if any(t in ctx for t in triggers):
            matched.append(l)
    if not matched:
        # always-on baseline lessons
        matched = [l for l in load_lessons()
                   if l.get("active", True)
                   and l["id"] in ("lsn_chin_age_decline",
                                   "lsn_anthro_vs_record",
                                   "lsn_unknown_fighter_fallback")][:2]
    return matched[:max_n]


def format_lessons_block(lessons: list[dict]) -> str:
    """Формат для инжекта в LLM prompt."""
    if not lessons:
        return ""
    lines = ["=== УРОКИ ИЗ ПРОШЛЫХ ОШИБОК (учитывай!) ==="]
    for i, l in enumerate(lessons, 1):
        lines.append(f"\n[{i}] {l['title']}\n{l['body']}")
    lines.append("=== END УРОКИ ===")
    return "\n".join(lines)


def build_context_string(fa: dict, fb: dict, ctx: dict, intel: str = "") -> str:
    """Формирует строку контекста для матчинга lesson triggers."""
    parts = [
        fa.get("name", ""), fb.get("name", ""),
        fa.get("style", ""), fb.get("style", ""),
        str(fa.get("age", "")), str(fb.get("age", "")),
        fa.get("record", ""), fb.get("record", ""),
        str(ctx.get("venue", "")), str(ctx.get("event", "")),
        intel,
    ]
    return " ".join(str(p) for p in parts)
