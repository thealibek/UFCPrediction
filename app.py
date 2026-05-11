"""
UFC AI Предиктор | Octagon Oracle
Streamlit-приложение: глубокая аналитика, прогнозы и трекинг ставок UFC.
Запуск: streamlit run app.py
"""
import json
import os
import re
from datetime import datetime, date, timedelta
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_seed import DEFAULT_FIGHTERS, DEFAULT_EVENTS
from live_data import get_live_events

# ---------- Файлы ----------
FIGHTERS_FILE = "fighters.json"
EVENTS_FILE = "upcoming_events.json"
HISTORY_FILE = "history.json"

UFC_RED = "#D20A0A"
UFC_GOLD = "#D4AF37"
BG = "#FFFFFF"
CARD_BG = "#FAFAFA"
TEXT = "#111111"
MUTED = "#666666"
BORDER = "#E5E5E5"

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
@import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&family=Inter:wght@400;500;600;700;800&display=swap');

/* ===== UFC.com Clean Light Theme ===== */
html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif !important;
}}
.stApp {{ background-color: {BG}; color: {TEXT}; }}

/* === SIDEBAR — белая, чёрный текст, как UFC.com nav === */
section[data-testid="stSidebar"] {{
    background-color: #FFFFFF !important;
    border-right: 1px solid {BORDER};
}}
section[data-testid="stSidebar"] * {{ color: {TEXT} !important; }}
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {{
    color: {TEXT} !important;
    font-family: 'Oswald', sans-serif !important;
    font-weight: 700; letter-spacing: 1px; text-transform: uppercase;
}}
section[data-testid="stSidebar"] .stCaption,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
section[data-testid="stSidebar"] small {{
    color: {MUTED} !important;
}}
/* Sidebar radio nav: UFC-style menu items */
section[data-testid="stSidebar"] [data-testid="stRadio"] > div {{
    gap: 0 !important;
}}
section[data-testid="stSidebar"] [data-testid="stRadio"] label {{
    background: transparent;
    border-left: 3px solid transparent;
    padding: 11px 14px !important;
    margin: 0 !important;
    font-family: 'Oswald', sans-serif !important;
    font-weight: 600; font-size: 0.95rem;
    letter-spacing: 1.2px; text-transform: uppercase;
    color: {TEXT} !important;
    border-bottom: 1px solid #f0f0f0;
    cursor: pointer; transition: all 0.12s;
    width: 100%;
}}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {{
    background: #f7f7f7; border-left-color: {UFC_RED};
}}
section[data-testid="stSidebar"] [data-testid="stRadio"] label[data-checked="true"],
section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {{
    background: #fff5f5;
    border-left: 3px solid {UFC_RED};
    color: {UFC_RED} !important;
}}
section[data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-child {{
    display: none !important;
}}
/* Sidebar buttons */
section[data-testid="stSidebar"] .stButton>button {{
    background: {TEXT}; color: white !important;
    border: none; font-family: 'Oswald', sans-serif !important;
    font-weight: 600; letter-spacing: 1px;
}}
section[data-testid="stSidebar"] .stButton>button:hover {{ background: {UFC_RED}; }}
/* Sidebar inputs visible */
section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] textarea,
section[data-testid="stSidebar"] [data-baseweb="select"] > div {{
    background: white !important;
    color: {TEXT} !important;
    border: 1px solid {BORDER} !important;
}}

/* === HEADINGS === */
h1, h2, h3, h4, h5 {{
    color: {TEXT} !important;
    font-family: 'Oswald', sans-serif !important;
    font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px;
}}
h1 {{ border-bottom: 3px solid {UFC_RED}; padding-bottom: 10px; font-size: 2rem; }}
h2 {{ font-size: 1.6rem; }}
h3 {{ font-size: 1.25rem; }}

/* === BUTTONS === */
.stButton>button {{
    background: {UFC_RED}; color: white !important;
    border: none; font-weight: 700; letter-spacing: 1px;
    padding: 10px 20px; border-radius: 2px;
    text-transform: uppercase; font-size: 0.82rem;
    font-family: 'Oswald', sans-serif !important;
    transition: all 0.12s;
}}
.stButton>button:hover {{ background: #a30808; transform: translateY(-1px); }}

/* === METRICS === */
[data-testid="stMetric"] {{
    background: white; padding: 16px; border-radius: 4px;
    border: 1px solid {BORDER}; border-left: 4px solid {UFC_RED};
}}
[data-testid="stMetricLabel"] {{
    color: {MUTED} !important; font-weight: 700;
    text-transform: uppercase; font-size: 0.72rem; letter-spacing: 1px;
    font-family: 'Inter', sans-serif !important;
}}
[data-testid="stMetricValue"] {{
    color: {TEXT} !important;
    font-family: 'Oswald', sans-serif !important;
    font-weight: 700; font-size: 2rem !important;
}}
[data-testid="stMetricDelta"] {{ color: {MUTED} !important; }}

/* === CARDS / TAGS === */
.fighter-card {{
    background: white; border: 1px solid {BORDER};
    border-left: 4px solid {UFC_RED};
    padding: 16px; border-radius: 4px; margin-bottom: 12px;
}}
.tag-red {{ background: {UFC_RED}; color: white; padding: 3px 10px;
    border-radius: 2px; font-size: 0.68rem; font-weight: 700;
    letter-spacing: 1.5px; font-family: 'Oswald', sans-serif; }}
.tag-gold {{ background: {TEXT}; color: white; padding: 3px 10px;
    border-radius: 2px; font-size: 0.68rem; font-weight: 700;
    letter-spacing: 1.5px; font-family: 'Oswald', sans-serif; }}
.tag-grey {{ background: #ccc; color: {TEXT}; padding: 3px 10px;
    border-radius: 2px; font-size: 0.68rem; font-weight: 700;
    letter-spacing: 1.5px; font-family: 'Oswald', sans-serif; }}

/* === HERO === */
.hero {{
    background: #000; color: white !important;
    padding: 32px 36px; border-radius: 4px;
    border-bottom: 4px solid {UFC_RED}; margin-bottom: 22px;
}}
.hero h1 {{
    font-size: 2.6rem; margin: 0; color: white !important;
    border: none; font-family: 'Oswald', sans-serif !important;
    font-weight: 700; letter-spacing: 3px; text-transform: uppercase;
}}
.hero p {{ color: #ccc; font-size: 1rem; margin: 8px 0 0 0;
    font-family: 'Inter', sans-serif !important;
    text-transform: uppercase; letter-spacing: 2px; font-size: 0.85rem; }}

/* === HERO STATS — продающие плашки === */
.hero-stats {{
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 12px;
    margin-bottom: 20px;
}}
.hs-card {{
    background: white;
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 18px 16px;
    position: relative; overflow: hidden;
    transition: transform 0.15s, box-shadow 0.15s;
}}
.hs-card:hover {{
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.08);
}}
.hs-card::before {{
    content: ''; position: absolute; top: 0; left: 0;
    width: 100%; height: 4px; background: {UFC_RED};
}}
.hs-card.hs-won::before {{ background: #16a34a; }}
.hs-card.hs-lost::before {{ background: #dc2626; }}
.hs-card.hs-pending::before {{ background: #ca8a04; }}
.hs-card.hs-event::before {{ background: {TEXT}; }}
.hs-card.hs-primary {{
    background: linear-gradient(135deg, #000 0%, #1a1a1a 100%);
    border: none;
}}
.hs-card.hs-primary::before {{ background: {UFC_RED}; height: 5px; }}
.hs-card.hs-primary .hs-label,
.hs-card.hs-primary .hs-value,
.hs-card.hs-primary .hs-sub {{ color: white !important; }}
.hs-card.hs-primary .hs-value {{ color: {UFC_RED} !important; }}

.hs-label {{
    font-family: 'Inter', sans-serif;
    font-size: 0.7rem; font-weight: 700;
    letter-spacing: 1.5px; color: {MUTED} !important;
    text-transform: uppercase; margin-bottom: 6px;
}}
.hs-value {{
    font-family: 'Oswald', sans-serif;
    font-size: 2.4rem; font-weight: 700;
    color: {TEXT}; line-height: 1; margin-bottom: 4px;
}}
.hs-card.hs-won .hs-value {{ color: #16a34a; }}
.hs-card.hs-lost .hs-value {{ color: #dc2626; }}
.hs-card.hs-pending .hs-value {{ color: #ca8a04; }}
.hs-card.hs-event .hs-value {{ color: {TEXT}; }}
.hs-sub {{
    font-family: 'Inter', sans-serif;
    font-size: 0.75rem; color: {MUTED} !important;
    font-weight: 500;
}}
@media (max-width: 1100px) {{
    .hero-stats {{ grid-template-columns: repeat(2, 1fr); }}
}}

/* === STAT BOXES === */
.stat-box {{
    background: white; padding: 16px; border-radius: 4px;
    border: 1px solid {BORDER}; margin-bottom: 10px;
}}
.stat-box h4 {{ margin: 0 0 6px 0; color: {MUTED} !important;
    font-size: 0.72rem; text-transform: uppercase; letter-spacing: 1.5px;
    font-family: 'Inter', sans-serif !important; font-weight: 600; }}
.stat-box .v {{ font-size: 2rem; font-weight: 700; color: {TEXT};
    font-family: 'Oswald', sans-serif; }}
.bet-won {{ color: #16a34a; font-weight: 700; }}
.bet-lost {{ color: #dc2626; font-weight: 700; }}
.bet-pending {{ color: #ca8a04; font-weight: 700; }}
hr {{ border-color: {BORDER}; }}

/* === INPUTS === */
.stTextInput input, .stTextArea textarea {{
    background: white !important;
    border: 1px solid {BORDER} !important;
    color: {TEXT} !important;
    border-radius: 2px;
}}
.stSelectbox div[data-baseweb="select"] > div {{
    background: white !important;
    border: 1px solid {BORDER} !important;
    color: {TEXT} !important;
}}
.stDataFrame {{ border: 1px solid {BORDER}; border-radius: 4px; }}
.stRadio label {{ color: {TEXT} !important; }}

/* ===== UFC.com Fight Card ===== */
.ufc-card-header {{
    background: #000; border-bottom: 4px solid {UFC_RED};
    padding: 22px 28px; border-radius: 4px 4px 0 0;
    display: flex; justify-content: space-between; align-items: center;
    margin-top: 24px;
}}
.ufc-card-header .title {{
    font-family: 'Oswald', sans-serif !important; font-size: 1.9rem;
    color: white !important; letter-spacing: 2.5px; margin: 0;
    text-transform: uppercase; font-weight: 700;
}}
.ufc-card-header .meta {{
    color: #ccc; font-size: 0.78rem; text-align: right;
    letter-spacing: 1.5px; text-transform: uppercase;
    font-family: 'Inter', sans-serif !important; font-weight: 500;
}}
.ufc-bout {{
    background: white; border: 1px solid {BORDER};
    border-top: none; padding: 0; margin: 0; overflow: hidden;
}}
.ufc-bout-label {{
    text-align: center; color: {MUTED}; font-size: 0.7rem;
    letter-spacing: 3px; padding: 14px 0 10px 0; font-weight: 600;
    text-transform: uppercase; background: white;
    border-bottom: 1px solid #f5f5f5;
    font-family: 'Inter', sans-serif !important;
}}
.ufc-row {{
    display: grid; grid-template-columns: 1fr auto 1fr;
    align-items: center; padding: 22px 28px; gap: 18px;
    background: white;
}}
.ufc-fighter {{ display: flex; align-items: center; gap: 18px; }}
.ufc-fighter.left {{ justify-content: flex-end; text-align: right; }}
.ufc-fighter.right {{ justify-content: flex-start; text-align: left; }}
.ufc-fighter img.headshot {{
    width: 96px; height: 96px; border-radius: 50%;
    object-fit: cover; background: #f5f5f5;
    border: 1px solid {BORDER};
}}
.ufc-fighter .info {{ display: flex; flex-direction: column; }}
.ufc-fighter .rank {{
    color: {MUTED}; font-size: 0.72rem; font-weight: 600;
    letter-spacing: 1px; font-family: 'Inter', sans-serif;
}}
.ufc-fighter .name {{
    font-family: 'Oswald', sans-serif !important;
    font-size: 1.5rem; color: {TEXT}; line-height: 1.05;
    text-transform: uppercase; letter-spacing: 1px;
    margin: 3px 0; font-weight: 700;
}}
.ufc-fighter .country {{
    color: {MUTED}; font-size: 0.72rem; margin-top: 6px;
    display: flex; align-items: center; gap: 6px;
    font-weight: 600; letter-spacing: 1.5px;
    text-transform: uppercase; font-family: 'Inter', sans-serif;
}}
.ufc-fighter.left .country {{ justify-content: flex-end; }}
.ufc-fighter .country img {{
    width: 22px; height: 14px; object-fit: cover;
    border-radius: 1px; border: 1px solid {BORDER};
}}
.ufc-vs {{
    font-family: 'Oswald', sans-serif !important; font-size: 1.4rem;
    color: {MUTED}; font-weight: 600; letter-spacing: 2px;
    text-align: center; min-width: 60px;
}}
.ufc-odds-row {{
    display: flex; justify-content: center; gap: 28px;
    border-top: 1px solid #f5f5f5; padding: 12px 24px;
    background: white; color: {TEXT}; font-size: 0.9rem;
    align-items: center;
}}
.ufc-odds-row .o {{
    font-weight: 700; font-size: 0.95rem;
    font-family: 'Inter', sans-serif;
}}
.ufc-odds-row .o.fav {{ color: #16a34a; }}
.ufc-odds-row .o.dog {{ color: {UFC_RED}; }}
.ufc-odds-row .lbl {{
    color: {MUTED}; letter-spacing: 2px;
    font-size: 0.68rem; font-weight: 700;
    text-decoration: underline; text-transform: uppercase;
    font-family: 'Inter', sans-serif;
}}
.ufc-status {{
    text-align: center; color: {UFC_RED}; font-weight: 700;
    font-size: 0.72rem; letter-spacing: 2px; padding: 9px 0;
    background: #fafafa; border-top: 1px solid #f5f5f5;
    text-transform: uppercase;
    font-family: 'Oswald', sans-serif !important;
}}
.ufc-winner-badge {{ color: #16a34a !important; }}
.ufc-check {{
    color: #16a34a; font-weight: 900;
    font-size: 1.1em; margin: 0 4px;
}}
.headshot-wrap {{ position: relative; display: inline-block; }}
.headshot-wrap.winner img.headshot {{
    border: 3px solid #16a34a;
}}
.headshot-wrap .win-overlay {{
    position: absolute; bottom: -2px; right: -2px;
    background: #16a34a; color: white;
    width: 28px; height: 28px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 900; font-size: 14px;
    border: 2px solid white; box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}}

/* === CONTRAST FIXES — всё видно на белом === */
.stApp p, .stApp span, .stApp li, .stApp label, .stApp div {{
    color: {TEXT};
}}
.stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown strong {{
    color: {TEXT} !important;
}}
.stCaption, [data-testid="stCaptionContainer"], small {{
    color: {MUTED} !important;
}}
[data-testid="stExpander"] {{
    background: white !important;
    border: 1px solid {BORDER}; border-radius: 4px;
    margin-bottom: 8px;
}}
[data-testid="stExpander"] details {{ background: white !important; }}
[data-testid="stExpander"] details summary {{
    color: {TEXT} !important; font-weight: 600;
    background: white !important;
    font-family: 'Oswald', sans-serif !important;
    letter-spacing: 1px; padding: 12px 16px;
}}
[data-testid="stExpander"] details summary:hover {{ background: #fafafa !important; }}
[data-testid="stExpander"] details summary p {{ color: {TEXT} !important; }}
[data-testid="stExpander"] details > div {{
    background: white !important; padding: 14px 16px;
}}
.stTabs [data-baseweb="tab"] {{
    color: {TEXT} !important; font-family: 'Oswald', sans-serif;
    font-weight: 600; letter-spacing: 1px; text-transform: uppercase;
}}
.stTabs [aria-selected="true"] {{
    color: {UFC_RED} !important; border-bottom-color: {UFC_RED} !important;
}}
.stAlert, [data-testid="stAlert"] {{
    background: white !important;
    border: 1px solid {BORDER} !important;
    border-left: 4px solid {UFC_RED} !important;
    color: {TEXT} !important;
}}
.stAlert *, [data-testid="stAlert"] * {{ color: {TEXT} !important; }}
.stRadio > div > label > div {{ color: {TEXT} !important; }}
.stCheckbox > label, .stCheckbox > label * {{ color: {TEXT} !important; }}
.stForm {{ background: white; border: 1px solid {BORDER}; padding: 14px; border-radius: 4px; }}
.stToggle label, .stToggle span {{ color: {TEXT} !important; }}
.stNumberInput input, .stDateInput input {{
    background: white !important; color: {TEXT} !important;
    border: 1px solid {BORDER} !important;
}}
[data-testid="stFileUploader"] {{ background: white; border: 2px dashed {BORDER}; }}
[data-testid="stFileUploader"] * {{ color: {TEXT} !important; }}
.stDownloadButton button {{ background: {TEXT} !important; }}
.stDownloadButton button:hover {{ background: {UFC_RED} !important; }}
table {{ color: {TEXT}; }}
[data-testid="stDataFrame"] * {{ color: {TEXT} !important; }}

/* Sidebar watchlist (теперь на белом sidebar) */
.watch-item {{
    background: #fafafa; border-left: 3px solid {UFC_RED};
    padding: 10px 12px; margin-bottom: 6px; border-radius: 2px;
    font-size: 0.82rem; color: {TEXT} !important;
    border-top: 1px solid {BORDER};
    border-right: 1px solid {BORDER};
    border-bottom: 1px solid {BORDER};
}}
.watch-item b {{ color: {TEXT} !important;
    font-family: 'Oswald', sans-serif; letter-spacing: 0.5px; }}

/* Streamlit links */
a {{ color: {UFC_RED} !important; }}

/* Hide Streamlit chrome */
#MainMenu, footer, header {{ visibility: hidden; }}
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
if "watchlist" not in st.session_state:
    st.session_state.watchlist = []  # list of {a, b, event}


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


def extract_probabilities(analysis: str) -> dict:
    """Парсим вероятности из markdown-вывода LLM.
    Возвращает {win_prob, ko_prob, sub_prob, dec_prob} (float 0-1 или None).
    """
    if not analysis:
        return {"win_prob": None, "ko_prob": None, "sub_prob": None, "dec_prob": None}

    out = {"win_prob": None, "ko_prob": None, "sub_prob": None, "dec_prob": None}

    # Win probability — ищем XX% возле "уверенности"/"вероятность"
    patterns_win = [
        r"\*\*[^*]+\*\*\s*[—-]\s*(\d{1,3})\s*%\s*уверенност",
        r"уверенност[ьи]+\s*[:—-]?\s*(\d{1,3})\s*%",
        r"вероятност[ьи]+\s*(\d{1,3})\s*%",
        r"Победитель:[^\n]*?(\d{1,3})\s*%",
    ]
    for p in patterns_win:
        m = re.search(p, analysis, re.IGNORECASE)
        if m:
            v = int(m.group(1))
            if 50 <= v <= 100:
                out["win_prob"] = v / 100.0
                break

    # Method probabilities
    m = re.search(r"KO/?TKO\s*(\d{1,3})\s*%", analysis, re.IGNORECASE)
    if m: out["ko_prob"] = int(m.group(1)) / 100.0
    m = re.search(r"Submission\s*(\d{1,3})\s*%", analysis, re.IGNORECASE)
    if m: out["sub_prob"] = int(m.group(1)) / 100.0
    m = re.search(r"Decision\s*(\d{1,3})\s*%", analysis, re.IGNORECASE)
    if m: out["dec_prob"] = int(m.group(1)) / 100.0

    return out


def compute_brier_score(history: list) -> float | None:
    """Brier Score = mean((predicted_prob - outcome)^2). Чем меньше тем лучше.
    Идеал = 0. Случайное = 0.25.
    """
    contribs = []
    for h in history:
        if h.get("status") not in ("won", "lost"):
            continue
        prob = h.get("win_prob")
        if prob is None:
            continue
        outcome = 1 if h["status"] == "won" else 0
        contribs.append((prob - outcome) ** 2)
    if not contribs:
        return None
    return sum(contribs) / len(contribs)


def calibration_buckets(history: list, n_bins: int = 5) -> list[dict]:
    """Бакетим прогнозы по predicted_prob и считаем actual hit rate.
    Возвращает [{bucket_low, bucket_high, predicted_avg, actual_rate, count}, ...]
    """
    edges = [0.5 + i * (0.5 / n_bins) for i in range(n_bins + 1)]  # 0.5..1.0
    buckets = []
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        items = [
            h for h in history
            if h.get("status") in ("won", "lost")
            and h.get("win_prob") is not None
            and lo <= h["win_prob"] < hi + (0.001 if i == n_bins - 1 else 0)
        ]
        if not items:
            buckets.append({
                "bucket_low": lo, "bucket_high": hi,
                "predicted_avg": (lo + hi) / 2,
                "actual_rate": None, "count": 0,
            })
            continue
        wins = sum(1 for h in items if h["status"] == "won")
        avg_pred = sum(h["win_prob"] for h in items) / len(items)
        buckets.append({
            "bucket_low": lo, "bucket_high": hi,
            "predicted_avg": avg_pred,
            "actual_rate": wins / len(items),
            "count": len(items),
        })
    return buckets


def extract_predicted_winner(analysis: str) -> str:
    """Достаём имя предсказанного победителя из вывода LLM."""
    if not analysis:
        return ""
    patterns = [
        r"Победитель:\s*\*\*([^*\n]+)\*\*",
        r"\*\*Победитель:\s*([^*\n]+)\*\*",
        r"Winner:\s*\*\*([^*\n]+)\*\*",
        r"Победит[ьея]+\s*\*\*([^*\n]+)\*\*",
    ]
    for p in patterns:
        m = re.search(p, analysis, re.IGNORECASE)
        if m:
            return m.group(1).strip().split("—")[0].split("(")[0].strip()
    return ""


def _name_match(a: str, b: str) -> bool:
    """Толерантное сравнение имён бойцов."""
    if not a or not b:
        return False
    na = re.sub(r"[^a-zа-я0-9 ]", "", a.lower()).strip()
    nb = re.sub(r"[^a-zа-я0-9 ]", "", b.lower()).strip()
    if not na or not nb:
        return False
    if na == nb:
        return True
    # Match by last name + intersection
    ta, tb = set(na.split()), set(nb.split())
    return len(ta & tb) >= 1 and (na in nb or nb in na or len(ta & tb) >= 2)


def auto_resolve_predictions(espn_events: list) -> int:
    """Идём по pending прогнозам, ищем завершённые бои в ESPN, проставляем won/lost.
    Возвращает кол-во резолвнутых."""
    if not espn_events:
        return 0
    resolved = 0
    for h in st.session_state.history:
        if h.get("status") != "pending":
            continue
        # Найти соответствующий бой в ESPN
        for ev in espn_events:
            for f in ev.get("fights", []):
                if not f.get("completed"):
                    continue
                a_name = (f.get("a") or {}).get("name", "")
                b_name = (f.get("b") or {}).get("name", "")
                if not (_name_match(h.get("fighter_a", ""), a_name) or
                        _name_match(h.get("fighter_a", ""), b_name)):
                    continue
                if not (_name_match(h.get("fighter_b", ""), a_name) or
                        _name_match(h.get("fighter_b", ""), b_name)):
                    continue
                # Нашли бой
                actual_winner = ""
                if (f.get("a") or {}).get("winner"):
                    actual_winner = a_name
                elif (f.get("b") or {}).get("winner"):
                    actual_winner = b_name
                if not actual_winner:
                    break
                predicted = h.get("predicted_winner") or extract_predicted_winner(h.get("analysis", ""))
                if not predicted:
                    break
                h["predicted_winner"] = predicted
                h["actual_winner"] = actual_winner
                h["actual_method"] = f.get("method", "")
                h["status"] = "won" if _name_match(predicted, actual_winner) else "lost"
                h["resolved_at"] = datetime.now().isoformat()
                resolved += 1
                break
            else:
                continue
            break
    if resolved > 0:
        persist_history()
    return resolved


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
    st.markdown(
        f"<div style='border-bottom:3px solid {UFC_RED};padding-bottom:10px;margin-bottom:14px'>"
        f"<h2 style='color:{TEXT};margin:0;font-family:Oswald,sans-serif;"
        f"letter-spacing:1.5px;font-weight:700'>🥊 OCTAGON ORACLE</h2>"
        f"<div style='color:{MUTED};font-size:0.72rem;letter-spacing:2px;"
        f"text-transform:uppercase;margin-top:4px'>UFC AI Predictor</div>"
        f"</div>",
        unsafe_allow_html=True)
    st.markdown("---")

    PAGES = [
        "🏠 Home",
        "🔴 Live Card",
        "👥 Fight Base",
        "🔮 Predictor",
        "🧠 Knowledge Base",
        "🎓 Fine-Tuning",
        "📊 Analytics",
        "⚖️ Weight Cut",
        "📚 History & Accuracy",
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
    st.subheader("📋 Watchlist")
    st.caption("Бои под наблюдением")
    if not st.session_state.watchlist:
        st.markdown("<span style='color:#666;font-size:0.85rem'>"
                    "Пусто. Добавь бой кнопкой 👁️ из Live Card или Home.</span>",
                    unsafe_allow_html=True)
    else:
        for wi, w in enumerate(st.session_state.watchlist):
            col_a, col_b = st.columns([4, 1])
            col_a.markdown(
                f"<div class='watch-item'><b>{w['a']}</b><br>"
                f"<span style='color:#666'>vs</span> <b>{w['b']}</b><br>"
                f"<span style='color:#888;font-size:0.7rem'>{w.get('event','')}</span></div>",
                unsafe_allow_html=True)
            if col_b.button("✕", key=f"rmw_{wi}"):
                st.session_state.watchlist.pop(wi)
                st.rerun()
        if st.button("→ В Predictor (последний)", use_container_width=True):
            w = st.session_state.watchlist[0]
            st.session_state.preselect = {
                "a": w["a"], "b": w["b"], "event": w.get("event", ""),
                "rounds": w.get("rounds", 3),
                "title_fight": w.get("title_fight", False),
            }
            st.session_state.page = "🔮 Predictor"
            st.rerun()

    st.markdown("---")
    if st.button("🔄 Сбросить события к дефолту"):
        st.session_state.events = DEFAULT_EVENTS
        persist_events()
        st.success("Events updated.")
        st.rerun()
    st.caption("📊 Данные: ESPN API (real-time) + ufcstats.com / FightMetric.")


# ---------- HEADER ----------
st.markdown(
    f"""<div class='hero'>
    <h1>🥊 UFC AI Предиктор <span style='color:{UFC_RED}'>|</span> Octagon Oracle</h1>
    <p>Глубокая аналитика. Умные ставки. Точные прогнозы.</p>
    </div>""",
    unsafe_allow_html=True,
)


# =================================================================
# UFC.com-style fight card renderer
# =================================================================
# Inline SVG силуэт — всегда работает, без интернета
PLACEHOLDER_HEADSHOT = (
    "data:image/svg+xml;utf8,"
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>"
    "<rect width='100' height='100' fill='%23f0f0f0'/>"
    "<circle cx='50' cy='38' r='16' fill='%23b8b8b8'/>"
    "<path d='M22 92 Q22 64 50 64 Q78 64 78 92 Z' fill='%23b8b8b8'/>"
    "</svg>"
)


def _safe(s, default=""):
    return s if s else default


def _slugify(name: str) -> str:
    """Кириллицу убираем, остаётся только ASCII slug — UFC.com использует такой."""
    s = (name or "").lower()
    s = re.sub(r"['`’]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _photo_with_fallback(fighter: dict) -> tuple[str, str]:
    """Возвращает (src, onerror_attr) с каскадом:
    1. ESPN headshot (если в API был)
    2. ESPN CDN по athlete_id
    3. UFC.com CDN по slug
    4. SVG placeholder
    """
    name = fighter.get("name", "")
    espn_id = fighter.get("id")
    primary = fighter.get("photo")  # уже содержит ESPN URL (с fallback на CDN/id)

    # Кандидаты в порядке убывания приоритета
    chain = []
    if primary:
        chain.append(primary)
    if espn_id and (not primary or "espncdn" not in str(primary)):
        chain.append(f"https://a.espncdn.com/i/headshots/mma/players/full/{espn_id}.png")
    slug = _slugify(name)
    if slug:
        # UFC.com Athlete Profile CDN — bio image
        chain.append(
            f"https://dmxg5wxfqgb4u.cloudfront.net/styles/athlete_bio_full_body/"
            f"s3/image/{slug}.png"
        )
        # UFC.com general athletes CDN
        chain.append(
            f"https://www.ufc.com/themes/custom/ufc/assets/img/athletes/{slug}.png"
        )
    chain.append(PLACEHOLDER_HEADSHOT)

    src = chain[0]
    # Строим вложенный onerror chain
    onerror_js = ""
    for i in range(len(chain) - 1, 0, -1):
        next_url = chain[i].replace("'", "\\'")
        if i == len(chain) - 1:
            onerror_js = f"this.onerror=null;this.src='{next_url}';"
        else:
            onerror_js = (
                f"this.onerror=function(){{{onerror_js}}};"
                f"this.src='{next_url}';"
            )
    return src, onerror_js


def render_ufc_bout(fight: dict, idx: str, allow_actions: bool = True,
                     hide_photos: bool = False):
    """Рендер одного боя в UFC.com-стиле.
    fight: {weight_class, a:{name,country,flag_url,photo,rank,winner}, b:{...},
            odds_a, odds_b, status, completed}
    """
    a = fight.get("a", {})
    b = fight.get("b", {})
    wc = fight.get("weight_class", "Bout")

    # photos с каскадом fallback: ESPN → UFC.com → placeholder
    photo_a, onerror_a = _photo_with_fallback(a)
    photo_b, onerror_b = _photo_with_fallback(b)

    # flags
    flag_a = (f"<img src='{a['flag_url']}' alt=''/>"
              if a.get("flag_url") else "🌍")
    flag_b = (f"<img src='{b['flag_url']}' alt=''/>"
              if b.get("flag_url") else "🌍")

    rank_a = f"<div class='rank'>#{a['rank']}</div>" if a.get("rank") else ""
    rank_b = f"<div class='rank'>#{b['rank']}</div>" if b.get("rank") else ""

    name_a = a.get("name", "TBD")
    name_b = b.get("name", "TBD")

    # winner highlight + galochka
    winner_a_cls = "ufc-winner-badge" if a.get("winner") else ""
    winner_b_cls = "ufc-winner-badge" if b.get("winner") else ""
    check_a = "<span class='ufc-check'>✓</span> " if a.get("winner") else ""
    check_b = " <span class='ufc-check'>✓</span>" if b.get("winner") else ""
    winner_a = f"{check_a}{winner_a_cls}" if False else winner_a_cls  # сохраняем имя
    winner_b = winner_b_cls

    odds_block = ""
    if fight.get("odds_a") or fight.get("odds_b"):
        odds_block = f"""<div class='ufc-odds-row'>
            <span class='o fav'>{_safe(fight.get('odds_a'), '—')}</span>
            <span class='lbl'>ODDS</span>
            <span class='o dog'>{_safe(fight.get('odds_b'), '—')}</span>
        </div>"""

    status_block = ""
    if fight.get("completed"):
        method = fight.get("method", "FINAL") or "FINAL"
        winner_name = (a.get("name") if a.get("winner")
                       else b.get("name") if b.get("winner") else None)
        if winner_name:
            status_block = (
                f"<div class='ufc-status'>"
                f"<b>{winner_name}</b> def. opponent · {method}"
                f"</div>"
            )
        else:
            status_block = f"<div class='ufc-status'>FINAL · {method}</div>"
    elif fight.get("status") and "Scheduled" not in fight.get("status", ""):
        status_block = f"<div class='ufc-status'>{fight.get('status','').upper()}</div>"

    # Win-photo overlay
    photo_overlay_a = "<div class='win-overlay'>✓</div>" if a.get("winner") else ""
    photo_overlay_b = "<div class='win-overlay'>✓</div>" if b.get("winner") else ""
    photo_class_a = "headshot-wrap" + (" winner" if a.get("winner") else "")
    photo_class_b = "headshot-wrap" + (" winner" if b.get("winner") else "")

    if hide_photos:
        photo_block_a = ""
        photo_block_b = ""
    else:
        photo_block_a = (f"<div class='{photo_class_a}'>"
                        f"<img class='headshot' src='{photo_a}' alt='' "
                        f"onerror=\"{onerror_a}\"/>"
                        f"{photo_overlay_a}</div>")
        photo_block_b = (f"<div class='{photo_class_b}'>"
                        f"<img class='headshot' src='{photo_b}' alt='' "
                        f"onerror=\"{onerror_b}\"/>"
                        f"{photo_overlay_b}</div>")

    # Собираем HTML БЕЗ переносов/отступов чтобы markdown не превратил в codeblock
    html = (
        f"<div class='ufc-bout'>"
        f"<div class='ufc-bout-label'>{wc}</div>"
        f"<div class='ufc-row'>"
            f"<div class='ufc-fighter left'>"
                f"<div class='info'>"
                    f"{rank_a}"
                    f"<div class='name {winner_a}'>{check_a}{name_a}</div>"
                    f"<div class='country'>{flag_a} {a.get('country','')}</div>"
                f"</div>"
                f"{photo_block_a}"
            f"</div>"
            f"<div class='ufc-vs'>VS</div>"
            f"<div class='ufc-fighter right'>"
                f"{photo_block_b}"
                f"<div class='info'>"
                    f"{rank_b}"
                    f"<div class='name {winner_b}'>{name_b}{check_b}</div>"
                    f"<div class='country'>{flag_b} {b.get('country','')}</div>"
                f"</div>"
            f"</div>"
        f"</div>"
        f"{odds_block}"
        f"{status_block}"
        f"</div>"
    )
    st.markdown(html, unsafe_allow_html=True)

    if allow_actions:
        ac1, ac2 = st.columns(2)
        if ac1.button(f"🔮 Предсказать", key=f"pred_{idx}", use_container_width=True):
            st.session_state.preselect = {
                "a": name_a, "b": name_b, "event": fight.get("event", ""),
                "rounds": fight.get("rounds", 5 if fight.get("title_fight") else 3),
                "title_fight": fight.get("title_fight", False),
            }
            st.session_state.page = "🔮 Predictor"
            st.rerun()
        if ac2.button(f"👁️ В Watchlist", key=f"watch_{idx}", use_container_width=True):
            entry = {"a": name_a, "b": name_b,
                     "event": fight.get("event", ""),
                     "rounds": fight.get("rounds", 3),
                     "title_fight": fight.get("title_fight", False)}
            if entry not in st.session_state.watchlist:
                st.session_state.watchlist.append(entry)
                st.toast(f"Добавлено: {name_a} vs {name_b}")
                st.rerun()


def render_ufc_card_header(title: str, date_str: str, venue: str, status: str = ""):
    html = (
        f"<div class='ufc-card-header'>"
        f"<h2 class='title'>{title}</h2>"
        f"<div class='meta'>{date_str}<br>{venue}<br>{status}</div>"
        f"</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def local_event_to_fights(ev: dict) -> list:
    """Конвертим локальный event в формат для render_ufc_bout (без фото)."""
    out = []
    for ft in ev.get("fights", []):
        if isinstance(ft, dict) and "winner" in ft:
            a_name, b_name = ft["a"], ft["b"]
            winner = ft.get("winner")
            out.append({
                "weight_class": ev.get("division", "Bout"),
                "a": _local_fighter_block(a_name, winner == a_name),
                "b": _local_fighter_block(b_name, winner == b_name),
                "odds_a": None, "odds_b": None,
                "status": ft.get("method", "FINAL"),
                "completed": True,
                "event": ev["title"],
                "title_fight": ev.get("title_fight", False),
                "rounds": 5 if ev.get("title_fight") else 3,
            })
        else:
            a_name, b_name = (ft[0], ft[1]) if isinstance(ft, (list, tuple)) \
                else (ft.get("a"), ft.get("b"))
            out.append({
                "weight_class": ev.get("division", "Bout"),
                "a": _local_fighter_block(a_name),
                "b": _local_fighter_block(b_name),
                "odds_a": None, "odds_b": None,
                "status": "",
                "completed": False,
                "event": ev["title"],
                "title_fight": ev.get("title_fight", False),
                "rounds": 5 if ev.get("title_fight") else 3,
            })
    return out


def _local_fighter_block(name: str, winner: bool = False) -> dict:
    f = get_fighter(name) or {}
    return {
        "name": name, "country": f.get("country", ""),
        "flag_url": None, "photo": None, "rank": None, "winner": winner,
    }


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
            if isinstance(ft, (list, tuple)):
                a, b = ft[0], ft[1]
            else:
                a, b = ft.get("a"), ft.get("b")
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
# Event Predictor (LLM helper для одного боя)
# =================================================================
def predict_single_fight(fight: dict, event_title: str, model: str,
                          api_key: str, base_url: str,
                          use_rag: bool = True) -> str:
    """LLM-прогноз одного боя с разделами Прогноз / Ставка / Риски."""
    a = fight.get("a", {})
    b = fight.get("b", {})
    name_a = a.get("name", "Fighter A")
    name_b = b.get("name", "Fighter B")
    wc = fight.get("weight_class", "")
    odds_a = fight.get("odds_a") or "—"
    odds_b = fight.get("odds_b") or "—"

    # Если есть в локальной базе — добавим стату
    fa = get_fighter(name_a) or {}
    fb = get_fighter(name_b) or {}

    # RAG retrieval
    rag_block = ""
    if use_rag:
        try:
            from rag_utils import retrieve_relevant_context
            r = retrieve_relevant_context(
                query=f"{name_a} vs {name_b} {wc} matchup prediction",
                fighter_a=name_a, fighter_b=name_b, top_k=5,
            )
            if r.get("context_text"):
                rag_block = (
                    "\n\n=== KNOWLEDGE BASE (real data, ground your analysis here) ===\n"
                    + r["context_text"]
                    + "\n=== END KB ===\n"
                )
        except Exception:
            pass

    def _stat_block(name, f):
        if not f:
            return f"{name}: данных в локальной базе нет — используй общие знания о бойце."
        return (
            f"{name} ({f.get('country','')}, {f.get('age','?')} лет, {f.get('record','?')}): "
            f"SLpM {f.get('SLpM','?')}, SApM {f.get('SApM','?')}, "
            f"StrAcc {f.get('StrAcc','?')}%, StrDef {f.get('StrDef','?')}%, "
            f"TDAvg {f.get('TDAvg','?')}, TDDef {f.get('TDDef','?')}%, "
            f"SubAvg {f.get('SubAvg','?')}. Стиль: {f.get('style','?')}. "
            f"Сильные: {', '.join(f.get('strengths',[]))}. "
            f"Слабые: {', '.join(f.get('weaknesses',[]))}."
        )

    user_msg = f"""Дай прогноз на бой UFC.

ИВЕНТ: {event_title}
ВЕСОВАЯ: {wc}
БОЙ: {name_a} vs {name_b}
ODDS: {name_a} {odds_a} / {name_b} {odds_b}

ДАННЫЕ:
{_stat_block(name_a, fa)}
{_stat_block(name_b, fb)}
{rag_block}

ФОРМАТ ОТВЕТА (строго в этом виде, используй markdown):

### 🎯 ПРОГНОЗ
Победитель: **[Имя]** — XX% уверенности.
Метод: KO/TKO XX% · Submission XX% · Decision XX%.
Раунд (если финиш): R[1-5].

### 📊 АНАЛИТИКА
2-3 коротких абзаца. Стилевой матч-ап, ключевые статы (с цифрами), форма, размер/reach, кардио, менталка. Используй MMA-сленг.

### 💰 ЛУЧШАЯ СТАВКА
Конкретно: что брать (Moneyline / Method / Round / Total). Где value/edge. 1-2 строки.

### ⚠️ РИСКИ
Жёстко перечисли 2-4 причины почему ставка может не зайти. Не разводи воду — конкретные сценарии (нокаут со встречки, sub в партере, размер фаворита просядет на дистанции и т.д.).

Будь острым и уверенным."""

    if not api_key:
        return "❌ Установи API Key в сайдбаре."
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": SYSTEM_PROMPT},
                      {"role": "user", "content": user_msg}],
            temperature=0.5, max_tokens=1500,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"❌ Ошибка LLM: {e}"


# =================================================================
# Event Predictor режим — перехватывает routing если установлен
# =================================================================
if st.session_state.get("event_to_predict"):
    ev = st.session_state.event_to_predict

    top_l, top_r = st.columns([5, 1])
    with top_l:
        st.markdown(f"## 🎯 Event Predictor")
    with top_r:
        if st.button("← Назад", use_container_width=True):
            st.session_state.event_to_predict = None
            st.session_state.pop("event_predictions", None)
            st.rerun()

    render_ufc_card_header(
        ev["title"], ev["date"], ev.get("venue", ""),
        f"{len(ev['fights'])} BOUTS · AI ПРОГНОЗ")

    fights = ev["fights"]
    st.markdown(
        f"<p style='color:{MUTED};margin-top:14px'>"
        f"Открой каждый бой — внутри готовый прогноз, лучшая ставка и риски."
        f"</p>", unsafe_allow_html=True)

    # Кэш прогнозов в session_state
    if "event_predictions" not in st.session_state:
        st.session_state.event_predictions = {}

    if st.button("⚡ Сгенерировать прогнозы для всех боёв",
                 use_container_width=True):
        if not api_key:
            st.error("Сначала введи API Key в сайдбаре.")
        else:
            progress = st.progress(0)
            for fi, fight in enumerate(fights):
                key = f"{ev['title']}::{fight['a'].get('name','?')}::{fight['b'].get('name','?')}"
                if key not in st.session_state.event_predictions:
                    with st.spinner(f"Анализирую {fight['a'].get('name')} vs {fight['b'].get('name')}..."):
                        st.session_state.event_predictions[key] = predict_single_fight(
                            fight, ev["title"], model, api_key, base_url)
                progress.progress((fi + 1) / len(fights))
            st.success("Готово!")
            st.rerun()

    st.markdown("---")

    for fi, fight in enumerate(fights):
        a_name = fight["a"].get("name", "TBD")
        b_name = fight["b"].get("name", "TBD")
        wc = fight.get("weight_class", "Bout")
        key = f"{ev['title']}::{a_name}::{b_name}"
        cached = st.session_state.event_predictions.get(key)
        title = f"#{fi+1}  {wc.upper()}  ·  {a_name}  VS  {b_name}"

        with st.expander(title, expanded=False):
            render_ufc_bout(fight, f"evp_{fi}", allow_actions=False, hide_photos=False)

            cb1, cb2 = st.columns([1, 1])
            if cb1.button("🔮 Сгенерировать прогноз", key=f"gen_{fi}",
                          use_container_width=True):
                if not api_key:
                    st.error("Введи API Key в сайдбаре.")
                else:
                    with st.spinner("Анализ..."):
                        st.session_state.event_predictions[key] = predict_single_fight(
                            fight, ev["title"], model, api_key, base_url)
                    st.rerun()
            if cached and cb2.button("🔄 Перегенерировать", key=f"regen_{fi}",
                                     use_container_width=True):
                with st.spinner("Анализ..."):
                    st.session_state.event_predictions[key] = predict_single_fight(
                        fight, ev["title"], model, api_key, base_url)
                st.rerun()

            if cached:
                st.markdown("---")
                st.markdown(cached)
                if st.button("💾 Сохранить в History", key=f"savehist_{fi}",
                             use_container_width=True):
                    probs_e = extract_probabilities(cached)
                    st.session_state.history.insert(0, {
                        "id": str(int(datetime.now().timestamp())),
                        "fa": a_name, "fb": b_name,
                        "fighter_a": a_name, "fighter_b": b_name,
                        "event": ev["title"], "weight_class": wc,
                        "rounds": 5 if "main" in title.lower() or "title" in wc.lower() else 3,
                        "title_fight": False,
                        "analysis": cached, "model": model,
                        "ts": datetime.now().isoformat(timespec="seconds"),
                        "timestamp": datetime.now().isoformat(),
                        "main_bet": extract_main_bet(cached),
                        "predicted_winner": extract_predicted_winner(cached),
                        "win_prob": probs_e["win_prob"],
                        "ko_prob": probs_e["ko_prob"],
                        "sub_prob": probs_e["sub_prob"],
                        "dec_prob": probs_e["dec_prob"],
                        "tracked": True,
                        "status": "pending",
                        "odds": None, "stake": None,
                    })
                    persist_history()
                    st.success("Сохранено в History.")
            else:
                st.info("Прогноз ещё не сгенерирован. Кликни 🔮 чтобы запустить ИИ.")

    st.stop()  # не рендерим остальные страницы


# =================================================================
# PAGE: HOME
# =================================================================
if page == "🏠 Home":
    stats = history_stats()
    from datetime import timedelta
    today = date.today()

    # ---------- REAL-TIME ESPN ----------
    # Берём диапазон: последние 60 дней + следующие 120 дней
    start_str = (today - timedelta(days=60)).strftime("%Y%m%d")
    end_str = (today + timedelta(days=120)).strftime("%Y%m%d")

    live_error = None
    espn_events = []
    try:
        from live_data import get_events_range
        with st.spinner("📡 Загружаю real-time данные с ESPN..."):
            espn_events = get_events_range(start_str, end_str)
    except Exception as e:
        live_error = str(e)

    # Авто-классификация past/upcoming
    def _is_past(ev):
        # Если хоть один бой completed — считаем event прошедшим
        if any(f.get("completed") for f in ev.get("fights", [])):
            return True
        try:
            evd = datetime.fromisoformat(ev["date"].replace("Z", "+00:00")).date()
            return evd < today
        except Exception:
            return False

    upcoming_live = sorted(
        [e for e in espn_events if not _is_past(e)],
        key=lambda e: e["date"])
    past_live = sorted(
        [e for e in espn_events if _is_past(e)],
        key=lambda e: e["date"], reverse=True)

    # Локальная база как фолбэк
    upcoming_local = sorted(
        [e for e in st.session_state.events if e.get("status") != "past"],
        key=lambda e: e["date"])
    past_local = sorted(
        [e for e in st.session_state.events if e.get("status") == "past"],
        key=lambda e: e["date"], reverse=True)

    use_live = bool(espn_events) and not live_error
    upcoming = upcoming_live if use_live else upcoming_local
    past = past_live if use_live else past_local

    # ---------- АВТО-РЕЗОЛВ ПРОГНОЗОВ ----------
    auto_resolved = 0
    if use_live:
        auto_resolved = auto_resolve_predictions(espn_events)
        if auto_resolved > 0:
            stats = history_stats()  # пересчёт после резолва

    # ---------- ПРОДАЮЩИЙ HERO STATS BLOCK ----------
    total_predicted = len(st.session_state.history)
    won = stats["won"]
    lost = stats["lost"]
    pending = stats["pending"]
    accuracy = stats["accuracy"]
    next_event = upcoming[0] if upcoming else None

    # Countdown до ближайшего ивента
    countdown_str = "—"
    next_title = "—"
    if next_event:
        try:
            if "fights" in next_event and isinstance(next_event["fights"][0].get("a"), dict):
                next_title = next_event.get("name", "UFC")
                ev_dt = datetime.fromisoformat(next_event["date"].replace("Z", "+00:00"))
            else:
                next_title = next_event.get("title", "UFC")
                ev_dt = datetime.fromisoformat(next_event["date"])
            delta = ev_dt.replace(tzinfo=None) - datetime.now()
            days = delta.days
            hours = delta.seconds // 3600
            if days > 0:
                countdown_str = f"{days}д {hours}ч"
            elif hours > 0:
                countdown_str = f"{hours}ч"
            else:
                countdown_str = "СКОРО"
        except Exception:
            countdown_str = ""

    acc_str = f"{accuracy:.0f}%" if accuracy is not None else "—"
    acc_caption = f"{won}W · {lost}L" if accuracy is not None else "нет данных"

    st.markdown(
        f"""
<div class='hero-stats'>
    <div class='hs-card hs-primary'>
        <div class='hs-label'>🎯 ТОЧНОСТЬ ИИ</div>
        <div class='hs-value'>{acc_str}</div>
        <div class='hs-sub'>{acc_caption}</div>
    </div>
    <div class='hs-card hs-won'>
        <div class='hs-label'>🟢 ЗАШЛО</div>
        <div class='hs-value'>{won}</div>
        <div class='hs-sub'>прогнозов в плюс</div>
    </div>
    <div class='hs-card hs-lost'>
        <div class='hs-label'>🔴 НЕ ЗАШЛО</div>
        <div class='hs-value'>{lost}</div>
        <div class='hs-sub'>в минус</div>
    </div>
    <div class='hs-card hs-pending'>
        <div class='hs-label'>⏳ ОЖИДАЮТ</div>
        <div class='hs-value'>{pending}</div>
        <div class='hs-sub'>боёв впереди</div>
    </div>
    <div class='hs-card hs-event'>
        <div class='hs-label'>📅 СЛЕДУЮЩИЙ ИВЕНТ</div>
        <div class='hs-value' style='font-size:1.4rem;line-height:1.1'>{countdown_str}</div>
        <div class='hs-sub' style='font-size:0.7rem;
             white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>{next_title[:40]}</div>
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

    if auto_resolved > 0:
        st.success(f"✅ Авто-резолв: {auto_resolved} прогнозов обновлено по итогам ESPN.")

    st.markdown("---")

    # Two-column layout: events left, history analytics right
    left, right = st.columns([2, 1])

    with left:
        if live_error:
            st.warning(f"⚠️ ESPN недоступен ({live_error[:80]}). Показываю локальную базу.")
        elif use_live:
            st.success("📡 Real-time данные с ESPN · Auto-refresh 5 мин")

        def _render_event_block(ev, idx_prefix, allow_actions):
            """Render одного event-а из live или local формата (без фото на Home)."""
            is_espn = ("fights" in ev and ev["fights"]
                       and isinstance(ev["fights"][0], dict)
                       and "a" in ev["fights"][0]
                       and isinstance(ev["fights"][0]["a"], dict))
            if is_espn:
                try:
                    dt = datetime.fromisoformat(ev["date"].replace("Z", "+00:00"))
                    date_str = dt.strftime("%a, %b %d, %Y")
                except Exception:
                    date_str = ev.get("date", "")
                event_title = ev.get("name", "UFC")
                event_meta = ev.get("venue", "")
                fights = ev["fights"]
                tag = "FINAL" if any(f.get("completed") for f in fights) else f"{len(fights)} BOUTS"
            else:
                date_str = ev["date"]
                event_title = ev["title"]
                event_meta = ev["location"]
                fights = local_event_to_fights(ev)
                tag = ("FINAL" if ev.get("status") == "past"
                       else ("TITLE FIGHT" if ev.get("title_fight") else ""))

            render_ufc_card_header(event_title, date_str, event_meta, tag)

            # Кнопка "Предсказать весь кард" — только для предстоящих
            if allow_actions:
                if st.button(f"🔮 Предсказать весь кард",
                             key=f"predcard_{idx_prefix}",
                             use_container_width=True):
                    st.session_state.event_to_predict = {
                        "title": event_title,
                        "date": date_str,
                        "venue": event_meta,
                        "fights": fights,
                    }
                    st.rerun()

            for fi, fight in enumerate(fights):
                fight["event"] = event_title
                render_ufc_bout(fight, f"{idx_prefix}_{fi}",
                                allow_actions=allow_actions, hide_photos=True)

        st.markdown("### 🔥 Ближайшие события")
        st.caption("UFC.com-style карточки. Кликни 🔮 чтобы предсказать")
        if not upcoming:
            st.info("Нет ближайших событий.")
        for ei, ev in enumerate(upcoming):
            _render_event_block(ev, f"home_up_{ei}", allow_actions=True)

        st.markdown("---")
        st.markdown("### 📜 Прошедшие события")
        st.caption("Победитель отмечен зелёной галочкой ✓ + метод финиша")
        if not past:
            st.info("Нет прошедших событий.")
        for ei, ev in enumerate(past):
            _render_event_block(ev, f"home_past_{ei}", allow_actions=False)

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
            pie.update_layout(paper_bgcolor=BG, font=dict(color=TEXT),
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
# PAGE: LIVE CARD (real-time ESPN)
# =================================================================
elif page == "🔴 Live Card":
    st.markdown("## 🔴 Live Card — Real-time данные ESPN")
    st.caption("Реальные данные с публичного ESPN API: фото, флаги, odds, статус. "
               "Кэш 5 минут. Источник: site.api.espn.com")

    rc1, rc2 = st.columns([1, 5])
    if rc1.button("🔄 Обновить"):
        st.cache_data.clear()
        st.rerun()

    try:
        live_events = get_live_events()
    except Exception as e:
        st.error(f"❌ Не удалось получить данные с ESPN: {e}")
        st.info("Проверь интернет-соединение. Локальная база на главной работает офлайн.")
        live_events = []

    if not live_events:
        st.warning("ESPN не вернул событий. Возможно, между ивентами.")
    for ei, ev in enumerate(live_events):
        # формат даты
        try:
            dt = datetime.fromisoformat(ev["date"].replace("Z", "+00:00"))
            date_str = dt.strftime("%a, %b %d, %Y · %H:%M UTC")
        except Exception:
            date_str = ev.get("date", "")
        render_ufc_card_header(
            ev["name"], date_str, ev.get("venue", ""),
            f"{len(ev['fights'])} BOUTS")
        for fi, fight in enumerate(ev["fights"]):
            fight["event"] = ev["name"]
            render_ufc_bout(fight, f"live_{ei}_{fi}")


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

    st.markdown("### 📚 RAG Knowledge Base")
    rag_c1, rag_c2 = st.columns([3, 1])
    use_rag = rag_c1.toggle(
        "Использовать Knowledge Base (исторические бои + профили)",
        value=True,
        help="Подмешивает в промпт релевантные документы из ChromaDB.",
    )
    rag_top_k = rag_c2.slider("Top-K", 3, 10, 6, label_visibility="collapsed")

    track_for_calibration = st.toggle(
        "📊 Track this prediction for accuracy evaluation",
        value=True,
        help="Авто-сохраняет прогноз в History с вероятностями. "
             "Используется для расчёта Brier Score и калибровки.",
    )

    st.markdown("---")
    if st.button("🔥 ЗАПУСТИТЬ ГЛУБОКИЙ АНАЛИЗ И ПРОГНОЗ", use_container_width=True):
        if not fa or not fb:
            st.error("Выбери обоих бойцов, бро.")
        elif fa.get("name") == fb.get("name"):
            st.error("Один и тот же боец.")
        else:
            ctx = {"rounds": rounds, "title_fight": title_fight,
                   "division": fa.get("division", "—"), "event": event_name}

            # ---------- RAG retrieval ----------
            rag_result = {"context_text": "", "sources": [], "raw": []}
            if use_rag:
                try:
                    from rag_utils import retrieve_relevant_context
                    with st.spinner("🧠 Ретриверю knowledge base..."):
                        query = (
                            f"{fa['name']} vs {fb['name']} stylistic matchup "
                            f"{fa.get('style', '')} {fb.get('style', '')} "
                            f"{ctx['division']} weight class fight prediction"
                        )
                        rag_result = retrieve_relevant_context(
                            query=query,
                            fighter_a=fa["name"], fighter_b=fb["name"],
                            top_k=rag_top_k,
                        )
                    if rag_result.get("error"):
                        st.warning(f"RAG warning: {rag_result['error']}")
                except Exception as e:
                    st.warning(f"RAG недоступен: {e}")
                    rag_result = {"context_text": "", "sources": [], "raw": []}

            # Подмешиваем RAG-контекст в intel
            enriched_intel = intel
            if rag_result.get("context_text"):
                enriched_intel = (
                    f"{intel}\n\n"
                    f"=== RETRIEVED KNOWLEDGE BASE CONTEXT ===\n"
                    f"Use the following real data and historical fights to ground your analysis. "
                    f"When making stylistic or probabilistic claims, cite relevant past fights "
                    f"in [Source N] format.\n\n"
                    f"{rag_result['context_text']}\n"
                    f"=== END KB CONTEXT ===\n"
                )

            with st.spinner("⏳ Анализируем стили, статистику, форму, менталку..."):
                try:
                    if demo_mode or not api_key:
                        analysis = demo_analysis(fa, fb, ctx, enriched_intel)
                        if not demo_mode and not api_key:
                            st.warning("API key пустой — показываю demo.")
                    else:
                        analysis = get_fight_prediction(fa, fb, ctx, enriched_intel,
                                                       api_key, base_url, model)
                    probs = extract_probabilities(analysis)
                    record = {
                        "fa": fa["name"], "fb": fb["name"],
                        "fighter_a": fa["name"], "fighter_b": fb["name"],
                        "weight_class": fa.get("division", "—"),
                        "event": event_name,
                        "ctx": ctx, "intel": intel, "analysis": analysis,
                        "ts": datetime.now().isoformat(timespec="seconds"),
                        "timestamp": datetime.now().isoformat(timespec="seconds"),
                        "main_bet": extract_main_bet(analysis),
                        "predicted_winner": extract_predicted_winner(analysis),
                        "win_prob": probs["win_prob"],
                        "ko_prob": probs["ko_prob"],
                        "sub_prob": probs["sub_prob"],
                        "dec_prob": probs["dec_prob"],
                        "rag_sources": rag_result.get("sources", []),
                        "rag_raw": rag_result.get("raw", []),
                        "rag_used": use_rag,
                        "tracked": track_for_calibration,
                        "model": model,
                        "status": "pending",
                    }
                    st.session_state.last_analysis = record

                    # Авто-сохранение если включён tracking
                    if track_for_calibration:
                        # Дедуп: не дублируем уже существующий с тем же fa/fb/event
                        already = any(
                            h.get("fa") == record["fa"]
                            and h.get("fb") == record["fb"]
                            and h.get("event") == record["event"]
                            and h.get("ts") == record["ts"]
                            for h in st.session_state.history
                        )
                        if not already:
                            # Без огромного rag_raw в персистентной истории
                            saved = {k: v for k, v in record.items() if k != "rag_raw"}
                            st.session_state.history.insert(0, saved)
                            persist_history()
                            st.toast("📊 Сохранено для трекинга калибровки")
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
            radialaxis=dict(visible=True, range=[0, 100], color=MUTED)),
            paper_bgcolor=BG, font=dict(color=TEXT), height=420,
            margin=dict(t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)

        metrics = ["SLpM", "SApM", "StrAcc", "StrDef", "TDAvg", "TDDef", "SubAvg"]
        bar_df = pd.DataFrame({
            "Метрика": metrics * 2,
            "Значение": [fa.get(m, 0) for m in metrics] + [fb.get(m, 0) for m in metrics],
            "Боец": [fa["name"]] * len(metrics) + [fb["name"]] * len(metrics),
        })
        bfig = px.bar(bar_df, x="Метрика", y="Значение", color="Боец", barmode="group",
                      color_discrete_map={fa["name"]: UFC_RED, fb["name"]: "#000000"})
        bfig.update_layout(paper_bgcolor=BG, plot_bgcolor=BG,
                          font=dict(color=TEXT), height=380, margin=dict(t=10))
        st.plotly_chart(bfig, use_container_width=True)

        st.markdown("---")
        st.markdown("## 🎯 Прогноз ИИ")

        # RAG transparency: что именно ИИ использовал из базы
        if la.get("rag_used") and la.get("rag_raw"):
            with st.expander(
                f"📚 Retrieved Knowledge Base Context "
                f"({len(la['rag_raw'])} документов)",
                expanded=False,
            ):
                st.caption(
                    "ИИ опирался на эти документы из ChromaDB. "
                    "Это grounding-контекст — реальные данные, а не галлюцинации."
                )
                for i, item in enumerate(la["rag_raw"], 1):
                    m = item["meta"]
                    score = item["score"]
                    if m.get("doc_type") == "fighter_profile":
                        title = f"[{i}] 🥋 {m.get('fighter_name')} · score: {score:.3f}"
                    else:
                        title = (
                            f"[{i}] 📜 {m.get('fighter_a')} vs "
                            f"{m.get('fighter_b')} · {m.get('date', '')} · "
                            f"score: {score:.3f}"
                        )
                    st.markdown(f"**{title}**")
                    st.code(item["doc"], language=None)

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
# PAGE: KNOWLEDGE BASE (RAG)
# =================================================================
elif page == "🧠 Knowledge Base":
    try:
        from rag_ui import render_knowledge_base_page
        render_knowledge_base_page()
    except ImportError as e:
        st.error(
            f"❌ RAG модули не установлены: `{e}`. "
            f"Запусти: `pip install -r requirements.txt`"
        )
    except Exception as e:
        st.error(f"❌ Ошибка Knowledge Base: {e}")
        st.exception(e)


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
            radialaxis=dict(visible=True, range=[0, 100], color=MUTED)),
            paper_bgcolor=BG, font=dict(color=TEXT), height=400)
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
# PAGE: HISTORY & ACCURACY (Calibration)
# =================================================================
elif page == "📚 History & Accuracy":
    st.markdown("## 📚 Prediction History & Accuracy")
    st.caption("Все прогнозы автоматически трекаются. Brier Score + калибровка показывают "
               "насколько вероятности модели соответствуют реальности.")

    stats = history_stats()
    history = st.session_state.history

    # ---------- HERO METRICS ----------
    brier = compute_brier_score(history)
    tracked = sum(1 for h in history if h.get("tracked"))
    avg_pred_prob = None
    probs = [h.get("win_prob") for h in history if h.get("win_prob") is not None]
    if probs:
        avg_pred_prob = sum(probs) / len(probs)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("📋 Всего", len(history))
    m2.metric("✅ Зашло", stats["won"])
    m3.metric("❌ Не зашло", stats["lost"])
    m4.metric("🎯 Точность",
              f"{stats['accuracy']:.1f}%" if stats["accuracy"] is not None else "—")
    if brier is not None:
        # Brier interpretation: 0=perfect, 0.25=random, 0.33+=bad
        brier_emoji = "🟢" if brier < 0.18 else "🟡" if brier < 0.25 else "🔴"
        m5.metric(f"{brier_emoji} Brier Score", f"{brier:.3f}",
                  help="Меньше = лучше. 0=идеал, 0.25=случайное угадывание.")
    else:
        m5.metric("Brier Score", "—", help="Появится после первых разрешённых прогнозов.")

    if not history:
        st.info("Пока пусто. Сделай первый прогноз во вкладке 🔮 Predictor — "
                "он автоматически попадёт сюда для оценки точности.")
        st.stop()

    st.markdown("---")

    # ---------- CALIBRATION CHART ----------
    st.markdown("### 📈 Калибровочный график")
    st.caption("Прогнозы группируются по предсказанной вероятности. "
               "Идеал — точки лежат на диагонали (зелёная линия): "
               "если модель сказала «70% вероятность», то такие прогнозы должны "
               "сбываться в ~70% случаев.")

    buckets = calibration_buckets(history, n_bins=5)
    if any(b["count"] > 0 for b in buckets):
        cal_fig = go.Figure()
        # Idealная диагональ
        cal_fig.add_trace(go.Scatter(
            x=[0.5, 1.0], y=[0.5, 1.0],
            mode="lines", name="Идеальная калибровка",
            line=dict(color="#16a34a", dash="dash", width=2),
        ))
        # Точки модели
        xs, ys, sizes, texts = [], [], [], []
        for b in buckets:
            if b["count"] == 0:
                continue
            xs.append(b["predicted_avg"])
            ys.append(b["actual_rate"])
            sizes.append(max(15, min(60, b["count"] * 8)))
            texts.append(f"n={b['count']}<br>pred={b['predicted_avg']:.2f}<br>actual={b['actual_rate']:.2f}")
        cal_fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers+text",
            name="Модель", marker=dict(
                size=sizes, color=UFC_RED,
                line=dict(color="white", width=2),
            ),
            text=[f"n={b['count']}" for b in buckets if b["count"] > 0],
            textposition="top center",
            hovertext=texts, hoverinfo="text",
        ))
        cal_fig.update_layout(
            xaxis=dict(title="Предсказанная вероятность", range=[0.45, 1.05],
                       gridcolor="#eee"),
            yaxis=dict(title="Фактическая частота побед", range=[0, 1.05],
                       gridcolor="#eee"),
            paper_bgcolor=BG, plot_bgcolor=BG,
            font=dict(color=TEXT), height=400, margin=dict(t=10, b=40),
            showlegend=True,
        )
        st.plotly_chart(cal_fig, use_container_width=True)

        # Бакет таблица
        cal_df = pd.DataFrame([
            {
                "Бакет": f"{b['bucket_low']:.2f}–{b['bucket_high']:.2f}",
                "Прогнозов": b["count"],
                "Avg predicted": f"{b['predicted_avg']:.3f}" if b["count"] else "—",
                "Actual win rate": f"{b['actual_rate']:.3f}" if b["actual_rate"] is not None else "—",
                "Δ (calibration error)": (
                    f"{(b['actual_rate'] - b['predicted_avg']):+.3f}"
                    if b["actual_rate"] is not None else "—"
                ),
            } for b in buckets
        ])
        st.dataframe(cal_df, use_container_width=True, hide_index=True)
    else:
        st.info(
            "Калибровочный график появится когда будут разрешённые (won/lost) прогнозы "
            "с извлечёнными вероятностями. Помеченных сейчас: "
            f"**{stats['won'] + stats['lost']}** из **{len(history)}**."
        )

    st.markdown("---")

    # ---------- FILTERS ----------
    st.markdown("### 🔍 Фильтры")
    fc1, fc2, fc3, fc4 = st.columns([2, 2, 2, 1])
    fighter_filter = fc1.text_input(
        "Боец (ищет в любом из двух)", "",
        placeholder="например: Topuria",
    )
    all_wcs = sorted({
        (h.get("weight_class") or h.get("ctx", {}).get("division") or "—")
        for h in history
    })
    wc_filter = fc2.multiselect("Весовая", all_wcs, default=[])
    status_filter = fc3.multiselect(
        "Статус", ["pending", "won", "lost"], default=[],
        help="Пусто = все",
    )
    days_back = fc4.number_input("Последние N дней", 1, 9999, 365)

    # Применяем фильтры
    cutoff = datetime.now() - timedelta(days=int(days_back))
    filtered = []
    for h in history:
        # name
        if fighter_filter:
            ff = fighter_filter.lower()
            if (ff not in (h.get("fa") or "").lower()
                and ff not in (h.get("fb") or "").lower()):
                continue
        # weight class
        wc = h.get("weight_class") or h.get("ctx", {}).get("division") or "—"
        if wc_filter and wc not in wc_filter:
            continue
        # status
        if status_filter and h.get("status", "pending") not in status_filter:
            continue
        # date
        try:
            ts_str = h.get("ts") or h.get("timestamp") or ""
            ts_dt = datetime.fromisoformat(ts_str.replace("Z", ""))
            if ts_dt < cutoff:
                continue
        except Exception:
            pass
        filtered.append(h)

    st.caption(f"Найдено: **{len(filtered)}** из {len(history)}")

    st.markdown("---")

    # ---------- TABLE VIEW ----------
    st.markdown("### 📋 Таблица прогнозов")
    if filtered:
        rows = []
        for h in filtered:
            rows.append({
                "Дата": (h.get("ts") or h.get("timestamp") or "")[:16],
                "Бой": f"{h.get('fa','?')} vs {h.get('fb','?')}",
                "Весовая": h.get("weight_class") or h.get("ctx", {}).get("division") or "—",
                "Прогноз": h.get("predicted_winner", "—") or "—",
                "Win %": f"{int(h['win_prob']*100)}%" if h.get("win_prob") else "—",
                "KO%": f"{int(h['ko_prob']*100)}" if h.get("ko_prob") else "—",
                "Sub%": f"{int(h['sub_prob']*100)}" if h.get("sub_prob") else "—",
                "Dec%": f"{int(h['dec_prob']*100)}" if h.get("dec_prob") else "—",
                "Статус": {"won": "✅", "lost": "❌", "pending": "⏳"}.get(
                    h.get("status", "pending"), "?"),
                "Победил факт.": h.get("actual_winner", "—") or "—",
            })
        df_view = pd.DataFrame(rows)
        st.dataframe(df_view, use_container_width=True, hide_index=True, height=320)

        # Export
        csv = df_view.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Экспорт CSV", csv,
            file_name=f"predictions_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

    st.markdown("---")

    # ---------- DETAIL CARDS / MANUAL MARK ----------
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
            wc = h.get("weight_class") or h.get("ctx", {}).get("division") or "—"
            event = h.get("event") or h.get("ctx", {}).get("event", "—")
            st.caption(
                f"📅 {event} · ⚖️ {wc} · 🤖 {h.get('model','—')} · "
                f"{'📚 RAG ON' if h.get('rag_used') else '📚 RAG OFF'}"
            )

            ic1, ic2, ic3, ic4 = st.columns(4)
            ic1.metric("Прогноз", h.get("predicted_winner", "—") or "—")
            ic2.metric("Win prob",
                       f"{int(h['win_prob']*100)}%" if h.get("win_prob") else "—")
            ic3.metric("Метод",
                       max([
                           ("KO/TKO", h.get("ko_prob") or 0),
                           ("Sub", h.get("sub_prob") or 0),
                           ("Decision", h.get("dec_prob") or 0),
                       ], key=lambda x: x[1])[0]
                       if any([h.get("ko_prob"), h.get("sub_prob"), h.get("dec_prob")])
                       else "—")
            ic4.metric("Статус", status.upper())

            if h.get("status") in ("won", "lost") and h.get("actual_winner"):
                correct = h.get("status") == "won"
                st.markdown(
                    f"**Факт.** Победил: **{h['actual_winner']}**"
                    + (f" · Метод: `{h['actual_method']}`" if h.get('actual_method') else "")
                    + (f" · {'✅ ПРОГНОЗ ВЕРНЫЙ' if correct else '❌ ПРОГНОЗ НЕВЕРНЫЙ'}")
                )

            # Manual outcome buttons
            mc1, mc2, mc3, mc4, mc5 = st.columns(5)
            real_idx = st.session_state.history.index(h)
            if mc1.button("✅ Прогноз верный", key=f"won_{real_idx}"):
                st.session_state.history[real_idx]["status"] = "won"
                st.session_state.history[real_idx]["actual_winner"] = h.get("predicted_winner", "")
                st.session_state.history[real_idx]["resolved_at"] = datetime.now().isoformat()
                persist_history(); st.rerun()
            if mc2.button("❌ Неверный", key=f"lost_{real_idx}"):
                st.session_state.history[real_idx]["status"] = "lost"
                # actual_winner = соперник
                pred = h.get("predicted_winner", "")
                opp = h.get("fb") if pred == h.get("fa") else h.get("fa")
                st.session_state.history[real_idx]["actual_winner"] = opp
                st.session_state.history[real_idx]["resolved_at"] = datetime.now().isoformat()
                persist_history(); st.rerun()
            if mc3.button("↩️ Сбросить", key=f"reset_{real_idx}"):
                for k in ("actual_winner", "actual_method", "resolved_at"):
                    st.session_state.history[real_idx].pop(k, None)
                st.session_state.history[real_idx]["status"] = "pending"
                persist_history(); st.rerun()

            with mc4:
                method_input = st.text_input(
                    "Метод (опц.)", h.get("actual_method", "") or "",
                    key=f"method_{real_idx}", placeholder="KO R2",
                    label_visibility="collapsed",
                )
            if mc5.button("💾 Метод", key=f"savemethod_{real_idx}"):
                st.session_state.history[real_idx]["actual_method"] = method_input
                persist_history(); st.rerun()

            # Bet sizing (опц.)
            with st.expander("💵 Odds / Stake / P&L"):
                oc1, oc2, oc3 = st.columns(3)
                odds = oc1.number_input("Коэф", 1.0, 50.0,
                    float(h.get("odds") or 2.0), key=f"odds_{real_idx}")
                stake = oc2.number_input("Ставка $", 0.0, 10000.0,
                    float(h.get("stake") or 100.0), key=f"stake_{real_idx}")
                if oc3.button("💾", key=f"save_odds_{real_idx}"):
                    st.session_state.history[real_idx]["odds"] = odds
                    st.session_state.history[real_idx]["stake"] = stake
                    if status == "won":
                        st.session_state.history[real_idx]["profit"] = round(stake * (odds - 1), 2)
                    elif status == "lost":
                        st.session_state.history[real_idx]["profit"] = -stake
                    persist_history(); st.rerun()
                if h.get("profit") is not None:
                    color = "bet-won" if h["profit"] > 0 else "bet-lost" if h["profit"] < 0 else "bet-pending"
                    st.markdown(f"**P&L:** <span class='{color}'>${h['profit']:+.2f}</span>",
                                unsafe_allow_html=True)

            if h.get("intel"):
                st.markdown(f"**🧠 Intel:** {h['intel']}")
            st.markdown("---")
            st.markdown(h.get("analysis", ""))

            if st.button("🗑️ Удалить прогноз", key=f"del_{real_idx}"):
                st.session_state.history.pop(real_idx)
                persist_history(); st.rerun()

    st.markdown("---")
    danger = st.checkbox("Подтверждаю — снести всё")
    if st.button("🧹 Очистить всю историю", disabled=not danger):
        st.session_state.history = []
        persist_history(); st.rerun()


# Footer
st.markdown("---")
st.caption(
    f"🥊 Octagon Oracle · Streamlit · "
    f"<span style='color:{UFC_RED}'>Не финансовая рекомендация. Ставь с умом.</span>",
    unsafe_allow_html=True,
)
