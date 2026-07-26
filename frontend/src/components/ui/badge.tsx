import type { ReactNode } from "react";

import { cn } from "@/lib/cn";
import type { Tone } from "@/lib/status";

const TONE_CLASSES: Record<Tone, string> = {
  neutral: "border-line-soft bg-sunken text-muted",
  info: "border-info/20 bg-info-soft text-info",
  brand: "border-brand/20 bg-brand-soft text-brand",
  warn: "border-warn/25 bg-warn-soft text-warn",
  danger: "border-danger/25 bg-danger-soft text-danger",
  success: "border-success/20 bg-success-soft text-success",
};

interface BadgeProps {
  tone?: Tone;
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
}

/** Pill badge (9999px rounded) with soft warm tints per Notion Warm Workspace specs. */
export function Badge({
  tone = "neutral",
  icon,
  children,
  className,
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-0.5",
        "text-xs font-semibold whitespace-nowrap tracking-wide",
        TONE_CLASSES[tone],
        className,
      )}
    >
      {icon ? <span className="shrink-0">{icon}</span> : null}
      {children}
    </span>
  );
}
