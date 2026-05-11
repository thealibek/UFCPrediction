"""External Intel ingestion module.

Принимает свободный текст (intel notes, новости, RSS-сводки) и
извлекает структурированный JSON по бойцам:
  - weight_cut, injury, travel, camp_drama, motivation
с severity 0.0–1.0 + sources.

Используется для:
  1. ML features (intel_severity_diff, ...)
  2. Инжект в LLM prompt блока === INTEL ===
  3. Post-LLM детерминированный override через apply_intel_modifier()
"""
from __future__ import annotations

import json
import re
from datetime import datetime


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

def empty_intel(fighter_name: str = "") -> dict:
    """Возвращает пустую (нейтральную) intel-структуру."""
    return {
        "fighter": fighter_name,
        "weight_cut": {
            "severity": 0.0,
            "missed_weight": False,
            "double_cut": False,
            "notes": "",
        },
        "injury": {
            "severity": 0.0,
            "body_part": "",
            "training_camp_impact_weeks": 0.0,
            "notes": "",
        },
        "travel": {
            "timezone_diff_hours": 0,
            "arrival_days_before": 14,
            "altitude_change_m": 0,
        },
        "camp_drama": {
            "coach_change": False,
            "team_split": False,
            "contract_dispute": False,
            "personal_issues_flag": False,
            "severity": 0.0,
            "notes": "",
        },
        "motivation": {
            "title_shot_implication": False,
            "comeback_after_ko": False,
            "months_inactive": 0,
            "fight_for_legacy": False,
            "notes": "",
        },
        "_meta": {
            "sources": [],
            "extracted_at": "",
            "confidence": 0.0,
            "raw_input": "",
        },
    }


# ---------------------------------------------------------------------------
# LLM-based extractor
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT = """Ты — экстрактор структурированной информации о бойцах UFC.
Из свободного текста (новости, intel notes, твиты) извлеки структурированный JSON по КАЖДОМУ упомянутому бойцу.

Твой ответ — ТОЛЬКО валидный JSON (без markdown-обёртки, без комментариев), формат:
{
  "fighters": [
    {
      "fighter": "Полное имя бойца",
      "weight_cut": {
        "severity": <0.0-1.0>,
        "missed_weight": <bool>,
        "double_cut": <bool>,
        "notes": "<краткая выдержка из текста>"
      },
      "injury": {
        "severity": <0.0-1.0>,
        "body_part": "<knee|hand|back|shoulder|elbow|...|''>",
        "training_camp_impact_weeks": <int>,
        "notes": "..."
      },
      "travel": {
        "timezone_diff_hours": <int>,
        "arrival_days_before": <int>,
        "altitude_change_m": <int>
      },
      "camp_drama": {
        "coach_change": <bool>,
        "team_split": <bool>,
        "contract_dispute": <bool>,
        "personal_issues_flag": <bool>,
        "severity": <0.0-1.0>,
        "notes": "..."
      },
      "motivation": {
        "title_shot_implication": <bool>,
        "comeback_after_ko": <bool>,
        "months_inactive": <int>,
        "fight_for_legacy": <bool>,
        "notes": "..."
      }
    }
  ],
  "sources": [
    {"url": "...", "title": "...", "date": "..."}
  ],
  "confidence": <0.0-1.0>
}

ПРАВИЛА severity (0.0=нет проблем, 1.0=катастрофа):
- weight_cut.severity = 0.0 если без упоминаний; 0.3 если "тяжёлая" / "сложная"; 0.6 если "double cut" / "поднимался в дивизион"; 0.9 если "missed weight"
- injury.severity = 0.0 если нет; 0.4 если "training was hampered"; 0.7 если "missed sparring"; 0.9 если "fighting through injury"
- camp_drama.severity = аналогично

Если о бойце ничего не сказано — НЕ ВКЛЮЧАЙ его в "fighters". Если нет источников — sources=[]. Если нет данных вообще — fighters=[].
"""


def extract_intel_from_text(notes_text: str,
                              api_key: str,
                              base_url: str,
                              model: str,
                              fighter_a_name: str = "",
                              fighter_b_name: str = "") -> dict:
    """Парсит свободный текст в структурированный intel через LLM.

    Returns:
        {
          "fighter_a": {...intel_schema...} | None,
          "fighter_b": {...intel_schema...} | None,
          "raw_response": str,
          "sources": list,
          "confidence": float,
          "error": str | None,
        }
    """
    if not notes_text or not notes_text.strip():
        return {
            "fighter_a": None, "fighter_b": None,
            "raw_response": "", "sources": [],
            "confidence": 0.0, "error": "empty_input",
        }
    if not api_key:
        return {
            "fighter_a": None, "fighter_b": None,
            "raw_response": "", "sources": [],
            "confidence": 0.0, "error": "no_api_key",
        }

    user_msg = (
        f"Бойцы в этом бою: A='{fighter_a_name}', B='{fighter_b_name}'.\n\n"
        f"Текст для анализа:\n```\n{notes_text}\n```\n\n"
        f"Извлеки JSON по правилам выше. Только JSON, без markdown."
    )

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": EXTRACTION_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
            max_tokens=2000,
        )
        raw = resp.choices[0].message.content or ""
    except Exception as e:
        return {
            "fighter_a": None, "fighter_b": None,
            "raw_response": "", "sources": [],
            "confidence": 0.0, "error": f"llm_error: {e}",
        }

    # Парсим JSON (с tolerance к ```json wrappers)
    parsed = _safe_json_parse(raw)
    if not parsed:
        return {
            "fighter_a": None, "fighter_b": None,
            "raw_response": raw, "sources": [],
            "confidence": 0.0, "error": "json_parse_failed",
        }

    fighters = parsed.get("fighters", [])
    sources = parsed.get("sources", [])
    confidence = float(parsed.get("confidence", 0.5))

    fa_intel = _match_fighter(fighters, fighter_a_name)
    fb_intel = _match_fighter(fighters, fighter_b_name)

    # Дополняем _meta
    now_iso = datetime.now().isoformat(timespec="seconds")
    for intel, name in [(fa_intel, fighter_a_name), (fb_intel, fighter_b_name)]:
        if intel:
            intel.setdefault("_meta", {})
            intel["_meta"]["sources"] = sources
            intel["_meta"]["extracted_at"] = now_iso
            intel["_meta"]["confidence"] = confidence
            intel["_meta"]["raw_input"] = notes_text[:500]
            intel["fighter"] = name

    return {
        "fighter_a": fa_intel,
        "fighter_b": fb_intel,
        "raw_response": raw,
        "sources": sources,
        "confidence": confidence,
        "error": None,
    }


def _safe_json_parse(text: str) -> dict | None:
    """Парсим JSON даже если LLM обернул его в ```json ... ```."""
    if not text:
        return None
    # Strip markdown fences
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip())
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    # Try direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Try to extract first {...} block
    m = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return None


def _match_fighter(fighters: list[dict], target_name: str) -> dict | None:
    """Найти запись о бойце по имени (нечувствительно к регистру, fuzzy)."""
    if not target_name or not fighters:
        return None
    target = target_name.lower()
    # Exact / substring match
    for f in fighters:
        n = (f.get("fighter") or "").lower()
        if n == target or target in n or n in target:
            # Нормализуем под empty_intel схему
            normalized = empty_intel(target_name)
            for k in ("weight_cut", "injury", "travel", "camp_drama", "motivation"):
                if k in f and isinstance(f[k], dict):
                    normalized[k].update(f[k])
            return normalized
    return None


# ---------------------------------------------------------------------------
# Prompt formatting
# ---------------------------------------------------------------------------

def format_intel_for_prompt(intel_a: dict | None, intel_b: dict | None,
                              fa_name: str, fb_name: str) -> str:
    """Форматированный блок === INTEL === для LLM."""
    def _fmt_one(intel: dict | None, name: str) -> str:
        if not intel:
            return f"  ▸ {name}: НЕТ СВЕЖИХ ДАННЫХ (интерпретируй с осторожностью)"
        wc = intel.get("weight_cut", {})
        inj = intel.get("injury", {})
        tr = intel.get("travel", {})
        cd = intel.get("camp_drama", {})
        mt = intel.get("motivation", {})
        lines = [f"  ▸ {name}"]
        if wc.get("severity", 0) > 0 or wc.get("notes"):
            lines.append(
                f"      weight_cut: severity={wc.get('severity',0):.2f}"
                + (" · MISSED WEIGHT" if wc.get("missed_weight") else "")
                + (" · double-cut" if wc.get("double_cut") else "")
                + (f" · {wc['notes']}" if wc.get("notes") else "")
            )
        if inj.get("severity", 0) > 0:
            lines.append(
                f"      injury: severity={inj.get('severity',0):.2f}"
                + (f" · {inj.get('body_part','')}" if inj.get("body_part") else "")
                + (f" · −{inj.get('training_camp_impact_weeks',0)} weeks camp" if inj.get("training_camp_impact_weeks") else "")
            )
        if tr.get("timezone_diff_hours") or tr.get("arrival_days_before", 14) < 7:
            lines.append(
                f"      travel: tz_diff={tr.get('timezone_diff_hours',0)}h · "
                f"arrived {tr.get('arrival_days_before','?')} days before · "
                f"altitude_change={tr.get('altitude_change_m',0)}m"
            )
        if cd.get("severity", 0) > 0 or cd.get("coach_change") or cd.get("team_split"):
            flags = [k for k in ("coach_change", "team_split", "contract_dispute",
                                  "personal_issues_flag") if cd.get(k)]
            lines.append(
                f"      camp_drama: severity={cd.get('severity',0):.2f}"
                + (f" · {','.join(flags)}" if flags else "")
                + (f" · {cd['notes']}" if cd.get("notes") else "")
            )
        if any(mt.get(k) for k in ("title_shot_implication", "comeback_after_ko",
                                     "fight_for_legacy")) or mt.get("months_inactive", 0) > 6:
            flags = [k for k in ("title_shot_implication", "comeback_after_ko",
                                  "fight_for_legacy") if mt.get(k)]
            lines.append(
                f"      motivation: "
                + (",".join(flags) if flags else "")
                + (f" · inactive {mt.get('months_inactive')}mo" if mt.get("months_inactive", 0) > 0 else "")
            )
        if len(lines) == 1:
            lines.append("      (no significant flags)")
        return "\n".join(lines)

    sources_str = ""
    meta_a = (intel_a or {}).get("_meta", {})
    sources = meta_a.get("sources", [])
    if sources:
        sources_str = "\nИсточники:\n" + "\n".join(
            f"  [{i+1}] {s.get('title','—')}: {s.get('url','—')} ({s.get('date','—')})"
            for i, s in enumerate(sources[:5])
        )

    return (
        "=== INTEL (External Context) ===\n"
        "Внешние данные о бойцах: весогонка, травмы, акклиматизация, драма в лагере, мотивация.\n"
        "severity 0.0–1.0 (0=норма, 1=катастрофа). Учитывай при калибровке вероятностей.\n\n"
        f"{_fmt_one(intel_a, fa_name)}\n\n"
        f"{_fmt_one(intel_b, fb_name)}"
        f"{sources_str}\n"
        "=== END INTEL ===\n"
    )


# ---------------------------------------------------------------------------
# Post-LLM hard modifier (детерминированный)
# ---------------------------------------------------------------------------

def apply_intel_modifier(final_prob_a: float | None,
                          intel_a: dict | None,
                          intel_b: dict | None) -> tuple[float | None, dict]:
    """Применяем детерминированный override к final_prob_a по severity-флагам.
    LLM мог пропустить severe intel — это страховка.

    Returns: (new_prob, info_dict)
    """
    if final_prob_a is None:
        return None, {"applied": False, "reason": "no_prob"}

    delta = 0.0
    explain = []

    def _add(amount: float, why: str):
        nonlocal delta
        delta += amount
        explain.append(f"{amount:+.3f} {why}")

    # Boец A — негатив (минусуем prob_a)
    if intel_a:
        wc = intel_a.get("weight_cut", {}).get("severity", 0)
        if wc > 0.0:
            _add(-0.07 * wc, f"A weight_cut={wc:.2f}")
        inj = intel_a.get("injury", {}).get("severity", 0)
        if inj > 0.0:
            _add(-0.05 * inj, f"A injury={inj:.2f}")
        cd = intel_a.get("camp_drama", {}).get("severity", 0)
        if cd > 0.0:
            _add(-0.04 * cd, f"A camp_drama={cd:.2f}")
        # Travel
        tr = intel_a.get("travel", {})
        tz = abs(tr.get("timezone_diff_hours", 0))
        arr = tr.get("arrival_days_before", 14)
        if tz >= 8 and arr < 5:
            _add(-0.04, f"A jet-lag (tz={tz}, arrived {arr}d)")
        # Inactivity
        inact = intel_a.get("motivation", {}).get("months_inactive", 0)
        if inact > 12:
            _add(-0.03, f"A inactive {inact}mo")
        # Comeback after KO
        if intel_a.get("motivation", {}).get("comeback_after_ko"):
            _add(-0.05, "A comeback after KO")

    # Боец B — зеркально (плюсуем prob_a)
    if intel_b:
        wc = intel_b.get("weight_cut", {}).get("severity", 0)
        if wc > 0.0:
            _add(+0.07 * wc, f"B weight_cut={wc:.2f}")
        inj = intel_b.get("injury", {}).get("severity", 0)
        if inj > 0.0:
            _add(+0.05 * inj, f"B injury={inj:.2f}")
        cd = intel_b.get("camp_drama", {}).get("severity", 0)
        if cd > 0.0:
            _add(+0.04 * cd, f"B camp_drama={cd:.2f}")
        tr = intel_b.get("travel", {})
        tz = abs(tr.get("timezone_diff_hours", 0))
        arr = tr.get("arrival_days_before", 14)
        if tz >= 8 and arr < 5:
            _add(+0.04, f"B jet-lag (tz={tz}, arrived {arr}d)")
        inact = intel_b.get("motivation", {}).get("months_inactive", 0)
        if inact > 12:
            _add(+0.03, f"B inactive {inact}mo")
        if intel_b.get("motivation", {}).get("comeback_after_ko"):
            _add(+0.05, "B comeback after KO")

    new_prob = max(0.05, min(0.95, final_prob_a + delta))
    return new_prob, {
        "applied": delta != 0.0,
        "delta": round(delta, 4),
        "before": round(final_prob_a, 4),
        "after": round(new_prob, 4),
        "factors": explain,
    }


# ---------------------------------------------------------------------------
# ML feature extraction
# ---------------------------------------------------------------------------

def extract_intel_features(intel_a: dict | None, intel_b: dict | None) -> dict:
    """Возвращает 5 diff-фич для ML-модели. Если intel пуст → нули."""
    def _val(intel: dict | None, *path) -> float:
        if not intel:
            return 0.0
        cur = intel
        for k in path:
            if not isinstance(cur, dict):
                return 0.0
            cur = cur.get(k, 0)
        try:
            return float(cur or 0.0)
        except (TypeError, ValueError):
            return 0.0

    def _accl(intel: dict | None) -> float:
        if not intel:
            return 0.0
        tr = intel.get("travel", {})
        tz = abs(tr.get("timezone_diff_hours", 0) or 0)
        arr = tr.get("arrival_days_before", 14) or 14
        return tz * max(0, (7 - arr)) / 7.0

    return {
        "weight_cut_severity_diff":
            _val(intel_a, "weight_cut", "severity") - _val(intel_b, "weight_cut", "severity"),
        "injury_severity_diff":
            _val(intel_a, "injury", "severity") - _val(intel_b, "injury", "severity"),
        "camp_drama_diff":
            _val(intel_a, "camp_drama", "severity") - _val(intel_b, "camp_drama", "severity"),
        "acclimatization_diff":
            _accl(intel_a) - _accl(intel_b),
        "inactivity_diff":
            _val(intel_a, "motivation", "months_inactive")
            - _val(intel_b, "motivation", "months_inactive"),
    }
