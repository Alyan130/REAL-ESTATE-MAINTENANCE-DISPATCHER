"use client";

import { motion } from "motion/react";
import type { ComponentPropsWithoutRef, ReactNode } from "react";

import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md";

const VARIANT_CLASSES: Record<Variant, string> = {
  primary:
    "bg-brand text-white hover:bg-brand-hover shadow-[0_2px_8px_rgba(0,117,222,0.25)]",
  secondary:
    "border border-line-soft bg-surface text-ink hover:bg-sunken hover:border-line",
  ghost: "text-muted hover:bg-sunken hover:text-ink-strong",
  danger:
    "border border-danger/30 bg-danger-soft text-danger hover:bg-danger/10",
};

const SIZE_CLASSES: Record<Size, string> = {
  sm: "h-9 gap-1.5 px-4 text-xs font-semibold",
  md: "h-10 gap-2 px-5 text-sm font-semibold",
};

interface ButtonProps
  extends Omit<
    ComponentPropsWithoutRef<"button">,
    "onAnimationStart" | "onDragStart" | "onDragEnd" | "onDrag"
  > {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: ReactNode;
  fullWidth?: boolean;
}

/**
 * Motion handles the tactile part of the press (lift on hover, -1px on active)
 * so no CSS transition is declared on an interactive element.
 * Shape: Pill-shaped (rounded-full 9999px) per Notion Warm Workspace specs.
 */
export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  icon,
  fullWidth = false,
  className,
  children,
  disabled,
  type = "button",
  ...props
}: ButtonProps) {
  const isDisabled = disabled || loading;

  return (
    <motion.button
      type={type}
      disabled={isDisabled}
      whileHover={
        isDisabled
          ? undefined
          : { y: -1, boxShadow: "0 4px 14px rgba(0,0,0,0.08)" }
      }
      whileTap={
        isDisabled ? undefined : { y: 1, boxShadow: "0 0px 0px rgba(0,0,0,0)" }
      }
      transition={{ duration: 0.2, ease: "easeOut" }}
      className={cn(
        "inline-flex items-center justify-center rounded-full font-semibold transition-colors",
        "disabled:cursor-not-allowed disabled:opacity-50",
        VARIANT_CLASSES[variant],
        SIZE_CLASSES[size],
        fullWidth && "w-full",
        className,
      )}
      {...props}
    >
      {loading ? (
        <LoadingDots />
      ) : (
        <>
          {icon ? <span className="shrink-0">{icon}</span> : null}
          {children}
        </>
      )}
    </motion.button>
  );
}

/** Three pulsing dots — the design system rules out circular spinners. */
function LoadingDots() {
  return (
    <span className="inline-flex items-center gap-1" aria-label="Working">
      {[0, 1, 2].map((index) => (
        <motion.span
          key={index}
          className="h-1.5 w-1.5 rounded-full bg-current"
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{
            duration: 1,
            repeat: Infinity,
            ease: "easeInOut",
            delay: index * 0.15,
          }}
        />
      ))}
    </span>
  );
}
