"""Blind v3: Multi-Agent (Stats + Style + Context + Opposition) + Lessons.
Цель: побьёт ли мульти-агентная система lessons-only V2.
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
from agents import run_multi_agent_prediction


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


def predict_multi(fa, fb, ctx):
    # Inject lessons как rag_context (агенты увидят это)
    ctx_str = build_context_string(fa, fb, ctx, "")
    lessons = relevant_lessons(ctx_str, max_n=5)
    lessons_block = format_lessons_block(lessons)

    res = run_multi_agent_prediction(
        fa=fa, fb=fb, ctx=ctx, intel="",
        rag_context=lessons_block,
        api_key=LLM_API_KEY, base_url=LLM_BASE_URL,
        models={"default": LLM_MODEL},
        parallel=True,
        include_opposition=True,
        include_historical=False,  # без RAG-параллелей у нас нет настоящих исторических данных
    )
    winner, win_prob, method = parse_final(res.final or "")
    return {
        "predicted_winner": winner, "win_prob": win_prob,
        "method": method, "round": None, "reasoning": res.final or "",
    }


def main():
    print(f"📡 Multi-agent run. model={LLM_MODEL}")
    raw = fetch_espn_range("20260420", "20260520")
    target = None
    for e in raw.get("events", []):
        if str(e.get("id")) == "600058807":
            target = parse_event(e); break
    if not target:
        print("❌ event not found"); sys.exit(1)

    blinded = bt.blind_fights(target["fights"])
    def progress(i, total, msg):
        print(f"  [{i}/{total}] {msg}")

    path = bt.run_blind_test(
        event_name=target["name"] + " [v3-multiagent]",
        event_date=target["date"],
        fights=blinded, predict_fn=predict_multi,
        model_meta={"llm_model": LLM_MODEL,
                    "system_prompt_version": "blind-v3-multiagent",
                    "agents": ["Stats","Style","Context","Opposition","Synthesizer"],
                    "lessons_injected": True},
        venue=target.get("venue",""), espn_id=target.get("id"),
        delay_s=3.0, progress_cb=progress,
    )
    print(f"\n💾 Saved → {path}")
    summ = bt.grade_test(path, target["fights"])
    print(f"📊 V3 (multi-agent + lessons): acc={summ['accuracy_%']:.1f}% brier={summ['brier']:.3f}")

    # сравним
    for label, fname in [
        ("V1 (no lessons)", "2026-05-02_ufc-fight-night-della-maddalena-vs-prates.json"),
        ("V2 (lessons)",    "2026-05-02_ufc-fight-night-della-maddalena-vs-prates-v2-lessons.json"),
    ]:
        p = Path("blind_tests") / fname
        if p.exists():
            s = json.loads(p.read_text())["summary"]
            if s.get("accuracy_%") is not None:
                print(f"📊 {label}: acc={s['accuracy_%']:.1f}% brier={s['brier']:.3f}")


if __name__ == "__main__":
    main()
