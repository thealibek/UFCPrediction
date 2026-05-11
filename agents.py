"""Multi-Agent архитектура для UFC Predictor.

Идея: вместо одного жирного промпта — 4 специализированных агента.
Каждый видит только свою часть контекста и думает узко-глубоко.
Финальный Synthesizer собирает их выводы в калиброванный прогноз + ставку.

Преимущества:
- Каждый агент даёт более глубокий разбор в своей области
- Можно использовать разные модели (дешёвая для Stats, мощная для Synthesizer)
- Параллельный запуск агентов 1-3 → быстрее по wall-clock
- Прозрачность: видно reasoning каждого агента отдельно
- Легко расширяется (добавь новый класс Agent + добавь в orchestrator)

Совместимо с любым OpenAI-API endpoint (OpenAI / Groq / Together / LiteLLM proxy).
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Agent system prompts
# ---------------------------------------------------------------------------

STATS_AGENT_PROMPT = """You are the **Stats & Data Agent** of a UFC prediction system.
Your ONLY job: cold quantitative analysis of fighter metrics.

Анализируй ТОЛЬКО цифры и факты:
- Striking volume (SLpM vs SApM) — кто кого переплюнет в обмене
- Точность и защита (StrAcc/StrDef) — кто чище попадает
- Wrestling differential (TDAvg vs TDDef оппонента)
- Submission threat (SubAvg)
- Возраст, рекорд (общий и за последние 5 боёв), reach/height advantage
- Цифры из RAG (исторические бои, прошлые матч-апы)

ФОРМАТ:
### 🔢 СТАТИСТИЧЕСКОЕ ПРЕИМУЩЕСТВО
- **Стенд-ап:** [кто фаворит, на сколько % edge]
- **Борьба:** [TDAvg vs TDDef matchup]
- **Сабмишены:** [угроза]
- **Физика:** [reach, height, age]
- **Историческая база:** [что говорят похожие matchups из RAG]

### 📊 ВЕРДИКТ STATS
Кому отдают цифры: **[Имя]**. Уровень уверенности: [Низкий/Средний/Высокий].
Ключевая цифра, на которую опираешься: [одна решающая метрика].

Будь сухим и точным. Никаких прогнозов исхода — это работа другого агента.
Только цифры и их интерпретация."""


STYLE_AGENT_PROMPT = """You are the **Style & Matchup Agent** of a UFC prediction system.
Your ONLY job: deep stylistic analysis. How styles clash.

Анализируй ТОЛЬКО стиль и matchup:
- Кто pressure fighter, кто counter-striker
- Wrestler vs striker dynamic — кому достаточно одного takedown
- Распределение распределения (orthodox/southpaw lead-leg dynamics)
- Кому помогают рауд-длина (3 vs 5 раундов)
- Комбинации, range, footwork, head movement
- Какие исторические matchups похожи (используй RAG-контекст)

ФОРМАТ:
### 🥊 СТИЛЕВОЙ МАТЧ-АП
- **Архетипы:** [тип A] vs [тип B]
- **Range game:** [кто диктует дистанцию]
- **Grappling exchanges:** [кому это выгодно]
- **Stance dynamics:** [orthodox/southpaw lead-leg, выпады]
- **Похожий исторический бой:** [из RAG если есть — какой и чем закончился]

### 🎯 СТИЛЕВОЙ ВЕРДИКТ
Кому matchup стилистически удобен: **[Имя]**.
Главный стилистический рычаг: [конкретный приём/паттерн].
Что должен сделать аутсайдер: [тактика на upset].

Будь жёстким и предметным. Используй MMA-сленг."""


CONTEXT_AGENT_PROMPT = """You are the **Context & Intel Agent** of a UFC prediction system.
Your ONLY job: ситуационный, ментальный и физический контекст.

Анализируй ТОЛЬКО:
- Травмы, лагерь, тренеры (если упомянуто в intel)
- Весогонка — насколько тяжёлая была, переходы между весами
- Лэйоф, активность за последние 12 месяцев
- Психология — мотивация, давление, последние KO/sub поражения
- Возрастные тренды (30+ декадирование, 35+ резкое падение)
- Внеспортивные факторы (драма, скандалы, контракт)
- Camp changes, новые тренеры, переезды

ФОРМАТ:
### 🧠 КОНТЕКСТ И МЕНТАЛКА
- **Форма (последние бои):** [тренд каждого]
- **Весогонка:** [риски и сложности]
- **Психология:** [уверенность, поражение от прошлого опыта]
- **Внеспортивное:** [то что в intel или известно]
- **Activity:** [последний бой когда, ring rust]

### ⚡ КОНТЕКСТНЫЙ ВЕРДИКТ
Кому ментально/физически контекст благоприятнее: **[Имя]**.
Главный risk-factor: [что может пойти не так].
Hidden edge: [неочевидный фактор].

Никакой статистики — это работа Stats Agent. Только soft factors."""


OPPOSITION_AGENT_PROMPT = """You are the **Opposition Agent** (devil's advocate) of a UFC
prediction system. Your ONLY job: построить СИЛЬНЕЙШИЙ кейс за АНДЕРДОГА.

Даже если фаворит очевиден — представь, что тебе платят только если андердог
побеждает. Найди все причины, пути к апсету, паттерны, подсказки из RAG/intel.

Анализируй:
- Слабости у фаворита, которые эксплойтит стиль андердога
- Исторические апсеты в похожих matchup-ах (RAG)
- Intangibles: motivation, mismatch в раздевалке, ring rust фаворита
- Конкретный game plan: «если X делает Y в раунде Z — апсет реален»

ФОРМАТ:
### 🚨 OPPOSITION CASE
- **Путь к апсету:** [конкретный сценарий]
- **Эксплойт-стиль:** [какая слабость фаворита кликает на стиль андердога]
- **Исторический прецедент:** [похожий апсет из RAG, если есть]
- **Скрытые факторы:** [intel/motivation/форма]

### ⚖️ ВЕРДИКТ OPPOSITION
Вероятность апсета (грубая оценка): XX%. Если >35% — это НЕ heavy favorite.
Главная причина: [одна фраза]."""


HISTORICAL_AGENT_PROMPT = """You are the **Historical Parallels Agent** of a UFC prediction
system. Your ONLY job: найти 2-3 наиболее похожих боя из прошлого (через RAG)
и спроецировать их исходы на текущий бой.

Критерии похожести: стили, физические данные, весовой класс, возраст, опыт,
опыт против конкретного типа оппонента.

ФОРМАТ:
### 📜 ИСТОРИЧЕСКИЕ ПАРАЛЛЕЛИ
1. **[Бой X vs Y, дата]** — чем похож на текущий, как закончился, урок.
2. **[Бой X vs Y, дата]** — чем похож, как закончился.
3. (опционально) **[Бой X vs Y]** — если есть.

### 🎯 ПРОЕКЦИЯ
Если большинство параллелей закончились одинаково → это **сильный сигнал**.
Если разнобой → это **близкий бой** и базы недостаточно.
Прогноз на основе истории: **[Имя]** побеждает, метод чаще всего [KO/Sub/Dec].
Уверенность базы: [Низкая/Средняя/Высокая]."""


SYNTHESIZER_PROMPT = """You are the **Betting Edge Synthesizer** — финальный агент UFC predictor system.
Ты получаешь выводы 3 специализированных агентов (Stats / Style / Context) и
формируешь финальный калиброванный прогноз + рекомендацию по ставке.

ПРАВИЛА КАЛИБРОВКИ:
- Если все 3 агента согласны → 70-80% уверенности
- Если 2 из 3 согласны → 60-70%
- Если агенты противоречат → 52-60% (близкий бой)
- НИКОГДА не ставь 90%+ если хотя бы один агент видит риск
- Учитывай, что Brier Score штрафует overconfidence жёстче чем underconfidence

ФОРМАТ ОТВЕТА (СТРОГО):

### 🎯 ПРОГНОЗ
Победитель: **[Имя]** — XX% уверенности.
Метод: KO/TKO XX% · Submission XX% · Decision XX%.
Раунд (если финиш): R[1-5].

### 📊 АНАЛИТИКА
2-3 коротких абзаца, синтезирующих выводы агентов. Цитируй: "Stats Agent отдаёт edge X...,
Style Agent видит matchup как..., Context Agent предупреждает о...".
Где агенты согласны, где расходятся.

### 💰 ЛУЧШАЯ СТАВКА
Конкретно: ML / Method / Round / Total. Где value (учитывая odds если даны).
Если все 3 агента уверены → main bet.
Если расхождение → safer prop (например, "над 2.5 раунда" или "идёт в decision").

### ⚠️ РИСКИ
2-4 жёстких сценария почему ставка может не зайти. Бери прямо из выводов агентов
(особенно Context Agent risk-factors).

Будь острым, калиброванным, не overconfident."""


# ---------------------------------------------------------------------------
# Agent class
# ---------------------------------------------------------------------------

@dataclass
class Agent:
    """Один агент: имя + system prompt + модель/endpoint."""
    name: str
    system_prompt: str
    model: str
    api_key: str
    base_url: str | None = None
    temperature: float = 0.4
    max_tokens: int = 900

    def run(self, user_msg: str) -> str:
        """Запустить агента. Возвращает текст ответа или error string."""
        try:
            from openai import OpenAI
            client = (
                OpenAI(api_key=self.api_key, base_url=self.base_url)
                if self.base_url
                else OpenAI(api_key=self.api_key)
            )
            resp = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f"❌ {self.name} error: {e}"


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

@dataclass
class MultiAgentResult:
    """Результат запуска multi-agent prediction."""
    final: str
    agent_outputs: dict[str, str] = field(default_factory=dict)
    timings: dict[str, float] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def _build_base_user_msg(fa: dict, fb: dict, ctx: dict, intel: str,
                          rag_context: str = "") -> str:
    """Базовый user message, отправляемый каждому агенту (всем — один и тот же)."""
    def stat(f):
        if not f: return "—"
        return (
            f"{f.get('name','?')} ({f.get('country','')}, {f.get('age','?')} лет, "
            f"{f.get('record','?')}, {f.get('stance','?')}). "
            f"Style: {f.get('style','?')}. "
            f"SLpM {f.get('SLpM','?')}, SApM {f.get('SApM','?')}, "
            f"StrAcc {f.get('StrAcc','?')}%, StrDef {f.get('StrDef','?')}%, "
            f"TDAvg {f.get('TDAvg','?')}, TDDef {f.get('TDDef','?')}%, "
            f"SubAvg {f.get('SubAvg','?')}. "
            f"Strengths: {', '.join(f.get('strengths',[]) or [])}. "
            f"Weaknesses: {', '.join(f.get('weaknesses',[]) or [])}."
        )

    base = (
        f"БОЙ: {fa.get('name','A')} vs {fb.get('name','B')}\n"
        f"ИВЕНТ: {ctx.get('event','UFC')}\n"
        f"ВЕСОВАЯ: {ctx.get('division','?')}\n"
        f"РАУНДОВ: {ctx.get('rounds',3)}{'  (TITLE)' if ctx.get('title_fight') else ''}\n\n"
        f"=== БОЕЦ A ===\n{stat(fa)}\n\n"
        f"=== БОЕЦ B ===\n{stat(fb)}\n"
    )
    if intel and intel.strip():
        base += f"\n=== INTEL / NEWS ===\n{intel.strip()}\n"
    if rag_context:
        base += (
            f"\n=== KNOWLEDGE BASE (real data, ground analysis here) ===\n"
            f"{rag_context}\n=== END KB ===\n"
        )
    return base


def _build_synthesizer_msg(base: str, agent_outputs: dict[str, str]) -> str:
    """User message для Synthesizer-агента: получает вывод всех остальных."""
    parts = [base, "\n=== ВЫВОДЫ АГЕНТОВ ==="]
    for name, output in agent_outputs.items():
        parts.append(f"\n--- {name} ---\n{output}\n")
    parts.append(
        "\n=== ЗАДАЧА ===\n"
        "Синтезируй финальный прогноз + ставку в строгом формате (см. system prompt). "
        "Калибруй уверенность по согласованности агентов."
    )
    return "\n".join(parts)


def run_multi_agent_prediction(
    fa: dict, fb: dict, ctx: dict, intel: str,
    rag_context: str = "",
    api_key: str = "",
    base_url: str | None = None,
    models: dict | None = None,
    parallel: bool = True,
    include_opposition: bool = False,
    include_historical: bool = False,
) -> MultiAgentResult:
    """Главный orchestrator. Запускает 3 агента (параллельно по умолчанию),
    затем Synthesizer.

    Args:
      models: dict с per-agent моделями. Ключи: 'stats','style','context','synthesizer'.
              Если ключ отсутствует — используется модель по умолчанию.
              Пример: {'stats': 'llama-3.1-8b-instant', 'synthesizer': 'gpt-4o'}
    """
    models = models or {}
    default_model = models.get("default", "llama-3.3-70b-versatile")

    # Builders
    base_msg = _build_base_user_msg(fa, fb, ctx, intel, rag_context)

    agents = {
        "Stats Agent": Agent(
            name="Stats Agent",
            system_prompt=STATS_AGENT_PROMPT,
            model=models.get("stats", default_model),
            api_key=api_key, base_url=base_url,
            temperature=0.3, max_tokens=700,
        ),
        "Style Agent": Agent(
            name="Style Agent",
            system_prompt=STYLE_AGENT_PROMPT,
            model=models.get("style", default_model),
            api_key=api_key, base_url=base_url,
            temperature=0.5, max_tokens=700,
        ),
        "Context Agent": Agent(
            name="Context Agent",
            system_prompt=CONTEXT_AGENT_PROMPT,
            model=models.get("context", default_model),
            api_key=api_key, base_url=base_url,
            temperature=0.5, max_tokens=600,
        ),
    }
    if include_opposition:
        agents["Opposition Agent"] = Agent(
            name="Opposition Agent",
            system_prompt=OPPOSITION_AGENT_PROMPT,
            model=models.get("opposition", default_model),
            api_key=api_key, base_url=base_url,
            temperature=0.6, max_tokens=600,
        )
    if include_historical:
        agents["Historical Parallels Agent"] = Agent(
            name="Historical Parallels Agent",
            system_prompt=HISTORICAL_AGENT_PROMPT,
            model=models.get("historical", default_model),
            api_key=api_key, base_url=base_url,
            temperature=0.4, max_tokens=700,
        )

    agent_outputs: dict[str, str] = {}
    timings: dict[str, float] = {}
    errors: list[str] = []

    # Запускаем агентов 1-3 параллельно
    if parallel:
        with ThreadPoolExecutor(max_workers=max(3, len(agents))) as ex:
            futures = {
                ex.submit(agent.run, base_msg): name
                for name, agent in agents.items()
            }
            for future in as_completed(futures):
                name = futures[future]
                t0 = time.time()
                try:
                    out = future.result()
                except Exception as e:
                    out = f"❌ {name} crashed: {e}"
                    errors.append(name)
                agent_outputs[name] = out
                timings[name] = time.time() - t0
    else:
        for name, agent in agents.items():
            t0 = time.time()
            agent_outputs[name] = agent.run(base_msg)
            timings[name] = time.time() - t0

    # Synthesizer (последовательно — должен видеть всё)
    synth = Agent(
        name="Synthesizer",
        system_prompt=SYNTHESIZER_PROMPT,
        model=models.get("synthesizer", default_model),
        api_key=api_key, base_url=base_url,
        temperature=0.4, max_tokens=1500,
    )
    synth_msg = _build_synthesizer_msg(base_msg, agent_outputs)
    t0 = time.time()
    final = synth.run(synth_msg)
    timings["Synthesizer"] = time.time() - t0

    return MultiAgentResult(
        final=final,
        agent_outputs=agent_outputs,
        timings=timings,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# Helper для UI: список доступных агентов (для отображения и расширения)
# ---------------------------------------------------------------------------

AGENT_REGISTRY = [
    {"key": "stats", "name": "Stats Agent",
     "icon": "🔢", "description": "Холодный анализ цифр и метрик"},
    {"key": "style", "name": "Style Agent",
     "icon": "🥊", "description": "Глубокий стилистический матч-ап"},
    {"key": "context", "name": "Context Agent",
     "icon": "🧠", "description": "Менталка, форма, весогонка, intel"},
    {"key": "opposition", "name": "Opposition Agent",
     "icon": "🚨", "description": "Devil's advocate — кейс за андердога"},
    {"key": "historical", "name": "Historical Parallels",
     "icon": "📜", "description": "RAG-параллели из прошлых боёв"},
    {"key": "synthesizer", "name": "Synthesizer",
     "icon": "🎯", "description": "Финальный синтез + калибровка ставки"},
]
