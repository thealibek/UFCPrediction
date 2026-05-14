"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { toast } from "sonner";

export type NotificationType =
  | "fight"
  | "model"
  | "reminder"
  | "subscription"
  | "system"
  | "admin";

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  createdAt: number; // epoch ms
  read: boolean;
  href?: string;
}

export interface NotificationPrefs {
  inApp: Record<NotificationType, boolean>;
  email: Record<NotificationType, boolean>;
}

const DEFAULT_PREFS: NotificationPrefs = {
  inApp: { fight: true, model: true, reminder: true, subscription: true, system: true, admin: true },
  email: { fight: false, model: false, reminder: true, subscription: true, system: false, admin: false },
};

interface NotificationsState {
  notifications: Notification[];
  unreadCount: number;
  prefs: NotificationPrefs;
  addNotification: (n: Omit<Notification, "id" | "createdAt" | "read">, opts?: { silent?: boolean }) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  removeNotification: (id: string) => void;
  clearAll: () => void;
  togglePref: (channel: "inApp" | "email", type: NotificationType) => void;
}

const NotificationsCtx = createContext<NotificationsState | null>(null);

const STORAGE_KEY = "octagon.notifications.v1";
const PREFS_KEY = "octagon.notifications.prefs.v1";

const seed = (now: number): Notification[] => [
  {
    id: "n1",
    type: "fight",
    title: "Новый бой добавлен",
    message: "Ilia Topuria vs Charles Oliveira — UFC 330, 14 июня",
    createdAt: now - 1000 * 60 * 5,
    read: false,
    href: "/",
  },
  {
    id: "n2",
    type: "model",
    title: "Модель обновлена",
    message: "V6-calibrated развёрнут. Точность выросла до 68.2% на тестовом наборе.",
    createdAt: now - 1000 * 60 * 60 * 2,
    read: false,
    href: "/admin/model",
  },
  {
    id: "n3",
    type: "reminder",
    title: "Бой уже завтра",
    message: "Pereira vs Ankalaev 2 — не пропусти прогноз AI.",
    createdAt: now - 1000 * 60 * 60 * 18,
    read: false,
  },
  {
    id: "n4",
    type: "subscription",
    title: "Подписка истекает через 3 дня",
    message: "Чтобы сохранить полный доступ, продли Octagon Pro.",
    createdAt: now - 1000 * 60 * 60 * 26,
    read: true,
    href: "/settings",
  },
  {
    id: "n5",
    type: "system",
    title: "Обновление приложения",
    message: "Добавлена страница Reliability Bins и калибровка confidence.",
    createdAt: now - 1000 * 60 * 60 * 48,
    read: true,
  },
];

export function NotificationsProvider({ children }: { children: ReactNode }) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [prefs, setPrefs] = useState<NotificationPrefs>(DEFAULT_PREFS);
  const [hydrated, setHydrated] = useState(false);

  // Hydrate from localStorage
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      const rawPrefs = localStorage.getItem(PREFS_KEY);
      if (raw) {
        setNotifications(JSON.parse(raw));
      } else {
        setNotifications(seed(Date.now()));
      }
      if (rawPrefs) setPrefs(JSON.parse(rawPrefs));
    } catch {
      setNotifications(seed(Date.now()));
    } finally {
      setHydrated(true);
    }
  }, []);

  // Persist
  useEffect(() => {
    if (!hydrated) return;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(notifications));
  }, [notifications, hydrated]);

  useEffect(() => {
    if (!hydrated) return;
    localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
  }, [prefs, hydrated]);

  const addNotification = useCallback<NotificationsState["addNotification"]>(
    (n, opts) => {
      const id = `n_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
      const full: Notification = { id, createdAt: Date.now(), read: false, ...n };
      setPrefs((currentPrefs) => {
        if (!currentPrefs.inApp[n.type]) return currentPrefs; // pref disabled → skip
        setNotifications((prev) => [full, ...prev]);
        if (!opts?.silent) {
          toast(n.title, { description: n.message });
        }
        return currentPrefs;
      });
    },
    []
  );

  const markAsRead = useCallback((id: string) => {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
  }, []);

  const markAllAsRead = useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  }, []);

  const removeNotification = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const clearAll = useCallback(() => setNotifications([]), []);

  const togglePref = useCallback((channel: "inApp" | "email", type: NotificationType) => {
    setPrefs((p) => ({ ...p, [channel]: { ...p[channel], [type]: !p[channel][type] } }));
  }, []);

  const value = useMemo<NotificationsState>(
    () => ({
      notifications,
      unreadCount: notifications.filter((n) => !n.read).length,
      prefs,
      addNotification,
      markAsRead,
      markAllAsRead,
      removeNotification,
      clearAll,
      togglePref,
    }),
    [notifications, prefs, addNotification, markAsRead, markAllAsRead, removeNotification, clearAll, togglePref]
  );

  return <NotificationsCtx.Provider value={value}>{children}</NotificationsCtx.Provider>;
}

export function useNotifications() {
  const ctx = useContext(NotificationsCtx);
  if (!ctx) throw new Error("useNotifications must be used within NotificationsProvider");
  return ctx;
}

export const NOTIFICATION_TYPE_LABELS: Record<NotificationType, string> = {
  fight: "Новые бои",
  model: "Обновления модели",
  reminder: "Напоминания о боях",
  subscription: "Подписка",
  system: "Системные",
  admin: "Админские (только для admin)",
};

export function timeAgo(ts: number): string {
  const diff = Date.now() - ts;
  const m = Math.floor(diff / 60000);
  if (m < 1) return "только что";
  if (m < 60) return `${m} мин назад`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} ч назад`;
  const d = Math.floor(h / 24);
  if (d < 7) return `${d} дн назад`;
  return new Date(ts).toLocaleDateString("ru-RU", { day: "numeric", month: "short" });
}
