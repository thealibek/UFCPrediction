"""
UFC AI Предиктор | Octagon Oracle
Streamlit-приложение: глубокая аналитика, прогнозы и трекинг ставок UFC.
Запуск: streamlit run app.py
"""
import json
import os
import re
from datetime import datetime, date
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_seed import DEFAULT_FIGHTERS, DEFAULT_EVENTS

# ---------- Файлы ----------
FIGHTERS_FILE = "fighters.json"
EVENTS_FILE = "upcoming_events.json"
HISTORY_FILE = "history.json"

UFC_RED = "#E30613"
UFC_GOLD = "#D4AF37"
BG = "#0D0D0D"
CARD_BG = "#161616"

DIVISIONS = [
    "Strawweight", "Flyweight", "Bantamweight", "Featherweight",
    "Lightweight", "Welterweight", "Middleweight",
    "Light Heavyweight", "Heavyweight",
    "Women's Strawweight", "Women's Flyweight", "Women's Bantamweight",
]

# ---------- Системный промпт LLM ----------
SYSTEM_PROMPT = """Ты — ведущий аналитик UFC и sharp bettor с 15+ летним опытом. Твои прогнозы точные, calibrated и actionable. Тон — острый аналитик-пундит: уверенно, по делу, с MMA-сленгом ("чётко", "реально доминирует", "весогонка", "менталка", "кардио", "грэпплинг", "канвас", "лоу-кики", "клинч").

Ты ВСЕГДА:
- Используешь предоставленные точные статистики (SLpM, SApM, StrAcc, StrDef, TDAvg, TDAcc, TDDef, SubAvg) — называешь конкретные цифры.
- Жёстко разбираешь стилевой матч-ап (борец против ударника, рестлер против джиу-джитсера, kickboxer vs pressure fighter и т.д.) и объясняешь, почему один стиль даёт преимущество ИМЕННО в этом бою.
- Учитываешь качество оппозиции, текущую форму (последние 5 боёв), возраст/прайм, кардио, чини, reach advantage, физику.
- Обязательно анализируешь весогонку и её влияние (особенно в 5-раундовых титульниках).
- Используешь ВЕСЬ additional_intel (новости, инсайды, менталка, проблемы в лагере, травмы) — если он пустой, прямо это отмечаешь.
- Даёшь win probability обычно в диапазоне 55-78% для фаворитов. 80%+ только для очевидных миссматчей. Учитываешь upset potential.
- Method probabilities: KO/TKO %, Submission %, Decision % — суммой 100%.
- Выдаёшь чёткие ставки в формате пользователя: "Берем [Имя] Moneyline, победа", "Победа удушкой — вероятность XX%", "Бой закончится до 3 раунда", "Избегать Over rounds потому что...". Объясняешь ГДЕ value/edge.

ФОРМАТ ОТВЕТА — строгий красивый markdown с эмодзи. Структура:

## 🥊 [Боец A] vs [Боец B] | [Весовая категория]

### 🏆 Итоговый прогноз
**Победитель: [Имя]** (вероятность XX%)
**Метод:** KO/TKO XX% / Submission YY% / Decision ZZ%

### 💰 Рекомендации по ставкам
- **Основная ставка:** Берем [Имя] Moneyline, победа. Почему: ...
- **Проп №1:** ...
- **Проп №2:** ...
- **Что избегать:** ...

### 📊 Подробный разбор
**🎯 Стилевой матч-ап:** ...
**📈 Статистический breakdown:** (конкретные цифры)
**🔥 Форма и тренды:** ...
**💪 Физика, возраст, reach:** ...
**🏆 Качество оппозиции:** ...
**🧠 Ментальная составляющая (с учётом инсайдов):** ...
**⚖️ Весогонка:** ...
**🎬 Как пройдёт бой (сценарий по раундам):** ...

### 🎯 Топ-3 причины за пик
1. ...
2. ...
3. ...

### ⚠️ Риски и upset potential
- ...
- ...

### 📌 Уверенность: [Низкая / Средняя / Высокая] — XX/100
**Ключевые неопределённости:** ...
"""

# ---------- Persistence ----------
def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def init_data():
    if not os.path.exists(FIGHTERS_FILE):
        save_json(FIGHTERS_FILE, DEFAULT_FIGHTERS)
    if not os.path.exists(EVENTS_FILE):
        save_json(EVENTS_FILE, DEFAULT_EVENTS)
    if not os.path.exists(HISTORY_FILE):
        save_json(HISTORY_FILE, [])


# ---------- Streamlit setup ----------
st.set_page_config(page_title="UFC AI Предиктор | Octagon Oracle",
                   page_icon="🥊", layout="wide", initial_sidebar_state="expanded")

CUSTOM_CSS = f"""
<style>
.stApp {{ background-color: {BG}; color: #FFFFFF; }}
section[data-testid="stSidebar"] {{ background-color: #0A0A0A; border-right: 1px solid #222; }}
h1, h2, h3, h4 {{ color: #FFFFFF !important; letter-spacing: 0.3px; }}
h1 {{ border-bottom: 3px solid {UFC_RED}; padding-bottom: 8px; }}
.stButton>button {{
    background: linear-gradient(135deg, {UFC_RED}, #8B0000);
    color: white; border: none; font-weight: 700; letter-spacing: 0.5px;
    padding: 10px 18px; border-radius: 6px; transition: all 0.15s;
}}
.stButton>button:hover {{ filter: brightness(1.15); transform: translateY(-1px); }}
[data-testid="stMetric"] {{
    background: {CARD_BG}; padding: 14px; border-radius: 8px;
    border-left: 4px solid {UFC_RED};
}}
[data-testid="stMetricLabel"] {{ color: {UFC_GOLD} !important; }}
.fighter-card {{
    background: linear-gradient(180deg, {CARD_BG}, #0D0D0D);
    border: 1px solid #222; border-left: 4px solid {UFC_RED};
    padding: 16px; border-radius: 8px; margin-bottom: 12px;
}}
.event-card {{
    background: {CARD_BG}; border: 1px solid #222;
    border-left: 4px solid {UFC_GOLD};
    padding: 14px 18px; border-radius: 8px; margin-bottom: 10px;
}}
.event-past {{
    background: #0F0F0F; border: 1px solid #1a1a1a;
    border-left: 4px solid #444; opacity: 0.85;
    padding: 14px 18px; border-radius: 8px; margin-bottom: 10px;
}}
.event-special {{
    background: linear-gradient(135deg, #1a0000, #1a1400);
    border: 2px solid {UFC_GOLD}; border-left: 6px solid {UFC_RED};
    padding: 16px 20px; border-radius: 10px; margin-bottom: 12px;
    box-shadow: 0 0 20px rgba(212,175,55,0.15);
}}
.event-title {{ color: {UFC_GOLD}; font-weight: 700; font-size: 1.05rem; }}
.tag-red {{ background: {UFC_RED}; color: white; padding: 2px 8px;
    border-radius: 4px; font-size: 0.75rem; font-weight: 700; }}
.tag-gold {{ background: {UFC_GOLD}; color: #000; padding: 2px 8px;
    border-radius: 4px; font-size: 0.75rem; font-weight: 700; }}
.tag-grey {{ background: #333; color: #ccc; padding: 2px 8px;
    border-radius: 4px; font-size: 0.75rem; font-weight: 700; }}
.hero {{
    background: linear-gradient(135deg, #1a0000, {BG} 60%);
    padding: 24px; border-radius: 10px;
    border: 1px solid #2a0000; margin-bottom: 16px;
}}
.hero h1 {{ font-size: 2.2rem; margin: 0; }}
.hero p {{ color: {UFC_GOLD}; font-size: 1.05rem; margin: 6px 0 0 0; }}
.stat-box {{
    background: {CARD_BG}; padding: 14px; border-radius: 8px;
    border: 1px solid #222; margin-bottom: 10px;
}}
.stat-box h4 {{ margin: 0 0 6px 0; color: {UFC_GOLD} !important; font-size: 0.9rem; }}
.stat-box .v {{ font-size: 1.8rem; font-weight: 700; color: white; }}
.bet-won {{ color: #2ecc71; font-weight: 700; }}
.bet-lost {{ color: #e74c3c; font-weight: 700; }}
.bet-pending {{ color: {UFC_GOLD}; font-weight: 700; }}
hr {{ border-color: #222; }}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

init_data()

# ---------- Session state ----------
if "fighters" not in st.session_state:
    st.session_state.fighters = load_json(FIGHTERS_FILE, [])
if "events" not in st.session_state:
    st.session_state.events = load_json(EVENTS_FILE, [])
if "history" not in st.session_state:
    st.session_state.history = load_json(HISTORY_FILE, [])
if "preselect" not in st.session_state:
    st.session_state.preselect = {"a": None, "b": None}
if "last_analysis" not in st.session_state:
    st.session_state.last_analysis = None
if "page" not in st.session_state:
    st.session_state.page = "🏠 Home"


def persist_fighters(): save_json(FIGHTERS_FILE, st.session_state.fighters)
def persist_events(): save_json(EVENTS_FILE, st.session_state.events)
def persist_history(): save_json(HISTORY_FILE, st.session_state.history)


def get_fighter(name): 
    for f in st.session_state.fighters:
        if f["name"] == name: return f
    return None


# ---------- Bet tracking helpers ----------
def history_stats():
    """Считаем W/L/Pending по основной ставке и общую точность ИИ."""
    won = sum(1 for h in st.session_state.history if h.get("status") == "won")
    lost = sum(1 for h in st.session_state.history if h.get("status") == "lost")
    pending = sum(1 for h in st.session_state.history if h.get("status", "pending") == "pending")
    total = won + lost
    accuracy = (won / total * 100) if total > 0 else None
    roi = sum(h.get("profit", 0) for h in st.session_state.history)
    return {"won": won, "lost": lost, "pending": pending,
            "total_resolved": total, "accuracy": accuracy, "roi": roi}


def extract_main_bet(analysis: str) -> str:
    """Достаём основную ставку из markdown-вывода ИИ."""
    m = re.search(r"\*\*Основная ставка:\*\*\s*([^\n]+)", analysis)
    if m:
        return m.group(1).strip()
    m = re.search(r"\*\*Победитель:\s*([^*\n]+)\*\*", analysis)
    if m:
        return f"Берем {m.group(1).strip()} Moneyline"
    return "—"


# ---------- Demo analysis ----------
def demo_analysis(fa, fb, ctx, intel):
    rf_a = sum(1 for x in fa.get('recent_fights', []) if x.get('result') == 'W')
    rf_b = sum(1 for x in fb.get('recent_fights', []) if x.get('result') == 'W')
    return f"""## 🥊 {fa['name']} vs {fb['name']} | {fa.get('division', '—')}

### 🏆 Итоговый прогноз
**Победитель: {fa['name']}** (вероятность 64%)
**Метод:** KO/TKO 28% / Submission 22% / Decision 50%

### 💰 Рекомендации по ставкам
- **Основная ставка:** Берем {fa['name']} Moneyline, победа. Почему: TDDef {fa.get('TDDef',0)}% vs {fb.get('TDDef',0)}%, плюс свежее камп.
- **Проп №1:** Бой пройдёт дистанцию — value на Over 2.5 раундов.
- **Проп №2:** {fa['name']} by Decision — неплохой плюс к коэффициенту.
- **Что избегать:** ставить на быстрый финиш в 1 раунде.

### 📊 Подробный разбор
**🎯 Стилевой матч-ап:** {fa['name']} ({fa.get('style','—')}) против {fb['name']} ({fb.get('style','—')}).
**📈 Статистический breakdown:** SLpM {fa.get('SLpM',0)} vs {fb.get('SLpM',0)}, StrDef {fa.get('StrDef',0)}% vs {fb.get('StrDef',0)}%.
**🔥 Форма:** последние 5 — {rf_a}W vs {rf_b}W.
**💪 Физика:** reach {fa.get('reach_cm',0)} vs {fb.get('reach_cm',0)}, возраст {fa.get('age',0)} vs {fb.get('age',0)}.
**🧠 Менталка:** {('инсайды учтены: ' + intel[:200]) if intel.strip() else 'инсайдов нет — оценка по публичным данным.'}
**⚖️ Весогонка:** {fa.get('weight_cut_difficulty','—')} vs {fb.get('weight_cut_difficulty','—')}.
**🎬 Сценарий:** R1 разведка, R2-3 {fa['name']} навязывает темп.

### 🎯 Топ-3 причины
1. Стилевое преимущество.
2. Лучшая защитная статистика.
3. Активность за последние 18 месяцев.

### ⚠️ Риски
- Один чистый удар может перевернуть бой.
- {fb['name']} опасен в клинче.

### 📌 Уверенность: Средняя — 62/100
*— Demo Mode. Включи Live AI для настоящего анализа.*
"""


# ---------- LLM ----------
def get_fight_prediction(fa, fb, ctx, intel, api_key, base_url, model):
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url)
    user_msg = f"""Проанализируй предстоящий бой UFC.

## БОЕЦ A
{json.dumps(fa, ensure_ascii=False, indent=2)}

## БОЕЦ B
{json.dumps(fb, ensure_ascii=False, indent=2)}

## КОНТЕКСТ
- Раундов: {ctx.get('rounds', 3)}
- Титульный: {'Да' if ctx.get('title_fight') else 'Нет'}
- Категория: {ctx.get('division', '—')}
- Событие: {ctx.get('event', '—')}

## ДОПОЛНИТЕЛЬНЫЙ ИНТЕЛЛЕКТ
{intel.strip() if intel.strip() else '(не предоставлено)'}

Дай развёрнутый прогноз строго по формату системного промпта. Только русский."""
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user", "content": user_msg}],
        temperature=0.5, max_tokens=3500,
    )
    return resp.choices[0].message.content


# ---------- Sidebar: Navigation + Settings ----------
with st.sidebar:
    st.markdown(f"<h2 style='color:{UFC_RED};margin:0'>🥊 OCTAGON ORACLE</h2>",
                unsafe_allow_html=True)
    st.caption("UFC AI Предиктор")
    st.markdown("---")

    PAGES = [
        "🏠 Home",
        "👥 Fight Base",
        "🔮 Predictor",
        "📊 Analytics",
        "⚖️ Weight Cut",
        "📚 History",
    ]
    page = st.radio("Навигация", PAGES, label_visibility="collapsed",
                    index=PAGES.index(st.session_state.page) if st.session_state.page in PAGES else 0)
    st.session_state.page = page

    st.markdown("---")
    st.subheader("⚙️ LLM")
    demo_mode = st.toggle("Demo Mode", value=True,
                          help="Без API. Выключи для Live AI.")
    api_key = st.text_input("API Key", type="password",
                            value=os.environ.get("LLM_API_KEY", ""))
    base_url = st.text_input("Base URL", value="https://api.groq.com/openai/v1")
    model = st.selectbox("Модель", [
        "llama-3.3-70b-versatile", "llama-3.1-70b-versatile",
        "deepseek-r1-distill-llama-70b", "mixtral-8x7b-32768",
        "gpt-4o-mini", "gpt-4o", "grok-2-latest",
    ])

    st.markdown("---")
    if st.button("🔄 Сбросить события к дефолту"):
        st.session_state.events = DEFAULT_EVENTS
        persist_events()
        st.success("Events updated.")
        st.rerun()
    st.caption("📊 Данные: ufcstats.com / FightMetric. База редактируется юзером.")


# ---------- HEADER ----------
st.markdown(
    f"""<div class='hero'>
    <h1>🥊 UFC AI Предиктор <span style='color:{UFC_RED}'>|</span> Octagon Oracle</h1>
    <p>Глубокая аналитика. Умные ставки. Точные прогнозы.</p>
    </div>""",
    unsafe_allow_html=True,
)


# =================================================================
# ROUTING
# =================================================================
def render_event_card(ev, idx, allow_click=True):
    is_special = ev.get("special")
    is_past = ev.get("status") == "past"
    css_class = "event-special" if is_special else ("event-past" if is_past else "event-card")
    status_tag = ""
    if is_past:
        status_tag = "<span class='tag-grey'>ПРОШЁЛ</span>"
    elif is_special:
        status_tag = "<span class='tag-red'>SPECIAL</span>"
    elif ev.get("title_fight"):
        status_tag = "<span class='tag-red'>TITLE</span>"

    st.markdown(
        f"""<div class='{css_class}'>
        <span class='event-title'>{ev['title']}</span>
        &nbsp;<span class='tag-gold'>{ev['date']}</span>
        &nbsp;{status_tag}
        <br><span style='color:#bbb'>📍 {ev['location']}</span>
        <br><b style='color:white'>🥊 {ev['main_event']}</b>
        <span style='color:#888'> — {ev.get('division','')}</span>
        </div>""",
        unsafe_allow_html=True,
    )

    if is_past:
        # Показываем результаты
        for ft in ev["fights"]:
            if isinstance(ft, dict):
                st.markdown(
                    f"&nbsp;&nbsp;✅ <b>{ft['winner']}</b> def. "
                    f"{ft['a'] if ft['winner']!=ft['a'] else ft['b']} "
                    f"<span style='color:#888'>via {ft['method']}</span>",
                    unsafe_allow_html=True,
                )
    elif allow_click:
        cols = st.columns(len(ev["fights"]))
        for i, ft in enumerate(ev["fights"]):
            a, b = (ft if isinstance(ft, tuple) else (ft.get("a"), ft.get("b")))
            if cols[i].button(f"➡️ {a} vs {b}",
                              key=f"ev_{idx}_{i}", use_container_width=True):
                st.session_state.preselect = {
                    "a": a, "b": b,
                    "rounds": 5 if ev.get("title_fight") else 3,
                    "title_fight": ev.get("title_fight", False),
                    "event": ev["title"],
                }
                st.session_state.page = "🔮 Predictor"
                st.rerun()


# =================================================================
# PAGE: HOME
# =================================================================
if page == "🏠 Home":
    stats = history_stats()
    today = date.today().isoformat()

    upcoming = sorted([e for e in st.session_state.events if e.get("status") != "past"],
                      key=lambda e: e["date"])
    past = sorted([e for e in st.session_state.events if e.get("status") == "past"],
                  key=lambda e: e["date"], reverse=True)

    # Top metrics
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("🥋 Бойцов", len(st.session_state.fighters))
    m2.metric("📅 Ближайших", len(upcoming))
    m3.metric("📜 Прошедших", len(past))
    if stats["accuracy"] is not None:
        m4.metric("🎯 Точность ИИ",
                  f"{stats['accuracy']:.0f}%",
                  f"{stats['won']}W / {stats['lost']}L")
    else:
        m4.metric("🎯 Точность ИИ", "—", "нет данных")
    m5.metric("⏳ Pending", stats["pending"])

    st.markdown("---")

    # Two-column layout: events left, history analytics right
    left, right = st.columns([2, 1])

    with left:
        st.markdown("### 🔥 Ближайшие события")
        st.caption("Кликни на бой — он подгрузится в Predictor")
        if not upcoming:
            st.info("Нет ближайших событий.")
        for i, ev in enumerate(upcoming):
            render_event_card(ev, f"up_{i}")

        st.markdown("---")
        st.markdown("### 📜 Прошедшие события")
        if not past:
            st.info("Нет прошедших событий в базе.")
        for i, ev in enumerate(past):
            render_event_card(ev, f"past_{i}", allow_click=False)

    with right:
        st.markdown("### 📈 Анализ истории")

        # Bet performance
        st.markdown(
            f"""<div class='stat-box'><h4>✅ Зашло</h4>
            <div class='v bet-won'>{stats['won']}</div></div>""",
            unsafe_allow_html=True)
        st.markdown(
            f"""<div class='stat-box'><h4>❌ Не зашло</h4>
            <div class='v bet-lost'>{stats['lost']}</div></div>""",
            unsafe_allow_html=True)
        st.markdown(
            f"""<div class='stat-box'><h4>⏳ Ожидают исхода</h4>
            <div class='v bet-pending'>{stats['pending']}</div></div>""",
            unsafe_allow_html=True)

        if stats["accuracy"] is not None:
            st.markdown(
                f"""<div class='stat-box'><h4>🎯 Win Rate</h4>
                <div class='v' style='color:{UFC_RED}'>{stats['accuracy']:.1f}%</div>
                <span style='color:#888'>из {stats['total_resolved']} resolved ставок</span>
                </div>""",
                unsafe_allow_html=True)

            # Pie chart
            pie = go.Figure(data=[go.Pie(
                labels=["Зашло", "Не зашло"],
                values=[stats["won"], stats["lost"]],
                marker=dict(colors=["#2ecc71", "#e74c3c"]),
                hole=0.5,
            )])
            pie.update_layout(paper_bgcolor=BG, font=dict(color="white"),
                              height=240, margin=dict(t=10, b=10, l=10, r=10),
                              showlegend=True)
            st.plotly_chart(pie, use_container_width=True)
        else:
            st.info("📊 Сделай первые прогнозы и отметь их исход во вкладке **History** — точность будет считаться автоматически.")

        # Last 5 predictions
        if st.session_state.history:
            st.markdown("#### 🕒 Последние прогнозы")
            for h in st.session_state.history[:5]:
                status = h.get("status", "pending")
                icon = {"won": "✅", "lost": "❌", "pending": "⏳"}[status]
                st.markdown(
                    f"<div class='stat-box' style='padding:10px'>"
                    f"{icon} <b>{h['fa']} vs {h['fb']}</b><br>"
                    f"<span style='color:#888;font-size:0.85rem'>"
                    f"{h.get('main_bet','—')[:80]}</span>"
                    f"</div>",
                    unsafe_allow_html=True)

        st.markdown("---")
        st.caption(
            "💡 **Как тренируется модель:** каждый прогноз сохраняется в History. "
            "После боя отметь — зашла ставка или нет. ИИ накапливает реальную "
            "статистику точности, а ты видишь свой ROI и win rate."
        )


# =================================================================
# PAGE: FIGHT BASE
# =================================================================
elif page == "👥 Fight Base":
    st.markdown("## 👥 Fight Base — База Бойцов")

    top1, top2, top3 = st.columns([2, 2, 1])
    search = top1.text_input("🔍 Поиск", "")
    div_filter = top2.selectbox("Дивизион", ["Все"] + DIVISIONS)
    sort_by = top3.selectbox("Сортировка", ["Имя", "Возраст", "SLpM", "TDAvg"])

    def matches(f):
        if div_filter != "Все" and f.get("division") != div_filter: return False
        if search:
            blob = f"{f.get('name','')} {f.get('country','')} {f.get('style','')} {f.get('nickname','')}".lower()
            if search.lower() not in blob: return False
        return True

    filtered = [f for f in st.session_state.fighters if matches(f)]
    sk = {"Имя": "name", "Возраст": "age", "SLpM": "SLpM", "TDAvg": "TDAvg"}
    filtered = sorted(filtered, key=lambda x: x.get(sk[sort_by], 0))

    if filtered:
        df = pd.DataFrame([{
            "Имя": f["name"], "Прозвище": f.get("nickname", "—"),
            "Дивизион": f.get("division", "—"), "Рекорд": f.get("record", "—"),
            "Возраст": f.get("age", 0), "Reach": f.get("reach_cm", 0),
            "SLpM": f.get("SLpM", 0), "StrDef%": f.get("StrDef", 0),
            "TDAvg": f.get("TDAvg", 0), "TDDef%": f.get("TDDef", 0),
        } for f in filtered])
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown(f"**Найдено: {len(filtered)}**")

    selected = st.selectbox("Открыть профиль", [""] + [f["name"] for f in filtered])
    if selected:
        f = get_fighter(selected)
        if f:
            h1, h2 = st.columns([1, 2])
            with h1:
                st.markdown(f"### {f['name']}")
                st.markdown(f"*{f.get('nickname','—')}*")
                st.markdown(f"🌍 {f.get('country','—')} | 🥊 **{f.get('division','—')}**")
                st.markdown(f"📋 **{f.get('record','—')}**")
            with h2:
                a, b, c, d = st.columns(4)
                a.metric("Возраст", f.get("age", 0))
                b.metric("Рост", f"{f.get('height_cm',0)} см")
                c.metric("Reach", f"{f.get('reach_cm',0)} см")
                d.metric("Стойка", f.get("stance", "—"))
                a, b, c, d = st.columns(4)
                a.metric("SLpM", f.get("SLpM", 0))
                b.metric("StrDef", f"{f.get('StrDef',0)}%")
                c.metric("TDAvg", f.get("TDAvg", 0))
                d.metric("TDDef", f"{f.get('TDDef',0)}%")

            st.markdown("**Стиль:** " + f.get("style", "—"))
            cc1, cc2 = st.columns(2)
            with cc1:
                st.markdown("#### 💪 Сильные")
                for s in f.get("strengths", []): st.markdown(f"- {s}")
            with cc2:
                st.markdown("#### ⚠️ Слабые")
                for s in f.get("weaknesses", []): st.markdown(f"- {s}")
            st.markdown(f"**⚖️ Весогонка:** {f.get('weight_cut_difficulty','—')}")

            st.markdown("#### 📜 Последние бои")
            rf = f.get("recent_fights", [])
            if rf: st.dataframe(pd.DataFrame(rf), use_container_width=True, hide_index=True)

            ec1, ec2 = st.columns(2)
            with ec1:
                if st.button("🗑️ Удалить", key=f"del_{selected}"):
                    st.session_state.fighters = [
                        x for x in st.session_state.fighters if x["name"] != selected]
                    persist_fighters(); st.rerun()
            with ec2:
                with st.expander("✏️ Редактировать (JSON)"):
                    edited = st.text_area("JSON",
                        value=json.dumps(f, ensure_ascii=False, indent=2),
                        height=300, key=f"edit_{selected}")
                    if st.button("💾 Сохранить", key=f"save_{selected}"):
                        try:
                            new_f = json.loads(edited)
                            st.session_state.fighters = [
                                new_f if x["name"] == selected else x
                                for x in st.session_state.fighters]
                            persist_fighters(); st.success("Сохранено."); st.rerun()
                        except Exception as e:
                            st.error(f"JSON error: {e}")

    st.markdown("---")
    with st.expander("➕ Добавить бойца"):
        with st.form("add_fighter"):
            a1, a2, a3 = st.columns(3)
            n_name = a1.text_input("Имя*"); n_nick = a2.text_input("Прозвище")
            n_country = a3.text_input("Страна")
            a4, a5, a6 = st.columns(3)
            n_div = a4.selectbox("Дивизион", DIVISIONS)
            n_age = a5.number_input("Возраст", 18, 50, 30)
            n_stance = a6.selectbox("Стойка", ["Orthodox", "Southpaw", "Switch"])
            a7, a8, a9 = st.columns(3)
            n_height = a7.number_input("Рост (см)", 150, 220, 180)
            n_reach = a8.number_input("Reach (см)", 150, 220, 183)
            n_record = a9.text_input("Рекорд", "0-0-0")
            s1, s2, s3, s4 = st.columns(4)
            n_slpm = s1.number_input("SLpM", 0.0, 15.0, 4.0)
            n_sapm = s2.number_input("SApM", 0.0, 15.0, 3.0)
            n_stracc = s3.number_input("StrAcc %", 0, 100, 50)
            n_strdef = s4.number_input("StrDef %", 0, 100, 55)
            s5, s6, s7, s8 = st.columns(4)
            n_tdavg = s5.number_input("TDAvg", 0.0, 10.0, 1.5)
            n_tdacc = s6.number_input("TDAcc %", 0, 100, 40)
            n_tddef = s7.number_input("TDDef %", 0, 100, 65)
            n_subavg = s8.number_input("SubAvg", 0.0, 5.0, 0.5)
            n_style = st.text_input("Стиль")
            n_str = st.text_input("Сильные стороны (через запятую)")
            n_weak = st.text_input("Слабые стороны (через запятую)")
            n_wcut = st.selectbox("Весогонка", ["Низкая", "Средняя", "Высокая", "Нулевая"])
            if st.form_submit_button("➕ Добавить"):
                if not n_name:
                    st.error("Имя обязательно")
                else:
                    st.session_state.fighters.append({
                        "name": n_name, "nickname": n_nick, "country": n_country,
                        "division": n_div, "age": n_age, "stance": n_stance,
                        "height_cm": n_height, "reach_cm": n_reach, "record": n_record,
                        "SLpM": n_slpm, "SApM": n_sapm, "StrAcc": n_stracc, "StrDef": n_strdef,
                        "TDAvg": n_tdavg, "TDAcc": n_tdacc, "TDDef": n_tddef, "SubAvg": n_subavg,
                        "style": n_style,
                        "strengths": [s.strip() for s in n_str.split(",") if s.strip()],
                        "weaknesses": [s.strip() for s in n_weak.split(",") if s.strip()],
                        "weight_cut_difficulty": n_wcut, "recent_fights": [],
                    })
                    persist_fighters(); st.success(f"Добавлен: {n_name}"); st.rerun()

    st.markdown("### 📦 Импорт / Экспорт")
    e1, e2 = st.columns(2)
    with e1:
        st.download_button("⬇️ JSON",
            data=json.dumps(st.session_state.fighters, ensure_ascii=False, indent=2),
            file_name="fighters_export.json", mime="application/json")
        st.download_button("⬇️ CSV",
            data=pd.DataFrame(st.session_state.fighters).to_csv(index=False).encode("utf-8"),
            file_name="fighters_export.csv", mime="text/csv")
    with e2:
        up = st.file_uploader("⬆️ Импорт JSON", type=["json"])
        if up is not None:
            try:
                data = json.load(up)
                if isinstance(data, list):
                    st.session_state.fighters = data
                    persist_fighters(); st.success(f"Импортировано: {len(data)}"); st.rerun()
            except Exception as e:
                st.error(f"Ошибка: {e}")


# =================================================================
# PAGE: PREDICTOR
# =================================================================
elif page == "🔮 Predictor":
    st.markdown("## 🔮 Predictor — Прогноз Боя")

    fighter_names = [f["name"] for f in st.session_state.fighters]
    pre = st.session_state.preselect
    pcol_a, pcol_b = st.columns(2)

    def pick(label, side, default_name):
        with (pcol_a if side == "a" else pcol_b):
            st.markdown(f"### 🥊 {label}")
            opts = ["— выбрать —"] + fighter_names + ["✍️ Custom"]
            idx = 0
            if default_name and default_name in fighter_names:
                idx = fighter_names.index(default_name) + 1
            choice = st.selectbox(label, opts, index=idx, key=f"pick_{side}",
                                  label_visibility="collapsed")
            if choice == "✍️ Custom":
                with st.expander("Custom Fighter", expanded=True):
                    cname = st.text_input("Имя", "Custom", key=f"cn_{side}")
                    cdiv = st.selectbox("Дивизион", DIVISIONS, key=f"cd_{side}")
                    cage = st.number_input("Возраст", 18, 50, 30, key=f"ca_{side}")
                    creach = st.number_input("Reach", 150, 220, 183, key=f"cr_{side}")
                    cslpm = st.number_input("SLpM", 0.0, 15.0, 4.0, key=f"cs_{side}")
                    cstrdef = st.number_input("StrDef %", 0, 100, 55, key=f"csd_{side}")
                    ctdavg = st.number_input("TDAvg", 0.0, 10.0, 1.5, key=f"ct_{side}")
                    ctddef = st.number_input("TDDef %", 0, 100, 65, key=f"ctd_{side}")
                    cstyle = st.text_input("Стиль", "Boxer-grappler", key=f"cst_{side}")
                    return {"name": cname, "division": cdiv, "age": cage, "reach_cm": creach,
                            "SLpM": cslpm, "SApM": 3.0, "StrAcc": 50, "StrDef": cstrdef,
                            "TDAvg": ctdavg, "TDAcc": 45, "TDDef": ctddef, "SubAvg": 0.5,
                            "style": cstyle, "strengths": [], "weaknesses": [],
                            "weight_cut_difficulty": "Средняя", "recent_fights": [],
                            "record": "—", "height_cm": 180, "stance": "Orthodox"}
            elif choice != "— выбрать —":
                f = get_fighter(choice)
                if f:
                    st.markdown("<div class='fighter-card'>", unsafe_allow_html=True)
                    st.markdown(f"**{f['name']}** *{f.get('nickname','')}*  \n"
                                f"🌍 {f.get('country','—')} | 🥊 {f.get('division','—')}  \n"
                                f"📋 {f.get('record','—')} | Возраст: {f.get('age','—')}")
                    a, b, c = st.columns(3)
                    a.metric("SLpM", f.get("SLpM", 0))
                    b.metric("StrDef", f"{f.get('StrDef',0)}%")
                    c.metric("TDDef", f"{f.get('TDDef',0)}%")
                    rf = f.get("recent_fights", [])[:3]
                    if rf:
                        st.markdown("**Last:** " + " · ".join(
                            f"{x['result']} vs {x['opponent']}" for x in rf))
                    st.markdown("</div>", unsafe_allow_html=True)
                    return f
            return None

    fa = pick("Боец A", "a", pre.get("a"))
    fb = pick("Боец B", "b", pre.get("b"))

    st.markdown("### ⚙️ Параметры")
    p1, p2, p3 = st.columns(3)
    rounds = p1.radio("Раундов", [3, 5],
                     index=1 if pre.get("rounds") == 5 else 0, horizontal=True)
    title_fight = p2.checkbox("Титульный", value=pre.get("title_fight", False))
    event_name = p3.text_input("Событие", pre.get("event", "UFC Event"))

    st.markdown("### 🧠 Дополнительный intel / новости / инсайды")
    intel = st.text_area("intel", height=140, label_visibility="collapsed",
        placeholder="Травмы, весогонка, драма в лагере, мотивация...")

    st.markdown("---")
    if st.button("🔥 ЗАПУСТИТЬ ГЛУБОКИЙ АНАЛИЗ И ПРОГНОЗ", use_container_width=True):
        if not fa or not fb:
            st.error("Выбери обоих бойцов, бро.")
        elif fa.get("name") == fb.get("name"):
            st.error("Один и тот же боец.")
        else:
            ctx = {"rounds": rounds, "title_fight": title_fight,
                   "division": fa.get("division", "—"), "event": event_name}
            with st.spinner("⏳ Анализируем стили, статистику, форму, менталку..."):
                try:
                    if demo_mode or not api_key:
                        analysis = demo_analysis(fa, fb, ctx, intel)
                        if not demo_mode and not api_key:
                            st.warning("API key пустой — показываю demo.")
                    else:
                        analysis = get_fight_prediction(fa, fb, ctx, intel,
                                                       api_key, base_url, model)
                    st.session_state.last_analysis = {
                        "fa": fa["name"], "fb": fb["name"],
                        "ctx": ctx, "intel": intel, "analysis": analysis,
                        "ts": datetime.now().isoformat(timespec="seconds"),
                        "main_bet": extract_main_bet(analysis),
                        "status": "pending",
                    }
                except Exception as e:
                    st.error(f"❌ LLM error: {e}")

    if st.session_state.last_analysis and fa and fb and \
       st.session_state.last_analysis["fa"] == fa["name"] and \
       st.session_state.last_analysis["fb"] == fb["name"]:
        la = st.session_state.last_analysis

        st.markdown("---")
        st.markdown("## 📊 Визуальное сравнение")

        cats = ["Удары/мин", "Защита", "Тейкдауны", "Защ.TD", "Сабмишены", "Точность"]
        def rv(f):
            return [min(f.get("SLpM", 0)/8*100, 100), f.get("StrDef", 0),
                    min(f.get("TDAvg", 0)/6*100, 100), f.get("TDDef", 0),
                    min(f.get("SubAvg", 0)/3*100, 100), f.get("StrAcc", 0)]
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=rv(fa), theta=cats, fill="toself",
            name=fa["name"], line=dict(color=UFC_RED)))
        fig.add_trace(go.Scatterpolar(r=rv(fb), theta=cats, fill="toself",
            name=fb["name"], line=dict(color=UFC_GOLD)))
        fig.update_layout(polar=dict(bgcolor=BG,
            radialaxis=dict(visible=True, range=[0, 100], color="#888")),
            paper_bgcolor=BG, font=dict(color="white"), height=420,
            margin=dict(t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)

        metrics = ["SLpM", "SApM", "StrAcc", "StrDef", "TDAvg", "TDDef", "SubAvg"]
        bar_df = pd.DataFrame({
            "Метрика": metrics * 2,
            "Значение": [fa.get(m, 0) for m in metrics] + [fb.get(m, 0) for m in metrics],
            "Боец": [fa["name"]] * len(metrics) + [fb["name"]] * len(metrics),
        })
        bfig = px.bar(bar_df, x="Метрика", y="Значение", color="Боец", barmode="group",
                      color_discrete_map={fa["name"]: UFC_RED, fb["name"]: UFC_GOLD})
        bfig.update_layout(paper_bgcolor=BG, plot_bgcolor=BG,
                          font=dict(color="white"), height=380, margin=dict(t=10))
        st.plotly_chart(bfig, use_container_width=True)

        st.markdown("---")
        st.markdown("## 🎯 Прогноз ИИ")
        st.markdown(la["analysis"])

        sc1, sc2 = st.columns(2)
        if sc1.button("💾 Сохранить в History", use_container_width=True):
            st.session_state.history.insert(0, la)
            persist_history()
            st.success("Сохранено. Отметишь исход после боя в History.")
        sc2.download_button("⬇️ Скачать (markdown)",
            data=la["analysis"], file_name=f"prediction_{la['fa']}_vs_{la['fb']}.md",
            mime="text/markdown", use_container_width=True)


# =================================================================
# PAGE: ANALYTICS
# =================================================================
elif page == "📊 Analytics":
    st.markdown("## 📊 Analytics — Сравнения")
    fnames = [f["name"] for f in st.session_state.fighters]
    c1, c2 = st.columns(2)
    a_n = c1.selectbox("Боец 1", fnames, key="cmp_a")
    b_n = c2.selectbox("Боец 2", fnames,
        index=1 if len(fnames) > 1 else 0, key="cmp_b")

    if a_n and b_n and a_n != b_n:
        a, b = get_fighter(a_n), get_fighter(b_n)
        cats = ["SLpM", "StrDef", "TDAvg", "TDDef", "SubAvg", "StrAcc"]
        def rv2(f):
            return [min(f.get("SLpM", 0)/8*100, 100), f.get("StrDef", 0),
                    min(f.get("TDAvg", 0)/6*100, 100), f.get("TDDef", 0),
                    min(f.get("SubAvg", 0)/3*100, 100), f.get("StrAcc", 0)]
        radar = go.Figure()
        radar.add_trace(go.Scatterpolar(r=rv2(a), theta=cats, fill="toself",
            name=a["name"], line=dict(color=UFC_RED)))
        radar.add_trace(go.Scatterpolar(r=rv2(b), theta=cats, fill="toself",
            name=b["name"], line=dict(color=UFC_GOLD)))
        radar.update_layout(polar=dict(bgcolor=BG,
            radialaxis=dict(visible=True, range=[0, 100], color="#888")),
            paper_bgcolor=BG, font=dict(color="white"), height=400)
        st.plotly_chart(radar, use_container_width=True)

        rows = []
        for label, k in [("Возраст","age"),("Рост","height_cm"),("Reach","reach_cm"),
                         ("Рекорд","record"),("Стойка","stance"),("SLpM","SLpM"),
                         ("SApM","SApM"),("StrAcc%","StrAcc"),("StrDef%","StrDef"),
                         ("TDAvg","TDAvg"),("TDDef%","TDDef"),("SubAvg","SubAvg"),
                         ("Стиль","style"),("Весогонка","weight_cut_difficulty")]:
            rows.append({"Параметр": label,
                         a["name"]: str(a.get(k,"—")),
                         b["name"]: str(b.get(k,"—"))})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### 📈 Средние по дивизионам")
    df_all = pd.DataFrame(st.session_state.fighters)
    if not df_all.empty and "division" in df_all.columns:
        agg = df_all.groupby("division")[["SLpM", "StrDef", "TDAvg", "TDDef"]].mean().round(2)
        st.dataframe(agg, use_container_width=True)


# =================================================================
# PAGE: WEIGHT CUT
# =================================================================
elif page == "⚖️ Weight Cut":
    st.markdown("## ⚖️ Weight Cut — Весогонка")
    risk_map = {"Высокая": 3, "Средняя": 2, "Низкая": 1, "Нулевая": 0}
    rows = []
    for f in st.session_state.fighters:
        wcd = f.get("weight_cut_difficulty", "Средняя")
        risk = next((v for k, v in risk_map.items() if k in str(wcd)), 1)
        rows.append({"Боец": f["name"], "Дивизион": f.get("division","—"),
                     "Весогонка": wcd, "Риск": risk, "Возраст": f.get("age", 0)})
    wdf = pd.DataFrame(rows).sort_values("Риск", ascending=False)
    st.dataframe(wdf, use_container_width=True, hide_index=True)

    st.markdown("### 🚩 Красные флаги")
    high = wdf[wdf["Риск"] == 3]
    for _, r in high.iterrows():
        st.markdown(
            f"<div class='event-card'><b style='color:{UFC_RED}'>⚠️ {r['Боец']}</b> "
            f"<span class='tag-gold'>{r['Дивизион']}</span><br>"
            f"Весогонка: <b>{r['Весогонка']}</b>. Учитывай в 5-раундовых титульниках.</div>",
            unsafe_allow_html=True)

    st.markdown("### 💡 Принципы")
    st.markdown("""
- **Тяжёлая весогонка → падение кардио в R3-R5**, особенно у 30+.
- **Подъём в дивизион выше** = свежесть, но падение в скорости.
- **Спуск в категорию ниже** для wrestler-а часто = доминирующая база.
- **Промахи на весах** → высокий риск раннего нокаута.
""")


# =================================================================
# PAGE: HISTORY
# =================================================================
elif page == "📚 History":
    st.markdown("## 📚 History — Прогнозы и Ставки")

    stats = history_stats()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Всего", len(st.session_state.history))
    m2.metric("✅ Зашло", stats["won"])
    m3.metric("❌ Не зашло", stats["lost"])
    m4.metric("🎯 Win Rate",
              f"{stats['accuracy']:.1f}%" if stats["accuracy"] is not None else "—")

    st.caption("💡 Отмечай исход каждой ставки — точность ИИ пересчитывается автоматически.")
    st.markdown("---")

    if not st.session_state.history:
        st.info("Пока пусто. Сделай первый прогноз во вкладке 🔮 Predictor.")
    else:
        flt = st.radio("Фильтр", ["Все", "⏳ Pending", "✅ Зашло", "❌ Не зашло"],
                       horizontal=True)
        for i, h in enumerate(st.session_state.history):
            status = h.get("status", "pending")
            if flt == "⏳ Pending" and status != "pending": continue
            if flt == "✅ Зашло" and status != "won": continue
            if flt == "❌ Не зашло" and status != "lost": continue

            icon = {"won": "✅", "lost": "❌", "pending": "⏳"}[status]
            with st.expander(f"{icon} {h['fa']} vs {h['fb']} — {h.get('ts','')[:16]}"):
                st.caption(f"Событие: {h['ctx'].get('event','—')} · "
                           f"{h['ctx'].get('rounds',3)} раундов · "
                           f"{'TITLE' if h['ctx'].get('title_fight') else 'Non-title'}")
                st.markdown(f"**🎯 Основная ставка:** `{h.get('main_bet','—')}`")
                st.markdown(f"**📊 Текущий статус:** "
                            f"<span class='bet-{status}'>{status.upper()}</span>",
                            unsafe_allow_html=True)

                # Bet outcome controls
                bc1, bc2, bc3, bc4 = st.columns(4)
                if bc1.button("✅ Зашла", key=f"won_{i}"):
                    h["status"] = "won"
                    h["resolved_at"] = datetime.now().isoformat(timespec="seconds")
                    persist_history(); st.rerun()
                if bc2.button("❌ Не зашла", key=f"lost_{i}"):
                    h["status"] = "lost"
                    h["resolved_at"] = datetime.now().isoformat(timespec="seconds")
                    persist_history(); st.rerun()
                if bc3.button("↩️ Сбросить", key=f"reset_{i}"):
                    h["status"] = "pending"
                    h.pop("resolved_at", None)
                    persist_history(); st.rerun()
                if bc4.button("🗑️ Удалить", key=f"del_{i}"):
                    st.session_state.history.pop(i)
                    persist_history(); st.rerun()

                # Optional odds/stake input
                with st.expander("💵 Добавить odds и stake (опционально)"):
                    oc1, oc2, oc3 = st.columns(3)
                    odds = oc1.number_input("Коэф", 1.0, 50.0,
                        float(h.get("odds", 2.0)), key=f"odds_{i}")
                    stake = oc2.number_input("Ставка $", 0.0, 10000.0,
                        float(h.get("stake", 100.0)), key=f"stake_{i}")
                    if oc3.button("💾 Сохранить", key=f"save_odds_{i}"):
                        h["odds"] = odds; h["stake"] = stake
                        if status == "won":
                            h["profit"] = round(stake * (odds - 1), 2)
                        elif status == "lost":
                            h["profit"] = -stake
                        else:
                            h["profit"] = 0
                        persist_history(); st.rerun()
                    if h.get("profit") is not None:
                        color = "bet-won" if h["profit"] > 0 else ("bet-lost" if h["profit"] < 0 else "bet-pending")
                        st.markdown(f"**P&L:** <span class='{color}'>${h['profit']:+.2f}</span>",
                                    unsafe_allow_html=True)

                if h.get("intel"):
                    st.markdown(f"**🧠 Intel:** {h['intel']}")
                st.markdown("---")
                st.markdown(h["analysis"])

        st.markdown("---")
        if st.button("🧹 Очистить всю историю"):
            st.session_state.history = []
            persist_history(); st.rerun()


# Footer
st.markdown("---")
st.caption(
    f"🥊 Octagon Oracle · Streamlit · "
    f"<span style='color:{UFC_RED}'>Не финансовая рекомендация. Ставь с умом.</span>",
    unsafe_allow_html=True,
)
