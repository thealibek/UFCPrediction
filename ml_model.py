"""Hybrid Prediction — Classical ML half.

XGBoost (с fallback на sklearn GradientBoostingClassifier если xgb не установлен)
на табличных фичах: разница метрик бойцов A−B + win-rates.

Тренируется на:
- Исторических боях из rag_seed (HISTORICAL_FIGHTS) — где оба бойца есть в БД
- Resolved предсказаниях из st.session_state.history

Возвращает калиброванные вероятности победы и метода.
Сохраняет важности фич — пользователь видит что влияет.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Backend selection: prefer XGBoost, fallback to sklearn
# ---------------------------------------------------------------------------
_BACKEND = None
try:
    import xgboost as xgb  # type: ignore
    _BACKEND = "xgboost"
except ImportError:
    try:
        from sklearn.ensemble import GradientBoostingClassifier  # type: ignore
        _BACKEND = "sklearn"
    except ImportError:
        _BACKEND = None


MODELS_DIR = Path("ml_models")
MODELS_DIR.mkdir(exist_ok=True)
WINNER_MODEL_PATH = MODELS_DIR / "winner_model.json"
METHOD_MODEL_PATH = MODELS_DIR / "method_model.json"
META_PATH = MODELS_DIR / "meta.json"

FEATURE_NAMES = [
    "age_diff", "slpm_diff", "sapm_diff", "stracc_diff", "strdef_diff",
    "tdavg_diff", "tddef_diff", "subavg_diff", "reach_diff", "height_diff",
    "winrate_a", "winrate_b", "exp_diff", "stance_match",
]
METHOD_CLASSES = ["KO/TKO", "Submission", "Decision"]


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

def _to_float(v, default=0.0) -> float:
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def _parse_record(record: str) -> tuple[int, int, int]:
    """Парсим '23-1-0' → (23, 1, 0)."""
    if not record:
        return (0, 0, 0)
    m = re.match(r"(\d+)\s*-\s*(\d+)(?:\s*-\s*(\d+))?", str(record))
    if not m:
        return (0, 0, 0)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0))


def _winrate(record: str) -> float:
    w, l, d = _parse_record(record)
    total = w + l + d
    return w / total if total > 0 else 0.5


def _exp(record: str) -> int:
    w, l, d = _parse_record(record)
    return w + l + d


def build_features(fa: dict, fb: dict) -> np.ndarray:
    """Вычисляем feature vector A vs B (разности метрик + winrates)."""
    feats = [
        _to_float(fa.get("age", 30)) - _to_float(fb.get("age", 30)),
        _to_float(fa.get("SLpM")) - _to_float(fb.get("SLpM")),
        _to_float(fa.get("SApM")) - _to_float(fb.get("SApM")),
        _to_float(fa.get("StrAcc")) - _to_float(fb.get("StrAcc")),
        _to_float(fa.get("StrDef")) - _to_float(fb.get("StrDef")),
        _to_float(fa.get("TDAvg")) - _to_float(fb.get("TDAvg")),
        _to_float(fa.get("TDDef")) - _to_float(fb.get("TDDef")),
        _to_float(fa.get("SubAvg")) - _to_float(fb.get("SubAvg")),
        _to_float(fa.get("reach")) - _to_float(fb.get("reach")),
        _to_float(fa.get("height")) - _to_float(fb.get("height")),
        _winrate(fa.get("record", "")),
        _winrate(fb.get("record", "")),
        _exp(fa.get("record", "")) - _exp(fb.get("record", "")),
        1.0 if fa.get("stance") == fb.get("stance") else 0.0,
    ]
    return np.array(feats, dtype=float)


# ---------------------------------------------------------------------------
# Training data assembly
# ---------------------------------------------------------------------------

def _method_to_class(method: str) -> int | None:
    """Маппинг строки метода в индекс класса."""
    if not method:
        return None
    m = method.lower()
    if "ko" in m or "tko" in m or "knockout" in m or "punches" in m or "kick" in m:
        return 0
    if "sub" in m or "submission" in m or "choke" in m or "armbar" in m or "tap" in m:
        return 1
    if "dec" in m or "decision" in m or "judges" in m:
        return 2
    return None


def assemble_training_data(fighters_db: list[dict],
                            historical_fights: list[dict],
                            resolved_history: list[dict] | None = None) -> dict:
    """Собираем (X, y_winner, y_method) из всех доступных источников.

    fighters_db: list of fighter dicts (нужен для look-up по имени)
    historical_fights: список из rag_seed.HISTORICAL_FIGHTS
    resolved_history: список prediction records со status='won'/'lost' и actual_winner

    Каждый бой даёт 2 строки (A vs B и B vs A), что удваивает датасет
    и убирает order bias.
    """
    by_name = {f["name"].lower(): f for f in fighters_db}

    X, y_win, y_method = [], [], []
    skipped = 0

    # 1) Исторические бои
    for fight in historical_fights or []:
        a_name = (fight.get("fighter_a") or "").lower()
        b_name = (fight.get("fighter_b") or "").lower()
        winner = (fight.get("winner") or "").lower()
        fa, fb = by_name.get(a_name), by_name.get(b_name)
        if not fa or not fb or not winner:
            skipped += 1
            continue
        a_won = 1 if winner == a_name else (0 if winner == b_name else None)
        if a_won is None:
            skipped += 1
            continue
        method_cls = _method_to_class(fight.get("method", ""))

        # A vs B
        X.append(build_features(fa, fb))
        y_win.append(a_won)
        y_method.append(method_cls if method_cls is not None else -1)

        # B vs A (mirror — увеличивает датасет, симметрия)
        X.append(build_features(fb, fa))
        y_win.append(1 - a_won)
        y_method.append(method_cls if method_cls is not None else -1)

    # 2) Resolved predictions
    for h in resolved_history or []:
        if h.get("status") not in ("won", "lost"):
            continue
        a_name = (h.get("fighter_a") or h.get("fa") or "").lower()
        b_name = (h.get("fighter_b") or h.get("fb") or "").lower()
        actual_w = (h.get("actual_winner") or "").lower()
        fa, fb = by_name.get(a_name), by_name.get(b_name)
        if not fa or not fb or not actual_w:
            continue
        a_won = 1 if a_name in actual_w or actual_w in a_name else (
            0 if b_name in actual_w or actual_w in b_name else None
        )
        if a_won is None:
            continue
        method_cls = _method_to_class(h.get("actual_method", ""))
        X.append(build_features(fa, fb))
        y_win.append(a_won)
        y_method.append(method_cls if method_cls is not None else -1)
        X.append(build_features(fb, fa))
        y_win.append(1 - a_won)
        y_method.append(method_cls if method_cls is not None else -1)

    return {
        "X": np.array(X) if X else np.zeros((0, len(FEATURE_NAMES))),
        "y_winner": np.array(y_win, dtype=int),
        "y_method": np.array(y_method, dtype=int),
        "n_samples": len(X),
        "skipped": skipped,
    }


# ---------------------------------------------------------------------------
# Train
# ---------------------------------------------------------------------------

def _make_classifier(n_classes: int = 2):
    """Создаёт классификатор. Auto-detect backend."""
    if _BACKEND == "xgboost":
        if n_classes == 2:
            return xgb.XGBClassifier(
                n_estimators=200, max_depth=4, learning_rate=0.08,
                subsample=0.85, colsample_bytree=0.85,
                eval_metric="logloss", use_label_encoder=False,
                random_state=42,
            )
        return xgb.XGBClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.08,
            objective="multi:softprob", num_class=n_classes,
            eval_metric="mlogloss", random_state=42,
        )
    if _BACKEND == "sklearn":
        return GradientBoostingClassifier(
            n_estimators=150, max_depth=3, learning_rate=0.08, random_state=42,
        )
    raise RuntimeError("Ни xgboost, ни sklearn не доступны. pip install xgboost scikit-learn")


def train_models(training: dict) -> dict:
    """Тренируем winner model + method model. Сохраняем на диск.

    Возвращает meta dict с информацией о тренировке.
    """
    if _BACKEND is None:
        raise RuntimeError("Нет ML-backend. pip install xgboost (или scikit-learn).")

    X = training["X"]
    y_win = training["y_winner"]
    y_method = training["y_method"]

    if len(X) < 6:
        raise RuntimeError(
            f"Слишком мало данных для тренировки: {len(X)} строк. "
            f"Нужно минимум 6 (3 уникальных боя). Добавь больше resolved предсказаний "
            f"или историю в rag_seed.HISTORICAL_FIGHTS."
        )

    # Winner model
    winner_clf = _make_classifier(n_classes=2)
    winner_clf.fit(X, y_win)
    train_acc_win = float(winner_clf.score(X, y_win))

    # Method model (только записи с известным методом)
    method_meta = {"trained": False, "n_samples": 0, "train_acc": None}
    method_clf = None
    method_mask = y_method >= 0
    if method_mask.sum() >= 6:
        method_clf = _make_classifier(n_classes=3)
        try:
            method_clf.fit(X[method_mask], y_method[method_mask])
            method_meta = {
                "trained": True,
                "n_samples": int(method_mask.sum()),
                "train_acc": float(method_clf.score(X[method_mask], y_method[method_mask])),
            }
        except Exception as e:
            method_meta["error"] = str(e)
            method_clf = None

    # Feature importance (winner model)
    fi = {}
    try:
        importances = winner_clf.feature_importances_
        fi = {FEATURE_NAMES[i]: float(importances[i]) for i in range(len(FEATURE_NAMES))}
    except Exception:
        pass

    # Save models
    if _BACKEND == "xgboost":
        winner_clf.save_model(str(WINNER_MODEL_PATH))
        if method_clf is not None:
            method_clf.save_model(str(METHOD_MODEL_PATH))
    else:
        # Pickle для sklearn
        import pickle
        with open(WINNER_MODEL_PATH.with_suffix(".pkl"), "wb") as f:
            pickle.dump(winner_clf, f)
        if method_clf is not None:
            with open(METHOD_MODEL_PATH.with_suffix(".pkl"), "wb") as f:
                pickle.dump(method_clf, f)

    meta = {
        "backend": _BACKEND,
        "n_samples": int(len(X)),
        "winner_train_accuracy": train_acc_win,
        "method": method_meta,
        "feature_importance": fi,
        "feature_names": FEATURE_NAMES,
        "method_classes": METHOD_CLASSES,
        "skipped_during_assembly": int(training.get("skipped", 0)),
    }
    META_PATH.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    return meta


# ---------------------------------------------------------------------------
# Load + Predict
# ---------------------------------------------------------------------------

_loaded = {"winner": None, "method": None, "meta": None}


def load_models() -> dict | None:
    """Грузим модели с диска. Возвращаем meta dict или None если нет."""
    if not META_PATH.exists():
        return None
    meta = json.loads(META_PATH.read_text())
    backend = meta.get("backend")

    try:
        if backend == "xgboost" and WINNER_MODEL_PATH.exists():
            wm = xgb.XGBClassifier()
            wm.load_model(str(WINNER_MODEL_PATH))
            _loaded["winner"] = wm
            if METHOD_MODEL_PATH.exists():
                mm = xgb.XGBClassifier()
                mm.load_model(str(METHOD_MODEL_PATH))
                _loaded["method"] = mm
        elif backend == "sklearn":
            import pickle
            wp = WINNER_MODEL_PATH.with_suffix(".pkl")
            if wp.exists():
                with open(wp, "rb") as f:
                    _loaded["winner"] = pickle.load(f)
            mp = METHOD_MODEL_PATH.with_suffix(".pkl")
            if mp.exists():
                with open(mp, "rb") as f:
                    _loaded["method"] = pickle.load(f)
        _loaded["meta"] = meta
        return meta
    except Exception as e:
        _loaded["meta"] = {**meta, "load_error": str(e)}
        return _loaded["meta"]


def predict_ml(fa: dict, fb: dict) -> dict:
    """ML-предсказание боя A vs B. Returns:
       {
         'win_prob_a': 0.62, 'win_prob_b': 0.38,
         'method_probs': {'KO/TKO': 0.4, 'Submission': 0.15, 'Decision': 0.45},
         'features': {feature_name: value},
         'available': True/False, 'reason': 'no_model'/None,
       }
    """
    if _loaded["winner"] is None:
        meta = load_models()
        if meta is None or _loaded["winner"] is None:
            return {"available": False, "reason": "no_trained_model"}

    feats = build_features(fa, fb).reshape(1, -1)
    feat_dict = {FEATURE_NAMES[i]: float(feats[0, i]) for i in range(len(FEATURE_NAMES))}

    try:
        proba = _loaded["winner"].predict_proba(feats)[0]
        # proba[1] = prob A wins (label=1)
        win_a = float(proba[1])
    except Exception as e:
        return {"available": False, "reason": f"predict_error: {e}"}

    method_probs = None
    if _loaded["method"] is not None:
        try:
            mp = _loaded["method"].predict_proba(feats)[0]
            method_probs = {METHOD_CLASSES[i]: float(mp[i]) for i in range(len(METHOD_CLASSES))}
        except Exception:
            method_probs = None

    return {
        "available": True,
        "win_prob_a": win_a,
        "win_prob_b": 1.0 - win_a,
        "method_probs": method_probs,
        "features": feat_dict,
    }


# ---------------------------------------------------------------------------
# Hybrid combine
# ---------------------------------------------------------------------------

def combine_hybrid(ml_pred: dict, llm_win_prob: float | None,
                    ml_weight: float = 0.4) -> dict:
    """Объединяем ML и LLM вероятности взвешенным средним.

    Args:
      ml_pred: результат predict_ml() (для бойца A)
      llm_win_prob: вероятность победы предсказанного бойца от LLM (0-1).
                    ВАЖНО: LLM-prob — для предсказанного победителя, не обязательно для A.
                    Передавай уже как prob для A.
      ml_weight: вес ML (0..1). LLM-вес = 1 - ml_weight.

    Returns:
      {'final_prob_a': 0.58, 'ml_prob_a': 0.62, 'llm_prob_a': 0.55,
       'ml_weight': 0.4, 'llm_weight': 0.6}
    """
    ml_p = ml_pred.get("win_prob_a") if ml_pred.get("available") else None

    if ml_p is None and llm_win_prob is None:
        return {"final_prob_a": None, "ml_prob_a": None, "llm_prob_a": None,
                "ml_weight": 0.0, "llm_weight": 0.0}
    if ml_p is None:
        return {"final_prob_a": llm_win_prob, "ml_prob_a": None,
                "llm_prob_a": llm_win_prob, "ml_weight": 0.0, "llm_weight": 1.0}
    if llm_win_prob is None:
        return {"final_prob_a": ml_p, "ml_prob_a": ml_p, "llm_prob_a": None,
                "ml_weight": 1.0, "llm_weight": 0.0}

    ml_w = max(0.0, min(1.0, ml_weight))
    llm_w = 1.0 - ml_w
    final = ml_w * ml_p + llm_w * llm_win_prob
    return {
        "final_prob_a": final,
        "ml_prob_a": ml_p,
        "llm_prob_a": llm_win_prob,
        "ml_weight": ml_w,
        "llm_weight": llm_w,
    }


def get_meta() -> dict | None:
    if _loaded["meta"] is None:
        load_models()
    return _loaded["meta"]


def is_available() -> bool:
    return _BACKEND is not None
