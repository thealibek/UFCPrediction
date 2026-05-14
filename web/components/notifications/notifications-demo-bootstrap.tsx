"use client";

import { useEffect, useRef } from "react";
import { useUser } from "@/lib/user";
import { useNotifications } from "@/lib/notifications";

/**
 * Demo helper: при первом монтировании добавляет одно admin-уведомление,
 * если пользователь admin (и его ещё нет в localStorage).
 */
export function NotificationsDemoBootstrap() {
  const { isAdmin } = useUser();
  const { notifications, addNotification } = useNotifications();
  const fired = useRef(false);

  useEffect(() => {
    if (fired.current) return;
    if (!isAdmin) return;
    const hasAdminSeed = notifications.some((n) => n.type === "admin");
    if (hasAdminSeed) {
      fired.current = true;
      return;
    }
    addNotification(
      {
        type: "admin",
        title: "Модель завершила обучение",
        message: "V6-calibrated готов к деплою. Accuracy 68.2%, Brier 0.198 на тестовом наборе.",
        href: "/admin/training",
      },
      { silent: true }
    );
    fired.current = true;
  }, [isAdmin, notifications, addNotification]);

  return null;
}
