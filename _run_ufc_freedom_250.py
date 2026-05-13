"""V5 predict + human baseline для UFC Freedom 250: Topuria vs Gaethje.

Сохраняет human picks (твоя интуиция) и предикт модели side-by-side.
"""
from __future__ import annotations
import os, sys, types, time, json, re
from pathlib import Path
from datetime import datetime


def _load_env(path=".env.local"):
    if not os.path.exists(path): return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
_load_env()

LLM_API_KEY = os.environ["LLM_API_KEY"]
LLM_BASE_URL = os.environ.get("LLM_BASE_URL")
LLM_MODEL = os.environ.get("LLM_MODEL", "openai/gpt-oss-120b:free")

_st = types.ModuleType("streamlit")
def _noop(*a, **kw):
    def deco(fn): return fn
    if a and callable(a[0]): return a[0]
    return deco
_st.cache_data = _noop
sys.modules["streamlit"] = _st

import blind_test as bt
from live_data import fetch_espn_range, parse_event
from lessons import relevant_lessons, format_lessons_block, build_context_string
from fighter_db import enrich_fighter

# ============ HUMAN BASELINE (твоя интуиция) ============
HUMAN_PICKS = {
    "Justin Gaethje vs Ilia Topuria":     {"winner": "Ilia Topuria",     "conf": 0.70, "reason": "Скорее всего заберёт"},
    "Ciryl Gane vs Alex Pereira":         {"winner": "Alex Pereira",     "conf": 0.55, "reason": "Тяжело предсказать, но Pereira"},
    "Aiemann Zahabi vs Sean O'Malley":    {"winner": "Sean O'Malley",    "conf": 0.75, "reason": "Разница в возрасте + O'Malley сильнее в ударке, защищается от борцов"},
    "Michael Chandler vs Mauricio Ruffy": {"winner": "Mauricio Ruffy",   "conf": 0.65, "reason": "40 лет vs 29, хорошая ударка у Ruffy"},
    "Kyle Daukaus vs Bo Nickal":          {"winner": "Bo Nickal",        "conf": 0.70, "reason": "Сильный грэпплер заберёт"},
    "Steve Garcia vs Diego Lopes":        {"winner": "Diego Lopes",      "conf": 0.65, "reason": "Опыт + мотивация Диего"},
    "Derrick Lewis vs Josh Hokit":        {"winner": None,               "conf": None, "reason": "Не было предикта"},
}

SYS_PROMPT = """Ты — UFC predictor с 15+ лет опыта. Анализируй холодно.
Учитывай антропометрию, quality of opposition, chin durability, возрастной декай,
home-crowd bias, мотивацию (особенно после потери пояса).

ВАЖНО: Используй РАСШИРЕННЫЙ диапазон уверенности 55-85%.
Если данных мало — снижай до 55%.

ФОРМАТ:
### 🎯 ПРОГНОЗ
Победитель: **[Имя]** — XX% уверенности.
Метод: KO/TKO XX% · Submission XX% · Decision XX%.

### 📊 АНАЛИТИКА
2-3 абзаца, применяй УРОКИ.

### ⚠️ РИСКИ
2-3 фактора."""


def parse_final(txt: str):
    win_prob = None; winner = ""
    m = re.search(r"\*\*([^*]+)\*\*\s*[—-]\s*(\d{1,3})\s*%", txt)
    if m:
        winner = m.group(1).strip().split("—")[0].strip()
        v = int(m.group(2))
        if 50 <= v <= 100: win_prob = v / 100.0
    return winner, win_prob


def llm_predict(fa, fb, ctx):
    from openai import OpenAI
    fa = enrich_fighter(fa); fb = enrich_fighter(fb)
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    ctx_str = build_context_string(fa, fb, ctx, "")
    lessons_block = format_lessons_block(relevant_lessons(ctx_str, max_n=8))

    def _profile(f):
        rec = f.get("record") or "?"
        return (
            f"{f.get('name')} ({f.get('country','?')})\n"
            f"  Record: {rec} | Age: {f.get('age','?')} | Stance: {f.get('stance','?')}\n"
            f"  Height: {f.get('height_cm','?')} cm | Reach: {f.get('reach_cm','?')} cm\n"
            f"  SLpM: {f.get('SLpM','?')} | StrAcc: {f.get('StrAcc','?')} | SApM: {f.get('SApM','?')} | StrDef: {f.get('StrDef','?')}\n"
            f"  TDAvg: {f.get('TDAvg','?')} | TDDef: {f.get('TDDef','?')} | SubAvg: {f.get('SubAvg','?')}\n"
            f"  Champion: {f.get('is_champion', False)}"
        )

    user_msg = (
        f"БОЙ: {fa.get('name')} vs {fb.get('name')}\n"
        f"ИВЕНТ: {ctx.get('event')}\nВЕС: {ctx.get('weight_class')}\n"
        f"VENUE: {ctx.get('venue','—')}\n\n"
        f"=== A ===\n{_profile(fa)}\n\n=== B ===\n{_profile(fb)}\n\n"
        f"{lessons_block}\n\nПрогноз с применением УРОКОВ."
    )
    for attempt in range(4):
        try:
            resp = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role":"system","content":SYS_PROMPT},
                          {"role":"user","content":user_msg}],
                temperature=0.5, max_tokens=900,
            )
            txt = resp.choices[0].message.content
            winner, wp = parse_final(txt or "")
            return {"predicted_winner": winner, "win_prob": wp,
                    "method": "Decision", "round": None, "reasoning": txt or ""}
        except Exception as e:
            print(f"   ⚠️ retry {attempt+1}: {str(e)[:60]}")
            time.sleep(8 + attempt*5)
    return {"predicted_winner":"", "win_prob":None, "method":"Decision",
            "round":None, "reasoning":"ERROR"}


def main():
    raw = fetch_espn_range("20260601", "20260620")
    target = None
    for e in raw.get("events", []):
        ev = parse_event(e)
        if "Topuria" in ev["name"] and "250" in ev["name"]:
            target = ev; break
    if not target:
        print("❌ UFC Freedom 250 not found"); return

    print(f"\n📡 {target['name']} | {target['date'][:10]}")
    print(f"   {len(target['fights'])} fights\n")

    blinded = bt.blind_fights(target["fights"])

    def predict_with_venue(fa, fb, ctx, _v=target.get("venue","")):
        ctx2 = dict(ctx, venue=_v)
        return llm_predict(fa, fb, ctx2)

    def prog(i, total, msg):
        print(f"   [{i}/{total}] {msg}")

    path = bt.run_blind_test(
        event_name=target["name"] + " [v5-with-motivation]",
        event_date=target["date"],
        fights=blinded, predict_fn=predict_with_venue,
        model_meta={
            "llm_model": LLM_MODEL,
            "system_prompt_version": "v5-with-motivation-lessons",
            "fighter_db": True, "lessons_injected": True,
            "lessons_count": 19,
            "human_baseline": HUMAN_PICKS,
        },
        venue=target.get("venue",""), espn_id=target.get("id"),
        delay_s=2.5, progress_cb=prog,
    )
    print(f"\n💾 Saved → {path}\n")

    # Side-by-side
    print("="*80)
    print(f"{'FIGHT':<45} {'V5 MODEL':<25} {'YOU':<25}")
    print("="*80)
    data = bt.load_test(path)
    for rec in data["predictions"]:
        fight = f"{rec['fighter_a']} vs {rec['fighter_b']}"[:43]
        mw = rec.get("predicted_winner") or "—"
        mp = f"{int((rec.get('win_prob') or 0)*100)}%"
        h = HUMAN_PICKS.get(f"{rec['fighter_a']} vs {rec['fighter_b']}", {})
        hw = h.get("winner") or "—"
        hp = f"{int(h.get('conf',0)*100)}%" if h.get("conf") else "—"
        agree = "✅" if mw and hw and mw.lower().split()[-1] == hw.lower().split()[-1] else "❌"
        print(f"{fight:<45} {mw[:18]+' '+mp:<25} {hw[:18]+' '+hp:<22} {agree}")

if __name__ == "__main__":
    main()
