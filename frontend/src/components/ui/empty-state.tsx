import type { ReactNode } from "react";

interface EmptyStateProps {
  icon: ReactNode;
  title: string;
  description: string;
  action?: ReactNode;
}

/** Icon-led composition with descriptive text and, where there is one, the next action. */
export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-card border border-dashed border-line bg-surface px-6 py-14 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-card bg-brand-soft text-brand">
        {icon}
      </span>
      <h3 className="text-lg font-bold text-ink-strong">{title}</h3>
      <p className="max-w-md text-sm text-muted">{description}</p>
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
