"use client";

import * as React from "react";
import { motion, type HTMLMotionProps } from "motion/react";
import { ANIMATIONS_ENABLED, fadeUp } from "@/lib/animations";

type Preset = "fadeUp" | "fade" | "none";

interface MotionDivProps extends HTMLMotionProps<"div"> {
  preset?: Preset;
  delay?: number;
}

export const MotionDiv = React.forwardRef<HTMLDivElement, MotionDivProps>(
  ({ preset = "fadeUp", delay = 0, children, ...rest }, ref) => {
    if (!ANIMATIONS_ENABLED || preset === "none") {
      const { className, style, id } = rest as React.HTMLAttributes<HTMLDivElement>;
      return (
        <div ref={ref} className={className} style={style} id={id}>
          {children as React.ReactNode}
        </div>
      );
    }

    const variants = preset === "fadeUp" ? fadeUp : undefined;

    return (
      <motion.div
        ref={ref}
        initial="hidden"
        animate="show"
        variants={variants}
        transition={{ delay }}
        {...rest}
      >
        {children}
      </motion.div>
    );
  }
);
MotionDiv.displayName = "MotionDiv";
