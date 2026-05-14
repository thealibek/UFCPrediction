"use client";

import { useState } from "react";
import { BellOff, CheckCheck, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { useNotifications } from "@/lib/notifications";
import { NotificationItem } from "./notification-item";

interface Props {
  onClose: () => void;
}

export function NotificationDropdown({ onClose }: Props) {
  const { notifications, unreadCount, markAllAsRead, clearAll } = useNotifications();
  const [tab, setTab] = useState<"all" | "unread">("all");

  const list = tab === "all" ? notifications : notifications.filter((n) => !n.read);

  return (
    <div className="w-[380px] max-w-[calc(100vw-2rem)] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3">
        <div>
          <div className="text-sm font-semibold">Уведомления</div>
          <div className="text-xs text-muted-foreground">
            {unreadCount > 0 ? `${unreadCount} непрочитанн${unreadCount === 1 ? "ое" : "ых"}` : "Всё прочитано"}
          </div>
        </div>
        <Tabs value={tab} onValueChange={(v: string) => setTab(v as "all" | "unread")}>
          <TabsList className="h-7">
            <TabsTrigger value="all" className="text-[11px] px-2.5">
              Все
            </TabsTrigger>
            <TabsTrigger value="unread" className="text-[11px] px-2.5">
              Непрочитанные
              {unreadCount > 0 && (
                <span className="ml-1 inline-flex items-center justify-center min-w-[1rem] h-4 px-1 rounded-full bg-primary text-primary-foreground text-[9px] font-semibold">
                  {unreadCount}
                </span>
              )}
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      <Separator />

      {/* List */}
      <div className="max-h-[420px] overflow-y-auto p-1.5">
        {list.length === 0 ? (
          <EmptyState filter={tab} />
        ) : (
          <div className="space-y-0.5">
            {list.map((n) => (
              <NotificationItem key={n.id} notification={n} onClose={onClose} />
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      {notifications.length > 0 && (
        <>
          <Separator />
          <div className="flex items-center justify-between px-3 py-2 bg-muted/30">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs gap-1.5"
              onClick={markAllAsRead}
              disabled={unreadCount === 0}
            >
              <CheckCheck className="h-3.5 w-3.5" />
              Прочитать все
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs gap-1.5 text-muted-foreground hover:text-destructive"
              onClick={clearAll}
            >
              <Trash2 className="h-3.5 w-3.5" />
              Очистить
            </Button>
          </div>
        </>
      )}
    </div>
  );
}

function EmptyState({ filter }: { filter: "all" | "unread" }) {
  return (
    <div className="flex flex-col items-center justify-center text-center px-6 py-12">
      <div className="grid place-items-center h-12 w-12 rounded-full bg-secondary mb-3">
        <BellOff className="h-5 w-5 text-muted-foreground" />
      </div>
      <div className="text-sm font-medium">
        {filter === "unread" ? "Все уведомления прочитаны" : "Пусто"}
      </div>
      <p className="text-xs text-muted-foreground mt-1 max-w-[240px]">
        {filter === "unread"
          ? "Отличная работа! Новые уведомления появятся здесь."
          : "Уведомления о боях, обновлениях модели и подписке будут появляться тут."}
      </p>
    </div>
  );
}
