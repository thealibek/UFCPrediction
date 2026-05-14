"""Ablation analysis: какие из 20 уроков помогли vs вредили в V4→V5.

Подход:
1. Для каждого V5-ивента: загрузить reasoning'и всех боёв
2. Для каждого урока: посчитать сколько раз он упомянут в reasoning'е (упоминание = LLM реально применил)
3. Скоррелировать % использования урока × дельта V4→V5
4. Урок с высоким usage в "проигранных" ивентах = подозрительный
"""
from __future__ import annotations
import json, re
from pathlib import Path
from collections import defaultdict


def load_runs(suffix: str):
    out = {}
    for p in sorted(Path("blind_tests").glob(f"*{suffix}*.json")):
        if "topuria" in p.name.lower(): continue
        d = json.loads(p.read_text())
        eid = str(d.get("event", {}).get("espn_id") or p.stem)
        out[eid] = d
    return out


def main():
    v4 = load_runs("-v4-mass")
    v5 = load_runs("-v5-")

    # Все 20 уроков
    lessons = json.loads(Path("lessons.json").read_text())
    active = [l for l in lessons if l.get("active", True)]

    # Для каждого V5-ивента: какие уроки реально упомянуты в reasoning + дельта vs V4
    event_data = []
    for eid, d5 in v5.items():
        d4 = v4.get(eid)
        if not d4: continue
        s4, s5 = d4.get("summary", {}), d5.get("summary", {})
        a4, a5 = s4.get("accuracy_%"), s5.get("accuracy_%")
        if a4 is None or a5 is None: continue
        delta = a5 - a4

        # Pool all reasoning text from this event
        all_text = " ".join((r.get("reasoning") or "").lower()
                            for r in d5.get("predictions", []))

        # Which lessons "fired" — keyword in text or title-words in text
        fired = set()
        for i, l in enumerate(active):
            triggers = l.get("trigger_keywords", []) or []
            title_words = re.findall(r'\w{4,}', (l.get("title") or "").lower())
            keys = [t.lower() for t in triggers] + title_words[:3]
            for k in keys:
                if k and k in all_text:
                    fired.add(i); break

        event_data.append({
            "name": d5["event"]["name"][:40],
            "delta": delta,
            "v4": a4, "v5": a5,
            "lessons_fired": fired,
        })

    # Per-lesson aggregate: in events where fired, что было с дельтой
    per_lesson = defaultdict(lambda: {"fired_events": 0, "delta_sum": 0.0,
                                       "wins": 0, "losses": 0})
    for ev in event_data:
        for li in ev["lessons_fired"]:
            per_lesson[li]["fired_events"] += 1
            per_lesson[li]["delta_sum"] += ev["delta"]
            if ev["delta"] > 5: per_lesson[li]["wins"] += 1
            elif ev["delta"] < -5: per_lesson[li]["losses"] += 1

    # Score = avg_delta when fired
    scored = []
    for i, l in enumerate(active):
        s = per_lesson.get(i, {})
        n = s.get("fired_events", 0)
        if n == 0:
            scored.append((i, l, 0.0, 0, 0, 0))
            continue
        avg = s["delta_sum"] / n
        scored.append((i, l, avg, n, s["wins"], s["losses"]))

    # Sort: most harmful first
    scored.sort(key=lambda x: x[2])

    print("=" * 100)
    print(f"{'#':>2} {'Avg Δ':>7} {'Fired':>6} {'W':>2} {'L':>2}  Title")
    print("=" * 100)
    for i, (idx, l, avg, n, w, lo) in enumerate(scored):
        title = l.get("title", "?")[:75]
        flag = "🟢" if avg > 3 else "🔴" if avg < -3 else "🟡" if n > 0 else "⚪"
        print(f"{flag} {idx:>2} {avg:>+6.1f}pp {n:>6} {w:>2} {lo:>2}  {title}")

    print()
    print("LEGEND: 🟢 helpful (avg Δ > +3pp)  🔴 harmful (avg Δ < -3pp)  🟡 neutral  ⚪ never fired")
    print()

    # Recommendations
    harmful = [s for s in scored if s[2] < -3 and s[3] >= 3]
    helpful = [s for s in scored if s[2] > 3 and s[3] >= 3]
    print(f"📌 Recommendation: deactivate {len(harmful)} harmful + keep {len(helpful)} clearly helpful")
    if harmful:
        print("\n🔴 DEACTIVATE candidates:")
        for idx, l, avg, n, w, lo in harmful:
            print(f"   #{idx}: {l['title'][:80]} (avg Δ {avg:+.1f}pp over {n} events)")
    if helpful:
        print("\n🟢 KEEP definitively:")
        for idx, l, avg, n, w, lo in helpful:
            print(f"   #{idx}: {l['title'][:80]} (avg Δ {avg:+.1f}pp over {n} events)")


if __name__ == "__main__":
    main()
