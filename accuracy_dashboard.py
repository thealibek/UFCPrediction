"""Prediction Tracking & Accuracy Dashboard.

Полноценный модуль аналитики точности модели:
- Hero metrics (точность, Brier, кол-во)
- Accuracy over time (rolling window) — Plotly
- Accuracy by bet type (Moneyline / Method / Confidence bands)
- Weak spots — где модель чаще ошибается (weight class / method / confidence)
- Calibration chart + per-bucket таблица
- Фильтры + таблица + CSV export
- Manual marking (зашло / не зашло / метод / раунд)
- Batch auto-resolve через ESPN
- Edit/delete записей

Дизайн: модуль принимает все callbacks/utility функции через параметры,
чтобы не было циклических импортов с app.py.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# ---------------------------------------------------------------------------
# Helpers (без зависимости от app.py)
# ---------------------------------------------------------------------------

def _predicted_method(h: dict) -> str | None:
    """argmax(ko, sub, dec) → 'KO/TKO' | 'Submission' | 'Decision' | None."""
    methods = [
        ("KO/TKO", h.get("ko_prob") or 0),
        ("Submission", h.get("sub_prob") or 0),
        ("Decision", h.get("dec_prob") or 0),
    ]
    if not any(m[1] for m in methods):
        return None
    return max(methods, key=lambda x: x[1])[0]


def _actual_method_class(actual_method: str) -> str | None:
    """Нормализуем строку метода → класс."""
    if not actual_method:
        return None
    m = actual_method.lower()
    if "ko" in m or "tko" in m or "knock" in m or "kick" in m or "punch" in m:
        return "KO/TKO"
    if "sub" in m or "choke" in m or "armbar" in m or "tap" in m:
        return "Submission"
    if "dec" in m or "judge" in m:
        return "Decision"
    return None


def _safe_dt(h: dict) -> datetime | None:
    ts = h.get("ts") or h.get("timestamp") or ""
    try:
        return datetime.fromisoformat(ts.replace("Z", ""))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

def accuracy_over_time(history: list[dict], window: int = 10) -> pd.DataFrame:
    """Rolling accuracy по resolved прогнозам, отсортированным по времени."""
    resolved = [h for h in history if h.get("status") in ("won", "lost")]
    resolved.sort(key=lambda h: _safe_dt(h) or datetime.min)
    if not resolved:
        return pd.DataFrame()
    rows = []
    correct_so_far = 0
    last_n = []
    for i, h in enumerate(resolved, start=1):
        is_correct = 1 if h["status"] == "won" else 0
        correct_so_far += is_correct
        last_n.append(is_correct)
        if len(last_n) > window:
            last_n.pop(0)
        rows.append({
            "n": i,
            "date": _safe_dt(h),
            "cumulative_acc": correct_so_far / i,
            "rolling_acc": sum(last_n) / len(last_n),
            "fight": f"{h.get('fa','?')} vs {h.get('fb','?')}",
        })
    return pd.DataFrame(rows)


def accuracy_by_bet_type(history: list[dict]) -> dict:
    """Метрики по типам ставок.
    Returns: {moneyline: {correct, total, acc}, method: {...}}
    """
    out = {"moneyline": {"correct": 0, "total": 0},
           "method": {"correct": 0, "total": 0}}
    for h in history:
        if h.get("status") not in ("won", "lost"):
            continue
        # Moneyline = базовая accuracy
        out["moneyline"]["total"] += 1
        if h["status"] == "won":
            out["moneyline"]["correct"] += 1
        # Method
        pred_m = _predicted_method(h)
        actual_m = _actual_method_class(h.get("actual_method", ""))
        if pred_m and actual_m:
            out["method"]["total"] += 1
            if pred_m == actual_m:
                out["method"]["correct"] += 1
    for k in out:
        t = out[k]["total"]
        out[k]["acc"] = (out[k]["correct"] / t) if t else None
    return out


def accuracy_by_confidence(history: list[dict], bands: list[tuple] | None = None) -> list[dict]:
    """Группировка по диапазонам уверенности → win rate."""
    bands = bands or [(0.50, 0.60), (0.60, 0.70), (0.70, 0.80), (0.80, 1.01)]
    out = []
    for lo, hi in bands:
        items = [
            h for h in history
            if h.get("status") in ("won", "lost")
            and h.get("win_prob") is not None
            and lo <= h["win_prob"] < hi
        ]
        wins = sum(1 for h in items if h["status"] == "won")
        out.append({
            "band": f"{int(lo*100)}-{int(hi*100)}%",
            "n": len(items),
            "wins": wins,
            "win_rate": wins / len(items) if items else None,
        })
    return out


def weak_spots(history: list[dict]) -> dict:
    """Где модель чаще промахивается. Группировка по division / method / confidence."""
    resolved = [h for h in history if h.get("status") in ("won", "lost")]

    def group_acc(items, key_fn):
        groups: dict[str, list] = {}
        for h in items:
            k = key_fn(h) or "—"
            groups.setdefault(k, []).append(h)
        out = []
        for k, lst in groups.items():
            wins = sum(1 for x in lst if x["status"] == "won")
            out.append({
                "key": k, "n": len(lst), "wins": wins,
                "acc": wins / len(lst) if lst else None,
            })
        # Сортируем по accuracy asc (худшие сверху), нужно минимум 2 прогноза
        return sorted([x for x in out if x["n"] >= 2], key=lambda x: x["acc"] or 0)

    by_wc = group_acc(resolved,
        lambda h: h.get("weight_class") or h.get("ctx", {}).get("division"))
    by_pred_method = group_acc(resolved, _predicted_method)
    by_rag = group_acc(resolved, lambda h: "RAG ON" if h.get("rag_used") else "RAG OFF")

    return {
        "by_weight_class": by_wc,
        "by_predicted_method": by_pred_method,
        "by_rag_usage": by_rag,
    }


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

def render_accuracy_dashboard(*,
    history: list[dict],
    persist_history,
    history_stats_fn,
    compute_brier_score_fn,
    calibration_buckets_fn,
    auto_resolve_fn,
    get_live_events_fn,
    theme: dict,
):
    """Главная render-функция. Все зависимости приходят явно через параметры.

    theme: {'UFC_RED', 'BG', 'TEXT', 'MUTED', 'BORDER'}
    """
    UFC_RED = theme["UFC_RED"]
    BG = theme["BG"]
    TEXT = theme["TEXT"]
    MUTED = theme["MUTED"]

    st.markdown("## 📚 Prediction Tracking & Accuracy")
    st.caption(
        "Каждый прогноз автоматически сохраняется. Здесь — точность модели, калибровка, "
        "слабые места и ROI. Это сердце трекинга."
    )

    # ============================================================
    # HERO METRICS
    # ============================================================
    stats = history_stats_fn()
    brier = compute_brier_score_fn(history)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("📋 Всего", len(history))
    m2.metric("✅ Зашло", stats["won"])
    m3.metric("❌ Не зашло", stats["lost"])
    m4.metric("🎯 Accuracy",
              f"{stats['accuracy']:.1f}%" if stats["accuracy"] is not None else "—",
              help="% правильных прогнозов победителя.")
    if brier is not None:
        brier_emoji = "🟢" if brier < 0.18 else "🟡" if brier < 0.25 else "🔴"
        m5.metric(f"{brier_emoji} Brier", f"{brier:.3f}",
                  help="0=идеал, 0.25=случайно. Меньше — лучше калибровка.")
    else:
        m5.metric("Brier", "—",
                  help="Появится после разрешённых прогнозов с win_prob.")

    # ============================================================
    # QUICK ACTIONS
    # ============================================================
    st.markdown("---")
    ac1, ac2, ac3 = st.columns([2, 2, 1])
    if ac1.button("🔄 Отметить все завершённые бои (ESPN auto-resolve)",
                   use_container_width=True):
        try:
            with st.spinner("Запрос ESPN..."):
                espn_events = get_live_events_fn(force_refresh=True)
                n = auto_resolve_fn(espn_events)
            if n > 0:
                st.success(f"✅ Резолвнуто {n} прогноз(ов)")
                st.rerun()
            else:
                st.info("Нет завершённых боёв для авто-резолва.")
        except Exception as e:
            st.error(f"ESPN недоступен: {e}")

    if ac2.button("⬇️ Экспорт всей истории в CSV", use_container_width=True):
        st.session_state["_csv_export_request"] = True

    if not history:
        st.info("Пока пусто. Сделай первый прогноз во вкладке 🔮 Predictor — "
                "он автоматически попадёт сюда.")
        return

    # ============================================================
    # ACCURACY OVER TIME
    # ============================================================
    st.markdown("---")
    st.markdown("### 📈 Точность по времени")
    aot_df = accuracy_over_time(history, window=10)
    if len(aot_df) >= 2:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=aot_df["n"], y=aot_df["cumulative_acc"] * 100,
            mode="lines+markers", name="Cumulative accuracy",
            line=dict(color="#000000", width=2),
        ))
        fig.add_trace(go.Scatter(
            x=aot_df["n"], y=aot_df["rolling_acc"] * 100,
            mode="lines", name="Rolling-10 accuracy",
            line=dict(color=UFC_RED, width=3, dash="solid"),
        ))
        fig.add_hline(y=50, line_dash="dot", line_color="#16a34a",
                      annotation_text="Coin flip (50%)",
                      annotation_position="bottom right")
        fig.update_layout(
            xaxis=dict(title="# resolved prediction", gridcolor="#eee"),
            yaxis=dict(title="Accuracy %", range=[0, 105], gridcolor="#eee"),
            paper_bgcolor=BG, plot_bgcolor=BG,
            font=dict(color=TEXT), height=340, margin=dict(t=10),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("Минимум 2 разрешённых прогноза нужно для графика.")

    # ============================================================
    # ACCURACY BY BET TYPE
    # ============================================================
    st.markdown("### 🎯 Точность по типам ставок")
    bet_acc = accuracy_by_bet_type(history)
    bc1, bc2 = st.columns(2)
    ml = bet_acc["moneyline"]
    bc1.metric(
        "🥊 Moneyline (победитель)",
        f"{ml['acc']*100:.1f}%" if ml["acc"] is not None else "—",
        delta=f"{ml['correct']}/{ml['total']}",
    )
    mt = bet_acc["method"]
    bc2.metric(
        "🥋 Method (KO/Sub/Dec)",
        f"{mt['acc']*100:.1f}%" if mt["acc"] is not None else "—",
        delta=f"{mt['correct']}/{mt['total']}",
    )

    # Confidence bands
    st.markdown("**📊 Win rate по диапазонам уверенности**")
    conf = accuracy_by_confidence(history)
    conf_df = pd.DataFrame([
        {
            "Диапазон": c["band"],
            "Прогнозов": c["n"],
            "Победы": c["wins"],
            "Win rate": (f"{c['win_rate']*100:.1f}%"
                          if c["win_rate"] is not None else "—"),
        } for c in conf
    ])
    st.dataframe(conf_df, use_container_width=True, hide_index=True)

    # ============================================================
    # WEAK SPOTS
    # ============================================================
    st.markdown("---")
    st.markdown("### ⚠️ Слабые места модели")
    st.caption("Группы (минимум 2 прогноза) отсортированы по accuracy ASC — где модель чаще промахивается.")
    ws = weak_spots(history)

    ws_c1, ws_c2, ws_c3 = st.columns(3)
    with ws_c1:
        st.markdown("**По весовым категориям**")
        if ws["by_weight_class"]:
            df = pd.DataFrame([
                {"Категория": x["key"], "Прогнозов": x["n"],
                 "Acc": f"{x['acc']*100:.0f}%"}
                for x in ws["by_weight_class"][:5]
            ])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.caption("Мало данных.")
    with ws_c2:
        st.markdown("**По методу (предсказанному)**")
        if ws["by_predicted_method"]:
            df = pd.DataFrame([
                {"Метод": x["key"], "Прогнозов": x["n"],
                 "Acc": f"{x['acc']*100:.0f}%"}
                for x in ws["by_predicted_method"]
            ])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.caption("Мало данных.")
    with ws_c3:
        st.markdown("**RAG ON vs OFF**")
        if ws["by_rag_usage"]:
            df = pd.DataFrame([
                {"Режим": x["key"], "Прогнозов": x["n"],
                 "Acc": f"{x['acc']*100:.0f}%"}
                for x in ws["by_rag_usage"]
            ])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.caption("Мало данных.")

    # ============================================================
    # CALIBRATION CHART
    # ============================================================
    st.markdown("---")
    st.markdown("### 📈 Калибровка вероятностей")
    st.caption("Идеал — точки на диагонали: 70% уверенность → 70% реальных побед.")
    buckets = calibration_buckets_fn(history, n_bins=5)
    if any(b["count"] > 0 for b in buckets):
        cal_fig = go.Figure()
        cal_fig.add_trace(go.Scatter(
            x=[0.5, 1.0], y=[0.5, 1.0], mode="lines",
            name="Идеальная калибровка",
            line=dict(color="#16a34a", dash="dash", width=2),
        ))
        xs, ys, sizes = [], [], []
        for b in buckets:
            if b["count"] == 0:
                continue
            xs.append(b["predicted_avg"])
            ys.append(b["actual_rate"])
            sizes.append(max(15, min(60, b["count"] * 8)))
        cal_fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers+text",
            name="Модель",
            marker=dict(size=sizes, color=UFC_RED,
                        line=dict(color="white", width=2)),
            text=[f"n={b['count']}" for b in buckets if b["count"] > 0],
            textposition="top center",
        ))
        cal_fig.update_layout(
            xaxis=dict(title="Предсказанная вероятность", range=[0.45, 1.05], gridcolor="#eee"),
            yaxis=dict(title="Фактическая частота побед", range=[0, 1.05], gridcolor="#eee"),
            paper_bgcolor=BG, plot_bgcolor=BG, font=dict(color=TEXT),
            height=380, margin=dict(t=10), showlegend=True,
        )
        st.plotly_chart(cal_fig, use_container_width=True)
    else:
        st.info("Появится после разрешённых прогнозов с вероятностями.")

    # ============================================================
    # FILTERS + TABLE + CSV
    # ============================================================
    st.markdown("---")
    st.markdown("### 🔍 Фильтры")
    fc1, fc2, fc3, fc4 = st.columns([2, 2, 2, 1])
    fighter_filter = fc1.text_input("Боец", "",
        placeholder="например: Topuria")
    all_wcs = sorted({
        (h.get("weight_class") or h.get("ctx", {}).get("division") or "—")
        for h in history
    })
    wc_filter = fc2.multiselect("Весовая", all_wcs)
    status_filter = fc3.multiselect("Статус",
        ["pending", "won", "lost"], default=[])
    days_back = fc4.number_input("Последние N дней", 1, 9999, 365)

    cutoff = datetime.now() - timedelta(days=int(days_back))
    filtered = []
    for h in history:
        if fighter_filter:
            ff = fighter_filter.lower()
            if (ff not in (h.get("fa") or "").lower()
                and ff not in (h.get("fb") or "").lower()):
                continue
        wc = h.get("weight_class") or h.get("ctx", {}).get("division") or "—"
        if wc_filter and wc not in wc_filter:
            continue
        if status_filter and h.get("status", "pending") not in status_filter:
            continue
        dt = _safe_dt(h)
        if dt and dt < cutoff:
            continue
        filtered.append(h)

    st.caption(f"Найдено: **{len(filtered)}** из {len(history)}")

    st.markdown("### 📋 Таблица прогнозов")
    if filtered:
        rows = []
        for h in filtered:
            rows.append({
                "ID": (h.get("id") or "—")[:8],
                "Дата": (h.get("ts") or h.get("timestamp") or "")[:16],
                "Бой": f"{h.get('fa','?')} vs {h.get('fb','?')}",
                "Весовая": h.get("weight_class") or h.get("ctx", {}).get("division") or "—",
                "Прогноз": h.get("predicted_winner", "—") or "—",
                "Win%": f"{int(h['win_prob']*100)}%" if h.get("win_prob") else "—",
                "Метод (pred)": _predicted_method(h) or "—",
                "Статус": {"won": "✅ Зашло", "lost": "❌ Не зашло",
                            "pending": "⏳ Ждём"}.get(h.get("status", "pending"), "?"),
                "Факт. победитель": h.get("actual_winner", "—") or "—",
                "Факт. метод": h.get("actual_method", "—") or "—",
                "RAG": "📚" if h.get("rag_used") else "—",
                "Hybrid": "🧮" if h.get("hybrid_used") else "—",
            })
        df_view = pd.DataFrame(rows)
        st.dataframe(df_view, use_container_width=True, hide_index=True, height=360)

        csv = df_view.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Экспорт отфильтрованных в CSV", csv,
            file_name=f"predictions_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
        )

    # ============================================================
    # DETAIL CARDS / MANUAL MARK
    # ============================================================
    st.markdown("---")
    st.markdown("### 📝 Детали + ручная отметка результата")
    for i, h in enumerate(filtered):
        status = h.get("status", "pending")
        icon = {"won": "✅", "lost": "❌", "pending": "⏳"}[status]
        prob_str = f" · {int(h['win_prob']*100)}%" if h.get("win_prob") else ""
        title = (
            f"{icon} {h.get('fa','?')} vs {h.get('fb','?')}"
            f"{prob_str} · {(h.get('ts') or '')[:16]}"
        )
        with st.expander(title):
            real_idx = st.session_state.history.index(h)
            wc = h.get("weight_class") or h.get("ctx", {}).get("division") or "—"
            event = h.get("event") or h.get("ctx", {}).get("event", "—")
            tags = []
            if h.get("rag_used"): tags.append("📚 RAG")
            if h.get("hybrid_used"): tags.append("🧮 Hybrid")
            if h.get("multi_agent_used"): tags.append("🤖 Multi-Agent")
            tag_str = " · ".join(tags) if tags else ""

            st.caption(
                f"🆔 `{h.get('id','—')}` · 📅 {event} · ⚖️ {wc} · 🤖 {h.get('model','—')}"
                + (f" · {tag_str}" if tag_str else "")
            )

            ic1, ic2, ic3, ic4 = st.columns(4)
            ic1.metric("Прогноз", h.get("predicted_winner", "—") or "—")
            ic2.metric("Win prob",
                       f"{int(h['win_prob']*100)}%" if h.get("win_prob") else "—")
            ic3.metric("Метод (pred)", _predicted_method(h) or "—")
            ic4.metric("Статус", status.upper())

            if h.get("status") in ("won", "lost") and h.get("actual_winner"):
                correct = h.get("status") == "won"
                st.markdown(
                    f"**Факт.** Победил: **{h['actual_winner']}**"
                    + (f" · Метод: `{h.get('actual_method','')}`" if h.get('actual_method') else "")
                    + (f" · Раунд: R{h['actual_round']}" if h.get('actual_round') else "")
                    + (f" · {'✅ ВЕРНО' if correct else '❌ МИМО'}")
                )

            # ----- Manual mark form -----
            st.markdown("**Отметить результат:**")
            mc1, mc2, mc3 = st.columns(3)
            actual_w = mc1.selectbox(
                "Реальный победитель",
                ["—", h.get("fa", ""), h.get("fb", "")],
                index=(["—", h.get("fa", ""), h.get("fb", "")].index(h.get("actual_winner", "—"))
                       if h.get("actual_winner") in [h.get("fa"), h.get("fb")] else 0),
                key=f"aw_{real_idx}",
            )
            actual_m = mc2.selectbox(
                "Метод",
                ["—", "KO/TKO", "Submission", "Decision"],
                index=(["—", "KO/TKO", "Submission", "Decision"].index(
                    _actual_method_class(h.get("actual_method", "")) or "—")),
                key=f"am_{real_idx}",
            )
            actual_r = mc3.number_input(
                "Раунд (1-5, 0 = decision)",
                min_value=0, max_value=5,
                value=int(h.get("actual_round") or 0),
                key=f"ar_{real_idx}",
            )

            sv1, sv2, sv3, sv4 = st.columns([1, 1, 1, 1])
            if sv1.button("💾 Сохранить результат", key=f"save_{real_idx}",
                          use_container_width=True):
                if actual_w != "—":
                    rec = st.session_state.history[real_idx]
                    rec["actual_winner"] = actual_w
                    rec["actual_method"] = actual_m if actual_m != "—" else ""
                    rec["actual_round"] = int(actual_r) if actual_r else None
                    pred = rec.get("predicted_winner", "")
                    # Tolerant match
                    rec["status"] = ("won"
                        if pred and (pred.lower() in actual_w.lower()
                                     or actual_w.lower() in pred.lower())
                        else "lost")
                    rec["resolved_at"] = datetime.now().isoformat()
                    persist_history()
                    st.success("Сохранено.")
                    st.rerun()
                else:
                    st.warning("Выбери победителя.")

            if sv2.button("↩️ Сбросить", key=f"reset_{real_idx}",
                          use_container_width=True):
                for k in ("actual_winner", "actual_method", "actual_round", "resolved_at"):
                    st.session_state.history[real_idx].pop(k, None)
                st.session_state.history[real_idx]["status"] = "pending"
                persist_history()
                st.rerun()

            if sv3.button("🗑️ Удалить", key=f"del_{real_idx}",
                          use_container_width=True):
                st.session_state.history.pop(real_idx)
                persist_history()
                st.rerun()

            # P&L
            with st.expander("💵 Odds / Stake / P&L"):
                oc1, oc2, oc3 = st.columns(3)
                odds = oc1.number_input("Коэф", 1.0, 50.0,
                    float(h.get("odds") or 2.0), key=f"odds_{real_idx}")
                stake = oc2.number_input("Ставка $", 0.0, 10000.0,
                    float(h.get("stake") or 100.0), key=f"stake_{real_idx}")
                if oc3.button("💾", key=f"sodds_{real_idx}"):
                    rec = st.session_state.history[real_idx]
                    rec["odds"] = odds
                    rec["stake"] = stake
                    if rec.get("status") == "won":
                        rec["profit"] = round(stake * (odds - 1), 2)
                    elif rec.get("status") == "lost":
                        rec["profit"] = -stake
                    persist_history()
                    st.rerun()
                if h.get("profit") is not None:
                    color = "#16a34a" if h["profit"] > 0 else "#dc2626"
                    st.markdown(
                        f"**P&L:** <span style='color:{color};font-weight:600'>"
                        f"${h['profit']:+.2f}</span>",
                        unsafe_allow_html=True,
                    )

            if h.get("intel"):
                st.markdown(f"**🧠 Intel:** {h['intel']}")
            with st.expander("📄 Полный анализ LLM"):
                st.markdown(h.get("analysis", "—"))

    # ============================================================
    # DANGER ZONE
    # ============================================================
    st.markdown("---")
    with st.expander("🧹 Danger zone"):
        danger = st.checkbox("Подтверждаю — снести ВСЁ")
        if st.button("Очистить всю историю", disabled=not danger):
            st.session_state.history = []
            persist_history()
            st.rerun()
