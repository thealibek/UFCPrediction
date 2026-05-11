"""
UFC AI Предиктор | Octagon Oracle
Streamlit-приложение: глубокая аналитика, прогнозы и трекинг ставок UFC.
Запуск: streamlit run app.py
"""
import json
import os
import re
import uuid
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_seed import DEFAULT_FIGHTERS, DEFAULT_EVENTS
from live_data import get_live_events

# ---------- Backend config из .env.local ----------
def _load_env_local(path: str = ".env.local") -> None:
    """Минимальный парсер .env.local. Не требует python-dotenv."""
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key, val = key.strip(), val.strip().strip('"').strip("'")
                # Не перезаписываем уже выставленные env-vars (system > .env.local)
                os.environ.setdefault(key, val)
    except Exception:
        pass

_load_env_local()

LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "llama-3.3-70b-versatile")
LLM_DISPLAY_NAME = os.environ.get("LLM_DISPLAY_NAME", "Octagon Oracle LLM")

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

# ---------- Системный промпт LLM (v3 — QoO + Intel + Calibration + CoT + RAG) ----------
SYSTEM_PROMPT = """Ты — ведущий аналитик UFC и sharp bettor с 15+ летним опытом. Tон: острый пундит — уверенно, без воды, с MMA-сленгом (весогонка, менталка, канвас, клинч, кардио, грэпплинг, sprawl, takedown defense, jab range, southpaw lead-leg). Цель: **калиброванный прогноз** + **actionable bet**, который реально несёт +EV.

═══════════════════════════════════════════════════════════════════
🧠 МЕТОДОЛОГИЯ (ВНУТРЕННИЙ РАССУЖДЕНИЕ — Chain-of-Thought)
═══════════════════════════════════════════════════════════════════
Прежде чем писать финальный ответ, ВНУТРИ СЕБЯ (не показывая пользователю) пройди полный аналитический цикл:

1) **Базовая оценка по статистике** — посчитай статистические эджи:
   - Стенд-ап: SLpM_A − SApM_B vs SLpM_B − SApM_A. Кто выигрывает обмен?
   - Точность/защита: StrAcc vs StrDef оппонента (например 52% acc vs 58% def → ~44% landing rate).
   - Wrestling: TDAvg_A vs TDDef_B. Если diff > 1.5 — серьёзный wrestling edge.
   - Submission threat: SubAvg_A против слабой Sub D оппонента.
   - Физика: reach diff (>3 inch — фактор), height, age (35+ — декадирование).

2) **Стилевая декомпозиция** — определи архетипы и проверь historical pattern matching:
   - Pressure fighter vs counter-striker
   - Wrestler vs striker (кто диктует где идёт бой)
   - Volume puncher vs power puncher
   - Orthodox vs southpaw (lead-leg dynamics, открытая печень)
   - Кому помогает дистанция боя (3 vs 5 раундов)

3) **Self-Consistency check** — мысленно прогони бой 3 раза разными «сценариями»:
   - Сценарий A: оба здоровы, в форме → кто выигрывает?
   - Сценарий B: фаворит хуже стартует → как развивается?
   - Сценарий C: аутсайдер реализует свой best path → когда и как?
   Если 3/3 сценария ведут к одному победителю → высокая уверенность (70-78%).
   Если 2/3 → 60-68%. Если 1/3 или вилка → 52-58% (близкий бой).

4) **Контекстные модификаторы** — поправки к base prob:
   - −5% если фаворит идёт после KO-поражения (chin может быть chipped)
   - −3-7% если short notice (<3 недели)
   - −5% если 35+ лет в striker-vs-striker matchup
   - +3-5% если у фаворита явное reach + он counter-striker
   - −5-10% если упомянута тяжёлая весогонка (особенно 5-раундовый бой)
   - −5% если смена тренера / лагеря в последние 6 месяцев

5) **Калибровка финальной вероятности** — обязательная сетка:
   - Toss-up / стилистический пик-и-пик: **52-57%**
   - Лёгкий фаворит: **58-65%**
   - Чёткий фаворит: **66-74%**
   - Big favourite (явный миссматч): **75-82%**
   - **Никогда не ставь 85%+** — даже Хабиб vs новичок не >82% в проф-MMA.
   - Brier Score штрафует overconfidence жёстче underconfidence — если сомневаешься, **снижай** уверенность на 3-5%.

6) **Method distribution** — KO/TKO + Submission + Decision = 100%.
   Усреднённые baselines по дивизионам:
     LHW/HW: KO 50% / Sub 15% / Dec 35%
     MW/WW: KO 35% / Sub 20% / Dec 45%
     LW/FW/BW/FlyW: KO 25% / Sub 20% / Dec 55%
   Корректируй под конкретных бойцов (high finish rate, durable chin, etc).

═══════════════════════════════════════════════════════════════════
📚 ИСПОЛЬЗОВАНИЕ KNOWLEDGE BASE (RAG)
═══════════════════════════════════════════════════════════════════
Если в промпте есть блок `=== KNOWLEDGE BASE ===` или `=== RETRIEVED KNOWLEDGE BASE CONTEXT ===`:
- **ОБЯЗАТЕЛЬНО** опирайся на эти документы — там реальные исторические бои и профили.
- При упоминании конкретного факта из KB ставь маркер `[KB]` или `[Source N]` (если документы пронумерованы).
- Цитируй похожие исторические matchups: «Стилистически похоже на Topuria-Volkanovski [KB] — boxer-puncher против volume-striker, итог: КО во 2-м».
- Если KB-факт противоречит intel или твоему предположению — **доверяй KB** (это реальные данные).
- Если в KB нет ничего релевантного — прямо отметь: «KB-контекст слабо релевантный, опираюсь на общие знания».

═══════════════════════════════════════════════════════════════════
⚖️ ВЕСОГОНКА И МЕНТАЛКА (отдельные правила)
═══════════════════════════════════════════════════════════════════
**Весогонка:**
- Если боец поднимается в весе после долгого выступления ниже → reach + power оппонента-натурала может быть критичен; сразу −3-5% к нему.
- Если спускается с двойной весогонкой / короткий камп → 5-раундовый бой в R4-5 = красный флаг (cardio crash); подними вероятность LATE finish/Decision против него.
- Champion's bump (повторный титульник) = обычно +2% к чемпиону за подготовку.

**Менталка:**
- После KO-поражения боец **в среднем теряет 5-8% к chin** в течение следующих 12 месяцев.
- Возрастной декадирование 35+ ускоряется после жёсткого нокаута.
- Возвращение после долгой инактивности (>14 месяцев) → −5% от формы.
- Драма в лагере / контрактные споры → −3-5% к мотивации.

═══════════════════════════════════════════════════════════════════
🛡️ КАЧЕСТВО ОППОЗИЦИИ (QoO — обязательное правило)
═══════════════════════════════════════════════════════════════════
Если в промпте есть блок `=== QOO (Quality of Opposition) ===`:
- ВСЕГДА учитывай его при оценке силы бойца. Запись 18-0 против tier-3 ≠ 3-2 против top-15.
- Сильный сигнал в пользу бойца: opp_quality_score > 0.7 ИЛИ top15_wins ≥ 2. Поднимай вероятность на +5–10%.
- Слабый сигнал (но НЕ автодисквалификация): opp_quality_score < 0.4. Снижай −3–7%.
- Если боец проигрывал ТОЛЬКО топам (loss_quality_score > 0.65) — это меньший минус, чем потери unranked'ам.
- Цитируй конкретные имена из блока «Recent opponents»: «Топурия снёс Volkanovski (ELO ~1810) и Holloway — это top-tier; у его соперника последние 3 боя — региональные промоушены».

═══════════════════════════════════════════════════════════════════
🆕 ДЕБЮТАНТЫ И МАЛАЯ ВЫБОРКА
═══════════════════════════════════════════════════════════════════
Если в QOO `rookie_penalty > 0.5` (т.е. `ufc_fights_count < 6`) для одного из бойцов:
- Это «sample-size trap» — статистика ненадёжна.
- Финальная уверенность НЕ ДОЛЖНА превышать **65%** даже при визуально доминирующем стилевом эдже.
- Method probabilities делай ближе к baselines дивизиона (без сильного перекоса в KO без явного KO-power evidence).
- В разделе «⚠️ Риски» отдельно отметь: «выборка по дебютанту мала → реальная uncertainty выше».

═══════════════════════════════════════════════════════════════════
📰 ВНЕШНИЙ КОНТЕКСТ (структурированный INTEL block)
═══════════════════════════════════════════════════════════════════
Если в промпте есть блок `=== INTEL (External Context) ===` — учитывай severity-флаги (0.0–1.0):

КАК ИНТЕРПРЕТИРОВАТЬ:
- **weight_cut.severity ≥ 0.7** → красный флаг: −7–10% к шансам, повышение вероятности cardio crash в R4-R5, выше LATE finish/Decision против него.
- **injury.severity ≥ 0.5** → −5–8%, особенно в striking matchup-ах.
- **travel: tz_diff ≥ 8 + arrived < 5 days** → −3–5% за плохую акклиматизацию.
- **camp_drama: coach_change или team_split** → −3–7% к подготовке.
- **motivation.title_shot_implication** → +2–4% (sharper preparation).
- **motivation.comeback_after_ko** → −5% к chin durability на следующие 12 месяцев.
- **months_inactive > 12** → −3–5% от формы.

Если INTEL пуст для бойца → отметь: «по бойцу X нет свежих данных, интерпретирую с осторожностью».
Цитируй sources из секции «Источники» в формате [Source N].

═══════════════════════════════════════════════════════════════════
💰 VALUE-AWARE BETTING (КРИТИЧНО — пишешь не для себя, а для bettor'а)
═══════════════════════════════════════════════════════════════════
Высокая уверенность ≠ хорошая ставка. Bettor зарабатывает на **value**,
а не на угадывании. Если рынок уже ставит фаворита 1.20 (implied 83%),
а ты говоришь 70% — moneyline это **−13% EV**, ставить деньги ТУПО.

ПРАВИЛО ВЫВОДА РЕКОМЕНДАЦИЙ В РАЗДЕЛЕ "💰 Рекомендации по ставкам":

1) **Если фаворит торгуется ≤ 1.30 (heavy favorite)** или ты подозреваешь
   что рынок уже его справедливо ценит:
   - НЕ предлагай moneyline на фаворита.
   - Предлагай **method props**: «{Имя} by Decision @ ~2.0» или «by KO @ ~3.0»
   - Предлагай **round totals**: «Over 2.5 если ожидаешь дистанцию» / «Under 1.5 если pressure-finisher»
   - Если бой кажется явно односторонним → «Skip moneyline, ищи альтернативные пропы»

2) **Если у underdog'а есть стилистический путь к победе** (борец vs страйкер
   без TDD, проблемы у фаворита с весогонкой/травмами):
   - Явно выдели: «Underdog @ 4.0+ имеет real path — small bet kelly 1-2%»
   - НЕ блефуй уверенностью — overconfidence = убыток в долгосрок.

3) **ВСЕГДА упоминай implied probability** для своей основной рекомендации:
   «Decision @ 1.85 = implied 54%. Я даю 60%. Edge +6% → +EV bet».

4) **Контр-индикаторы** (когда НЕ ставить):
   - Фаворит в плохом виде, но коэф очень короткий → no value
   - Underdog мог бы — но коэф уже подъехал к real probability → fair price, skip
   - Бой close, а коэф 50/50 → нет edge, skip

5) **Risk warnings обязательны**:
   - Тяжёлая весогонка фаворита, но рынок не успел отреагировать → отметь это явно
   - Long layoff бойца (>14 мес.) → дисконтируй уверенность, упомяни «cage rust factor»

ФОРМАТ блока "💰 Рекомендации по ставкам":
- **Основная ставка:** {bet} @ {примерный коэф ~X.XX} — implied YY%, наша prob ZZ%, edge +Δ%
- **Альтернатива (если main bet нет value):** {другой пик с пояснением value}
- **Skip:** {ставки которые НЕ брать с пояснением «коэф съел весь edge»}

═══════════════════════════════════════════════════════════════════
📋 ФОРМАТ ВЫВОДА (СТРОГО — regex-парсится для калибровки)
═══════════════════════════════════════════════════════════════════
Используй markdown с эмодзи. Структура **точно** такая:

## 🥊 [Боец A] vs [Боец B] | [Весовая категория]

### 🏆 Итоговый прогноз
**Победитель: [Имя]** — XX% уверенности.
**Метод:** KO/TKO XX% / Submission YY% / Decision ZZ%
**Раунд (если финиш):** R[1-5] (или «дистанция» для Decision).

### 💰 Рекомендации по ставкам
- **Основная ставка:** Берем [Имя] Moneyline / Method / Round / Total — конкретно. Где value: ...
- **Проп №1:** ...
- **Проп №2:** ...
- **Что избегать:** ...

### 📊 Глубокий разбор
**🎯 Стилевой матч-ап:** Архетипы + кто диктует где идёт бой. 2-3 предложения.
**📈 Статистический breakdown:** Конкретные цифры (SLpM, StrAcc/Def, TDAvg/Def, SubAvg) и что они значат для ЭТОГО матч-апа.
**🔥 Форма и тренды:** Последние 3-5 боёв каждого, тренд.
**💪 Физика и возраст:** Reach diff, height diff, age curves.
**🏆 Качество оппозиции:** С кем дрался каждый, реальный уровень.
**🧠 Ментальная составляющая:** Использовать intel + KB + общие знания о бойце.
**⚖️ Весогонка:** Риски, особенно для 5-раундовиков.
**📚 Историческая параллель (если есть в KB):** «Похоже на [Fight] [KB] — [как закончилось]».
**🎬 Сценарий по раундам:** R1: ... / R2: ... / R3-5: ...

### 🎯 Топ-3 причины за пик
1. ...
2. ...
3. ...

### ⚠️ Риски и upset potential
- 2-4 жёстких сценария почему пик может не зайти. Конкретно: «KO со встречки от X», «sub в партере если Y зайдёт за спину», «cardio crash в R4 из-за весогонки».

### 📌 Калибровка
**Уверенность:** [Низкая / Средняя / Высокая] — XX/100
**Self-consistency:** Из 3 mental simulations [N]/3 закончились этим исходом.
**Ключевые неопределённости:** 1-2 фактора которые могли бы перевернуть прогноз.

═══════════════════════════════════════════════════════════════════
🚫 ЗАПРЕЩЕНО
═══════════════════════════════════════════════════════════════════
- НЕ показывать внутренний CoT (мысли пунктов 1-6) — только финальный markdown.
- НЕ ставить уверенность 85%+ кроме гарантированных миссматчей.
- НЕ выдумывать факты которых нет ни в данных бойцов, ни в intel, ни в KB.
- НЕ давать стандартный «всё может быть» вердикт — всегда конкретный пик с аргументами.
- НЕ рекомендовать Moneyline на underdog'е без явного стилистического или контекстного эджа.
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
    # Backfill UUID для старых записей, которые сохранялись без id
    _need_save = False
    for _h in st.session_state.history:
        if not _h.get("id") or len(str(_h.get("id"))) < 8:
            _h["id"] = uuid.uuid4().hex[:12]
            _need_save = True
    if _need_save:
        save_json(HISTORY_FILE, st.session_state.history)
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
    from lessons import relevant_lessons, format_lessons_block, build_context_string
    client = OpenAI(api_key=api_key, base_url=base_url)

    # --- Инжект Lessons из персистентной памяти ошибок ---
    ctx_str = build_context_string(fa, fb, ctx, intel)
    lessons = relevant_lessons(ctx_str, max_n=5)
    lessons_block = format_lessons_block(lessons)

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
- Venue: {ctx.get('venue', '—')}

## ДОПОЛНИТЕЛЬНЫЙ ИНТЕЛЛЕКТ
{intel.strip() if intel.strip() else '(не предоставлено)'}

{lessons_block}

Дай развёрнутый прогноз строго по формату системного промпта. Только русский.
Применяй УРОКИ выше — это правила извлечённые из прошлых ошибок модели."""
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user", "content": user_msg}],
        temperature=0.5, max_tokens=3500,
    )
    return resp.choices[0].message.content


# ---------- Sidebar: Navigation + Settings ----------
with st.sidebar:
    # --- Кликабельный логотип PREDICTOR → Home ---
    st.markdown(
        f"""
        <style>
        /* Стилизуем первую кнопку в сайдбаре под логотип */
        section[data-testid="stSidebar"] div[data-testid="stButton"]:first-of-type button {{
            background: transparent !important;
            border: none !important;
            border-bottom: 3px solid {UFC_RED} !important;
            border-radius: 0 !important;
            padding: 4px 0 14px 0 !important;
            margin-bottom: 14px !important;
            width: 100% !important;
            text-align: left !important;
            font-family: 'Oswald', sans-serif !important;
            font-size: 1.6rem !important;
            font-weight: 700 !important;
            letter-spacing: 2px !important;
            color: {TEXT} !important;
            cursor: pointer !important;
            box-shadow: none !important;
        }}
        section[data-testid="stSidebar"] div[data-testid="stButton"]:first-of-type button:hover {{
            color: {UFC_RED} !important;
            background: transparent !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    if st.button("🥊 PREDICTOR", key="logo_home_btn",
                 help="На главную"):
        st.session_state.page = "🏠 Home"
        st.session_state.event_to_predict = None
        st.rerun()

    PAGES = [
        "🏠 Home",
        "🔴 Live Card",
        "👥 Fight Base",
        "🔮 Predictor",
        "🧠 Knowledge Base",
        "🧮 ML Model",
        "🎓 Fine-Tuning",
        "📊 Analytics",
        "⚖️ Weight Cut",
        "📚 History & Accuracy",
        "🧪 Backtesting",
        "❤️ Model Health",
        "🎯 Blind Tests",
        "📖 Lessons",
    ]
    page = st.radio("Навигация", PAGES, label_visibility="collapsed",
                    index=PAGES.index(st.session_state.page) if st.session_state.page in PAGES else 0)
    st.session_state.page = page

    # ---- Backend status (вместо LLM-блока с Demo Mode) ----
    api_key = LLM_API_KEY
    base_url = LLM_BASE_URL
    model = LLM_MODEL
    demo_mode = False  # больше не используется, оставлено для обратной совместимости

    st.markdown("---")
    if api_key:
        st.markdown(
            f"<div style='font-size:0.78rem;color:{MUTED};line-height:1.5'>"
            f"<b style='color:{TEXT}'>🟢 Backend</b><br>"
            f"<span style='color:{TEXT}'>{LLM_DISPLAY_NAME}</span><br>"
            f"<code style='font-size:0.72rem'>{model}</code>"
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.warning(
            "⚠️ Backend не настроен.\n\n"
            "Скопируй `.env.local.example` → `.env.local` и заполни "
            "`LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`."
        )

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

    rc1, rc2, rc3 = st.columns([1, 1, 4])
    if rc1.button("🔄 Обновить"):
        st.cache_data.clear()
        st.rerun()

    # ----- Live odds toggle -----
    try:
        from odds_provider import is_available as _odds_avail
        _odds_ready = _odds_avail()
    except Exception:
        _odds_ready = False
    show_value = rc2.toggle("💰 Auto-value scan", value=_odds_ready,
                              disabled=not _odds_ready,
                              help="Сравнить наши прошлые predictions с current market "
                                   "odds для каждого боя на live card.")

    # ----- Value Edge Scanner (auto-comparison) -----
    if show_value and _odds_ready:
        try:
            from odds_provider import get_ufc_events, find_fight_odds
            from odds_engine import (analyze_fight_odds,
                                       remove_vig_two_way, implied_prob)
            with st.spinner("📡 Pull market odds..."):
                events_odds = get_ufc_events(force_refresh=False)

            # Сканируем history → ищем pending predictions с матчами в odds
            scan_rows = []
            for h in st.session_state.history:
                if h.get("status") != "pending":
                    continue
                fa_n = h.get("fa", "")
                fb_n = h.get("fb", "")
                if not (fa_n and fb_n):
                    continue
                match = find_fight_odds(fa_n, fb_n, events_odds)
                if not match:
                    continue
                # Наша prob
                our_a = h.get("hybrid", {}).get("final_prob_a") if h.get("hybrid") else None
                if our_a is None and h.get("win_prob") is not None:
                    pw = h.get("predicted_winner", "")
                    if pw and (pw.lower() in fa_n.lower() or fa_n.lower() in pw.lower()):
                        our_a = h["win_prob"]
                    elif pw:
                        our_a = 1.0 - h["win_prob"]
                if our_a is None:
                    continue
                our_b = 1.0 - our_a

                mp_a, mp_b = remove_vig_two_way(match["odds_a"], match["odds_b"])
                edge_a = our_a - mp_a
                edge_b = our_b - mp_b
                # Bullish сторона
                if edge_a > edge_b:
                    side = fa_n
                    side_odds = match["odds_a"]
                    side_edge = edge_a
                    side_our = our_a
                else:
                    side = fb_n
                    side_odds = match["odds_b"]
                    side_edge = edge_b
                    side_our = our_b
                if side_edge < -0.02:
                    continue  # нет value
                scan_rows.append({
                    " ": ("💰" if side_edge >= 0.05 else
                          "✅" if side_edge >= 0.02 else "🟡"),
                    "Бой": f"{fa_n} vs {fb_n}",
                    "Value side": side,
                    "Best odds": f"{side_odds:.2f}",
                    "Our prob": f"{side_our*100:.1f}%",
                    "Implied": f"{implied_prob(side_odds)*100:.1f}%",
                    "Edge": f"{side_edge*100:+.1f}%",
                })
            if scan_rows:
                st.markdown("### 💰 Value Edge Scanner — pending predictions vs live odds")
                scan_rows.sort(key=lambda r: float(r["Edge"].replace("%", "")), reverse=True)
                st.dataframe(pd.DataFrame(scan_rows),
                              use_container_width=True, hide_index=True)
            else:
                st.caption("🟡 Нет +EV value на pending predictions сейчас. "
                            "Сделай прогноз в **🔮 Predictor** — потом увидишь его здесь.")
        except Exception as e:
            st.caption(f"Value scan недоступен: {e}")

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
        placeholder="Травмы, весогонка, драма в лагере, мотивация, jet-lag, новости...")

    # --- Pull intel button: парсит свободный текст в структурированный JSON ---
    pi_c1, pi_c2 = st.columns([1, 3])
    if pi_c1.button("🔍 Pull intel", use_container_width=True,
                     help="LLM-парсер извлекает severity-флаги из свободного текста "
                          "(weight cut, injury, jet-lag, drama, motivation)."):
        if not intel.strip():
            st.warning("Сначала впиши заметки.")
        elif not api_key:
            st.warning("API key не настроен.")
        elif not fa or not fb:
            st.warning("Сначала выбери обоих бойцов.")
        else:
            try:
                from intel_ingest import extract_intel_from_text
                with st.spinner("🤖 Извлекаю структурированный intel..."):
                    res = extract_intel_from_text(
                        notes_text=intel,
                        api_key=api_key, base_url=base_url, model=model,
                        fighter_a_name=fa["name"], fighter_b_name=fb["name"],
                    )
                if res.get("error"):
                    st.error(f"Ошибка: {res['error']}")
                else:
                    st.session_state["intel_struct"] = {
                        "fa_name": fa["name"], "fb_name": fb["name"],
                        "intel_a": res["fighter_a"], "intel_b": res["fighter_b"],
                        "sources": res["sources"], "confidence": res["confidence"],
                    }
                    st.success(
                        f"✅ Извлечено · confidence={res['confidence']:.2f} · "
                        f"A: {'есть данные' if res['fighter_a'] else 'нет'} · "
                        f"B: {'есть данные' if res['fighter_b'] else 'нет'}"
                    )
            except Exception as e:
                st.error(f"Intel extractor failed: {e}")

    # Показываем структурированный intel если есть
    if (st.session_state.get("intel_struct") and fa and fb
            and st.session_state["intel_struct"].get("fa_name") == fa["name"]
            and st.session_state["intel_struct"].get("fb_name") == fb["name"]):
        with pi_c2:
            with st.expander("📰 Структурированный intel (extracted)", expanded=False):
                istr = st.session_state["intel_struct"]
                ia, ib = st.columns(2)
                ia.markdown(f"**{istr['fa_name']}**")
                ia.json(istr.get("intel_a") or {"info": "no data"})
                ib.markdown(f"**{istr['fb_name']}**")
                ib.json(istr.get("intel_b") or {"info": "no data"})

    st.markdown("### 📚 RAG Knowledge Base")
    rag_c1, rag_c2 = st.columns([3, 1])
    use_rag = rag_c1.toggle(
        "Использовать Knowledge Base (исторические бои + профили)",
        value=True,
        help="Подмешивает в промпт релевантные документы из ChromaDB.",
    )
    rag_top_k = rag_c2.slider("Top-K", 3, 10, 6, label_visibility="collapsed")

    # Auto-tracking всегда включён — каждый прогноз попадает в History/Accuracy.
    st.caption("📊 Все прогнозы автоматически сохраняются в **History & Accuracy** для трекинга точности и калибровки.")

    # ---------- Multi-Agent Mode ----------
    st.markdown("### 🤖 Multi-Agent Reasoning")
    ma_c1, ma_c2 = st.columns([3, 1])
    use_multi_agent = ma_c1.toggle(
        "Использовать Multi-Agent режим (Stats + Style + Context → Synthesizer)",
        value=False,
        help="4 специализированных агента вместо одного промпта. "
             "Глубже разбор, но дольше и дороже (~4 LLM-вызова).",
    )
    ma_parallel = ma_c2.checkbox("Parallel", value=True,
        help="Stats/Style/Context запускаются параллельно.")

    # Per-agent model override (опционально)
    agent_models = {}
    if use_multi_agent:
        with st.expander("⚙️ Модели по агентам (опционально)"):
            st.caption(
                "По умолчанию все агенты используют модель из сайдбара. "
                "Можно задать отдельную модель для каждого агента "
                "(например, дешёвая для Stats, мощная для Synthesizer)."
            )
            am1, am2 = st.columns(2)
            stats_m = am1.text_input("Stats Agent model", "",
                placeholder=f"default: {model}")
            style_m = am2.text_input("Style Agent model", "",
                placeholder=f"default: {model}")
            ctx_m = am1.text_input("Context Agent model", "",
                placeholder=f"default: {model}")
            synth_m = am2.text_input("Synthesizer model", "",
                placeholder=f"default: {model}")
            if stats_m: agent_models["stats"] = stats_m
            if style_m: agent_models["style"] = style_m
            if ctx_m: agent_models["context"] = ctx_m
            if synth_m: agent_models["synthesizer"] = synth_m
        agent_models["default"] = model

    # ---------- Hybrid ML+LLM Mode ----------
    st.markdown("### 🧮 Hybrid ML + LLM")
    try:
        import ml_model
        ml_meta = ml_model.get_meta()
        ml_trained = ml_meta is not None and "load_error" not in ml_meta
    except ImportError:
        ml_model, ml_meta, ml_trained = None, None, False

    h_c1, h_c2 = st.columns([3, 1])
    use_hybrid = h_c1.toggle(
        "Использовать Hybrid (ML probability + LLM analysis)",
        value=ml_trained,
        disabled=not ml_trained,
        help=("Объединяет XGBoost-вероятность с LLM-аналитикой для лучшей калибровки. "
              "Натренируй модель на странице 🧮 ML Model." if not ml_trained else
              "ML-модель даёт base probability, LLM добавляет qualitative reasoning."),
    )
    ml_weight = h_c2.slider("ML weight", 0.0, 1.0, 0.4, 0.05,
        disabled=not (use_hybrid and ml_trained),
        help="Какой вес дать ML-модели. Остальное — LLM.")
    if not ml_trained:
        st.caption("⚠️ ML-модель не натренирована. Перейди на **🧮 ML Model** → Train.")

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

            # ---------- QoO retrieval (всегда) ----------
            qoo_a, qoo_b = None, None
            try:
                from qoo import build_qoo_pair, format_qoo_for_prompt
                from rag_seed import HISTORICAL_FIGHTS as _HF
                qoo_a, qoo_b = build_qoo_pair(
                    fa["name"], fb["name"],
                    fighters_db=st.session_state.fighters,
                    historical_fights=_HF,
                    resolved_history=st.session_state.history,
                )
            except Exception as e:
                st.warning(f"QoO недоступен: {e}")

            # ---------- Intel retrieval (из session, если был extract) ----------
            intel_a, intel_b = None, None
            istr = st.session_state.get("intel_struct")
            if (istr and istr.get("fa_name") == fa["name"]
                    and istr.get("fb_name") == fb["name"]):
                intel_a = istr.get("intel_a")
                intel_b = istr.get("intel_b")

            # Собираем расширенный intel: оригинальный текст + QOO + INTEL + RAG
            enriched_intel = intel
            if qoo_a or qoo_b:
                try:
                    enriched_intel += "\n\n" + format_qoo_for_prompt(qoo_a, qoo_b)
                except Exception:
                    pass
            if intel_a or intel_b:
                try:
                    from intel_ingest import format_intel_for_prompt
                    enriched_intel += "\n\n" + format_intel_for_prompt(
                        intel_a, intel_b, fa["name"], fb["name"])
                except Exception:
                    pass
            if rag_result.get("context_text"):
                enriched_intel += (
                    f"\n\n=== RETRIEVED KNOWLEDGE BASE CONTEXT ===\n"
                    f"Use the following real data and historical fights to ground your analysis. "
                    f"When making stylistic or probabilistic claims, cite relevant past fights "
                    f"in [Source N] format.\n\n"
                    f"{rag_result['context_text']}\n"
                    f"=== END KB CONTEXT ===\n"
                )

            agent_outputs = {}
            agent_timings = {}
            with st.spinner(
                "🤖 Multi-agent reasoning..." if use_multi_agent
                else "⏳ Анализируем стили, статистику, форму, менталку..."
            ):
                try:
                    if not api_key:
                        st.error(
                            "❌ Backend не настроен. Заполни `.env.local` "
                            "(`LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`) и перезапусти."
                        )
                        st.stop()
                    if use_multi_agent:
                        from agents import run_multi_agent_prediction
                        rag_text = rag_result.get("context_text", "") if use_rag else ""
                        ma_result = run_multi_agent_prediction(
                            fa=fa, fb=fb, ctx=ctx, intel=intel,
                            rag_context=rag_text,
                            api_key=api_key, base_url=base_url,
                            models=agent_models,
                            parallel=ma_parallel,
                        )
                        analysis = ma_result.final
                        agent_outputs = ma_result.agent_outputs
                        agent_timings = ma_result.timings
                    else:
                        analysis = get_fight_prediction(fa, fb, ctx, enriched_intel,
                                                       api_key, base_url, model)
                    probs = extract_probabilities(analysis)

                    # ----- ML prediction (всегда, если модель есть) -----
                    ml_pred = {"available": False}
                    hybrid_info = None
                    if ml_model is not None:
                        try:
                            ml_pred = ml_model.predict_ml(
                                fa, fb,
                                qoo_a=qoo_a, qoo_b=qoo_b,
                                intel_a=intel_a, intel_b=intel_b,
                            )
                        except Exception as e:
                            ml_pred = {"available": False, "reason": f"err: {e}"}

                    # ----- LLM prob для бойца A (для гибрида) -----
                    # probs['win_prob'] — для предсказанного победителя.
                    # Конвертируем в prob_a:
                    llm_prob_a = None
                    pw = extract_predicted_winner(analysis)
                    if probs["win_prob"] is not None and pw:
                        if _name_match(pw, fa["name"]):
                            llm_prob_a = probs["win_prob"]
                        elif _name_match(pw, fb["name"]):
                            llm_prob_a = 1.0 - probs["win_prob"]

                    # ----- Hybrid combine -----
                    rookie_info = {"applied": False}
                    intel_mod_info = {"applied": False}
                    if use_hybrid and ml_pred.get("available") and llm_prob_a is not None:
                        hybrid_info = ml_model.combine_hybrid(
                            ml_pred, llm_prob_a, ml_weight=ml_weight)
                        final_a = hybrid_info["final_prob_a"]
                    else:
                        # Без hybrid — берём LLM prob как базовый final
                        final_a = llm_prob_a

                    # ----- Rookie dampening (QoO) -----
                    if final_a is not None and (qoo_a or qoo_b):
                        try:
                            from qoo import apply_rookie_dampening
                            final_a, rookie_info = apply_rookie_dampening(
                                final_a, qoo_a or {}, qoo_b or {})
                        except Exception:
                            pass

                    # ----- Intel deterministic modifier -----
                    if final_a is not None and (intel_a or intel_b):
                        try:
                            from intel_ingest import apply_intel_modifier
                            final_a, intel_mod_info = apply_intel_modifier(
                                final_a, intel_a, intel_b)
                        except Exception:
                            pass

                    # Записываем итог в probs (для Brier-калибровки)
                    if final_a is not None and pw:
                        if _name_match(pw, fa["name"]):
                            probs["win_prob"] = final_a
                        elif _name_match(pw, fb["name"]):
                            probs["win_prob"] = 1.0 - final_a
                        if hybrid_info is None:
                            hybrid_info = {"final_prob_a": final_a, "ml_weight": 0.0,
                                            "applied": False, "reason": "llm_only_with_overrides"}

                    record = {
                        "id": uuid.uuid4().hex[:12],
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
                        "tracked": True,
                        "model": model,
                        "multi_agent_used": use_multi_agent,
                        "agent_outputs": agent_outputs,
                        "agent_timings": agent_timings,
                        "ml_pred": ml_pred,
                        "hybrid": hybrid_info,
                        "hybrid_used": use_hybrid and hybrid_info is not None,
                        "ml_weight_setting": ml_weight if use_hybrid else None,
                        # --- v3 snapshots (QoO + Intel) — для backtest replay ---
                        "qoo_snapshot": {"a": qoo_a, "b": qoo_b},
                        "intel_snapshot": {"a": intel_a, "b": intel_b},
                        "rookie_dampening": rookie_info,
                        "intel_modifier": intel_mod_info,
                        "status": "pending",
                    }

                    # --- Market odds snapshot (если был pull) — для CLV ---
                    pulled_odds = st.session_state.get("odds_pulled")
                    if (pulled_odds and pulled_odds.get("fighter_a") == fa["name"]
                            and pulled_odds.get("fighter_b") == fb["name"]):
                        try:
                            from clv_tracker import attach_market_odds_snapshot
                            record = attach_market_odds_snapshot(record, pulled_odds)
                        except Exception:
                            pass
                    st.session_state.last_analysis = record

                    # АВТОСЕЙВ ВСЕГДА. Дедуп по (fa, fb, event, дата-минута).
                    already = any(
                        h.get("fa") == record["fa"]
                        and h.get("fb") == record["fb"]
                        and h.get("event") == record["event"]
                        and (h.get("ts") or "")[:16] == record["ts"][:16]
                        for h in st.session_state.history
                    )
                    if not already:
                        # Без огромного rag_raw в персистентной истории
                        saved = {k: v for k, v in record.items() if k != "rag_raw"}
                        st.session_state.history.insert(0, saved)
                        persist_history()
                        st.toast(f"📊 Auto-saved · ID `{record['id'][:8]}`")
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

        # Hybrid ML + LLM сравнение
        if la.get("ml_pred", {}).get("available") or la.get("hybrid_used"):
            ml_p = la.get("ml_pred", {})
            hyb = la.get("hybrid") or {}
            fa_name = la.get("fa", "A")
            fb_name = la.get("fb", "B")

            st.markdown("### 🧮 Hybrid Breakdown")
            hc1, hc2, hc3 = st.columns(3)

            ml_a = ml_p.get("win_prob_a")
            with hc1:
                st.markdown("**🧮 ML Model**")
                if ml_a is not None:
                    fav_name = fa_name if ml_a >= 0.5 else fb_name
                    fav_p = ml_a if ml_a >= 0.5 else 1 - ml_a
                    st.metric(fav_name, f"{fav_p*100:.1f}%")
                    st.caption(f"{fa_name}: {ml_a*100:.1f}% / {fb_name}: {(1-ml_a)*100:.1f}%")
                else:
                    st.caption("Модель не доступна")

            llm_a = hyb.get("llm_prob_a") if hyb else None
            with hc2:
                st.markdown("**🤖 LLM Only**")
                if llm_a is not None:
                    fav_name = fa_name if llm_a >= 0.5 else fb_name
                    fav_p = llm_a if llm_a >= 0.5 else 1 - llm_a
                    st.metric(fav_name, f"{fav_p*100:.1f}%")
                    st.caption(f"{fa_name}: {llm_a*100:.1f}% / {fb_name}: {(1-llm_a)*100:.1f}%")
                else:
                    st.caption("LLM-prob не извлечена")

            final_a = hyb.get("final_prob_a") if hyb else None
            with hc3:
                st.markdown("**🎯 Hybrid (Final)**")
                if final_a is not None:
                    fav_name = fa_name if final_a >= 0.5 else fb_name
                    fav_p = final_a if final_a >= 0.5 else 1 - final_a
                    st.metric(fav_name, f"{fav_p*100:.1f}%",
                              delta=f"weights ML {hyb['ml_weight']:.0%} / LLM {hyb['llm_weight']:.0%}")
                    st.caption(f"{fa_name}: {final_a*100:.1f}% / {fb_name}: {(1-final_a)*100:.1f}%")
                else:
                    st.caption("Hybrid не активирован")

            # ML method probs
            if ml_p.get("method_probs"):
                mp = ml_p["method_probs"]
                with st.expander("🥋 ML method distribution"):
                    mc1, mc2, mc3 = st.columns(3)
                    mc1.metric("KO/TKO", f"{mp.get('KO/TKO',0)*100:.1f}%")
                    mc2.metric("Submission", f"{mp.get('Submission',0)*100:.1f}%")
                    mc3.metric("Decision", f"{mp.get('Decision',0)*100:.1f}%")
            st.markdown("---")

        # Multi-Agent transparency: вывод каждого агента
        if la.get("multi_agent_used") and la.get("agent_outputs"):
            st.markdown(
                "🤖 **Multi-Agent Mode** — финальный прогноз построен синтезом "
                "выводов специализированных агентов. Развернуть каждого:"
            )
            agent_icons = {
                "Stats Agent": "🔢",
                "Style Agent": "🥊",
                "Context Agent": "🧠",
            }
            for agent_name, output in la["agent_outputs"].items():
                icon = agent_icons.get(agent_name, "🤖")
                t = la.get("agent_timings", {}).get(agent_name)
                t_str = f" · {t:.1f}s" if t else ""
                with st.expander(f"{icon} {agent_name}{t_str}"):
                    st.markdown(output)
            st.markdown("---")
            st.markdown("### 🎯 Synthesizer — финальный прогноз")

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

        # ================================================================
        # 💰 VALUE BET ANALYZER — odds-aware рекомендации
        # ================================================================
        st.markdown("---")
        st.markdown("## 💰 Value Bet Analyzer")
        st.caption(
            "Введи коэффициенты букмекера (decimal формат: 1.20, 2.50, 4.00). "
            "Модель сравнит наши probs с implied probs рынка и покажет где **+EV value**, "
            "а где негатив — даже если победитель угадан."
        )

        # Достаём наши probs из last_analysis
        win_a_our = la.get("hybrid", {}).get("final_prob_a")
        if win_a_our is None and la.get("win_prob") is not None:
            pw = la.get("predicted_winner", "")
            if _name_match(pw, fa["name"]):
                win_a_our = la["win_prob"]
            elif _name_match(pw, fb["name"]):
                win_a_our = 1.0 - la["win_prob"]
            else:
                win_a_our = 0.5
        win_a_our = win_a_our if win_a_our is not None else 0.5
        win_b_our = 1.0 - win_a_our

        ko_w = la.get("ko_prob") or 0.0
        sub_w = la.get("sub_prob") or 0.0
        dec_w = la.get("dec_prob") or 0.0

        st.markdown("##### 📊 Наши probs (из v3 модели)")
        ip1, ip2, ip3, ip4, ip5 = st.columns(5)
        ip1.metric(f"{fa['name'][:14]} ML", f"{win_a_our*100:.1f}%")
        ip2.metric(f"{fb['name'][:14]} ML", f"{win_b_our*100:.1f}%")
        ip3.metric("KO/TKO", f"{ko_w*100:.0f}%")
        ip4.metric("Submission", f"{sub_w*100:.0f}%")
        ip5.metric("Decision", f"{dec_w*100:.0f}%")

        st.markdown("##### 🎲 Рыночные коэффициенты")

        # ----- Real-time pull from TheOddsAPI -----
        try:
            from odds_provider import (is_available as _odds_avail,
                                         get_ufc_events, find_fight_odds)
            odds_api_ready = _odds_avail()
        except Exception:
            odds_api_ready = False

        if odds_api_ready:
            pl1, pl2 = st.columns([1, 3])
            if pl1.button("🔄 Pull live odds", use_container_width=True,
                           key="pull_live_odds",
                           help="Fetch текущих коэфов с TheOddsAPI (кеш 30 мин)"):
                try:
                    with st.spinner("📡 Запрашиваю TheOddsAPI..."):
                        events = get_ufc_events(force_refresh=True)
                        match = find_fight_odds(fa["name"], fb["name"], events)
                    if match:
                        st.session_state["odds_pulled"] = match
                        st.success(
                            f"✅ Найдено в {match['n_books']} книгах · "
                            f"best: {fa['name']} @ {match['odds_a']:.2f} · "
                            f"{fb['name']} @ {match['odds_b']:.2f}"
                        )
                        st.rerun()
                    else:
                        st.warning(
                            "Не нашёл этот бой в live-карте TheOddsAPI. "
                            "Возможно, не открыли линию ещё, или имена не совпадают."
                        )
                except Exception as e:
                    st.error(f"API error: {e}")
            with pl2:
                pulled = st.session_state.get("odds_pulled")
                if pulled and pulled.get("fighter_a") == fa["name"]:
                    bk_str = " · ".join(
                        f"{v['title'][:8]}: {v['odds_a']:.2f}/{v['odds_b']:.2f}"
                        for k, v in list(pulled.get("bookmakers", {}).items())[:4]
                    )
                    st.caption(f"📊 {bk_str}")
        else:
            st.caption(
                "💡 Set `THE_ODDS_API_KEY` in `.env.local` для **🔄 Pull live odds** "
                "(free 500 req/мес на the-odds-api.com)."
            )

        # Pre-fill из pulled odds
        pulled = st.session_state.get("odds_pulled")
        default_a = (pulled.get("odds_a") if (pulled
            and pulled.get("fighter_a") == fa["name"]) else 2.00)
        default_b = (pulled.get("odds_b") if (pulled
            and pulled.get("fighter_b") == fb["name"]) else 2.00)

        oc1, oc2 = st.columns(2)
        with oc1:
            st.markdown(f"**{fa['name']}**")
            ml_a = st.number_input(f"ML — {fa['name']}", 1.01, 50.0,
                                    float(default_a), 0.01,
                                    key="odds_ml_a", format="%.2f")
        with oc2:
            st.markdown(f"**{fb['name']}**")
            ml_b = st.number_input(f"ML — {fb['name']}", 1.01, 50.0,
                                    float(default_b), 0.01,
                                    key="odds_ml_b", format="%.2f")

        # Method/Total props (опционально)
        with st.expander("➕ Method props и total rounds (опционально)"):
            mc1, mc2, mc3 = st.columns(3)
            ko_odds = mc1.number_input("Winner by KO/TKO", 1.01, 50.0, 0.0, 0.01,
                                         key="odds_ko", format="%.2f",
                                         help="Оставь 0 если не знаешь")
            sub_odds = mc2.number_input("Winner by Submission", 1.01, 50.0, 0.0, 0.01,
                                          key="odds_sub", format="%.2f")
            dec_odds = mc3.number_input("Winner by Decision", 1.01, 50.0, 0.0, 0.01,
                                          key="odds_dec", format="%.2f")
            tc1, tc2 = st.columns(2)
            over_odds = tc1.number_input("Over 2.5 rounds", 1.01, 50.0, 0.0, 0.01,
                                           key="odds_over", format="%.2f")
            under_odds = tc2.number_input("Under 2.5 rounds", 1.01, 50.0, 0.0, 0.01,
                                            key="odds_under", format="%.2f")

        if st.button("🎯 Анализировать value", use_container_width=True):
            from odds_engine import (analyze_fight_odds, heavy_favorite_warning,
                                       remove_vig_two_way)
            our_probs = {
                "fa_name": fa["name"], "fb_name": fb["name"],
                "win_prob_a": win_a_our, "win_prob_b": win_b_our,
                "ko_prob_winner": ko_w, "sub_prob_winner": sub_w,
                "dec_prob_winner": dec_w,
            }
            market_odds = {
                "ml_a": ml_a, "ml_b": ml_b,
                "ko_winner": ko_odds if ko_odds > 1.0 else None,
                "sub_winner": sub_odds if sub_odds > 1.0 else None,
                "dec_winner": dec_odds if dec_odds > 1.0 else None,
                "over_2_5": over_odds if over_odds > 1.0 else None,
                "under_2_5": under_odds if under_odds > 1.0 else None,
            }
            result = analyze_fight_odds(our_probs, market_odds)

            # Heavy favorite warning
            fav_odds = min(ml_a, ml_b)
            fav_name = fa["name"] if ml_a < ml_b else fb["name"]
            fav_prob = win_a_our if ml_a < ml_b else win_b_our
            warn = heavy_favorite_warning(fav_odds, fav_prob)
            if warn:
                st.warning(warn["message"])

            # De-vig market probs
            mp_a, mp_b = remove_vig_two_way(ml_a, ml_b)
            st.markdown("##### 📐 De-vigged market probs")
            dvc1, dvc2, dvc3, dvc4 = st.columns(4)
            dvc1.metric(f"Market: {fa['name'][:12]}", f"{mp_a*100:.1f}%")
            dvc2.metric(f"Market: {fb['name'][:12]}", f"{mp_b*100:.1f}%")
            dvc3.metric(f"Our: {fa['name'][:12]}",
                          f"{win_a_our*100:.1f}%",
                          delta=f"{(win_a_our - mp_a)*100:+.1f}%")
            dvc4.metric(f"Our: {fb['name'][:12]}",
                          f"{win_b_our*100:.1f}%",
                          delta=f"{(win_b_our - mp_b)*100:+.1f}%")

            # Summary
            st.markdown("##### 🎯 Вердикт")
            st.markdown(result["summary"])

            # Bets table
            if result["bets"]:
                rows = []
                for b in result["bets"]:
                    icon = {
                        "strong_value": "💰", "lean_value": "✅",
                        "fair": "🟡", "lean_against": "🟠",
                        "strong_against": "❌", "no_odds": "❓",
                    }.get(b["verdict"], "—")
                    rows.append({
                        " ": icon,
                        "Ставка": b["label"],
                        "Наша prob": f"{b['our_prob']*100:.1f}%",
                        "Коэф": f"{b['market_odds']:.2f}",
                        "Implied": f"{(b['implied'] or 0)*100:.1f}%",
                        "Edge": f"{(b['edge'] or 0)*100:+.1f}%",
                        "EV/$100": f"${b['ev_per_100']:+.1f}",
                        "Kelly": f"{b['kelly']*100:.1f}%",
                        "Рекомендация": b["recommendation"],
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True,
                              hide_index=True)

            # Top picks highlight
            if result["value_bets"]:
                st.markdown("##### 🚀 Value picks")
                for b in result["value_bets"][:3]:
                    st.success(
                        f"**{b['label']}** @ {b['market_odds']:.2f} · "
                        f"edge {b['edge']*100:+.1f}% · "
                        f"EV ${b['ev_per_100']:+.1f}/$100 · "
                        f"Kelly {b['kelly']*100:.1f}%"
                    )
            else:
                st.info(
                    "🟡 No clean +EV bets found. Рынок прав. Skip moneyline, "
                    "ищи живой edge или другой бой."
                )

        st.markdown("---")
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
# PAGE: ML MODEL (Hybrid backbone)
# =================================================================
elif page == "🧮 ML Model":
    st.markdown("## 🧮 Classical ML Model (XGBoost / GBM)")
    st.caption(
        "Табличная модель на разностях метрик бойцов. Используется как base-prob "
        "в Hybrid режиме предиктора. Пере-тренируй после каждого ивента — "
        "она автоматически подтянет новые resolved предсказания."
    )

    try:
        import ml_model
    except ImportError:
        st.error("ml_model не импортируется. Проверь зависимости.")
        st.stop()

    if not ml_model.is_available():
        st.error(
            "❌ Нет ML-backend. Установи XGBoost (рекомендуется) или scikit-learn:\n\n"
            "`pip install xgboost`  ← или  `pip install scikit-learn`"
        )
        st.stop()

    # ---- Подготовка данных ----
    try:
        from rag_seed import HISTORICAL_FIGHTS
    except ImportError:
        HISTORICAL_FIGHTS = []

    training = ml_model.assemble_training_data(
        fighters_db=st.session_state.fighters,
        historical_fights=HISTORICAL_FIGHTS,
        resolved_history=st.session_state.history,
    )

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Training samples", training["n_samples"])
    s2.metric("Hist. fights skipped",
              training["skipped"],
              help="Бои где боец не найден в локальной БД.")
    s3.metric("Backend", ml_model._BACKEND or "—")
    meta_now = ml_model.get_meta()
    s4.metric("Trained model", "✅ есть" if meta_now and "load_error" not in meta_now else "—")

    st.markdown("### 🎯 Train / Retrain")
    if st.button("🚀 Train ML Model", type="primary", use_container_width=True):
        if training["n_samples"] < 6:
            st.error(
                f"Слишком мало данных: {training['n_samples']} строк. "
                f"Нужно минимум 6. Добавь больше resolved предсказаний или "
                f"расширь rag_seed.HISTORICAL_FIGHTS."
            )
        else:
            with st.spinner("Тренируем..."):
                try:
                    meta = ml_model.train_models(training)
                    st.success(
                        f"✅ Модель обучена. Train accuracy: "
                        f"{meta['winner_train_accuracy']*100:.1f}%"
                    )
                    st.session_state.ml_meta_refresh = datetime.now().isoformat()
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Тренировка упала: {e}")
                    st.exception(e)

    # ---- Meta + feature importance ----
    if meta_now and "load_error" not in meta_now:
        st.markdown("### 📊 Model Meta")
        m1, m2, m3 = st.columns(3)
        m1.metric("Train accuracy (winner)",
                  f"{meta_now['winner_train_accuracy']*100:.1f}%")
        method_meta = meta_now.get("method", {})
        m2.metric("Method model",
                  f"{method_meta.get('train_acc', 0)*100:.1f}%" if method_meta.get("trained")
                  else "—")
        m3.metric("Samples", meta_now["n_samples"])

        fi = meta_now.get("feature_importance", {})
        if fi:
            st.markdown("### 🏆 Feature Importance")
            st.caption("Какие признаки модель считает решающими.")
            fi_sorted = sorted(fi.items(), key=lambda x: x[1], reverse=True)
            fi_df = pd.DataFrame(fi_sorted, columns=["Feature", "Importance"])
            fig = px.bar(fi_df, x="Importance", y="Feature", orientation="h",
                         color="Importance", color_continuous_scale="Reds")
            fig.update_layout(paper_bgcolor=BG, plot_bgcolor=BG,
                              font=dict(color=TEXT), height=480,
                              yaxis={"categoryorder": "total ascending"},
                              margin=dict(t=20))
            st.plotly_chart(fig, use_container_width=True)

        with st.expander("🧬 Raw meta JSON"):
            st.json(meta_now)
    else:
        st.info(
            "Модель ещё не натренирована. Нажми **🚀 Train ML Model** выше "
            "когда наберётся достаточно данных."
        )

    # ---- Feature preview ----
    with st.expander("🔬 Preview features для пары бойцов"):
        names = [f["name"] for f in st.session_state.fighters]
        pa, pb = st.columns(2)
        an = pa.selectbox("Fighter A", names, key="ml_prev_a")
        bn = pb.selectbox("Fighter B", names, key="ml_prev_b",
                          index=1 if len(names) > 1 else 0)
        fa_p = next((f for f in st.session_state.fighters if f["name"] == an), None)
        fb_p = next((f for f in st.session_state.fighters if f["name"] == bn), None)
        if fa_p and fb_p:
            feats = ml_model.build_features(fa_p, fb_p)
            df = pd.DataFrame({
                "Feature": ml_model.FEATURE_NAMES,
                "A vs B value": feats,
            })
            st.dataframe(df, use_container_width=True, hide_index=True)
            if meta_now and "load_error" not in meta_now:
                pred = ml_model.predict_ml(fa_p, fb_p)
                if pred.get("available"):
                    st.success(
                        f"ML prediction: **{an}** {pred['win_prob_a']*100:.1f}% / "
                        f"**{bn}** {pred['win_prob_b']*100:.1f}%"
                    )


# =================================================================
# PAGE: FINE-TUNING
# =================================================================
elif page == "🎓 Fine-Tuning":
    try:
        from finetune_ui import render_finetune_page
        render_finetune_page()
    except Exception as e:
        st.error(f"❌ Ошибка Fine-Tuning: {e}")
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
# PAGE: HISTORY & ACCURACY (full dashboard)
# =================================================================
elif page == "📚 History & Accuracy":
    from accuracy_dashboard import render_accuracy_dashboard
    render_accuracy_dashboard(
        history=st.session_state.history,
        persist_history=persist_history,
        history_stats_fn=history_stats,
        compute_brier_score_fn=compute_brier_score,
        calibration_buckets_fn=calibration_buckets,
        auto_resolve_fn=auto_resolve_predictions,
        get_live_events_fn=get_live_events,
        theme={"UFC_RED": UFC_RED, "BG": BG, "TEXT": TEXT,
                "MUTED": MUTED, "BORDER": BORDER},
    )

# (старая инлайновая реализация удалена — теперь в accuracy_dashboard.py)
_OLD_DEAD_BLOCK = """
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
"""


# =================================================================
# PAGE: BACKTESTING (Phase 3)
# =================================================================
if page == "🧪 Backtesting":
    st.markdown("## 🧪 Backtesting Harness")
    st.caption("Оффлайн прогон по разрешённой истории прогнозов. LLM не зовётся.")

    from backtest import run_backtest

    hist = st.session_state.history or []
    resolved_n = sum(1 for h in hist if h.get("tracked") and h.get("result") in ("won","lost"))
    if resolved_n == 0:
        st.info("Нет разрешённых прогнозов. Резолвни хотя бы 1 во вкладке History & Accuracy.")
        st.stop()

    # Filters
    fcol1, fcol2, fcol3 = st.columns(3)
    divisions = sorted({(h.get("ctx") or {}).get("division") or h.get("weight_class") or "—"
                        for h in hist if h.get("tracked")})
    div_sel = fcol1.multiselect("Дивизион", divisions, default=divisions)
    min_conf = fcol2.slider("Min уверенность модели (%)", 50, 95, 50, step=5)
    window = fcol3.slider("Rolling window", 5, 50, 10, step=5)

    def _flt(h):
        if not (h.get("tracked") and h.get("result") in ("won","lost")):
            return False
        d = (h.get("ctx") or {}).get("division") or h.get("weight_class") or "—"
        if d not in div_sel:
            return False
        p = h.get("win_prob")
        try:
            if p is not None and float(p) * 100 < min_conf:
                return False
        except Exception:
            pass
        return True

    rep = run_backtest(hist, filter_fn=_flt, window=window)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📋 В выборке", rep.n_resolved)
    c2.metric("🎯 Accuracy", f"{rep.accuracy_pct:.1f}%" if rep.accuracy_pct is not None else "—")
    c3.metric("📉 Brier", f"{rep.brier:.3f}" if rep.brier is not None else "—",
              help="Меньше=лучше. 0=идеал, 0.25=случайно.")
    c4.metric("📐 LogLoss", f"{rep.log_loss:.3f}" if rep.log_loss is not None else "—")
    if rep.roi.get("roi_pct") is not None:
        c5.metric("💰 ROI", f"{rep.roi['roi_pct']:+.1f}%",
                  help=f"n_bets={rep.roi['n_bets']}, profit={rep.roi['profit']:+.2f}u")
    else:
        c5.metric("💰 ROI", "—", help="Нет записей с bet_odds.")

    st.markdown("---")
    st.markdown("### 📈 Rolling метрики по времени")
    if not rep.over_time.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=rep.over_time["n"], y=rep.over_time["rolling_acc_%"],
                                 name="Rolling Acc %", line=dict(color=UFC_RED, width=3)))
        fig.add_trace(go.Scatter(x=rep.over_time["n"], y=rep.over_time["rolling_brier"]*100,
                                 name="Rolling Brier ×100", line=dict(color=UFC_GOLD, dash="dash")))
        fig.update_layout(paper_bgcolor=BG, plot_bgcolor=BG, font=dict(color=TEXT),
                          height=340, margin=dict(t=10, b=40),
                          xaxis=dict(title="N (хронологически)"), yaxis=dict(title="Значение"))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("Недостаточно данных для графика.")

    bcol1, bcol2 = st.columns(2)
    with bcol1:
        st.markdown("### 🥋 По дивизионам")
        if not rep.by_division.empty:
            st.dataframe(rep.by_division, use_container_width=True, hide_index=True)
        else:
            st.caption("—")
    with bcol2:
        st.markdown("### 🎚️ По уверенности")
        if not rep.by_confidence.empty:
            st.dataframe(rep.by_confidence, use_container_width=True, hide_index=True)
        else:
            st.caption("—")

    with st.expander("📤 Export report (JSON)"):
        import json as _json
        payload = {
            "n_total": rep.n_total, "n_resolved": rep.n_resolved,
            "accuracy_pct": rep.accuracy_pct, "brier": rep.brier,
            "log_loss": rep.log_loss, "roi": rep.roi,
            "by_division": rep.by_division.to_dict("records"),
            "by_confidence": rep.by_confidence.to_dict("records"),
        }
        st.download_button("⬇️ backtest_report.json",
            data=_json.dumps(payload, indent=2, default=str),
            file_name="backtest_report.json", mime="application/json")


# =================================================================
# PAGE: MODEL HEALTH (Phase 5)
# =================================================================
if page == "❤️ Model Health":
    st.markdown("## ❤️ Model Health & Auto-Retrain")
    st.caption("Мониторинг деградации модели и автопереобучение ML при drift.")

    from model_health import (evaluate_health, auto_retrain_if_needed,
                              can_retrain_now, _load_state, THRESHOLDS)

    hist = st.session_state.history or []
    window = st.slider("Rolling window (последние N разрешённых)", 5, 50, 20, step=5)
    health = evaluate_health(hist, window=window)

    status = health["status"]
    status_color = {"healthy": "#16a34a", "warn": UFC_GOLD,
                    "critical": UFC_RED, "unknown": MUTED}.get(status, MUTED)
    st.markdown(
        f"<div style='padding:14px;border-radius:8px;background:{status_color}22;"
        f"border-left:4px solid {status_color};margin-bottom:14px'>"
        f"<b style='color:{status_color};font-size:1.1rem'>Status: {status.upper()}</b>"
        f"</div>", unsafe_allow_html=True)

    stats = health["stats"]
    if not stats.get("insufficient"):
        r, b = stats["recent"], stats["baseline"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Recent N", r["n"])
        c2.metric("Recent Acc",
                  f"{r['accuracy_%']:.1f}%" if r["accuracy_%"] is not None else "—",
                  delta=(f"{(r['accuracy_%'] - b['accuracy_%']):+.1f}pp"
                         if r["accuracy_%"] is not None and b["accuracy_%"] is not None else None))
        c3.metric("Recent Brier",
                  f"{r['brier']:.3f}" if r["brier"] is not None else "—",
                  delta=(f"{(r['brier'] - b['brier']):+.3f}"
                         if r["brier"] is not None and b["brier"] is not None else None),
                  delta_color="inverse")
        c4.metric("Recent ROI",
                  f"{r['roi_pct']:+.1f}%" if r["roi_pct"] is not None else "—",
                  help=f"n_bets={r['n_bets']}")

    if health["alerts"]:
        st.markdown("### 🚨 Алерты")
        for a in health["alerts"]:
            icon = {"critical": "🔴", "warn": "🟡", "info": "ℹ️"}.get(a["level"], "•")
            st.markdown(f"- {icon} **{a['code']}** — {a['message']}")
    else:
        st.success("✅ Все метрики в зелёной зоне.")

    st.markdown("---")
    st.markdown("### 🔁 Retrain ML model")
    ok, msg = can_retrain_now()
    state = _load_state()
    if state.get("last_retrain_iso"):
        st.caption(f"Последний retrain: `{state['last_retrain_iso']}`.")
    if not ok:
        st.warning(msg)

    colr1, colr2 = st.columns(2)

    def _do_retrain():
        from ml_model import assemble_training_data, train_models
        td = assemble_training_data(st.session_state.fighters, st.session_state.history)
        return train_models(td)

    if colr1.button("🤖 Auto-retrain (только если drift)",
                    disabled=not ok, use_container_width=True):
        with st.spinner("Проверяю health и обучаю..."):
            res = auto_retrain_if_needed(hist, _do_retrain, force=False, window=window)
        if res["retrained"]:
            st.success(f"✅ Retrained! Meta: {res.get('meta')}")
        else:
            st.info(f"⏭️ Skipped — {res['reason']}")

    if colr2.button("⚡ Force retrain сейчас", disabled=not ok, use_container_width=True):
        with st.spinner("Force retraining..."):
            res = auto_retrain_if_needed(hist, _do_retrain, force=True, window=window)
        if res["retrained"]:
            st.success(f"✅ Retrained! Meta: {res.get('meta')}")
        else:
            st.error(f"❌ {res['reason']}")

    with st.expander("⚙️ Пороги (config)"):
        st.json(THRESHOLDS)


# =================================================================
# PAGE: BLIND TESTS — модель прогнозирует ивент не зная результатов
# =================================================================
if page == "🎯 Blind Tests":
    st.markdown("## 🎯 Blind Tests")
    st.caption("Прогон модели на ивенте без знания исходов → грейдинг по факту → "
               "иммутабельный лог в `blind_tests/`. Так видно, насколько модель "
               "реально умеет читать карды, без data leakage.")

    import blind_test as bt
    from live_data import get_events_range, parse_event, fetch_espn_scoreboard

    tab_new, tab_history, tab_compare = st.tabs(
        ["🆕 New Blind Run", "📜 History & Grading", "🆚 Compare Runs"])

    # ---------- NEW RUN ----------
    with tab_new:
        st.markdown("### 1️⃣ Выбери ивент")
        col1, col2 = st.columns([1, 1])
        date_from = col1.date_input("От", value=date.today() - timedelta(days=30))
        date_to = col2.date_input("До", value=date.today() + timedelta(days=30))

        events = []
        try:
            events = get_events_range(date_from.strftime("%Y%m%d"),
                                      date_to.strftime("%Y%m%d"))
        except Exception as e:
            st.error(f"ESPN error: {e}")

        if not events:
            st.info("Ивентов в диапазоне нет. Расширь даты.")
        else:
            labels = [f"{e.get('date','')[:10]} — {e['name']} ({len(e.get('fights',[]))} fights)"
                      for e in events]
            sel = st.selectbox("Ивент", range(len(events)), format_func=lambda i: labels[i])
            ev = events[sel]
            st.markdown(f"**🏟 Venue:** {ev.get('venue','—')}  |  **🆔 ESPN ID:** `{ev.get('id')}`")

            # Проверка существующего blind-test файла
            existing = bt.file_for(ev["name"], ev.get("date",""))
            if existing.exists():
                st.warning(f"⚠️ Blind test для этого ивента уже существует: `{existing.name}`. "
                           f"Запуск перезапишет его. Используй вкладку History для просмотра.")

            n_completed = sum(1 for f in ev["fights"] if f.get("completed"))
            st.markdown(
                f"**Бои в карде:** {len(ev['fights'])} "
                f"({n_completed} уже завершено по ESPN — будут blinded для модели)"
            )
            with st.expander("📋 Полный ростер (с реальными результатами — для тебя)"):
                for f in ev["fights"]:
                    a = (f.get("a") or {}).get("name","?")
                    b = (f.get("b") or {}).get("name","?")
                    wc = f.get("weight_class","")
                    res = (f"✅ winner: {(f.get('a') or {}).get('name') if (f.get('a') or {}).get('winner') else (f.get('b') or {}).get('name')} "
                           f"by {f.get('method','?')} R{f.get('round','?')}") if f.get("completed") else "🕒 not finished"
                    st.markdown(f"- **{a} vs {b}** ({wc}) — {res}")

            st.markdown("### 2️⃣ Конфиг прогона")
            ccol1, ccol2 = st.columns(2)
            delay = ccol1.number_input("Пауза между боями (сек, rate-limit)",
                                       0.0, 10.0, 1.5, step=0.5)
            use_demo = ccol2.checkbox("Demo mode (без LLM, заглушка)",
                                      value=not bool(LLM_API_KEY))

            if st.button("🚀 Запустить Blind Test", type="primary",
                         use_container_width=True):
                blinded_fights = bt.blind_fights(ev["fights"])
                progress = st.progress(0.0)
                status = st.empty()

                def _predict(fa, fb, ctx):
                    if use_demo:
                        out = demo_analysis(fa, fb, ctx, "")
                    else:
                        out = get_fight_prediction(fa, fb, ctx, "",
                                                   LLM_API_KEY, LLM_BASE_URL, LLM_MODEL)
                    probs = extract_probabilities(out)
                    return {
                        "predicted_winner": extract_predicted_winner(out),
                        "win_prob": probs.get("win_prob"),
                        "method": (
                            "KO/TKO" if (probs.get("ko_prob") or 0) >= max(
                                probs.get("sub_prob") or 0, probs.get("dec_prob") or 0)
                            else "Submission" if (probs.get("sub_prob") or 0) >= (probs.get("dec_prob") or 0)
                            else "Decision"
                        ) if any([probs.get("ko_prob"), probs.get("sub_prob"), probs.get("dec_prob")]) else None,
                        "round": None,
                        "reasoning": out,
                    }

                def _cb(i, total, msg):
                    progress.progress(i / total)
                    status.markdown(f"🔮 **{i}/{total}** — {msg}")

                path = bt.run_blind_test(
                    event_name=ev["name"],
                    event_date=ev.get("date",""),
                    fights=blinded_fights,
                    predict_fn=_predict,
                    model_meta={"llm_model": LLM_MODEL,
                                "system_prompt_version": "v3",
                                "demo": use_demo},
                    venue=ev.get("venue",""),
                    espn_id=ev.get("id"),
                    delay_s=delay,
                    progress_cb=_cb,
                )
                progress.progress(1.0)
                status.success(f"✅ Blind test сохранён → `{path}`")
                st.balloons()

    # ---------- HISTORY ----------
    with tab_history:
        st.markdown("### 📜 Все blind-tests")
        tests = bt.list_tests()
        if not tests:
            st.info("Ещё ни одного blind-test не запущено. Перейди во вкладку **🆕 New Blind Run**.")
        else:
            rows = []
            for p in tests:
                try:
                    d = bt.load_test(p)
                except Exception:
                    continue
                rows.append({
                    "file": p.name, "path": str(p),
                    "event": d["event"]["name"],
                    "date": d["event"]["date"][:10],
                    "model": d.get("model_meta", {}).get("llm_model","—"),
                    "n": d["summary"]["n"],
                    "graded": d["summary"]["n_graded"],
                    "accuracy_%": d["summary"]["accuracy_%"],
                    "brier": d["summary"]["brier"],
                })
            df = pd.DataFrame(rows)
            st.dataframe(df.drop(columns=["path"]), use_container_width=True, hide_index=True)

            sel_file = st.selectbox("Открыть test", [r["file"] for r in rows])
            sel_path = next(r["path"] for r in rows if r["file"] == sel_file)
            data = bt.load_test(Path(sel_path))

            st.markdown(f"### 🏷 {data['event']['name']}")
            cc1, cc2, cc3, cc4 = st.columns(4)
            cc1.metric("Боёв", data["summary"]["n"])
            cc2.metric("Грейдинг", data["summary"]["n_graded"])
            acc = data["summary"]["accuracy_%"]
            cc3.metric("Accuracy", f"{acc:.1f}%" if acc is not None else "—")
            brier = data["summary"]["brier"]
            cc4.metric("Brier", f"{brier:.3f}" if brier is not None else "—")

            # Грейдинг кнопка
            if st.button("🔄 Pull ESPN results & grade this test"):
                espn_id = data["event"].get("espn_id")
                try:
                    raw = fetch_espn_scoreboard(
                        data["event"]["date"][:10].replace("-","")
                    )
                    matched_ev = None
                    for e in raw.get("events", []):
                        if str(e.get("id")) == str(espn_id):
                            matched_ev = parse_event(e); break
                    if not matched_ev:
                        # fallback: ищем по имени
                        for e in raw.get("events", []):
                            p = parse_event(e)
                            if p["name"] == data["event"]["name"]:
                                matched_ev = p; break
                    if matched_ev:
                        summ = bt.grade_test(Path(sel_path), matched_ev["fights"])
                        st.success(f"✅ Graded: {summ['n_graded']}/{summ['n']}, "
                                   f"acc={summ['accuracy_%']}, brier={summ['brier']}")
                        st.rerun()
                    else:
                        st.error("ESPN event не найден для этой даты.")
                except Exception as e:
                    st.error(f"Grading error: {e}")

            st.markdown("---")
            st.markdown("### 🥊 Прогнозы по боям")
            for rec in data["predictions"]:
                graded = rec.get("graded")
                icon = "✅" if rec.get("correct") else "❌" if graded else "⏳"
                with st.expander(
                    f"{icon} {rec['fighter_a']} vs {rec['fighter_b']} ({rec.get('weight_class','—')})"):
                    cA, cB = st.columns(2)
                    with cA:
                        st.markdown("**🔮 Predicted**")
                        st.markdown(f"- Winner: **{rec.get('predicted_winner') or '—'}**")
                        wp = rec.get("win_prob")
                        st.markdown(f"- Confidence: **{wp*100:.0f}%**" if wp else "- Confidence: —")
                        st.markdown(f"- Method: {rec.get('method') or '—'}")
                        st.markdown(f"- Odds (a/b): {rec.get('odds_a') or '—'} / {rec.get('odds_b') or '—'}")
                    with cB:
                        st.markdown("**📊 Actual**")
                        if graded:
                            st.markdown(f"- Winner: **{rec.get('actual_winner') or '—'}**")
                            st.markdown(f"- Method: {rec.get('actual_method') or '—'}")
                            st.markdown(f"- Round: {rec.get('actual_round') or '—'}")
                            br = rec.get("brier")
                            if br is not None:
                                st.markdown(f"- Brier: **{br:.3f}**")
                        else:
                            st.markdown("_Не грейднут. Нажми Pull & grade._")
                    if rec.get("reasoning"):
                        with st.expander("🧠 Reasoning"):
                            st.markdown(rec["reasoning"])

                    # ---- Извлечь урок из промаха ----
                    if graded and rec.get("correct") is False:
                        from lessons import add_lesson
                        with st.expander("📝 Извлечь урок из этого промаха"):
                            lt = st.text_input(
                                "Заголовок урока",
                                key=f"lt_{rec['fighter_a']}_{rec['fighter_b']}",
                                placeholder="Напр.: Старый ветеран vs молодой нокаутер")
                            lb = st.text_area(
                                "Описание правила",
                                key=f"lb_{rec['fighter_a']}_{rec['fighter_b']}",
                                placeholder="Что модель не учла и что должна была учесть.",
                                height=100)
                            lk = st.text_input(
                                "Trigger keywords (через запятую)",
                                key=f"lk_{rec['fighter_a']}_{rec['fighter_b']}",
                                placeholder="35+, chin, prospect, перт")
                            if st.button("➕ Сохранить урок",
                                         key=f"savel_{rec['fighter_a']}_{rec['fighter_b']}"):
                                if lt and lb:
                                    add_lesson(
                                        lt, lb,
                                        tags=[],
                                        trigger_keywords=[k.strip() for k in lk.split(",") if k.strip()],
                                        source=f"blind_test:{Path(sel_path).name}",
                                    )
                                    st.success("✅ Урок сохранён в lessons.json")
                                else:
                                    st.warning("Заполни title и body.")

            st.markdown("---")
            st.download_button("⬇️ Export JSON",
                data=json.dumps(data, indent=2, ensure_ascii=False, default=str),
                file_name=Path(sel_path).name,
                mime="application/json")

    # ---------- COMPARE RUNS ----------
    with tab_compare:
        st.markdown("### 🆚 Сравнить несколько прогонов одного ивента")
        st.caption("Группирует blind-tests по ESPN event id. Показывает дельту "
                   "метрик и per-fight разницу.")
        tests = bt.list_tests()
        if not tests:
            st.info("Нет blind-tests для сравнения.")
        else:
            # группировка по espn_id
            groups = {}
            for p in tests:
                try:
                    d = bt.load_test(p)
                except Exception:
                    continue
                key = d["event"].get("espn_id") or d["event"]["name"].split(" [")[0]
                groups.setdefault(key, []).append((p, d))

            gkeys = [k for k, v in groups.items() if len(v) >= 2]
            if not gkeys:
                st.info("Пока только 1 прогон на ивент. Сделай второй (с другим "
                        "промптом/агентами/lessons) — тогда появится сравнение.")
            else:
                def _label(k):
                    d = groups[k][0][1]
                    return f"{d['event']['date'][:10]} — {d['event']['name'].split(' [')[0]}  ({len(groups[k])} runs)"
                sel_group = st.selectbox("Ивент", gkeys, format_func=_label)
                runs = groups[sel_group]

                # summary table
                summary_rows = []
                for path, d in runs:
                    s = d["summary"]
                    meta = d.get("model_meta", {})
                    summary_rows.append({
                        "file": path.name,
                        "version": meta.get("system_prompt_version", "—"),
                        "model": meta.get("llm_model", "—"),
                        "lessons": "✅" if meta.get("lessons_injected") or "lessons" in str(meta.get("system_prompt_version","")) else "—",
                        "n": s["n"], "graded": s["n_graded"],
                        "accuracy_%": s.get("accuracy_%"),
                        "brier": s.get("brier"),
                    })
                st.dataframe(pd.DataFrame(summary_rows),
                             use_container_width=True, hide_index=True)

                # Bar chart comparing metrics
                cmp_fig = go.Figure()
                labels = [r["version"] for r in summary_rows]
                accs = [r["accuracy_%"] or 0 for r in summary_rows]
                briers = [(r["brier"] or 0) * 100 for r in summary_rows]
                cmp_fig.add_trace(go.Bar(name="Accuracy %", x=labels, y=accs,
                                         marker_color=UFC_RED))
                cmp_fig.add_trace(go.Bar(name="Brier ×100", x=labels, y=briers,
                                         marker_color=UFC_GOLD))
                cmp_fig.update_layout(barmode="group",
                    paper_bgcolor=BG, plot_bgcolor=BG, font=dict(color=TEXT),
                    height=320, margin=dict(t=10, b=40))
                st.plotly_chart(cmp_fig, use_container_width=True)

                st.markdown("---")
                st.markdown("### 🥊 Per-fight сравнение")
                # Собираем все бои с прогнозами всех runs
                # ключ: (fighter_a, fighter_b)
                fight_map = {}
                for path, d in runs:
                    for rec in d["predictions"]:
                        k = (rec["fighter_a"], rec["fighter_b"])
                        fight_map.setdefault(k, {})
                        fight_map[k][d.get("model_meta",{}).get("system_prompt_version","run")] = rec

                # Строим сравнительную таблицу
                comp_rows = []
                for (a, b), by_run in fight_map.items():
                    row = {"bout": f"{a} vs {b}"}
                    actual = None
                    for ver, rec in by_run.items():
                        wp = rec.get("win_prob")
                        wp_s = f"{wp*100:.0f}%" if wp else "—"
                        ok = rec.get("correct")
                        icon = "✅" if ok else "❌" if rec.get("graded") else "⏳"
                        row[ver] = f"{icon} {rec.get('predicted_winner','—')} ({wp_s})"
                        if rec.get("graded") and actual is None:
                            actual = rec.get("actual_winner")
                    row["actual"] = actual or "—"
                    comp_rows.append(row)
                st.dataframe(pd.DataFrame(comp_rows),
                             use_container_width=True, hide_index=True)


# =================================================================
# PAGE: LESSONS — память ошибок модели
# =================================================================
if page == "📖 Lessons":
    st.markdown("## 📖 Lessons Memory")
    st.caption("Персистентные уроки извлечённые из промахов. Автоматически "
               "инжектятся в промпт перед каждым прогнозом если совпадают "
               "trigger keywords.")

    from lessons import (load_lessons, add_lesson, remove_lesson,
                          toggle_lesson, save_lessons)

    lessons = load_lessons()
    active = sum(1 for l in lessons if l.get("active", True))
    mc1, mc2 = st.columns(2)
    mc1.metric("📚 Всего уроков", len(lessons))
    mc2.metric("✅ Активных", active)

    st.markdown("---")
    st.markdown("### ➕ Добавить новый урок")
    with st.form("new_lesson", clear_on_submit=True):
        nt = st.text_input("Заголовок", placeholder="Напр.: Home crowd bias в Австралии")
        nb = st.text_area("Правило", height=120,
            placeholder="Опиши паттерн чётко. Когда срабатывает, что делать.")
        nk = st.text_input("Trigger keywords (через запятую)",
            placeholder="perth, sydney, australia, австрал")
        ntags = st.text_input("Tags (через запятую)",
            placeholder="home_bias, judge_bias")
        if st.form_submit_button("➕ Сохранить"):
            if nt and nb:
                add_lesson(nt, nb,
                    tags=[t.strip() for t in ntags.split(",") if t.strip()],
                    trigger_keywords=[k.strip() for k in nk.split(",") if k.strip()],
                    source="manual")
                st.success("✅ Урок добавлен"); st.rerun()
            else:
                st.warning("Title и body обязательны.")

    st.markdown("---")
    st.markdown("### 📜 Все уроки")
    for l in lessons:
        active_emoji = "🟢" if l.get("active", True) else "⚪"
        with st.expander(f"{active_emoji} {l['title']}"):
            st.markdown(l["body"])
            if l.get("tags"):
                st.markdown("**Tags:** " + ", ".join(f"`{t}`" for t in l["tags"]))
            if l.get("trigger_keywords"):
                st.markdown("**Triggers:** " + ", ".join(f"`{k}`" for k in l["trigger_keywords"]))
            st.caption(f"id: `{l['id']}` · source: `{l.get('source','—')}` · "
                       f"created: {l.get('created_at','—')}")
            c1, c2 = st.columns(2)
            if c1.button(("🔇 Деактивировать" if l.get("active", True)
                          else "🔊 Активировать"), key=f"tog_{l['id']}"):
                toggle_lesson(l["id"]); st.rerun()
            if c2.button("🗑️ Удалить", key=f"del_{l['id']}"):
                remove_lesson(l["id"]); st.rerun()


# Footer
st.markdown("---")
st.caption(
    f"🥊 Octagon Oracle · Streamlit · "
    f"<span style='color:{UFC_RED}'>Не финансовая рекомендация. Ставь с умом.</span>",
    unsafe_allow_html=True,
)
