"use client";

import { useState } from "react";
import { Bell } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useNotifications } from "@/lib/notifications";
import { NotificationDropdown } from "./notification-dropdown";

export function NotificationBell() {
  const { unreadCount } = useNotifications();
  const [open, setOpen] = useState(false);

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          aria-label={`Notifications (${unreadCount} unread)`}
          className="relative h-10 w-10 grid place-items-center rounded-md hover:bg-accent transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        >
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1.5 rounded-full bg-red-500 text-white text-[11px] font-semibold ring-2 ring-background tabular-nums">
              {unreadCount > 99 ? "99+" : unreadCount}
            </span>
          )}
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" sideOffset={8} className="p-0">
        <NotificationDropdown onClose={() => setOpen(false)} />
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
