"use client";

import * as React from "react";
import Image from "next/image";
import { motion } from "motion/react";
import { ANIMATIONS_ENABLED } from "@/lib/animations";
import { cn } from "@/lib/utils";

interface FighterPhotoProps {
  src: string | null | undefined;
  alt: string;
  /** Pixel size for both width and height. Default 64. */
  size?: number;
  /** Tailwind classes appended to the outer div (e.g. border colour). */
  className?: string;
  /** Override sizes attr (default `${size}px`). */
  sizes?: string;
  /** Prefer high-fetch priority (above-the-fold hero shots). */
  priority?: boolean;
}

/**
 * Optimised, lazy-loaded fighter avatar built on next/image.
 *  - Circular crop, head-aligned (`object-top`).
 *  - Falls back to initials chip if no src or load error.
 *  - Sizes default to the rendered pixel size so Next emits a tight srcset.
 */
export function FighterPhoto({
  src,
  alt,
  size = 64,
  className,
  sizes,
  priority = false,
}: FighterPhotoProps) {
  const [errored, setErrored] = React.useState(false);
  const [loaded, setLoaded] = React.useState(false);
  const showImage = !!src && !errored;

  return (
    <motion.div
      className={cn(
        "relative overflow-hidden rounded-full bg-secondary shrink-0",
        className
      )}
      style={{ width: size, height: size }}
      whileHover={ANIMATIONS_ENABLED ? { scale: 1.06 } : undefined}
      transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
    >
      {showImage ? (
        <motion.div
          className="absolute inset-0"
          initial={ANIMATIONS_ENABLED ? { opacity: 0, scale: 1.08 } : false}
          animate={loaded || !ANIMATIONS_ENABLED ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 1.08 }}
          transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
        >
          <Image
            src={src}
            alt={alt}
            fill
            sizes={sizes ?? `${size}px`}
            priority={priority}
            className="object-cover object-top"
            onLoad={() => setLoaded(true)}
            onError={() => setErrored(true)}
          />
        </motion.div>
      ) : (
        <div className="absolute inset-0 grid place-items-center text-muted-foreground font-semibold">
          <span style={{ fontSize: Math.max(10, Math.round(size * 0.32)) }}>{initials(alt)}</span>
        </div>
      )}
    </motion.div>
  );
}

function initials(n: string): string {
  return n
    .split(/\s+/)
    .map((w) => w[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();
}
