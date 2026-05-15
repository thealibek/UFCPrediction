# Web App Architecture — `web/`

> Snapshot текущего состояния Next.js dashboard. Обновлять в конце каждой сессии (см. `END_SESSION.md`).

---

## Стек

| Уровень | Технология |
|---|---|
| Framework | Next.js 15 (App Router) |
| UI | React 19, TypeScript strict |
| Стили | Tailwind CSS 4, `cn()` helper |
| Компоненты | shadcn/ui (Radix primitives) |
| Иконки | lucide-react |
| Изображения | `next/image` через `<FighterPhoto>` |
| Тосты | sonner |
| Графики | recharts |
| Auth | mock через `UserProvider` (нет бэкенда) |
| Хранилище | JSON файлы в `web/lib/*.json` |

---

## Структура `web/`

```
web/
├── app/                              # Next.js App Router
│   ├── layout.tsx                    # Root layout: UserProvider + NotificationsProvider + Sidebar + Header
│   ├── page.tsx                      # / — Dashboard (events grid + past fights)
│   ├── upcoming/page.tsx             # /upcoming — все будущие бои сгруппированные по ивенту
│   ├── events/
│   │   ├── [id]/page.tsx             # /events/:id — детальная страница ивента (все бои)
│   │   └── [id]/[boutId]/page.tsx    # /events/:id/:boutId — конкретный бой (Tabs: Prediction / Stats)
│   ├── fighters/
│   │   ├── page.tsx                  # /fighters — Fighters Database (grid + поиск + весовая)
│   │   └── [id]/page.tsx             # /fighters/:id — профиль бойца (статы, био)
│   ├── fights/[id]/page.tsx          # /fights/:id — старая страница боя (legacy?)
│   ├── history/page.tsx              # /history — паид: история прогнозов пользователя
│   ├── insights/page.tsx             # /insights — паид: аналитика
│   ├── settings/page.tsx             # /settings — настройки + admin refresh card
│   ├── admin/
│   │   ├── page.tsx                  # /admin — админ дашборд + кнопка обновления БД
│   │   ├── training/page.tsx
│   │   ├── analytics/page.tsx
│   │   ├── lessons/page.tsx
│   │   └── model/page.tsx
│   └── api/
│       ├── events/route.ts           # GET /api/events — список ивентов из ESPN scoreboard
│       ├── events/[id]/route.ts      # GET /api/events/:id — детали ивента + bouts
│       ├── upcoming-fights/route.ts  # GET /api/upcoming-fights — плоский список боёв
│       ├── fighters/[id]/route.ts    # GET /api/fighters/:id — профиль + статы
│       └── admin/refresh-fighters/   # POST/GET — обновление JSON-базы из ESPN
│
├── components/
│   ├── ui/                           # shadcn/ui (button, card, dialog, tabs, avatar, etc.)
│   ├── fighter-photo.tsx             # 🏆 Универсальная аватарка бойца — next/image + fallback инициалы
│   ├── upgrade-modal.tsx             # Paywall модалка для paid фич
│   ├── layout/
│   │   ├── sidebar.tsx               # Левый сайдбар (sticky), nav + admin section
│   │   └── header.tsx                # Топ-бар: search, notifications, user menu
│   ├── dashboard/
│   │   ├── event-card.tsx            # Карточка ивента (Main Event фото + локация)
│   │   ├── past-fights.tsx           # Recent Results виджет (correct / wrong)
│   │   └── ...
│   ├── notifications/
│   │   ├── notification-bell.tsx     # Колокольчик с unread badge
│   │   ├── notification-dropdown.tsx
│   │   └── ...
│   ├── admin/
│   │   └── refresh-fighters-card.tsx # Кнопка обновления БД (compact + full варианты)
│   └── motion/                       # 🎬 Motion wrappers (см. секцию "Animations")
│       ├── motion-div.tsx            # <MotionDiv preset="fadeUp" delay={n}>
│       ├── motion-card.tsx           # Hover lift + glow border
│       ├── motion-button.tsx         # Scale 1.03 hover / 0.97 tap (через motion.span)
│       ├── stagger-container.tsx     # <StaggerContainer> + <StaggerItem> для grid
│       ├── page-transition.tsx       # AnimatePresence по pathname в root layout
│       └── index.ts
│
├── lib/
│   ├── events.ts                     # Типы Event/Bout + парсер main event из названия
│   ├── fights.ts                     # Типы Fight/PastFight + sample data
│   ├── fighter-images.ts             # 🏆 getFighterImage() с защитой от collision по фамилии
│   ├── fighter-images.json           # 910 бойцов: имя → ESPN headshot URL (или null)
│   ├── fighter-data.json             # Enrichment: weight, height, age, country, weightClass, ESPN id
│   ├── fighter-meta.json             # { lastUpdated, totalFighters, withImage, withWeight }
│   ├── notifications.tsx             # NotificationsProvider + useNotifications hook
│   ├── user.tsx                      # UserProvider — mock auth (role, hasFullAccess)
│   ├── utils.ts                      # cn() helper
│   └── admin/
│       └── refresh-fighters.ts       # 3-фазный refresh: roster names → headshots → enrichment
│
├── next.config.ts                    # remotePatterns для a.espncdn.com (next/image)
├── tailwind.config.ts                # Tailwind config (theme colors через CSS vars)
└── components.json                   # shadcn config
```

---

## Ключевые компоненты и инварианты

### `<FighterPhoto>` (`components/fighter-photo.tsx`)
**Используется ВЕЗДЕ** где показывается боец. Никаких прямых `<img>` или `<Avatar><AvatarImage>` для бойцов.
- `next/image` с `fill`, `object-top` (головы не обрезаются)
- Fallback на инициалы при отсутствии URL или ошибке загрузки
- Lazy loading по умолчанию, `priority` для hero-изображений (профиль, детали боя)

### `getFighterImage(name, hint?)` (`lib/fighter-images.ts`)
Резолвит имя бойца в headshot URL. **Strict matching:**
1. Точное совпадение
2. Case-insensitive
3. (опц.) фильтр по `weightClass`
4. First+last name match
5. **Уникальный** surname match — если в базе 2+ бойцов с этой фамилией, возвращает `undefined` (избегаем wrong-photo bug)

### `parseMainEvent(name)` (`lib/events.ts`)
Извлекает имена бойцов из названия ивента ("UFC FN: Allen vs Costa" → `{ "Allen", "Costa" }`). Если паттерна `X vs Y` нет — возвращает пустые строки → UI показывает "Main event TBA".

### `/api/events` route
**Источник истины для main event:** берёт первый competition из ESPN scoreboard (там полные имена + хедшоты), а парсинг названия — fallback. Этим решается проблема surname collision (Costa, Edwards, Allen и т.д.).

### `<Sidebar>` (sticky)
`sticky top-0 h-screen self-start overflow-y-auto` — не скроллится с контентом.

---

## Роли пользователей

`UserProvider` (`lib/user.tsx`) держит:

| Роль | `hasFullAccess` | `isAdmin` |
|---|---|---|
| Free | false | false |
| Pro / Paid | true | false |
| Admin | true | true |

- **Free** видит paywall на детальных боях, history, insights
- **Pro** разблокирует прогнозы и аналитику
- **Admin** видит секцию Admin в сайдбаре + карточку Refresh DB

Переключение роли — в `lib/user.tsx` (мок, нет реального login).

---

## Интеграции

### ESPN public APIs (без auth)
- **Scoreboard:** `https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard` — список ивентов и боёв
- **Athlete:** `https://site.web.api.espn.com/apis/common/v3/sports/mma/athletes/:id` — статы конкретного бойца
- **Search:** `https://site.web.api.espn.com/apis/common/v3/search?query=...` — поиск бойца по имени
- Все endpoints кешируются Next ISR на 30 минут

### Что НЕ подключено
- ❌ Реальный Python predictor → `/api/upcoming-fights` использует `syntheticPrediction()` (детерминистичный seed-based)
- ❌ ChromaDB / RAG
- ❌ Apify / Octagon API
- ❌ Реальная авторизация (Clerk / NextAuth)
- ❌ База данных (Postgres / MongoDB)

---

## Refresh Fighters Database

**UI:** `/admin` → "Refresh Fighters Database"
**API:** `POST /api/admin/refresh-fighters` (`maxDuration: 300s`)
**Lib:** `lib/admin/refresh-fighters.ts` — 3 фазы:

1. **Roster names** — собирает имена бойцов из ESPN scoreboard за ±6 месяцев
2. **Headshots** — для новых имён ищет фото через ESPN search; ретраит NULL-ы автоматически
3. **Enrichment** — для каждого бойца с фото подтягивает weight/height/age/country/weightClass

Результат пишется в `lib/fighter-images.json` + `lib/fighter-data.json` + `lib/fighter-meta.json`.

**Поведение:**
- Warm cache: 1-2 сек
- 1-2 новых события: 3-10 сек
- Cold cache: ~3 минуты

Идемпотентно — переиспользует существующий кеш.

---

## TypeScript / билд

```bash
cd web
npm run dev          # localhost:3000
npx tsc --noEmit -p . # type check
npm run build         # production build
npm run lint
```

`tsconfig.json` strict + `paths: { "@/*": ["./*"] }`.

---

## Известные технические долги

- `app/fights/[id]/page.tsx` — legacy маршрут, есть дубликат `/events/[id]/[boutId]`. Выяснить какой используется и удалить второй
- `lib/fights.ts` содержит hardcoded sample data — не используется в production, но импортируется компонентами
- Unused exports в `lib/events.ts` (`syntheticPrediction`)
- `notifications-demo-bootstrap.tsx` — демо нотификации, в проде убрать
