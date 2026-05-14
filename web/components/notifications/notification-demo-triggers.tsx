"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useNotifications, type NotificationType } from "@/lib/notifications";
import { useUser } from "@/lib/user";

const demos: Array<{ type: NotificationType; title: string; message: string; href?: string }> = [
  {
    type: "fight",
    title: "Новый бой добавлен",
    message: "Khabib Nurmagomedov vs Tony Ferguson — UFC 350, 12 сентября",
    href: "/",
  },
  {
    type: "model",
    title: "Модель обновлена",
    message: "V7 deploy. Точность выросла до 69.1% на тестовом наборе.",
    href: "/admin/model",
  },
  {
    type: "reminder",
    title: "Бой уже завтра",
    message: "Topuria vs Oliveira — не пропусти.",
  },
  {
    type: "subscription",
    title: "Спасибо за продление!",
    message: "Octagon Pro продлён ещё на месяц.",
    href: "/settings",
  },
  {
    type: "system",
    title: "Обновление приложения",
    message: "Релиз v6.1: добавлена self-consistency для близких боёв.",
  },
  {
    type: "admin",
    title: "Новый пользователь зарегистрировался",
    message: "newuser@example.com создал аккаунт. Total users: 1,248.",
  },
];

export function NotificationDemoTriggers() {
  const { addNotification } = useNotifications();
  const { isAdmin } = useUser();

  return (
    <Card>
      <CardHeader>
        <CardTitle>Demo: trigger notifications</CardTitle>
        <CardDescription>
          Кнопки добавляют уведомление в bell + показывают toast. В проде вызывается из бэкенда / webhook&apos;ов.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-wrap gap-2">
        {demos
          .filter((d) => d.type !== "admin" || isAdmin)
          .map((d) => (
            <Button
              key={d.type}
              size="sm"
              variant="outline"
              onClick={() => addNotification(d)}
              className="capitalize"
            >
              {d.type}
            </Button>
          ))}
      </CardContent>
    </Card>
  );
}
