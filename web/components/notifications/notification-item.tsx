"use client";

import Link from "next/link";
import { Swords, Brain, Bell, CreditCard, Info, Shield, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { timeAgo, useNotifications, type Notification, type NotificationType } from "@/lib/notifications";

const ICONS: Record<NotificationType, typeof Swords> = {
  fight: Swords,
  model: Brain,
  reminder: Bell,
  subscription: CreditCard,
  system: Info,
  admin: Shield,
};

const TONE: Record<NotificationType, string> = {
  fight: "bg-blue-100 text-blue-700",
  model: "bg-purple-100 text-purple-700",
  reminder: "bg-amber-100 text-amber-700",
  subscription: "bg-emerald-100 text-emerald-700",
  system: "bg-slate-100 text-slate-700",
  admin: "bg-rose-100 text-rose-700",
};

export function NotificationItem({
  notification,
  onClose,
}: {
  notification: Notification;
  onClose?: () => void;
}) {
  const { markAsRead, removeNotification } = useNotifications();
  const Icon = ICONS[notification.type];

  const Inner = (
    <div
      className={cn(
        "group relative flex gap-3 px-3 py-3 rounded-md transition-colors hover:bg-accent",
        !notification.read && "bg-accent/40"
      )}
    >
      <div className={cn("grid place-items-center h-8 w-8 rounded-full shrink-0", TONE[notification.type])}>
        <Icon className="h-4 w-4" />
      </div>
      <div className="flex-1 min-w-0 pr-5">
        <div className="flex items-baseline justify-between gap-2">
          <span className={cn("text-sm truncate", !notification.read ? "font-semibold" : "font-medium")}>
            {notification.title}
          </span>
          <span className="text-[10px] text-muted-foreground shrink-0">{timeAgo(notification.createdAt)}</span>
        </div>
        <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{notification.message}</p>
      </div>
      {!notification.read && (
        <span className="absolute top-3.5 right-9 h-1.5 w-1.5 rounded-full bg-primary" aria-hidden />
      )}
      <button
        type="button"
        aria-label="Удалить"
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          removeNotification(notification.id);
        }}
        className="absolute top-2.5 right-2 grid place-items-center h-5 w-5 rounded-md text-muted-foreground opacity-0 group-hover:opacity-100 hover:bg-background hover:text-foreground transition"
      >
        <X className="h-3 w-3" />
      </button>
    </div>
  );

  const handleClick = () => {
    if (!notification.read) markAsRead(notification.id);
    onClose?.();
  };

  if (notification.href) {
    return (
      <Link href={notification.href} onClick={handleClick}>
        {Inner}
      </Link>
    );
  }
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          handleClick();
        }
      }}
      className="block w-full text-left cursor-pointer focus:outline-none focus-visible:ring-1 focus-visible:ring-ring rounded-md"
    >
      {Inner}
    </div>
  );
}
