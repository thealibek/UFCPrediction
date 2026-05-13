"""Прогон blind-test V4 (GPT-OSS + DB + lessons) на ВСЕХ
gradeable UFC-ивентах 2026 года. Resumable: пропускает уже сделанные.

Структура: для каждого ивента отдельный JSON в blind_tests/.
В конце — агрегированный summary с per-event и overall метриками.
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
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai/v1")
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
    return winner, win_prob, method


def llm_predict(fa, fb, ctx):
    from openai import OpenAI
    fa = enrich_fighter(fa)
    fb = enrich_fighter(fb)
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    ctx_str = build_context_string(fa, fb, ctx, "")
    lessons_block = format_lessons_block(relevant_lessons(ctx_str, max_n=5))

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
        "Сделай прогноз в формате. Применяй УРОКИ. Используй конкретные цифры."
    )
    # retry on rate-limit
    last_err = None
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
            last_err = e
            wait = 5 + attempt * 5
            print(f"      ⚠️  attempt {attempt+1}: {type(e).__name__}: {str(e)[:80]} (wait {wait}s)")
            time.sleep(wait)
    return {"predicted_winner": "", "win_prob": None,
            "method": "Decision", "round": None,
            "reasoning": f"ERROR: {last_err}"}


# ---------------------------------------------------------------------------
# Resume helpers
# ---------------------------------------------------------------------------

def already_done(event_id: str) -> Path | None:
    """Find existing blind test for this espn_id (v4-prefix to differentiate)."""
    for p in Path("blind_tests").glob("*-v4-*.json"):
        try:
            d = json.loads(p.read_text())
            if str(d.get("event", {}).get("espn_id")) == str(event_id):
                return p
        except Exception:
            continue
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"📡 Mass blind 2026 | model={LLM_MODEL}")
    raw = fetch_espn_range("20260101", "20260520")
    today = date.today()
    targets = []
    for e in raw.get("events", []):
        ev = parse_event(e)
        try:
            d = datetime.fromisoformat(ev["date"].replace("Z", "+00:00")).date()
        except Exception:
            continue
        if d >= today:
            continue  # future event
        # check first fight status = Final
        first = (ev.get("fights") or [{}])[0]
        if first.get("status") not in ("Final", "Post-Event", "Completed"):
            continue
        targets.append(ev)

    print(f"✅ Found {len(targets)} gradeable events ({sum(len(e.get('fights',[])) for e in targets)} fights)\n")

    # filter — skip done
    to_run = []
    for ev in targets:
        ex = already_done(ev.get("id"))
        if ex:
            print(f"⏭️  SKIP (done): {ev['date'][:10]} {ev['name'][:50]} → {ex.name}")
        else:
            to_run.append(ev)

    print(f"\n🚀 Running {len(to_run)} new events "
          f"({sum(len(e.get('fights',[])) for e in to_run)} fights)\n")

    results = []
    for i, ev in enumerate(to_run, 1):
        print(f"\n{'='*70}\n[{i}/{len(to_run)}] {ev['date'][:10]} {ev['name']}")
        print(f"   {len(ev.get('fights',[]))} fights | venue: {ev.get('venue','?')}")
        print(f"{'='*70}")

        blinded = bt.blind_fights(ev["fights"])
        def predict_with_venue(fa, fb, ctx, _venue=ev.get("venue","")):
            ctx2 = dict(ctx, venue=_venue)
            return llm_predict(fa, fb, ctx2)

        def progress(j, total, msg):
            print(f"   [{j}/{total}] {msg}")

        try:
            path = bt.run_blind_test(
                event_name=ev["name"] + " [v4-mass]",
                event_date=ev["date"],
                fights=blinded, predict_fn=predict_with_venue,
                model_meta={"llm_model": LLM_MODEL,
                            "system_prompt_version": "blind-v4-mass",
                            "fighter_db": True, "lessons_injected": True},
                venue=ev.get("venue",""), espn_id=ev.get("id"),
                delay_s=2.5, progress_cb=progress,
            )
            print(f"💾 Saved → {path}")
            summ = bt.grade_test(path, ev["fights"])
            print(f"📊 acc={summ['accuracy_%']:.1f}% brier={summ['brier']:.3f} "
                  f"({summ['n_graded']}/{summ['n']})")
            results.append({"event": ev["name"], "date": ev["date"][:10],
                            "id": ev["id"], "path": str(path), "summary": summ})
        except KeyboardInterrupt:
            print("\n⛔ Interrupted. Resume by re-running this script.")
            break
        except Exception as e:
            print(f"❌ Event failed: {e}")
            results.append({"event": ev["name"], "error": str(e)})

    # ---- Final aggregation ----
    print(f"\n{'='*70}\n🏆 FINAL AGGREGATE — V4 mass run 2026\n{'='*70}")
    # collect all v4 mass files
    all_files = sorted(Path("blind_tests").glob("*-v4-*.json"))
    total_n = total_graded = total_correct = 0
    total_brier_sum = 0.0
    per_event = []
    for p in all_files:
        try:
            d = json.loads(p.read_text())
        except Exception: continue
        s = d.get("summary") or {}
        if not s.get("n_graded"): continue
        total_n += s.get("n", 0)
        total_graded += s["n_graded"]
        total_correct += round(s.get("accuracy_%", 0) * s["n_graded"] / 100)
        total_brier_sum += s.get("brier", 0) * s["n_graded"]
        per_event.append({
            "date": d["event"]["date"][:10],
            "name": d["event"]["name"].split(" [")[0],
            "n": s["n"], "graded": s["n_graded"],
            "acc": s["accuracy_%"], "brier": s["brier"],
        })

    if total_graded:
        agg_acc = total_correct / total_graded * 100
        agg_brier = total_brier_sum / total_graded
        print(f"\nTOTAL: {total_correct}/{total_graded} correct = {agg_acc:.1f}% accuracy")
        print(f"Weighted Brier: {agg_brier:.3f}")
        print(f"\n=== PER EVENT ===")
        for e in sorted(per_event, key=lambda x: x["date"]):
            print(f"  {e['date']} | {e['acc']:5.1f}% | brier {e['brier']:.3f} | "
                  f"{e['graded']}/{e['n']} | {e['name'][:50]}")

    # save aggregate
    Path("blind_tests/_aggregate_2026.json").write_text(
        json.dumps({"generated_at": datetime.now().isoformat(timespec="seconds"),
                    "model": LLM_MODEL,
                    "total_fights": total_graded,
                    "accuracy_%": agg_acc if total_graded else None,
                    "brier": agg_brier if total_graded else None,
                    "per_event": per_event}, indent=2, ensure_ascii=False))
    print(f"\n💾 Aggregate → blind_tests/_aggregate_2026.json")


if __name__ == "__main__":
    main()
