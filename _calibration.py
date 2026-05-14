"""Calibration analysis на текущих blind-test results.

Считает:
1. Per-confidence-bin accuracy (reliability diagram)
2. Brier (overall + per bin)
3. Log-loss
4. ROC-AUC
5. Per-version comparison (V4 vs V5)
6. Per-division accuracy
7. High-conf (>=70%) vs low-conf (<60%)
"""
from __future__ import annotations
import json, math
from pathlib import Path
from collections import defaultdict


def collect_predictions(suffix: str):
    """Возвращает list of (predicted_winner_correct: 0/1, win_prob: float, weight_class: str)."""
    out = []
    for p in sorted(Path("blind_tests").glob(f"*{suffix}*.json")):
        if "topuria" in p.name.lower(): continue
        try:
            d = json.loads(p.read_text())
        except Exception:
            continue
        for r in d.get("predictions", []):
            if not r.get("graded"): continue
            wp = r.get("win_prob")
            if wp is None: continue
            correct = 1 if r.get("correct") else 0
            out.append({
                "correct": correct,
                "wp": wp,
                "wc": r.get("weight_class") or "Bout",
                "fav": r.get("predicted_winner"),
                "actual": r.get("actual_winner"),
            })
    return out


def reliability_bins(preds, n_bins=7):
    """Делит [0.5, 1.0] на bins, считает accuracy в каждом."""
    bins = [(0.50, 0.55), (0.55, 0.60), (0.60, 0.65), (0.65, 0.70),
            (0.70, 0.75), (0.75, 0.80), (0.80, 1.00)]
    out = []
    for lo, hi in bins:
        sub = [p for p in preds if lo <= p["wp"] < hi]
        if not sub:
            out.append((lo, hi, 0, 0, None, None)); continue
        n = len(sub)
        correct = sum(p["correct"] for p in sub)
        acc = correct / n
        avg_conf = sum(p["wp"] for p in sub) / n
        out.append((lo, hi, n, correct, acc, avg_conf))
    return out


def brier(preds):
    if not preds: return None
    return sum((p["wp"] - p["correct"])**2 for p in preds) / len(preds)


def log_loss(preds, eps=1e-9):
    if not preds: return None
    s = 0.0
    for p in preds:
        wp = max(min(p["wp"], 1-eps), eps)
        s += -(p["correct"] * math.log(wp) + (1-p["correct"]) * math.log(1-wp))
    return s / len(preds)


def roc_auc(preds):
    """Простой Mann-Whitney U-based AUC."""
    pos = [p["wp"] for p in preds if p["correct"]]
    neg = [p["wp"] for p in preds if not p["correct"]]
    if not pos or not neg: return None
    n = 0; total = 0
    for x in pos:
        for y in neg:
            total += 1
            if x > y: n += 1
            elif x == y: n += 0.5
    return n / total


def divisions_breakdown(preds):
    by_div = defaultdict(list)
    for p in preds:
        wc = p["wc"] or "Bout"
        by_div[wc].append(p)
    out = []
    for wc, sub in sorted(by_div.items()):
        if len(sub) < 5: continue
        acc = sum(s["correct"] for s in sub) / len(sub)
        out.append((wc, len(sub), acc))
    return out


def main():
    print("=" * 80)
    print("CALIBRATION ANALYSIS — UFC Predictor V4 vs V5")
    print("=" * 80)

    versions = {
        "V4": collect_predictions("-v4-mass"),
        "V5": collect_predictions("-v5-"),
    }

    # Combined
    all_preds = versions["V4"] + versions["V5"]
    versions["BOTH"] = all_preds

    for vname, preds in versions.items():
        print(f"\n## {vname} — N={len(preds)} predictions")
        if not preds:
            print("  (no data)")
            continue
        acc = sum(p["correct"] for p in preds) / len(preds)
        b = brier(preds)
        ll = log_loss(preds)
        auc = roc_auc(preds)

        print(f"  Accuracy: {acc*100:.2f}%")
        print(f"  Brier:    {b:.3f}")
        print(f"  Log-loss: {ll:.3f}")
        print(f"  ROC-AUC:  {auc:.3f}" if auc else "  ROC-AUC:  —")

    print("\n" + "=" * 80)
    print("RELIABILITY DIAGRAM (V4 + V5 combined)")
    print("=" * 80)
    print(f"{'Confidence':<14} {'N':>5} {'Correct':>8} {'Real Acc':>10} {'Avg Conf':>10} {'Bias':>9}")
    bins = reliability_bins(all_preds)
    for lo, hi, n, c, acc, avg_c in bins:
        if n == 0:
            print(f"{int(lo*100)}-{int(hi*100)}%      {n:>5}  —")
            continue
        bias = avg_c - acc
        flag = "✅" if abs(bias) < 0.05 else "⚠️" if abs(bias) < 0.10 else "🔴"
        print(f"{int(lo*100)}-{int(hi*100)}%        {n:>5} {c:>8} {acc*100:>9.1f}% {avg_c*100:>9.1f}% {bias*100:+8.1f}pp {flag}")

    print("\n  Bias = Avg Conf - Real Acc.")
    print("  Положительный = overconfident (модель завышает), Отрицательный = underconfident.")

    # By confidence threshold
    print("\n" + "=" * 80)
    print("HIGH-CONFIDENCE vs LOW-CONFIDENCE BUCKETS")
    print("=" * 80)
    for thr_name, lo, hi in [
        ("HIGH (≥70%)", 0.70, 1.01),
        ("MID  (60-70%)", 0.60, 0.70),
        ("LOW  (50-60%)", 0.50, 0.60),
    ]:
        sub = [p for p in all_preds if lo <= p["wp"] < hi]
        if not sub:
            print(f"  {thr_name}: (no data)"); continue
        acc = sum(s["correct"] for s in sub) / len(sub)
        avg_c = sum(s["wp"] for s in sub) / len(sub)
        print(f"  {thr_name}: N={len(sub):>3}  Acc={acc*100:.1f}%  AvgConf={avg_c*100:.1f}%  Bias={(avg_c-acc)*100:+.1f}pp")

    # Per-division
    print("\n" + "=" * 80)
    print("BY DIVISION (V4+V5 combined, N>=5)")
    print("=" * 80)
    for wc, n, acc in divisions_breakdown(all_preds):
        print(f"  {wc:<35} N={n:>3}  Acc={acc*100:.1f}%")

    # Recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS FOR V6")
    print("=" * 80)
    overconf = [b for b in bins if b[4] is not None and b[5] - b[4] > 0.05 and b[2] >= 5]
    if overconf:
        print(f"  🔴 {len(overconf)} bins показывают overconfidence (avg_conf > real_acc на 5+pp)")
        for lo, hi, n, c, acc, avg_c in overconf:
            print(f"     {int(lo*100)}-{int(hi*100)}%: модель говорит {avg_c*100:.0f}% но реально побеждаем {acc*100:.0f}%  → нужно сжать confidence")
    else:
        print("  ✅ Calibration выглядит OK (overconfidence нет)")

    print()


if __name__ == "__main__":
    main()
