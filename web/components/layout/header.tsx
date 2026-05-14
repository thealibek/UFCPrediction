"use client";

import { ChevronDown, LogOut, User as UserIcon, Crown, Search } from "lucide-react";
import { useUser, type UserRole } from "@/lib/user";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { NotificationBell } from "@/components/notifications/notification-bell";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function Header() {
  const { name, email, role, isAdmin, viewMode, setViewMode, setRole, hasFullAccess } = useUser();

  const initials = name
    .split(" ")
    .map((n) => n[0])
    .slice(0, 2)
    .join("");

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-4 border-b bg-background/80 px-6 backdrop-blur">
      <div className="relative flex-1 max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
        <input
          type="search"
          placeholder="Search fighters, events, predictions..."
          className="w-full h-9 pl-9 pr-3 rounded-md border bg-background text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring transition-colors"
        />
      </div>
      <div className="flex-1 hidden md:block" />

      {isAdmin && (
        <div className="flex items-center gap-2 rounded-md border bg-card px-3 py-1.5">
          <span className="text-xs font-medium text-muted-foreground">User</span>
          <Switch
            checked={viewMode === "admin"}
            onCheckedChange={(v: boolean) => setViewMode(v ? "admin" : "user")}
          />
          <span className="text-xs font-medium text-muted-foreground">Admin</span>
        </div>
      )}

      {!hasFullAccess && (
        <Button size="sm" variant="default" className="gap-1.5">
          <Crown className="h-3.5 w-3.5" />
          Upgrade to Pro
        </Button>
      )}

      <NotificationBell />

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button className="flex items-center gap-2 rounded-full p-1 transition-colors hover:bg-accent">
            <Avatar className="h-8 w-8">
              <AvatarFallback>{initials}</AvatarFallback>
            </Avatar>
            <ChevronDown className="h-3 w-3 text-muted-foreground" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-60">
          <DropdownMenuLabel>
            <div className="flex flex-col">
              <span className="font-medium text-sm">{name}</span>
              <span className="text-xs font-normal text-muted-foreground">{email}</span>
              <div className="flex items-center gap-1 mt-2">
                <Badge variant={role === "paid" || role === "admin" ? "success" : "outline"} className="capitalize">
                  {role}
                </Badge>
              </div>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuLabel className="text-xs uppercase tracking-wider text-muted-foreground">
            Demo: switch role
          </DropdownMenuLabel>
          <DropdownMenuRadioGroup value={role} onValueChange={(v: string) => setRole(v as UserRole)}>
            <DropdownMenuRadioItem value="free">Free user</DropdownMenuRadioItem>
            <DropdownMenuRadioItem value="paid">Paid user</DropdownMenuRadioItem>
            <DropdownMenuRadioItem value="admin">Admin</DropdownMenuRadioItem>
          </DropdownMenuRadioGroup>
          <DropdownMenuSeparator />
          <DropdownMenuItem>
            <UserIcon className="mr-2 h-4 w-4" /> Profile
          </DropdownMenuItem>
          <DropdownMenuItem>
            <LogOut className="mr-2 h-4 w-4" /> Sign out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}
