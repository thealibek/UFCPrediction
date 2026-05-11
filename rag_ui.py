"""Knowledge Base страница — UI для управления RAG-индексом."""
from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
import streamlit as st

from rag_utils import (
    bootstrap_if_empty,
    collection_stats,
    fighter_to_doc,
    fight_to_doc,
    index_documents,
    index_fighters,
    index_fights,
    list_all_documents,
    reindex_all,
    reset_collection,
    retrieve_relevant_context,
)


def render_knowledge_base_page():
    """Главная функция рендера страницы Knowledge Base."""

    st.markdown("## 🧠 Knowledge Base — RAG Индекс")
    st.caption(
        "Семантическая база бойцов и исторических боёв. "
        "Используется в Predictor для grounding-аналитики ИИ."
    )

    # ---------- Bootstrap on first run ----------
    fighters = st.session_state.get("fighters", [])
    boot = bootstrap_if_empty(fighters)
    if not boot["skipped"]:
        st.success(
            f"✅ База инициализирована: {boot['fighters_indexed']} бойцов "
            f"+ {boot['fights_indexed']} исторических боёв."
        )

    stats = collection_stats()

    # ---------- Stats dashboard ----------
    st.markdown("### 📊 Состояние базы")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📚 Всего документов", stats.get("total", 0))
    c2.metric("🥋 Профилей бойцов", stats.get("fighters", 0))
    c3.metric("📜 Записей боёв", stats.get("fights", 0))
    last = stats.get("last_indexed", "")
    if last:
        try:
            dt = datetime.fromisoformat(last)
            c4.metric("🕒 Обновлено", dt.strftime("%d.%m %H:%M"))
        except Exception:
            c4.metric("🕒 Обновлено", "—")
    else:
        c4.metric("🕒 Обновлено", "—")

    if stats.get("error"):
        st.error(f"⚠️ Ошибка: {stats['error']}")

    st.markdown("---")

    # ---------- Tabs ----------
    tab_search, tab_add, tab_upload, tab_inspect, tab_admin = st.tabs([
        "🔍 Поиск (Test Retrieval)",
        "➕ Добавить вручную",
        "📤 Импорт CSV / JSON",
        "📋 Все документы",
        "⚙️ Админ",
    ])

    # =====================================================================
    # TAB: SEARCH / TEST RETRIEVAL
    # =====================================================================
    with tab_search:
        st.markdown("#### 🔍 Тест семантического поиска")
        st.caption("Введи запрос — увидишь какие чанки выдаст ретривер.")

        sc1, sc2, sc3 = st.columns([2, 1, 1])
        query = sc1.text_input(
            "Запрос",
            value="wrestler vs boxer matchup",
            placeholder="например: pressure boxer vs counter striker",
        )
        f_a = sc2.text_input("Boost: боец A (опц.)", "")
        f_b = sc3.text_input("Boost: боец B (опц.)", "")
        top_k = st.slider("Top K", 3, 12, 6)

        if st.button("🚀 Найти", use_container_width=True):
            with st.spinner("Ретриверю..."):
                result = retrieve_relevant_context(
                    query=query, fighter_a=f_a or None,
                    fighter_b=f_b or None, top_k=top_k,
                )
            if result.get("error"):
                st.error(result["error"])
            elif not result["raw"]:
                st.warning("Ничего не найдено.")
            else:
                st.success(f"Найдено {len(result['raw'])} чанков:")
                for i, c in enumerate(result["raw"], 1):
                    score = c["score"]
                    m = c["meta"]
                    if m.get("doc_type") == "fighter_profile":
                        title = f"[{i}] 🥋 {m.get('fighter_name')} · score: {score:.3f}"
                    else:
                        title = (
                            f"[{i}] 📜 {m.get('fighter_a')} vs "
                            f"{m.get('fighter_b')} · {m.get('date')} · score: {score:.3f}"
                        )
                    with st.expander(title):
                        st.code(c["doc"], language=None)
                        st.json(m)

    # =====================================================================
    # TAB: ADD MANUALLY
    # =====================================================================
    with tab_add:
        st.markdown("#### ➕ Добавить документ вручную")

        which = st.radio(
            "Тип",
            ["Профиль бойца", "Запись боя"],
            horizontal=True, label_visibility="collapsed",
        )

        if which == "Профиль бойца":
            with st.form("add_fighter_form"):
                fc1, fc2 = st.columns(2)
                name = fc1.text_input("Имя *", "")
                division = fc2.text_input("Весовая *", "Lightweight")
                country = fc1.text_input("Страна", "")
                age = fc2.number_input("Возраст", 18, 60, 28)
                record = fc1.text_input("Рекорд", "0-0-0")
                stance = fc2.selectbox("Стойка",
                    ["Orthodox", "Southpaw", "Switch"], index=0)
                style = st.text_input("Стиль (1 строка)",
                    "Boxer-puncher with pressure")
                strengths = st.text_input("Сильные стороны (через запятую)", "")
                weaknesses = st.text_input("Слабые стороны (через запятую)", "")
                bio = st.text_area("Био (опц.)", "", height=80)
                stat1, stat2, stat3 = st.columns(3)
                slpm = stat1.number_input("SLpM", 0.0, 15.0, 4.5)
                str_acc = stat2.number_input("StrAcc %", 0, 100, 50)
                str_def = stat3.number_input("StrDef %", 0, 100, 55)
                td_avg = stat1.number_input("TDAvg", 0.0, 10.0, 1.5)
                td_def = stat2.number_input("TDDef %", 0, 100, 60)
                sub_avg = stat3.number_input("SubAvg", 0.0, 5.0, 0.5)
                submit = st.form_submit_button("✅ Индексировать",
                    use_container_width=True)

            if submit and name:
                f = {
                    "name": name, "division": division, "country": country,
                    "age": age, "record": record, "stance": stance,
                    "style": style, "bio": bio,
                    "strengths": [s.strip() for s in strengths.split(",") if s.strip()],
                    "weaknesses": [s.strip() for s in weaknesses.split(",") if s.strip()],
                    "SLpM": slpm, "StrAcc": str_acc, "StrDef": str_def,
                    "TDAvg": td_avg, "TDDef": td_def, "SubAvg": sub_avg,
                }
                n = index_fighters([f])
                st.success(f"✅ Проиндексирован: {name} ({n} doc)")

        else:
            with st.form("add_fight_form"):
                fc1, fc2 = st.columns(2)
                a = fc1.text_input("Боец A *", "")
                b = fc2.text_input("Боец B *", "")
                event = fc1.text_input("Ивент", "UFC ___")
                date_str = fc2.text_input("Дата (YYYY-MM-DD)", "")
                wc = fc1.text_input("Весовая", "Lightweight")
                winner = fc2.text_input("Победитель", "")
                method = fc1.text_input("Метод",
                    "Decision (unanimous)")
                rnd = fc2.number_input("Раунд", 1, 5, 3)
                notes = st.text_area("Ключевые моменты", "", height=80)
                lessons = st.text_area("Стилистические уроки", "", height=80)
                submit_f = st.form_submit_button("✅ Индексировать",
                    use_container_width=True)

            if submit_f and a and b:
                fight = {
                    "fighter_a": a, "fighter_b": b, "event": event,
                    "date": date_str, "weight_class": wc, "winner": winner,
                    "method": method, "round": rnd,
                    "notes": notes, "stylistic_lessons": lessons,
                }
                n = index_fights([fight])
                st.success(f"✅ Проиндексирован бой: {a} vs {b}")

    # =====================================================================
    # TAB: UPLOAD CSV / JSON
    # =====================================================================
    with tab_upload:
        st.markdown("#### 📤 Массовый импорт")
        st.caption("CSV или JSON. Поля как в шаблоне ниже.")

        up_type = st.radio(
            "Тип данных",
            ["Бойцы", "Бои"],
            horizontal=True, label_visibility="collapsed",
        )

        if up_type == "Бойцы":
            template = pd.DataFrame([{
                "name": "Example Fighter",
                "division": "Lightweight",
                "country": "USA",
                "age": 28,
                "record": "20-3-0",
                "stance": "Orthodox",
                "style": "Wrestler with strong top control",
                "SLpM": 4.5, "SApM": 3.2, "StrAcc": 50, "StrDef": 55,
                "TDAvg": 3.5, "TDDef": 70, "SubAvg": 1.0,
                "strengths": "wrestling,cardio",
                "weaknesses": "striking range",
                "bio": "",
            }])
        else:
            template = pd.DataFrame([{
                "fighter_a": "Fighter A",
                "fighter_b": "Fighter B",
                "event": "UFC ___",
                "date": "2024-01-01",
                "weight_class": "Lightweight",
                "winner": "Fighter A",
                "method": "KO (punches)",
                "round": 2,
                "notes": "Какие моменты определили исход",
                "stylistic_lessons": "Что это даёт для будущих matchups",
            }])

        st.download_button(
            "⬇️ Скачать шаблон CSV",
            template.to_csv(index=False).encode("utf-8"),
            file_name=f"template_{up_type.lower()}.csv",
            mime="text/csv",
            use_container_width=True,
        )

        uploaded = st.file_uploader(
            f"Загрузи CSV/JSON с {up_type.lower()}",
            type=["csv", "json"],
            key=f"upload_{up_type}",
        )

        if uploaded:
            try:
                if uploaded.name.endswith(".json"):
                    data = json.loads(uploaded.read().decode("utf-8"))
                    if isinstance(data, dict):
                        data = [data]
                else:
                    df = pd.read_csv(uploaded)
                    data = df.to_dict("records")

                st.write(f"Прочитано записей: **{len(data)}**")
                st.dataframe(pd.DataFrame(data).head(5), use_container_width=True)

                if st.button("🚀 Индексировать", use_container_width=True):
                    if up_type == "Бойцы":
                        # CSV strengths/weaknesses → list
                        for d in data:
                            for k in ("strengths", "weaknesses"):
                                if isinstance(d.get(k), str):
                                    d[k] = [s.strip() for s in d[k].split(",") if s.strip()]
                        n = index_fighters(data)
                    else:
                        n = index_fights(data)
                    st.success(f"✅ Проиндексировано записей: {n}")
                    st.rerun()
            except Exception as e:
                st.error(f"Ошибка: {e}")

    # =====================================================================
    # TAB: INSPECT ALL DOCS
    # =====================================================================
    with tab_inspect:
        st.markdown("#### 📋 Все документы в базе")
        all_docs = list_all_documents()
        if not all_docs:
            st.info("База пустая.")
        else:
            filt = st.radio(
                "Фильтр",
                ["Все", "Только бойцы", "Только бои"],
                horizontal=True, label_visibility="collapsed",
            )
            for d in all_docs:
                dt = d["meta"].get("doc_type")
                if filt == "Только бойцы" and dt != "fighter_profile":
                    continue
                if filt == "Только бои" and dt != "fight_record":
                    continue
                if dt == "fighter_profile":
                    title = f"🥋 {d['meta'].get('fighter_name', '?')} · {d['meta'].get('division', '')}"
                else:
                    title = (
                        f"📜 {d['meta'].get('fighter_a', '?')} vs "
                        f"{d['meta'].get('fighter_b', '?')} · "
                        f"{d['meta'].get('date', '')}"
                    )
                with st.expander(title):
                    st.code(d["text"])
                    st.caption(f"ID: `{d['id']}`")

    # =====================================================================
    # TAB: ADMIN
    # =====================================================================
    with tab_admin:
        st.markdown("#### ⚙️ Управление индексом")

        ac1, ac2 = st.columns(2)
        with ac1:
            if st.button("🔄 Re-index (бойцы из базы + сиды)",
                         use_container_width=True):
                with st.spinner("Переиндексация..."):
                    r = reindex_all(st.session_state.get("fighters", []))
                st.success(
                    f"✅ Готово: {r['fighters_indexed']} бойцов "
                    f"+ {r['fights_indexed']} боёв."
                )
                st.rerun()
        with ac2:
            danger = st.checkbox("Подтверждаю — снести всё")
            if st.button("🗑️ Очистить и пересоздать индекс",
                         disabled=not danger, use_container_width=True):
                reset_collection()
                st.warning("База очищена.")
                st.rerun()

        st.markdown("---")
        st.caption(
            "📁 Хранилище: `./chroma_db/` (persistent, всё переживёт рестарт). "
            "Эмбеддинги: `all-MiniLM-L6-v2` (384-мерные, cosine similarity)."
        )
