"use client";

import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

export type UserRole = "guest" | "free" | "paid" | "admin";
export type ViewMode = "user" | "admin";

export interface UserState {
  name: string;
  email: string;
  role: UserRole;
  isSubscribed: boolean;
  viewMode: ViewMode;
  setRole: (r: UserRole) => void;
  setSubscribed: (v: boolean) => void;
  setViewMode: (m: ViewMode) => void;
  hasFullAccess: boolean;
  isAdmin: boolean;
  showAdminUI: boolean;
}

const UserCtx = createContext<UserState | null>(null);

/**
 * Demo provider — в проде заменить на NextAuth/Clerk + Stripe webhook.
 * Для демо: дефолт = admin, чтобы можно было посмотреть оба режима.
 */
export function UserProvider({ children }: { children: ReactNode }) {
  const [role, setRole] = useState<UserRole>("admin");
  const [isSubscribed, setSubscribed] = useState<boolean>(true);
  const [viewMode, setViewMode] = useState<ViewMode>("user");

  const value = useMemo<UserState>(() => {
    const isAdmin = role === "admin";
    const hasFullAccess = role === "paid" || role === "admin" || isSubscribed;
    return {
      name: role === "admin" ? "Alibek (Admin)" : role === "paid" ? "Sarah Chen" : "Guest User",
      email: role === "admin" ? "admin@octagon.ai" : "user@example.com",
      role,
      isSubscribed,
      viewMode,
      setRole,
      setSubscribed,
      setViewMode,
      hasFullAccess: role === "guest" || role === "free" ? false : hasFullAccess,
      isAdmin,
      showAdminUI: isAdmin && viewMode === "admin",
    };
  }, [role, isSubscribed, viewMode]);

  return <UserCtx.Provider value={value}>{children}</UserCtx.Provider>;
}

export function useUser(): UserState {
  const ctx = useContext(UserCtx);
  if (!ctx) throw new Error("useUser must be used within UserProvider");
  return ctx;
}
