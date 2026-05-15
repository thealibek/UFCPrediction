"use client";

import * as React from "react";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion } from "motion/react";
import { ANIMATIONS_ENABLED } from "@/lib/animations";

export function PageTransition({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  if (!ANIMATIONS_ENABLED) return <>{children}</>;

  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={pathname}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -4 }}
        transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
