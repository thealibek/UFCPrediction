"""Model Health & Auto-Retrain.

Отслеживает деградацию модели по скользящим окнам Brier/accuracy/ROI,
генерирует алерты и триггерит автопереобучение ML когда drift превышает порог.

Работает поверх history.json (разрешённые прогнозы) и последнего снапшота
метаданных ML-модели (`ml_models/meta.json`).
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

from backtest import brier, accuracy, roi, _resolved, _prob, _winner_correct, _dt

HEALTH_STATE_FILE = Path("model_health_state.json")


# ---------------------------------------------------------------------------
# Thresholds (можно тюнить)
# ---------------------------------------------------------------------------

THRESHOLDS = {
    "brier_warn": 0.23,          # >= → warn
    "brier_critical": 0.26,      # >= → critical
    "brier_drift_pct": 0.20,     # свежее окно хуже baseline на >20% → drift
    "accuracy_warn_pct": 55.0,   # < → warn
    "accuracy_critical_pct": 50.0,
    "roi_warn_pct": -5.0,        # < → warn
    "roi_critical_pct": -15.0,
    "min_window": 10,            # минимум боёв в окне для оценки
    "retrain_cooldown_hours": 24,
}


# ---------------------------------------------------------------------------
# Rolling metrics
# ---------------------------------------------------------------------------

def _resolved_sorted(history: list[dict]) -> list[dict]:
    return sorted([h for h in history if _resolved(h)],
                  key=lambda x: _dt(x) or datetime.min)


def rolling_windows(history: list[dict], window: int = 20) -> dict:
    """Возвращает baseline (первые 50%) vs recent (последнее окно)."""
    items = _resolved_sorted(history)
    if len(items) < max(THRESHOLDS["min_window"], window):
        return {"insufficient": True, "n": len(items)}

    recent = items[-window:]
    # baseline — всё кроме последнего окна
    baseline = items[:-window] or items

    _, _, acc_r = accuracy(recent)
    _, _, acc_b = accuracy(baseline)
    b_r = brier(recent); b_b = brier(baseline)
    roi_r = roi(recent); roi_b = roi(baseline)

    return {
        "insufficient": False,
        "n_total": len(items),
        "recent": {
            "n": len(recent),
            "accuracy_%": acc_r,
            "brier": b_r,
            "roi_pct": roi_r["roi_pct"],
            "n_bets": roi_r["n_bets"],
        },
        "baseline": {
            "n": len(baseline),
            "accuracy_%": acc_b,
            "brier": b_b,
            "roi_pct": roi_b["roi_pct"],
            "n_bets": roi_b["n_bets"],
        },
    }


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

@dataclass
class HealthAlert:
    level: str          # "info" | "warn" | "critical"
    code: str
    message: str
    value: float | None = None


def evaluate_health(history: list[dict], window: int = 20) -> dict:
    """Возвращает diagnostics + список алертов + флаг should_retrain."""
    stats = rolling_windows(history, window=window)
    alerts: list[HealthAlert] = []
    if stats.get("insufficient"):
        return {
            "stats": stats,
            "alerts": [asdict(HealthAlert("info", "insufficient_data",
                f"Недостаточно разрешённых прогнозов для оценки health. "
                f"Нужно минимум {max(THRESHOLDS['min_window'], window)}, есть {stats.get('n', 0)}."))],
            "should_retrain": False,
            "status": "unknown",
        }

    r = stats["recent"]; b = stats["baseline"]

    # Brier absolute
    if r["brier"] is not None:
        if r["brier"] >= THRESHOLDS["brier_critical"]:
            alerts.append(HealthAlert("critical", "brier_critical",
                f"Brier на последнем окне {r['brier']:.3f} — критически высокий.", r["brier"]))
        elif r["brier"] >= THRESHOLDS["brier_warn"]:
            alerts.append(HealthAlert("warn", "brier_warn",
                f"Brier {r['brier']:.3f} выше порога {THRESHOLDS['brier_warn']}.", r["brier"]))

    # Brier drift vs baseline
    if r["brier"] is not None and b["brier"] is not None and b["brier"] > 0:
        drift = (r["brier"] - b["brier"]) / b["brier"]
        if drift > THRESHOLDS["brier_drift_pct"]:
            alerts.append(HealthAlert("critical", "brier_drift",
                f"Brier ухудшился на {drift*100:.0f}% vs baseline "
                f"({b['brier']:.3f} → {r['brier']:.3f}).", drift))

    # Accuracy
    if r["accuracy_%"] is not None:
        if r["accuracy_%"] < THRESHOLDS["accuracy_critical_pct"]:
            alerts.append(HealthAlert("critical", "accuracy_critical",
                f"Accuracy {r['accuracy_%']:.1f}% ниже {THRESHOLDS['accuracy_critical_pct']}%.",
                r["accuracy_%"]))
        elif r["accuracy_%"] < THRESHOLDS["accuracy_warn_pct"]:
            alerts.append(HealthAlert("warn", "accuracy_warn",
                f"Accuracy {r['accuracy_%']:.1f}% ниже {THRESHOLDS['accuracy_warn_pct']}%.",
                r["accuracy_%"]))

    # ROI (если были ставки)
    if r.get("n_bets", 0) >= 5 and r["roi_pct"] is not None:
        if r["roi_pct"] < THRESHOLDS["roi_critical_pct"]:
            alerts.append(HealthAlert("critical", "roi_critical",
                f"ROI {r['roi_pct']:+.1f}% ниже {THRESHOLDS['roi_critical_pct']}%.",
                r["roi_pct"]))
        elif r["roi_pct"] < THRESHOLDS["roi_warn_pct"]:
            alerts.append(HealthAlert("warn", "roi_warn",
                f"ROI {r['roi_pct']:+.1f}% в минусе.", r["roi_pct"]))

    # Решение о retrain: любой critical → yes
    should_retrain = any(a.level == "critical" for a in alerts)
    status = (
        "critical" if any(a.level == "critical" for a in alerts)
        else "warn" if any(a.level == "warn" for a in alerts)
        else "healthy"
    )

    return {
        "stats": stats,
        "alerts": [asdict(a) for a in alerts],
        "should_retrain": should_retrain,
        "status": status,
    }


# ---------------------------------------------------------------------------
# Retrain state (cooldown)
# ---------------------------------------------------------------------------

def _load_state() -> dict:
    if HEALTH_STATE_FILE.exists():
        try:
            return json.loads(HEALTH_STATE_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_state(state: dict) -> None:
    try:
        HEALTH_STATE_FILE.write_text(json.dumps(state, indent=2))
    except Exception:
        pass


def can_retrain_now() -> tuple[bool, str]:
    state = _load_state()
    last = state.get("last_retrain_ts")
    cooldown_s = THRESHOLDS["retrain_cooldown_hours"] * 3600
    if last and (time.time() - last) < cooldown_s:
        left_h = (cooldown_s - (time.time() - last)) / 3600
        return False, f"Cooldown: следующий retrain через {left_h:.1f}ч."
    return True, "OK"


def mark_retrained(meta: dict | None = None) -> None:
    state = _load_state()
    state["last_retrain_ts"] = time.time()
    state["last_retrain_iso"] = datetime.now().isoformat(timespec="seconds")
    if meta:
        state["last_retrain_meta"] = meta
    _save_state(state)


def auto_retrain_if_needed(history: list[dict],
                           train_fn,
                           force: bool = False,
                           window: int = 20) -> dict:
    """Проверяет health и триггерит retrain при drift.

    Args:
      history: список всех прогнозов
      train_fn: callable() → dict с результатом обучения (обычно
                лямбда, которая зовёт assemble_training_data + train_models)
      force: игнорировать health-check (но уважать cooldown)
    """
    health = evaluate_health(history, window=window)
    if not force and not health["should_retrain"]:
        return {"retrained": False, "reason": "health OK", "health": health}

    ok, msg = can_retrain_now()
    if not ok:
        return {"retrained": False, "reason": msg, "health": health}

    try:
        meta = train_fn() or {}
        mark_retrained(meta)
        return {"retrained": True, "meta": meta, "health": health}
    except Exception as e:
        return {"retrained": False, "reason": f"train failed: {e}", "health": health}
