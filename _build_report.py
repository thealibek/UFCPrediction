"""Генерит RESULTS.md с side-by-side V4 vs V5 + детали по ивентам."""
from __future__ import annotations
import json
from pathlib import Path


def load_runs(suffix: str):
    """Возвращает {espn_id: dict} для всех файлов с suffix-ом."""
    out = {}
    for p in sorted(Path("blind_tests").glob(f"*{suffix}*.json")):
        if "topuria" in p.name.lower() or "freedom" in p.name.lower():
            continue  # upcoming
        try:
            d = json.loads(p.read_text())
        except Exception:
            continue
        eid = str(d.get("event", {}).get("espn_id") or p.stem)
        out[eid] = d
    return out


def agg(runs):
    n_ev = total_g = total_c = 0
    total_b = 0.0
    for d in runs.values():
        s = d.get("summary", {})
        if not s.get("n_graded"):
            continue
        n_ev += 1
        g = s["n_graded"]
        total_g += g
        total_c += round(s["accuracy_%"] * g / 100)
        total_b += s["brier"] * g
    if total_g == 0:
        return 0, 0, 0, 0.0
    return n_ev, total_g, total_c, total_b / total_g


def main():
    v4 = load_runs("-v4-mass")
    v5 = load_runs("-v5-")

    v4_ev, v4_g, v4_c, v4_b = agg(v4)
    v5_ev, v5_g, v5_c, v5_b = agg(v5)
    v4_acc = (v4_c / v4_g * 100) if v4_g else 0
    v5_acc = (v5_c / v5_g * 100) if v5_g else 0

    md = []
    md.append("# 🥊 UFC Predictor — V4 vs V5 Results\n")
    md.append(f"_Generated: {__import__('datetime').datetime.now():%Y-%m-%d %H:%M}_\n")
    md.append("\n## 📊 Aggregate Summary\n")
    md.append("| Version | Events | Fights Graded | Correct | Accuracy | Brier |")
    md.append("|---|---:|---:|---:|---:|---:|")
    md.append(f"| **V4** (10 lessons, baseline) | {v4_ev} | {v4_g} | {v4_c} | **{v4_acc:.1f}%** | {v4_b:.3f} |")
    md.append(f"| **V5** (20 lessons + motivation) | {v5_ev} | {v5_g} | {v5_c} | **{v5_acc:.1f}%** | {v5_b:.3f} |")
    delta_acc = v5_acc - v4_acc
    delta_b = v5_b - v4_b
    md.append(f"| **Δ** | — | — | — | **{delta_acc:+.1f}pp** | **{delta_b:+.3f}** |")

    md.append("\n## 📋 Per-Event Comparison\n")
    md.append("| Date | Event | V4 Acc | V5 Acc | Δ | V4 Brier | V5 Brier |")
    md.append("|---|---|---:|---:|---:|---:|---:|")

    all_eids = sorted(set(v4) | set(v5),
                       key=lambda e: (v4.get(e) or v5.get(e))["event"]["date"])
    for eid in all_eids:
        d4 = v4.get(eid); d5 = v5.get(eid)
        base = d4 or d5
        date = base["event"]["date"][:10]
        name = base["event"]["name"].split(" [")[0][:45]
        s4 = (d4 or {}).get("summary", {}) if d4 else {}
        s5 = (d5 or {}).get("summary", {}) if d5 else {}
        a4 = s4.get("accuracy_%"); a5 = s5.get("accuracy_%")
        b4 = s4.get("brier"); b5 = s5.get("brier")
        delta = (a5 - a4) if (a4 and a5) else None

        a4_s = f"{a4:.1f}%" if a4 is not None else "—"
        a5_s = f"{a5:.1f}%" if a5 is not None else "—"
        d_s = f"{delta:+.1f}pp" if delta is not None else "—"
        b4_s = f"{b4:.3f}" if b4 is not None else "—"
        b5_s = f"{b5:.3f}" if b5 is not None else "—"
        # Highlight winners
        if delta is not None:
            if delta > 5: d_s = f"🟢 {d_s}"
            elif delta < -5: d_s = f"🔴 {d_s}"
        md.append(f"| {date} | {name} | {a4_s} | {a5_s} | {d_s} | {b4_s} | {b5_s} |")

    # Lessons used
    md.append("\n## 📖 Lessons Library (20 active)\n")
    try:
        from lessons import load_lessons
        for i, l in enumerate(load_lessons(), 1):
            if not l.get("active", True):
                continue
            md.append(f"**{i}. {l['title']}**")
            md.append(f"  _src: {l.get('source','manual')}_  ")
            md.append(f"  {l['body'][:200]}{'…' if len(l['body']) > 200 else ''}")
            md.append("")
    except Exception as e:
        md.append(f"_failed to load lessons: {e}_")

    # Misses analysis
    md.append("\n## ❌ Top V5 Overconfident Misses\n")
    md.append("| Date | Event | Predicted | Conf | Actual |")
    md.append("|---|---|---|---:|---|")
    misses = []
    for d in v5.values():
        for r in d.get("predictions", []):
            if r.get("graded") and not r.get("correct") and (r.get("win_prob") or 0) >= 0.65:
                misses.append({
                    "date": d["event"]["date"][:10],
                    "event": d["event"]["name"].split(" [")[0][:35],
                    "pred": r.get("predicted_winner",""),
                    "conf": (r.get("win_prob") or 0) * 100,
                    "actual": r.get("actual_winner",""),
                })
    misses.sort(key=lambda x: -x["conf"])
    for m in misses[:20]:
        md.append(f"| {m['date']} | {m['event']} | {m['pred']} | {m['conf']:.0f}% | {m['actual']} |")

    out_path = Path("RESULTS.md")
    out_path.write_text("\n".join(md), encoding="utf-8")
    print(f"✅ Written: {out_path}")
    print(f"\nSummary: V4={v4_acc:.1f}% → V5={v5_acc:.1f}% (Δ {delta_acc:+.1f}pp)")
    print(f"         Brier {v4_b:.3f} → {v5_b:.3f}")

    # Also JSON
    json_out = Path("RESULTS.json")
    json_out.write_text(json.dumps({
        "v4": {"events": v4_ev, "graded": v4_g, "correct": v4_c,
               "accuracy_%": round(v4_acc, 2), "brier": round(v4_b, 3)},
        "v5": {"events": v5_ev, "graded": v5_g, "correct": v5_c,
               "accuracy_%": round(v5_acc, 2), "brier": round(v5_b, 3)},
        "delta": {"accuracy_pp": round(delta_acc, 2),
                  "brier_change": round(delta_b, 3)},
    }, indent=2))
    print(f"✅ Written: {json_out}")


if __name__ == "__main__":
    main()
