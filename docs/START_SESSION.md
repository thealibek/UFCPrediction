# Start Session — Context Bootstrap

> Скинь этот файл в начале каждой новой сессии с AI ассистентом. Цель — за 30 секунд погрузить ассистента в контекст проекта без повторных объяснений.

---

## Что это за проект

**Octagon AI** — UFC fight prediction engine + web dashboard.

Состоит из двух слоёв:

| Слой | Где живёт | Стек |
|---|---|---|
| **Predictor (Python)** | `/Users/alibek/Documents/UFC Predictor/*.py` | Python, XGBoost, ChromaDB, Groq LLM |
| **Web app (Next.js)** | `/Users/alibek/Documents/UFC Predictor/web/` | Next.js 15 App Router, React 19, TypeScript, Tailwind, shadcn/ui |

Полная архитектура: см. `docs/WEB_ARCHITECTURE.md` (web) и `ARCHITECTURE.md` в корне (Python predictor).

---

## Кто я (пользователь)

- **Роль:** соло-разработчик и владелец продукта
- **Язык общения:** русский (короткие, прямые ответы)
- **Стиль работы:** terse, без преамбул, минимум воды; только конкретные изменения и факты
- **Приоритет:** сначала рабочая фича, потом полировка

---

## Что должен делать AI в начале сессии

1. **Прочитать `docs/WEB_ARCHITECTURE.md`** — понять текущее состояние веб-приложения
2. **Прочитать `progress.txt`** (если есть) — знать что было в прошлой сессии
3. **Спросить меня кратко** что хотим делать сегодня — НЕ начинать кодить наугад
4. **Не дублировать вопросы** про стек / фреймворки / папки — всё уже задокументировано
5. **Использовать `code_search`** для исследования кода вместо случайных `grep` / `find`
6. **Перед кодом** проверять текущую структуру файла через `read_file`, не угадывать

---

## Конвенции которые AI должен соблюдать

### Код
- **Никаких комментариев** в коде если я не попросил
- **TypeScript strict** — никаких `any` без явной причины
- **Tailwind only** для стилей (никаких CSS modules / styled-components)
- **shadcn/ui компоненты** уже есть в `web/components/ui/` — переиспользовать, не создавать аналоги
- **next/image** для всех картинок (уже настроены `remotePatterns` в `next.config.ts`)
- Существующий компонент `<FighterPhoto>` (`web/components/fighter-photo.tsx`) — для всех аватарок бойцов

### Файлы
- **Ничего не создавать в корне** проекта — только в `web/` или `docs/`
- **Не писать helper-скрипты** на каждый чих — в большинстве случаев существующая логика покрывает
- **Не создавать README/notes** просто так — только если они реально нужны для следующих сессий

### Общение
- **Без "You're absolutely right!"** и других ритуальных фраз — сразу к делу
- **Tool calls параллельно** где можно (независимые grep / read)
- **Цитировать файлы в формате** `` `@/абсолютный/путь:строка` ``
- **Быстро решать** — не задавать 5 уточняющих вопросов если можно сделать разумный default

### Тесты и валидация
- После изменений в TS/TSX — `npx tsc --noEmit -p .` из `web/`
- Никогда не удалять тесты или ослаблять их без явного разрешения

---

## Активные ограничения и контекст

- **Apify API не подключен** — данные из ESPN public scoreboard
- **ChromaDB не подключена к web** — только в Python predictor
- **Python predictor не дёргается из web** — на дашборде сейчас детерминистичные синтетические прогнозы (placeholder)
- **Аутентификация** — фейковая через `lib/user.tsx` (UserProvider), нет реального бэкенда
- **БД** — нет; всё хранится в JSON файлах в `web/lib/*.json`

---

## Команды быстрого старта

```bash
# Запустить веб-приложение
cd web && npm run dev

# Проверить TS
cd web && npx tsc --noEmit -p .

# Обновить базу бойцов (фото + статы из ESPN)
# В UI: /admin → Refresh Fighters Database
# Программно: POST /api/admin/refresh-fighters
```

---

## Структура за 10 секунд

```
UFC Predictor/
├── *.py                    # Python predictor (predictions, ML, RAG, lessons)
├── ARCHITECTURE.md         # Python pipeline docs
├── docs/                   # ← AI session docs (этот файл)
└── web/                    # Next.js dashboard
    ├── app/                # App Router pages + API routes
    ├── components/         # React components (ui/ — shadcn, остальное custom)
    ├── lib/                # Бизнес-логика, типы, JSON датасеты
    └── public/             # Static assets
```

---

**Готово. Жду что хотим делать.**
