import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

interface CardProps {
  children: ReactNode;
  className?: string;
}

export function Card({ children, className }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-line-soft bg-surface shadow-card transition-shadow",
        className,
      )}
    >
      {children}
    </div>
  );
}

interface CardHeaderProps {
  title: string;
  description?: string;
  action?: ReactNode;
  icon?: ReactNode;
}

export function CardHeader({
  title,
  description,
  action,
  icon,
}: CardHeaderProps) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line-soft/80 px-6 py-4">
      <div className="flex items-start gap-3">
        {icon ? (
          <span className="mt-0.5 flex h-8 w-8 items-center justify-center rounded-full bg-brand-soft text-brand">
            {icon}
          </span>
        ) : null}
        <div>
          <h2 className="text-base font-bold text-ink-strong">{title}</h2>
          {description ? (
            <p className="mt-0.5 text-xs text-muted">{description}</p>
          ) : null}
        </div>
      </div>
      {action}
    </div>
  );
}

export function CardBody({ children, className }: CardProps) {
  return <div className={cn("px-6 py-5", className)}>{children}</div>;
}
