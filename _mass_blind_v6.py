"""V6 mass-run на ВСЁМ backlog (2024 + 2025 + 2026).

Изменения vs V5:
1. **Tighter low-conf range**: модель должна выводить 50-52% если нет 3+ сильных факторов
2. **Wider high-conf allowed**: если 5+ сильных факторов в одну сторону → разрешить 80-90%
3. **Temperature 0.5 → 0.2**: меньше variance
4. **18 lessons** (после ablation pruning)
5. **Method-parser**: regex поддерживает "Mauricio \"Ruffy\"" формат
"""
from __future__ import annotations
import os, sys, types, time, json, re
from datetime import date, datetime
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
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1")
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

# V6 SYSTEM PROMPT
SYS_PROMPT = """Ты — UFC predictor с 15+ лет опыта. Анализируй холодно и калиброванно.

КАЛИБРАЦИЯ УВЕРЕННОСТИ (КРИТИЧНО — основано на анализе 351 прошлых прогнозов):

🔴 НЕ ИЗОБРАЖАЙ ЗНАНИЕ ЕСЛИ ЕГО НЕТ.
Если у тебя НЕТ 3+ конкретных факторов в одну сторону:
  → Выводи 50-52% уверенности (не 55-60%!)
  → Это «coin flip zone» — мы не делаем bet здесь.

🟢 НЕ БОЙСЯ БЫТЬ УВЕРЕННЫМ ЕСЛИ ДАННЫЕ ЯВНЫЕ.
Если у тебя 5+ конкретных факторов в одну сторону:
  → Разрешено 80-85%, в overwhelming случаях 88-92%
  → Champion vs unranked debutant с явной разницей stats = 85%+

ДИАПАЗОНЫ:
- 50-52%: реальный coin flip, нет факторов
- 53-58%: 1-2 weak factors
- 59-65%: solid edge, 3-4 factors
- 66-74%: clear favorite, 4-5 factors
- 75-85%: dominant favorite, 5+ factors
- 86-92%: overwhelming evidence (champion + age gap + style mismatch + form)

ВАЖНО: При отсутствии данных в БД (height/reach/SLpM = ?) — НЕ выдумывай цифры.
Если у одного бойца нет данных, а у другого есть — выводи 50-52%, не больше.

ФОРМАТ (строго):
### 🎯 ПРОГНОЗ
Победитель: **[Имя]** — XX% уверенности.
Метод: KO/TKO XX% · Submission XX% · Decision XX%.
Раунд (если финиш): R[1-5].

### 📊 АНАЛИТИКА
3 коротких абзаца — стиль, физика+форма, контекст. Каждый абзац = факт + вывод.
Применяй УРОКИ только если они уместны в этом конкретном бою.

### ⚠️ РИСКИ
2-3 фактора риска."""


def parse_final(txt: str):
    win_prob = None; winner = ""
    m = re.search(r"\*\*([^*]+?)\*\*\s*[—\-–]\s*(?:\*\*)?(\d{1,3})\s*%", txt)
    if not m:
        m = re.search(r"Победитель:\s*\*\*([^*]+?)\*\*.*?(\d{1,3})\s*%", txt, re.DOTALL)
    if m:
        winner = re.sub(r'[«»"""„]', '', m.group(1)).strip().split("—")[0].strip()
        v = int(m.group(2))
        if 50 <= v <= 100: win_prob = v / 100.0
    ko = re.search(r"KO/?TKO\s*(\d{1,3})\s*%", txt)
    sub = re.search(r"Submission\s*(\d{1,3})\s*%", txt)
    dec = re.search(r"Decision\s*(\d{1,3})\s*%", txt)
    ko_p = int(ko.group(1))/100 if ko else 0
    sub_p = int(sub.group(1))/100 if sub else 0
    dec_p = int(dec.group(1))/100 if dec else 0
    method = "KO/TKO" if ko_p >= max(sub_p, dec_p) else "Submission" if sub_p >= dec_p else "Decision"
    return winner, win_prob, method


def llm_predict(fa, fb, ctx):
    from openai import OpenAI
    fa = enrich_fighter(fa); fb = enrich_fighter(fb)
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    ctx_str = build_context_string(fa, fb, ctx, "")
    lessons_block = format_lessons_block(relevant_lessons(ctx_str, max_n=6))  # tighter

    def _profile(f):
        rec = f.get("record") or "?"
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
        f"ИВЕНТ: {ctx.get('event')}\nВЕС: {ctx.get('weight_class')}\n"
        f"VENUE: {ctx.get('venue','—')}\nРАУНДОВ: {ctx.get('rounds', 3)}\n\n"
        f"=== БОЕЦ A ===\n{_profile(fa)}\n\n"
        f"=== БОЕЦ B ===\n{_profile(fb)}\n\n"
        f"{lessons_block}\n\n"
        "Сделай прогноз. ПОМНИ КАЛИБРАЦИЮ: coin flip = 50-52%, "
        "overwhelming evidence = 85%+, midground = только при 3+ конкретных факторах."
    )
    for attempt in range(4):
        try:
            resp = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role":"system","content":SYS_PROMPT},
                          {"role":"user","content":user_msg}],
                temperature=0.2,  # ↓ from 0.5
                max_tokens=900,
            )
            txt = resp.choices[0].message.content
            winner, win_prob, method = parse_final(txt or "")
            return {"predicted_winner": winner, "win_prob": win_prob,
                    "method": method, "round": None, "reasoning": txt or ""}
        except Exception as e:
            wait = 5 + attempt * 5
            print(f"      ⚠️ attempt {attempt+1}: {str(e)[:80]} (wait {wait}s)")
            time.sleep(wait)
    return {"predicted_winner": "", "win_prob": None,
            "method": "Decision", "round": None, "reasoning": "ERROR"}


def already_done_v6(event_id):
    for p in Path("blind_tests").glob("*-v6-*.json"):
        try:
            d = json.loads(p.read_text())
            if str(d.get("event", {}).get("espn_id")) == str(event_id):
                return p
        except Exception:
            continue
    return None


def main():
    print(f"📡 V6 mass blind ALL YEARS | model={LLM_MODEL} | calibrated prompt | temp=0.2")
    raw_2024 = fetch_espn_range("20240101", "20241231")
    raw_2025 = fetch_espn_range("20250101", "20251231")
    raw_2026 = fetch_espn_range("20260101", "20261231")

    today = date.today()
    targets = []
    for raw in (raw_2024, raw_2025, raw_2026):
        for e in raw.get("events", []):
            ev = parse_event(e)
            try:
                d = datetime.fromisoformat(ev["date"].replace("Z","+00:00")).date()
            except Exception: continue
            if d >= today: continue
            n_completed = sum(1 for f in ev.get("fights",[]) if f.get("completed"))
            if n_completed < 5: continue  # skip mostly-incomplete events
            targets.append(ev)

    print(f"✅ Found {len(targets)} gradeable events (2024-2026)\n")
    to_run = [e for e in targets if not already_done_v6(e.get("id"))]
    print(f"🚀 Running {len(to_run)} events (skipping {len(targets)-len(to_run)} already V6'd)\n")

    for i, ev in enumerate(to_run, 1):
        print(f"\n[{i}/{len(to_run)}] {ev['date'][:10]} {ev['name']}")
        blinded = bt.blind_fights(ev["fights"])

        def predict_with_venue(fa, fb, ctx, _v=ev.get("venue","")):
            ctx2 = dict(ctx, venue=_v)
            return llm_predict(fa, fb, ctx2)

        def prog(j, t, msg):
            print(f"   [{j}/{t}] {msg}")
        try:
            path = bt.run_blind_test(
                event_name=ev["name"] + " [v6-calibrated]",
                event_date=ev["date"],
                fights=blinded, predict_fn=predict_with_venue,
                model_meta={"llm_model": LLM_MODEL,
                            "system_prompt_version": "v6-calibrated",
                            "fighter_db": True, "lessons_injected": True,
                            "lessons_count": 18, "max_lessons_per_pred": 6,
                            "temperature": 0.2,
                            "calibration_changes": [
                                "tighter low-conf (50-52% no-bet zone)",
                                "wider high-conf (allow up to 92%)",
                                "lower temp 0.5→0.2",
                                "ablated lessons #18 #19",
                            ]},
                venue=ev.get("venue",""), espn_id=ev.get("id"),
                delay_s=2.5, progress_cb=prog,
            )
            summ = bt.grade_test(path, ev["fights"])
            print(f"📊 V6 acc={summ['accuracy_%']:.1f}% brier={summ['brier']:.3f}")
        except KeyboardInterrupt:
            print("\n⛔ Interrupted"); break
        except Exception as e:
            print(f"❌ {e}")

    # Final
    print("\n" + "="*70 + "\n🏆 V6 FINAL AGGREGATE\n" + "="*70)
    total_g = total_c = 0; total_b = 0.0
    rows = []
    for p in sorted(Path("blind_tests").glob("*-v6-*.json")):
        d = json.loads(p.read_text())
        s = d.get("summary",{})
        if not s.get("n_graded"): continue
        n = s["n_graded"]
        total_g += n
        total_c += round(s["accuracy_%"]*n/100)
        total_b += s["brier"]*n
        rows.append((d["event"]["date"][:10], d["event"]["name"].split(" [")[0],
                     s["accuracy_%"], s["brier"], n))
    if total_g:
        print(f"\nV6 TOTAL: {total_c}/{total_g} = {total_c/total_g*100:.1f}% | Brier {total_b/total_g:.3f}")


if __name__ == "__main__":
    main()
