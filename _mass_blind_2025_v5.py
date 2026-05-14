"""V5 mass-run на тех же 2026-ивентах с расширенными уроками (17 правил).

Сохраняет под -v5-2025-expanded-lessons суффиксом чтобы не перезатереть V4.
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

SYS_PROMPT = """Ты — UFC predictor с 15+ лет опыта. Анализируй холодно.
Учитывай антропометрию, quality of opposition, chin durability, возрастной
декай, home-crowd bias. Не overconfidence на 'имени' — Brier штрафует.

ВАЖНО: При отсутствии данных в БД (height/reach/SLpM = ?), НЕ выдумывай цифры.
Если у одного бойца нет данных, а у другого есть — снижай уверенность до 55%,
не выше 60% (нет основания для overconfidence).

ВАЖНО: Используй РАСШИРЕННЫЙ диапазон уверенности 55-85%.
- 55-58% — близкий бой, мало данных
- 60-68% — есть преимущество, но риски
- 70-78% — явный фаворит со всеми факторами
- 80-85% — overwhelming favorite (например champion vs unranked debut)

ФОРМАТ (строго):
### 🎯 ПРОГНОЗ
Победитель: **[Имя]** — XX% уверенности.
Метод: KO/TKO XX% · Submission XX% · Decision XX%.
Раунд (если финиш): R[1-5].

### 📊 АНАЛИТИКА
2-3 коротких абзаца — стиль, физика, форма, контекст. Применяй УРОКИ.

### ⚠️ РИСКИ
2-3 фактора риска."""


def parse_final(txt: str):
    win_prob = None; winner = ""
    # tolerant к nested-quotes (Mauricio "Ruffy")
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
    fa = enrich_fighter(fa)
    fb = enrich_fighter(fb)
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    ctx_str = build_context_string(fa, fb, ctx, "")
    # V5: больше уроков (top-8 вместо top-5)
    lessons_block = format_lessons_block(relevant_lessons(ctx_str, max_n=8))

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
        f"ИВЕНТ: {ctx.get('event')}\nВЕСОВАЯ: {ctx.get('weight_class')}\n"
        f"VENUE: {ctx.get('venue','—')}\nРАУНДОВ: {ctx.get('rounds', 3)}\n\n"
        f"=== БОЕЦ A ===\n{_profile(fa)}\n\n"
        f"=== БОЕЦ B ===\n{_profile(fb)}\n\n"
        f"{lessons_block}\n\n"
        "Сделай прогноз. Применяй УРОКИ. Используй конкретные цифры. "
        "Если данных мало — будь скромнее в уверенности."
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
            winner, win_prob, method = parse_final(txt or "")
            return {"predicted_winner": winner, "win_prob": win_prob,
                    "method": method, "round": None, "reasoning": txt or ""}
        except Exception as e:
            wait = 5 + attempt * 5
            print(f"      ⚠️ attempt {attempt+1}: {str(e)[:80]} (wait {wait}s)")
            time.sleep(wait)
    return {"predicted_winner": "", "win_prob": None,
            "method": "Decision", "round": None, "reasoning": "ERROR"}


def already_done_v5(event_id):
    for p in Path("blind_tests").glob("*-v5-2025-*.json"):
        try:
            d = json.loads(p.read_text())
            if str(d.get("event", {}).get("espn_id")) == str(event_id):
                return p
        except Exception:
            continue
    return None


def main():
    print(f"📡 V5 mass blind 2025 | model={LLM_MODEL} | 17 lessons")
    raw = fetch_espn_range("20250101", "20251231")
    today = date.today()
    targets = []
    for e in raw.get("events", []):
        ev = parse_event(e)
        try:
            d = datetime.fromisoformat(ev["date"].replace("Z","+00:00")).date()
        except Exception: continue
        if d >= today: continue
        first = (ev.get("fights") or [{}])[0]
        if first.get("status") not in ("Final","Post-Event","Completed"): continue
        targets.append(ev)

    print(f"✅ Found {len(targets)} gradeable events\n")
    to_run = [e for e in targets if not already_done_v5(e.get("id"))]
    print(f"🚀 Running {len(to_run)} events\n")

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
                event_name=ev["name"] + " [v5-2025]",
                event_date=ev["date"],
                fights=blinded, predict_fn=predict_with_venue,
                model_meta={"llm_model": LLM_MODEL,
                            "system_prompt_version": "blind-v5-2025-expanded-lessons",
                            "fighter_db": True, "lessons_injected": True,
                            "lessons_count": 17, "max_lessons_per_pred": 8},
                venue=ev.get("venue",""), espn_id=ev.get("id"),
                delay_s=2.5, progress_cb=prog,
            )
            summ = bt.grade_test(path, ev["fights"])
            print(f"📊 V5 acc={summ['accuracy_%']:.1f}% brier={summ['brier']:.3f}")
        except KeyboardInterrupt:
            print("\n⛔ Interrupted"); break
        except Exception as e:
            print(f"❌ {e}")

    # final
    print("\n" + "="*70 + "\n🏆 V5 FINAL AGGREGATE\n" + "="*70)
    total_g = total_c = 0; total_b = 0.0
    rows = []
    for p in sorted(Path("blind_tests").glob("*-v5-2025-*.json")):
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
        print(f"\nV5 TOTAL: {total_c}/{total_g} = {total_c/total_g*100:.1f}% | Brier {total_b/total_g:.3f}")
        print("\n=== PER EVENT (V5) ===")
        for d, n, acc, br, gr in sorted(rows):
            print(f"  {d} | {acc:5.1f}% | brier {br:.3f} | {gr} | {n[:55]}")


if __name__ == "__main__":
    main()
