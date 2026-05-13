"""Blind Test Framework.

Идея: прогоняем модель на ивенте, скрывая от неё результаты. Сохраняем все
прогнозы в `blind_tests/<date>_<slug>.json` ДО факта. Потом грейдим против
реальных исходов из ESPN. Видим, насколько модель умеет читать карды.

Каждый blind test = атомарный иммутабельный файл с timestamp прогноза.
Не путать с `history.json` (там обычные прогнозы из UI).

Структура файла:
{
  "event": {"name", "date", "venue", "espn_id"},
  "model_meta": {"llm_model", "system_prompt_version", "created_at"},
  "predictions": [
      {
        "fighter_a", "fighter_b", "weight_class",
        "predicted_winner", "win_prob", "method", "round",
        "reasoning", "odds_a", "odds_b", "created_at",
        "actual_winner", "actual_method", "actual_round",
        "graded", "correct", "brier"
      }, ...
  ],
  "summary": {"n", "n_graded", "accuracy_%", "brier", "graded_at"}
}
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

BLIND_DIR = Path("blind_tests")
BLIND_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(s: str) -> str:
    s = re.sub(r"[^\w\s-]", "", s.lower())
    return re.sub(r"[\s_-]+", "-", s).strip("-")[:80]


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def file_for(event_name: str, event_date: str) -> Path:
    """Стабильное имя файла blind-test по ивенту."""
    date_part = (event_date or "")[:10]
    return BLIND_DIR / f"{date_part}_{slugify(event_name)}.json"


def list_tests() -> list[Path]:
    # Игнорируем служебные файлы с префиксом _ (e.g. _aggregate_2026.json)
    return sorted(p for p in BLIND_DIR.glob("*.json")
                  if not p.name.startswith("_"))


def load_test(path: Path) -> dict:
    return json.loads(path.read_text())


def save_test(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Blinding (strip results from ESPN data)
# ---------------------------------------------------------------------------

def blind_fights(fights: list[dict]) -> list[dict]:
    """Удаляем все поля, которые могут раскрыть исход боя."""
    blinded = []
    for f in fights:
        bf = json.loads(json.dumps(f))  # deepcopy
        bf["completed"] = False
        bf["method"] = ""
        bf["round"] = 0
        bf["status"] = ""
        for side in ("a", "b"):
            if side in bf and isinstance(bf[side], dict):
                bf[side].pop("winner", None)
        blinded.append(bf)
    return blinded


# ---------------------------------------------------------------------------
# Prediction runner
# ---------------------------------------------------------------------------

def run_blind_test(
    event_name: str,
    event_date: str,
    fights: list[dict],
    predict_fn: Callable[[dict, dict, dict], dict],
    model_meta: dict | None = None,
    venue: str = "",
    espn_id: str | None = None,
    delay_s: float = 1.5,
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> Path:
    """Запускает прогноз по каждому бою, сохраняет файл и возвращает путь.

    Args:
      fights: список ESPN-боёв (уже blinded — без результатов)
      predict_fn: callable(fa, fb, ctx) -> dict с ключами
                  {predicted_winner, win_prob, method, round, reasoning,
                   odds_a, odds_b}
      progress_cb: опциональный (i, total, msg) для UI
    """
    path = file_for(event_name, event_date)
    data = {
        "event": {
            "name": event_name, "date": event_date,
            "venue": venue, "espn_id": espn_id,
        },
        "model_meta": {**(model_meta or {}), "created_at": _now_iso()},
        "predictions": [],
        "summary": {"n": 0, "n_graded": 0, "accuracy_%": None, "brier": None},
    }

    total = len(fights)
    for i, f in enumerate(fights, 1):
        a = f.get("a") or {}
        b = f.get("b") or {}
        fa = {"name": a.get("name"), "record": a.get("record"),
              "country": a.get("country")}
        fb = {"name": b.get("name"), "record": b.get("record"),
              "country": b.get("country")}
        ctx = {
            "event": event_name,
            "weight_class": f.get("weight_class"),
            "division": f.get("weight_class"),
            "rounds": 5 if (i == total or "title" in str(f.get("weight_class","")).lower()) else 3,
        }
        if progress_cb:
            progress_cb(i, total, f"{fa['name']} vs {fb['name']}")
        try:
            pred = predict_fn(fa, fb, ctx)
        except Exception as e:
            pred = {"error": str(e)}
        rec = {
            "fighter_a": fa["name"], "fighter_b": fb["name"],
            "weight_class": ctx["weight_class"],
            "odds_a": f.get("odds_a"), "odds_b": f.get("odds_b"),
            "created_at": _now_iso(),
            "predicted_winner": pred.get("predicted_winner"),
            "win_prob": pred.get("win_prob"),
            "method": pred.get("method"),
            "round": pred.get("round"),
            "reasoning": pred.get("reasoning", "")[:4000],
            "error": pred.get("error"),
            # placeholders for grading
            "actual_winner": None, "actual_method": None, "actual_round": None,
            "graded": False, "correct": None, "brier": None,
        }
        data["predictions"].append(rec)
        save_test(path, data)  # инкрементальный save после каждого боя
        if delay_s and i < total:
            time.sleep(delay_s)

    data["summary"]["n"] = len(data["predictions"])
    save_test(path, data)
    return path


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------

def _name_match(a: str, b: str) -> bool:
    if not a or not b: return False
    a = re.sub(r"\s+", " ", a.lower().strip())
    b = re.sub(r"\s+", " ", b.lower().strip())
    if a == b: return True
    a_last = a.split()[-1] if a else ""
    b_last = b.split()[-1] if b else ""
    return bool(a_last) and a_last == b_last


def _actual_winner(fight: dict) -> str | None:
    for side in ("a", "b"):
        s = fight.get(side) or {}
        if s.get("winner"):
            return s.get("name")
    return None


def grade_test(path: Path, espn_fights: list[dict]) -> dict:
    """Грейдим blind test файл против ESPN-боёв (с результатами).
    Возвращает summary."""
    data = load_test(path)
    graded_n = 0
    correct_n = 0
    brier_sum = 0.0
    brier_n = 0

    for rec in data["predictions"]:
        # ищем match в ESPN-боях по именам
        match = None
        for f in espn_fights:
            an = (f.get("a") or {}).get("name", "")
            bn = (f.get("b") or {}).get("name", "")
            if ((_name_match(an, rec["fighter_a"]) and _name_match(bn, rec["fighter_b"]))
                or (_name_match(an, rec["fighter_b"]) and _name_match(bn, rec["fighter_a"]))):
                match = f
                break
        if not match or not match.get("completed"):
            continue
        winner = _actual_winner(match)
        if not winner:
            continue
        rec["actual_winner"] = winner
        rec["actual_method"] = match.get("method")
        rec["actual_round"] = match.get("round")
        is_correct = _name_match(winner, rec.get("predicted_winner") or "")
        rec["correct"] = bool(is_correct)
        rec["graded"] = True
        graded_n += 1
        if is_correct: correct_n += 1
        p = rec.get("win_prob")
        if p is not None:
            try:
                p = float(p)
                y = 1.0 if is_correct else 0.0
                brier_sum += (p - y) ** 2
                brier_n += 1
            except Exception:
                pass

    data["summary"] = {
        "n": len(data["predictions"]),
        "n_graded": graded_n,
        "correct": correct_n,
        "accuracy_%": (correct_n / graded_n * 100) if graded_n else None,
        "brier": (brier_sum / brier_n) if brier_n else None,
        "graded_at": _now_iso(),
    }
    save_test(path, data)
    return data["summary"]
