import type { Transition, Variants } from "motion/react";

export const ANIMATIONS_ENABLED =
  process.env.NEXT_PUBLIC_DISABLE_ANIMATIONS !== "1";

export const ease = {
  out: [0.22, 1, 0.36, 1] as const,
  inOut: [0.83, 0, 0.17, 1] as const,
};

export const duration = {
  fast: 0.18,
  base: 0.32,
  slow: 0.6,
} as const;

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { duration: duration.base, ease: ease.out } },
};

export const fade: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: duration.base, ease: ease.out } },
};

export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.96 },
  show: { opacity: 1, scale: 1, transition: { duration: duration.base, ease: ease.out } },
};

export const stagger = (gap = 0.06): Variants => ({
  hidden: {},
  show: { transition: { staggerChildren: gap, delayChildren: 0.05 } },
});

export const cardHover = {
  rest: { y: 0, boxShadow: "0 0 0 0 rgba(0,0,0,0)" },
  hover: {
    y: -3,
    boxShadow: "0 12px 28px rgba(0,0,0,0.08), 0 0 0 1px rgb(212 175 55 / 0.55)",
    transition: { duration: duration.fast, ease: ease.out },
  },
};

export const buttonTap = {
  whileHover: { scale: 1.03, transition: { duration: duration.fast, ease: ease.out } },
  whileTap: { scale: 0.97, transition: { duration: 0.05 } },
};

export const pageTransition: Transition = {
  duration: duration.base,
  ease: ease.out,
};
