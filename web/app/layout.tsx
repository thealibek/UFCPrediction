import type { Metadata } from "next";
import "./globals.css";
import { UserProvider } from "@/lib/user";
import { NotificationsProvider } from "@/lib/notifications";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { Toaster } from "@/components/ui/sonner";
import { NotificationsDemoBootstrap } from "@/components/notifications/notifications-demo-bootstrap";
import { PageTransition } from "@/components/motion/page-transition";

export const metadata: Metadata = {
  title: "Octagon AI — UFC Prediction Engine",
  description: "AI-powered UFC fight predictions, calibrated on 351+ historical fights.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-background text-foreground antialiased" suppressHydrationWarning>
        <UserProvider>
          <NotificationsProvider>
            <NotificationsDemoBootstrap />
            <div className="flex min-h-screen">
              <Sidebar />
              <div className="flex flex-1 flex-col">
                <Header />
                <main className="flex-1 px-6 py-8 md:px-10 lg:px-12 max-w-7xl w-full mx-auto">
                  <PageTransition>{children}</PageTransition>
                </main>
              </div>
            </div>
            <Toaster />
          </NotificationsProvider>
        </UserProvider>
      </body>
    </html>
  );
}
