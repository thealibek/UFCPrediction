"""Blind v2: тот же ивент, но с инжектом Lessons Memory.

Сравнивает результат v1 (без уроков) vs v2 (с уроками) на UFC FN JDM vs Prates.
"""
import os, sys, re, types, json
from pathlib import Path

def _load_env(path=".env.local"):
    if not os.path.exists(path): return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
_load_env()

LLM_API_KEY = os.environ["LLM_API_KEY"]
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "llama-3.3-70b-versatile")

# stub streamlit
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

SYS_PROMPT = """Ты — UFC predictor с 15+ лет опыта. Анализируй холодно.
Учитывай антропометрию, quality of opposition, chin durability, возрастной
декай, home-crowd bias. Не overconfidence на 'имени' — Brier штрафует.

ФОРМАТ (строго):
### 🎯 ПРОГНОЗ
Победитель: **[Имя]** — XX% уверенности.
Метод: KO/TKO XX% · Submission XX% · Decision XX%.
Раунд (если финиш): R[1-5].

### 📊 АНАЛИТИКА
2-3 коротких абзаца — стиль, физика, форма, контекст. Применяй УРОКИ.

### ⚠️ РИСКИ
2-3 фактора риска."""


def llm_predict_v2(fa, fb, ctx):
    from openai import OpenAI
    # Auto-enrich из fighters_db.json
    fa = enrich_fighter(fa)
    fb = enrich_fighter(fb)
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    ctx_str = build_context_string(fa, fb, ctx, "")
    lessons = relevant_lessons(ctx_str, max_n=5)
    lessons_block = format_lessons_block(lessons)

    def _profile(f):
        rec = f.get("record") or (
            f"{f.get('wins')}-{f.get('losses')}-{f.get('draws')}"
            if f.get("wins") is not None else "?")
        return (
            f"{f.get('name')} ({f.get('country','?')})\n"
            f"  Record: {rec} | Age: {f.get('age','?')} | Stance: {f.get('stance','?')}\n"
            f"  Height: {f.get('height_cm','?')} cm | Reach: {f.get('reach_cm','?')} cm\n"
            f"  SLpM: {f.get('SLpM','?')} | StrAcc: {f.get('StrAcc','?')} | "
            f"SApM: {f.get('SApM','?')} | StrDef: {f.get('StrDef','?')}\n"
            f"  TDAvg: {f.get('TDAvg','?')} | TDDef: {f.get('TDDef','?')} | "
            f"SubAvg: {f.get('SubAvg','?')}\n"
            f"  Champion: {f.get('is_champion', False)}"
        )
    user_msg = (
        f"БОЙ: {fa.get('name')} vs {fb.get('name')}\n"
        f"ИВЕНТ: {ctx.get('event')}\n"
        f"ВЕСОВАЯ: {ctx.get('weight_class')}\n"
        f"VENUE: {ctx.get('venue','—')}\n"
        f"РАУНДОВ: {ctx.get('rounds', 3)}\n\n"
        f"=== БОЕЦ A ===\n{_profile(fa)}\n\n"
        f"=== БОЕЦ B ===\n{_profile(fb)}\n\n"
        f"{lessons_block}\n\n"
        "Сделай прогноз в формате. Применяй УРОКИ. "
        "Используй конкретные цифры (reach, SLpM, TDDef и т.д.) если они есть в данных."
    )
    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role":"system","content":SYS_PROMPT},
                  {"role":"user","content":user_msg}],
        temperature=0.5, max_tokens=900,
    )
    txt = resp.choices[0].message.content

    win_prob = None; winner = ""
    m = re.search(r"\*\*([^*]+)\*\*\s*[—-]\s*(\d{1,3})\s*%", txt)
    if m:
        winner = m.group(1).strip().split("—")[0].strip()
        v = int(m.group(2))
        if 50 <= v <= 100: win_prob = v / 100.0
    ko = re.search(r"KO/?TKO\s*(\d{1,3})\s*%", txt)
    sub = re.search(r"Submission\s*(\d{1,3})\s*%", txt)
    dec = re.search(r"Decision\s*(\d{1,3})\s*%", txt)
    ko_p = int(ko.group(1))/100 if ko else 0
    sub_p = int(sub.group(1))/100 if sub else 0
    dec_p = int(dec.group(1))/100 if dec else 0
    method = "KO/TKO" if ko_p >= max(sub_p, dec_p) else "Submission" if sub_p >= dec_p else "Decision"

    return {"predicted_winner": winner, "win_prob": win_prob,
            "method": method, "round": None, "reasoning": txt}


def main():
    print(f"📡 Fetching ESPN... model={LLM_MODEL}")
    raw = fetch_espn_range("20260420", "20260520")
    target = None
    for e in raw.get("events", []):
        if str(e.get("id")) == "600058807":
            target = parse_event(e); break
    if not target:
        print("❌ event not found"); sys.exit(1)

    # Переименовываем файл (чтобы не перезаписать v1)
    print(f"✅ Event: {target['name']}  fights: {len(target['fights'])}")
    blinded = bt.blind_fights(target["fights"])

    # ставим venue в ctx для lesson triggers
    for f in target["fights"]:
        f["_venue"] = target.get("venue","")

    def progress(i, total, msg):
        print(f"  [{i}/{total}] {msg}")

    # Подмена predict_fn чтобы добавить venue в ctx
    def predict_with_venue(fa, fb, ctx):
        ctx2 = dict(ctx, venue=target.get("venue",""))
        return llm_predict_v2(fa, fb, ctx2)

    # Сохраняем под отдельным именем
    path = bt.run_blind_test(
        event_name=target["name"] + " [v4-db-lessons-gpt-oss]",
        event_date=target["date"],
        fights=blinded, predict_fn=predict_with_venue,
        model_meta={"llm_model": LLM_MODEL,
                    "system_prompt_version": "blind-v4-db-lessons",
                    "fighter_db": True, "lessons_injected": True},
        venue=target.get("venue",""), espn_id=target.get("id"),
        delay_s=2.0, progress_cb=progress,
    )
    print(f"\n💾 Saved → {path}")

    print("\n🔄 Grading...")
    summ = bt.grade_test(path, target["fights"])
    print(f"📊 V2 (lessons): {summ['n_graded']}/{summ['n']} acc={summ['accuracy_%']:.1f}% brier={summ['brier']:.3f}")

    # сравним с v1
    v1_path = Path("blind_tests/2026-05-02_ufc-fight-night-della-maddalena-vs-prates.json")
    if v1_path.exists():
        v1 = json.loads(v1_path.read_text())["summary"]
        if v1.get("accuracy_%") is not None:
            print(f"📊 V1 (no lessons): {v1['n_graded']}/{v1['n']} acc={v1['accuracy_%']:.1f}% brier={v1['brier']:.3f}")
            print(f"\n🆚 DELTA: acc {summ['accuracy_%']-v1['accuracy_%']:+.1f}pp  "
                  f"brier {summ['brier']-v1['brier']:+.3f}")

    # per-fight
    data = bt.load_test(path)
    print("\n=== РЕЗУЛЬТАТЫ V2 ===")
    for r in data["predictions"]:
        icon = "✅" if r.get("correct") else "❌" if r.get("graded") else "⏳"
        wp_s = f"{r.get('win_prob')*100:.0f}%" if r.get("win_prob") else "—"
        print(f"{icon} {r['fighter_a']} vs {r['fighter_b']}")
        print(f"   predicted: {r.get('predicted_winner')} ({wp_s}, {r.get('method')})")
        if r.get("graded"):
            print(f"   actual:    {r.get('actual_winner')} by {r.get('actual_method')}")


if __name__ == "__main__":
    main()
