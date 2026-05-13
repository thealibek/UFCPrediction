"""Auto-extract lessons from blind-test misses.

Workflow:
1. Сканирует все blind_tests/*.json
2. Собирает все промахи (correct=False)
3. Группирует по типу ошибки (overconfident-favorite-lost, underdog-win, и т.п.)
4. Отправляет батч LLM-у с инструкцией извлечь PATTERN (что общего у промахов)
5. LLM выдаёт JSON массив новых уроков
6. Сохраняет как drafts → пользователь approve через UI
"""
from __future__ import annotations

import json, os, re
from pathlib import Path
from typing import Any

from lessons import add_lesson, load_lessons

DRAFTS_FILE = Path("lessons_drafts.json")


def collect_misses(min_confidence: float = 0.55) -> list[dict]:
    """Возвращает список промахов с context-ом."""
    misses = []
    for p in sorted(Path("blind_tests").glob("*.json")):
        if p.name.startswith("_"): continue
        try:
            d = json.loads(p.read_text())
        except Exception: continue
        for rec in d.get("predictions", []):
            if not rec.get("graded"): continue
            if rec.get("correct"): continue
            wp = rec.get("win_prob") or 0
            if wp < min_confidence: continue  # ловим только overconfident
            misses.append({
                "event": d["event"]["name"].split(" [")[0],
                "date": d["event"]["date"][:10],
                "venue": d["event"].get("venue"),
                "fighter_a": rec["fighter_a"],
                "fighter_b": rec["fighter_b"],
                "predicted": rec.get("predicted_winner"),
                "win_prob": wp,
                "method_pred": rec.get("method"),
                "actual_winner": rec.get("actual_winner"),
                "actual_method": rec.get("actual_method"),
                "reasoning_excerpt": (rec.get("reasoning") or "")[:600],
                "source_file": p.name,
            })
    return misses


def suggest_lessons_via_llm(misses: list[dict],
                             max_misses: int = 30) -> list[dict]:
    """Отправляет промахи в LLM, получает JSON-список новых уроков."""
    from openai import OpenAI

    api_key = os.environ["LLM_API_KEY"]
    base_url = os.environ.get("LLM_BASE_URL")
    model = os.environ.get("LLM_MODEL")

    sample = misses[:max_misses]
    if not sample:
        return []

    client = OpenAI(api_key=api_key, base_url=base_url)

    existing = load_lessons()
    existing_titles = "\n".join(f"- {l['title']}" for l in existing)

    user_msg = (
        "Вот список промахов модели UFC-предиктора. Я хочу извлечь повторяющиеся "
        "PATTERN-ы (где модель систематически ошибается).\n\n"
        "ЗАДАЧА: верни JSON-массив из 3-7 НОВЫХ уроков (правил), которые помогут "
        "избежать таких промахов в будущем. НЕ дублируй существующие.\n\n"
        f"=== УЖЕ ЕСТЬ УРОКИ ===\n{existing_titles}\n\n"
        "=== ПРОМАХИ ===\n"
        + json.dumps(sample, ensure_ascii=False, indent=2)
        + "\n\nФОРМАТ ОТВЕТА (только JSON, без объяснений):\n"
        '```json\n'
        '[\n'
        '  {\n'
        '    "title": "Короткое название правила",\n'
        '    "body": "Конкретное правило. Когда срабатывает + что делать. 2-4 предложения.",\n'
        '    "tags": ["category1", "category2"],\n'
        '    "trigger_keywords": ["слово1", "слово2", "phrase"]\n'
        '  }\n'
        ']\n```'
    )

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content":
             "Ты — meta-анализатор предсказательной модели. "
             "Извлекаешь обобщённые правила из конкретных ошибок. "
             "Отвечай ТОЛЬКО валидным JSON в указанном формате."},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.3, max_tokens=3000,
    )
    txt = resp.choices[0].message.content or ""
    # Extract JSON
    m = re.search(r"\[\s*\{.*\}\s*\]", txt, re.DOTALL)
    if not m:
        m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", txt, re.DOTALL)
        if m: txt_json = m.group(1)
        else: return [{"_raw_response": txt}]
    else:
        txt_json = m.group(0)

    try:
        return json.loads(txt_json)
    except Exception as e:
        return [{"_parse_error": str(e), "_raw": txt[:500]}]


def save_drafts(drafts: list[dict]) -> Path:
    """Сохраняет предложенные уроки в lessons_drafts.json (без auto-publish)."""
    DRAFTS_FILE.write_text(json.dumps(drafts, indent=2, ensure_ascii=False))
    return DRAFTS_FILE


def approve_draft(idx: int) -> dict | None:
    """Публикует один draft в активные lessons по индексу."""
    if not DRAFTS_FILE.exists(): return None
    drafts = json.loads(DRAFTS_FILE.read_text())
    if idx < 0 or idx >= len(drafts): return None
    d = drafts[idx]
    if "title" not in d or "body" not in d: return None
    add_lesson(d["title"], d["body"],
               tags=d.get("tags", []),
               trigger_keywords=d.get("trigger_keywords", []),
               source="auto_extracted_v1")
    return d


def remove_draft(idx: int) -> None:
    if not DRAFTS_FILE.exists(): return
    drafts = json.loads(DRAFTS_FILE.read_text())
    if 0 <= idx < len(drafts):
        drafts.pop(idx)
        DRAFTS_FILE.write_text(json.dumps(drafts, indent=2, ensure_ascii=False))


def load_drafts() -> list[dict]:
    if not DRAFTS_FILE.exists(): return []
    return json.loads(DRAFTS_FILE.read_text())
