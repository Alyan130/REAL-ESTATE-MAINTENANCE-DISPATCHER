"use client";

import type { ComponentPropsWithoutRef, ReactNode } from "react";
import { useId } from "react";

import { cn } from "@/lib/cn";

const CONTROL_CLASSES =
  "w-full rounded-xl border border-line-soft bg-surface px-3.5 py-2.5 text-sm text-ink placeholder:text-faint transition-colors focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20 disabled:bg-sunken disabled:text-muted";

const INVALID_CLASSES = "border-danger focus:border-danger focus:ring-danger/20";

interface FieldShellProps {
  id: string;
  label: string;
  hint?: string;
  error?: string | null;
  required?: boolean;
  children: ReactNode;
}

/** Label above the control, error below it — no floating labels. */
function FieldShell({
  id,
  label,
  hint,
  error,
  required,
  children,
}: FieldShellProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="label-ui font-medium text-ink-strong">
        {label}
        {required ? <span className="ml-0.5 text-danger">*</span> : null}
        {!required ? (
          <span className="ml-1.5 text-xs text-faint">Optional</span>
        ) : null}
      </label>
      {children}
      {hint && !error ? <p className="text-xs text-muted">{hint}</p> : null}
      {error ? (
        <p id={`${id}-error`} role="alert" className="text-xs font-medium text-danger">
          {error}
        </p>
      ) : null}
    </div>
  );
}

interface InputProps extends Omit<ComponentPropsWithoutRef<"input">, "id"> {
  label: string;
  hint?: string;
  error?: string | null;
}

export function Input({
  label,
  hint,
  error,
  required,
  className,
  ...props
}: InputProps) {
  const id = useId();

  return (
    <FieldShell id={id} label={label} hint={hint} error={error} required={required}>
      <input
        id={id}
        required={required}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : undefined}
        className={cn(CONTROL_CLASSES, error && INVALID_CLASSES, className)}
        {...props}
      />
    </FieldShell>
  );
}

interface TextareaProps
  extends Omit<ComponentPropsWithoutRef<"textarea">, "id"> {
  label: string;
  hint?: string;
  error?: string | null;
}

export function Textarea({
  label,
  hint,
  error,
  required,
  className,
  rows = 4,
  ...props
}: TextareaProps) {
  const id = useId();

  return (
    <FieldShell id={id} label={label} hint={hint} error={error} required={required}>
      <textarea
        id={id}
        rows={rows}
        required={required}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : undefined}
        className={cn(CONTROL_CLASSES, "resize-y", error && INVALID_CLASSES, className)}
        {...props}
      />
    </FieldShell>
  );
}

interface SelectProps
  extends Omit<ComponentPropsWithoutRef<"select">, "id"> {
  label: string;
  hint?: string;
  error?: string | null;
}

export function Select({
  label,
  hint,
  error,
  required,
  className,
  children,
  ...props
}: SelectProps) {
  const id = useId();

  return (
    <FieldShell id={id} label={label} hint={hint} error={error} required={required}>
      <select
        id={id}
        required={required}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : undefined}
        className={cn(
          CONTROL_CLASSES,
          "appearance-none pr-8 bg-[radial-gradient(ellipse_at_right,_var(--tw-gradient-stops))] cursor-pointer",
          error && INVALID_CLASSES,
          className,
        )}
        {...props}
      >
        {children}
      </select>
    </FieldShell>
  );
}

interface CheckboxProps
  extends Omit<ComponentPropsWithoutRef<"input">, "id" | "type"> {
  label: string;
  description?: string;
}

export function Checkbox({
  label,
  description,
  className,
  ...props
}: CheckboxProps) {
  const id = useId();

  return (
    <div className="flex items-start gap-3 rounded-xl border border-line-soft bg-surface p-3.5 transition-colors hover:border-line">
      <input
        id={id}
        type="checkbox"
        className={cn(
          "mt-0.5 h-4 w-4 shrink-0 rounded border-line-soft text-brand accent-brand focus:ring-brand/20",
          className,
        )}
        {...props}
      />
      <label htmlFor={id} className="cursor-pointer">
        <span className="label-ui block text-sm font-semibold text-ink-strong">{label}</span>
        {description ? (
          <span className="mt-0.5 block text-xs text-muted">{description}</span>
        ) : null}
      </label>
    </div>
  );
}
