# UFC AI Предиктор | Octagon Oracle

Профессиональный AI-предиктор боёв UFC на Streamlit. Глубокая аналитика, статистика, прогнозы и рекомендации по ставкам.

## Запуск

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Настройка LLM

В сайдбаре укажи API Key и Base URL. По умолчанию — Groq (`https://api.groq.com/openai/v1`).
Поддерживаются OpenAI-совместимые провайдеры: Groq, xAI, OpenAI, Together.

Демо-режим работает без ключа — отдаёт качественный пример анализа.

## Данные

- `fighters.json` — база бойцов (создаётся автоматически с 15+ реальными бойцами)
- `upcoming_events.json` — ближайшие события
- `history.json` — сохранённые прогнозы

Статистика основана на открытых данных ufcstats.com / FightMetric. База редактируется пользователем.
