"""CLI blind test runner: UFC Fight Night Della Maddalena vs Prates (2 May 2026).

Дёргает ESPN, скрывает результаты, прогоняет LLM-прогноз на каждом бою,
сохраняет blind_tests/2026-05-02_*.json. Потом грейдит результаты.
"""
import os
import sys
import time
import re

# load .env.local
def _load_env(path=".env.local"):
    if not os.path.exists(path): return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
_load_env()

LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "llama-3.3-70b-versatile")

if not LLM_API_KEY:
    print("❌ LLM_API_KEY не задан в .env.local"); sys.exit(1)

# stub streamlit (live_data импортирует его только ради @st.cache_data)
import types
_st = types.ModuleType("streamlit")
def _noop_decorator(*a, **kw):
    def deco(fn): return fn
    if a and callable(a[0]): return a[0]
    return deco
_st.cache_data = _noop_decorator
sys.modules["streamlit"] = _st

import blind_test as bt
from live_data import fetch_espn_range, parse_event

SYS_PROMPT = """Ты — UFC predictor. Анализируй бой холодно. Учитывай только
известные публично данные. Стиль, рекорд, физика, форма.

ФОРМАТ (строго):
### 🎯 ПРОГНОЗ
Победитель: **[Имя]** — XX% уверенности.
Метод: KO/TKO XX% · Submission XX% · Decision XX%.
Раунд (если финиш): R[1-5].

### 📊 АНАЛИТИКА
2 коротких абзаца — стиль, физика, форма, контекст.

### ⚠️ РИСКИ
2-3 фактора риска."""


def llm_predict(fa, fb, ctx):
    from openai import OpenAI
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    user_msg = (
        f"БОЙ: {fa.get('name')} vs {fb.get('name')}\n"
        f"ИВЕНТ: {ctx.get('event')}\n"
        f"ВЕСОВАЯ: {ctx.get('weight_class')}\n"
        f"РАУНДОВ: {ctx.get('rounds', 3)}\n\n"
        f"=== БОЕЦ A ===\n{fa.get('name')} | record: {fa.get('record')}\n"
        f"=== БОЕЦ B ===\n{fb.get('name')} | record: {fb.get('record')}\n\n"
        "Сделай прогноз в формате."
    )
    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role":"system","content":SYS_PROMPT},
                  {"role":"user","content":user_msg}],
        temperature=0.5, max_tokens=900,
    )
    txt = resp.choices[0].message.content

    # parse
    win_prob = None
    m = re.search(r"\*\*([^*]+)\*\*\s*[—-]\s*(\d{1,3})\s*%", txt)
    if m:
        winner = m.group(1).strip().split("—")[0].strip()
        v = int(m.group(2))
        if 50 <= v <= 100:
            win_prob = v / 100.0
    else:
        winner = ""
    ko = re.search(r"KO/?TKO\s*(\d{1,3})\s*%", txt)
    sub = re.search(r"Submission\s*(\d{1,3})\s*%", txt)
    dec = re.search(r"Decision\s*(\d{1,3})\s*%", txt)
    ko_p = int(ko.group(1))/100 if ko else 0
    sub_p = int(sub.group(1))/100 if sub else 0
    dec_p = int(dec.group(1))/100 if dec else 0
    method = "KO/TKO" if ko_p >= max(sub_p, dec_p) else "Submission" if sub_p >= dec_p else "Decision"

    return {
        "predicted_winner": winner, "win_prob": win_prob,
        "method": method, "round": None, "reasoning": txt,
    }


def main():
    print(f"📡 Fetching ESPN events 20260420-20260520... model={LLM_MODEL}")
    raw = fetch_espn_range("20260420", "20260520")
    target = None
    for e in raw.get("events", []):
        if str(e.get("id")) == "600058807":
            target = parse_event(e); break
    if not target:
        print("❌ Event 600058807 not found"); sys.exit(1)

    print(f"✅ Event: {target['name']}  date: {target['date']}  fights: {len(target['fights'])}")
    blinded = bt.blind_fights(target["fights"])

    def progress(i, total, msg):
        print(f"  [{i}/{total}] {msg}")

    path = bt.run_blind_test(
        event_name=target["name"], event_date=target["date"],
        fights=blinded, predict_fn=llm_predict,
        model_meta={"llm_model": LLM_MODEL, "system_prompt_version": "blind-v1"},
        venue=target.get("venue",""), espn_id=target.get("id"),
        delay_s=2.0, progress_cb=progress,
    )
    print(f"\n💾 Saved → {path}")

    # Grade immediately (event is in the past)
    print("\n🔄 Grading vs real ESPN results...")
    summ = bt.grade_test(path, target["fights"])
    print(f"📊 Graded: {summ['n_graded']}/{summ['n']}  "
          f"accuracy={summ['accuracy_%']}  brier={summ['brier']}")

    # Show per-fight summary
    data = bt.load_test(path)
    print("\n=== РЕЗУЛЬТАТЫ ===")
    for r in data["predictions"]:
        icon = "✅" if r.get("correct") else "❌" if r.get("graded") else "⏳"
        wp = r.get("win_prob")
        wp_s = f"{wp*100:.0f}%" if wp else "—"
        print(f"{icon} {r['fighter_a']} vs {r['fighter_b']}")
        print(f"   predicted: {r.get('predicted_winner')} ({wp_s}, {r.get('method')})")
        if r.get("graded"):
            print(f"   actual:    {r.get('actual_winner')} by {r.get('actual_method')} R{r.get('actual_round')}")


if __name__ == "__main__":
    main()
