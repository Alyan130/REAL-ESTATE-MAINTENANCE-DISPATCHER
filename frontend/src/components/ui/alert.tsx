import { CircleCheck, Info, TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type AlertTone = "info" | "warn" | "danger" | "success";

const TONE_CLASSES: Record<AlertTone, string> = {
  info: "border-info/20 bg-info-soft text-info",
  warn: "border-warn/25 bg-warn-soft text-warn",
  danger: "border-danger/25 bg-danger-soft text-danger",
  success: "border-success/20 bg-success-soft text-success",
};

const TONE_ICONS: Record<AlertTone, ReactNode> = {
  info: <Info size={18} />,
  warn: <TriangleAlert size={18} />,
  danger: <TriangleAlert size={18} />,
  success: <CircleCheck size={18} />,
};

interface AlertProps {
  tone?: AlertTone;
  title?: string;
  children: ReactNode;
  className?: string;
}

export function Alert({
  tone = "info",
  title,
  children,
  className,
}: AlertProps) {
  return (
    <div
      role={tone === "danger" ? "alert" : "status"}
      className={cn(
        "flex items-start gap-3 rounded-xl border px-4 py-3.5 text-sm",
        TONE_CLASSES[tone],
        className,
      )}
    >
      <span className="mt-0.5 shrink-0">{TONE_ICONS[tone]}</span>
      <div className="min-w-0">
        {title ? <p className="font-semibold text-ink-strong">{title}</p> : null}
        <div className={cn(title && "mt-0.5", "text-ink")}>{children}</div>
      </div>
    </div>
  );
}
