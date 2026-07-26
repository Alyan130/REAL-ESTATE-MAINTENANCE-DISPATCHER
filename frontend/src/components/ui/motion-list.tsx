"use client";

import { motion } from "motion/react";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

/**
 * Entry motion from the design system: fade + 16px translate-Y over 420ms
 * ease-out, cascading 80ms between items.
 */
const CONTAINER = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.08 } },
};

const ITEM = {
  hidden: { opacity: 0, y: 16 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.42, ease: [0, 0, 0.2, 1] as const },
  },
};

interface StaggerProps {
  children: ReactNode;
  className?: string;
}

export function StaggerList({ children, className }: StaggerProps) {
  return (
    <motion.div
      variants={CONTAINER}
      initial="hidden"
      animate="visible"
      className={cn("flex flex-col gap-3", className)}
    >
      {children}
    </motion.div>
  );
}

export function StaggerItem({ children, className }: StaggerProps) {
  return (
    <motion.div variants={ITEM} className={className}>
      {children}
    </motion.div>
  );
}

/** One-off entry for a page section. */
export function FadeIn({
  children,
  className,
  delay = 0,
}: StaggerProps & { delay?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.42, ease: [0, 0, 0.2, 1], delay }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
