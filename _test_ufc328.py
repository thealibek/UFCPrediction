"""Blind-test: прогоняем v3 модель на UFC 328 (9 мая 2026) — карте, чьи
результаты модель не знает (knowledge cutoff Llama 3.3 70B раньше).
"""
import os
import re
import sys
import time

# Load .env.local
with open(".env.local") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

# Импортируем из app.py: SYSTEM_PROMPT + extractors
sys.path.insert(0, ".")
# Не запускаем app.py целиком (он Streamlit) — копируем нужные фрагменты:

import importlib.util
spec = importlib.util.spec_from_file_location("_app_src", "app.py")
# Парсим текстом — slishком много Streamlit-state, не импортируется чисто
src = open("app.py").read()

# SYSTEM_PROMPT
m = re.search(r'SYSTEM_PROMPT = """(.*?)"""', src, re.DOTALL)
SYSTEM_PROMPT = m.group(1)

CARD = [
    {"a": "Khamzat Chimaev", "b": "Sean Strickland",
     "div": "Middleweight", "rounds": 5, "title": True,
     "intel": "Chimaev — undefeated wrestler-боксёр. Strickland бывший чемпион 185, "
              "philly shell, кардио на 5 раундов, чугунный подбородок. Чимаев "
              "после долгого простоя возвращается."},
    {"a": "Joshua Van", "b": "Tatsuro Taira",
     "div": "Flyweight", "rounds": 5, "title": True,
     "intel": "Joshua Van — agressive striker/pressure из Мьянмы, восходящая звезда. "
              "Tatsuro Taira — японский борец-самбист, BJJ. Чемпионский бой."},
    {"a": "Alexander Volkov", "b": "Waldo Cortes-Acosta",
     "div": "Heavyweight", "rounds": 3, "title": False,
     "intel": "Volkov — рослый kickboxer 36 лет, опыт топовый, кардио средний. "
              "Cortes-Acosta — Доминиканец, бокс, моложе и плотнее, активный темп."},
    {"a": "Sean Brady", "b": "Joaquin Buckley",
     "div": "Welterweight", "rounds": 3, "title": False,
     "intel": "Brady — wrestler-grappler, single-leg-shots, недавний luxury win. "
              "Buckley — power-striker, одно из самых ярких KO в истории, но защита борьбы средняя."},
    {"a": "Bobby Green", "b": "Jeremy Stephens",
     "div": "Lightweight", "rounds": 3, "title": False,
     "intel": "Bobby Green — boxer-counter, slick movement, прошёл много апсетов. "
              "Jeremy Stephens — heavy hands, ветеран, после долгого простоя возвращается из Bellator/PFL."},
]


def predict(fight):
    user_msg = (
        f"Прогноз боя UFC: **{fight['a']}** vs **{fight['b']}**.\n"
        f"Дивизион: {fight['div']}. {'Титульный' if fight['title'] else 'Нетитульный'} бой, "
        f"{fight['rounds']} раундов.\n\n"
        f"Контекст: {fight['intel']}\n\n"
        f"Используй свои знания о бойцах + методологию (CoT, calibration grid, "
        f"method baselines) и выдай прогноз СТРОГО в формате с regex-парсингом."
    )
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["LLM_API_KEY"], base_url=os.environ["LLM_BASE_URL"])
    t0 = time.time()
    resp = client.chat.completions.create(
        model=os.environ["LLM_MODEL"],
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user", "content": user_msg}],
        temperature=0.5, max_tokens=2500,
    )
    elapsed = time.time() - t0
    text = resp.choices[0].message.content
    return text, elapsed, resp.usage.total_tokens


def extract_winner(text):
    m = re.search(r"Победитель[:\s]+\*\*([^\*]+?)\*\*", text)
    return m.group(1).strip() if m else None


def extract_win_prob(text):
    m = re.search(r"(\d{1,3})\s*%\s*уверенности", text)
    return int(m.group(1)) / 100 if m else None


def extract_methods(text):
    out = {}
    m = re.search(r"KO/TKO\s*(\d{1,3})", text)
    out["ko"] = int(m.group(1)) if m else None
    m = re.search(r"Submission\s*(\d{1,3})", text)
    out["sub"] = int(m.group(1)) if m else None
    m = re.search(r"Decision\s*(\d{1,3})", text)
    out["dec"] = int(m.group(1)) if m else None
    return out


def extract_main_bet(text):
    m = re.search(r"Основная ставка[:\s]+(.+?)(?=\n|$)", text)
    if m:
        return m.group(1).strip()[:120]
    return None


# --- Run all ---
results = []
for i, f in enumerate(CARD, start=1):
    print(f"\n[{i}/{len(CARD)}] {f['a']} vs {f['b']} ({f['div']})...", flush=True)
    try:
        analysis, t, tok = predict(f)
        winner = extract_winner(analysis)
        prob = extract_win_prob(analysis)
        methods = extract_methods(analysis)
        bet = extract_main_bet(analysis)
        results.append({
            "fight": f"{f['a']} vs {f['b']}",
            "div": f["div"],
            "winner": winner, "prob": prob,
            "methods": methods, "bet": bet,
            "elapsed": t, "tokens": tok,
            "analysis": analysis,
        })
        print(f"  → {winner} {int((prob or 0)*100)}% · "
              f"KO {methods['ko']}/Sub {methods['sub']}/Dec {methods['dec']} · "
              f"{tok} tok · {t:.1f}s", flush=True)
    except Exception as e:
        print(f"  ERROR: {e}", flush=True)
        results.append({"fight": f"{f['a']} vs {f['b']}", "error": str(e)})


# --- Markdown table ---
print("\n\n" + "="*80)
print("PREDICTIONS TABLE — UFC 328 (May 9, 2026)")
print("="*80)
print()
print("| # | Бой | Прогноз | Win % | KO% | Sub% | Dec% | Основная ставка |")
print("|---|-----|---------|-------|-----|------|------|-----------------|")
for i, r in enumerate(results, start=1):
    if r.get("error"):
        print(f"| {i} | {r['fight']} | ERROR | — | — | — | — | — |")
        continue
    m = r["methods"]
    bet = (r["bet"] or "—").replace("|", "/")[:60]
    print(f"| {i} | **{r['fight']}** | {r['winner'] or '?'} | "
          f"{int((r['prob'] or 0)*100)}% | {m['ko'] or '?'} | {m['sub'] or '?'} | "
          f"{m['dec'] or '?'} | {bet} |")

# Save full analysis
import json
with open("_ufc328_predictions.json", "w") as f:
    json.dump(results, f, ensure_ascii=False, indent=2, default=str)
print("\n📦 Full analyses saved to _ufc328_predictions.json")
