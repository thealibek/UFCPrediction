"use client";

import * as React from "react";
import { motion, type HTMLMotionProps } from "motion/react";
import { ANIMATIONS_ENABLED, fadeUp, stagger } from "@/lib/animations";

interface StaggerContainerProps extends HTMLMotionProps<"div"> {
  gap?: number;
  as?: "div";
}

export const StaggerContainer = React.forwardRef<HTMLDivElement, StaggerContainerProps>(
  ({ gap = 0.06, children, ...rest }, ref) => {
    if (!ANIMATIONS_ENABLED) {
      const { className, style } = rest as React.HTMLAttributes<HTMLDivElement>;
      return (
        <div ref={ref} className={className} style={style}>
          {children as React.ReactNode}
        </div>
      );
    }

    return (
      <motion.div
        ref={ref}
        initial="hidden"
        animate="show"
        variants={stagger(gap)}
        {...rest}
      >
        {children}
      </motion.div>
    );
  }
);
StaggerContainer.displayName = "StaggerContainer";

interface StaggerItemProps extends HTMLMotionProps<"div"> {
  as?: "div";
}

export const StaggerItem = React.forwardRef<HTMLDivElement, StaggerItemProps>(
  ({ children, ...rest }, ref) => {
    if (!ANIMATIONS_ENABLED) {
      const { className, style } = rest as React.HTMLAttributes<HTMLDivElement>;
      return (
        <div ref={ref} className={className} style={style}>
          {children as React.ReactNode}
        </div>
      );
    }

    return (
      <motion.div ref={ref} variants={fadeUp} {...rest}>
        {children}
      </motion.div>
    );
  }
);
StaggerItem.displayName = "StaggerItem";
