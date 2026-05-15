"use client";

import * as React from "react";
import { motion, type HTMLMotionProps } from "motion/react";
import { ANIMATIONS_ENABLED, fadeUp } from "@/lib/animations";
import { cn } from "@/lib/utils";

interface MotionCardProps extends HTMLMotionProps<"div"> {
  hoverLift?: boolean;
  delay?: number;
}

export const MotionCard = React.forwardRef<HTMLDivElement, MotionCardProps>(
  ({ hoverLift = true, delay = 0, className, children, ...rest }, ref) => {
    if (!ANIMATIONS_ENABLED) {
      return (
        <div ref={ref} className={className} {...(rest as React.HTMLAttributes<HTMLDivElement>)}>
          {children as React.ReactNode}
        </div>
      );
    }

    return (
      <motion.div
        ref={ref}
        className={cn("will-change-transform", className)}
        initial="hidden"
        animate="show"
        variants={fadeUp}
        transition={{ delay }}
        whileHover={
          hoverLift
            ? {
                y: -3,
                boxShadow: "0 12px 28px rgba(0,0,0,0.08), 0 0 0 1px rgb(212 175 55 / 0.55)",
                transition: { duration: 0.18, ease: [0.22, 1, 0.36, 1] },
              }
            : undefined
        }
        {...rest}
      >
        {children}
      </motion.div>
    );
  }
);
MotionCard.displayName = "MotionCard";
