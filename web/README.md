# Octagon AI — Web (Next.js 15 + shadcn/ui)

Современный SaaS-интерфейс для UFC AI Predictor.

## Стек
- **Next.js 15** (App Router) + **React 19** + **TypeScript**
- **Tailwind CSS** + **shadcn/ui** (Radix primitives)
- **lucide-react** (иконки)

## Запуск
```bash
cd web
npm install
npm run dev
# http://localhost:3000
```

## Demo: переключение ролей
В шапке справа (аватар → меню) можно переключиться между **Free / Paid / Admin** для проверки UI без бэкенда.

При роли **Admin** появляется toggle `User ⇄ Admin` mode в шапке.

## Структура

```
app/
  layout.tsx           — Root layout + UserProvider
  page.tsx             — Dashboard (user или admin overview)
  settings/page.tsx    — Subscription + account
  admin/
    lessons/           — Управление prompt-уроками
    model/             — Версии модели + rollback
    training/          — Mass blind-test progress
    analytics/         — Reliability bins + ROC

components/
  ui/                  — shadcn primitives
  layout/              — sidebar, header
  dashboard/           — welcome, prediction-card, upcoming-fights
  admin/               — admin-overview, page-shell
  upgrade-modal.tsx    — Stripe stub

lib/
  user.tsx             — UserProvider (role/subscription context)
  fights.ts            — Mock data
  utils.ts             — cn()
```

## Роли и доступ

| Роль | Видит предсказания | Sidebar | Admin Mode |
|---|---|---|---|
| `guest` | Размытые + CTA "Upgrade" | User nav | — |
| `free` | Размытые + CTA "Upgrade" | User nav | — |
| `paid` | Полные | User nav | — |
| `admin` | Полные | User nav (default) или Admin nav | ✅ Toggle |

## Что нужно подключить в продакшене

- **Auth**: NextAuth / Clerk → заменить `UserProvider` на реальный
- **Stripe**: `/api/checkout` → handler в `upgrade-modal.tsx`
- **Backend**: REST/GraphQL endpoint для `lib/fights.ts` (сейчас мок-данные)
- **Stripe webhook** → обновляет `role: 'paid'` в БД
- **Middleware** для защиты `/admin/*` маршрутов
