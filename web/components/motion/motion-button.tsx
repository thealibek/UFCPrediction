"use client";

import * as React from "react";
import { motion } from "motion/react";
import { Button, type ButtonProps } from "@/components/ui/button";
import { ANIMATIONS_ENABLED } from "@/lib/animations";

export const MotionButton = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ children, className, ...props }, ref) => {
    if (!ANIMATIONS_ENABLED) {
      return (
        <Button ref={ref} className={className} {...props}>
          {children}
        </Button>
      );
    }

    return (
      <motion.span
        className="inline-block"
        whileHover={{
          scale: 1.03,
          transition: { duration: 0.18, ease: [0.22, 1, 0.36, 1] },
        }}
        whileTap={{ scale: 0.97, transition: { duration: 0.05 } }}
      >
        <Button ref={ref} className={className} {...props}>
          {children}
        </Button>
      </motion.span>
    );
  }
);
MotionButton.displayName = "MotionButton";
