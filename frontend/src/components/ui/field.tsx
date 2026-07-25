"use client";

import type { ComponentPropsWithoutRef, ReactNode } from "react";
import { useId } from "react";

import { cn } from "@/lib/cn";

const CONTROL_CLASSES =
  "w-full rounded-card border border-line bg-surface px-3 py-2.5 text-base text-ink placeholder:text-faint disabled:bg-sunken disabled:text-muted";

const INVALID_CLASSES = "border-danger";

interface FieldShellProps {
  id: string;
  label: string;
  hint?: string;
  error?: string | null;
  required?: boolean;
  children: ReactNode;
}

/** Label above the control, error below it — no floating labels. */
function FieldShell({ id, label, hint, error, required, children }: FieldShellProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="label-ui text-ink">
        {label}
        {required ? <span className="ml-0.5 text-danger">*</span> : null}
        {!required ? <span className="ml-1.5 text-xs text-faint">Optional</span> : null}
      </label>
      {children}
      {hint && !error ? <p className="text-sm text-muted">{hint}</p> : null}
      {error ? (
        <p id={`${id}-error`} role="alert" className="text-sm text-danger">
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

export function Input({ label, hint, error, required, className, ...props }: InputProps) {
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

interface TextareaProps extends Omit<ComponentPropsWithoutRef<"textarea">, "id"> {
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

interface SelectProps extends Omit<ComponentPropsWithoutRef<"select">, "id"> {
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
        className={cn(CONTROL_CLASSES, "appearance-none pr-8", error && INVALID_CLASSES, className)}
        {...props}
      >
        {children}
      </select>
    </FieldShell>
  );
}

interface CheckboxProps extends Omit<ComponentPropsWithoutRef<"input">, "id" | "type"> {
  label: string;
  description?: string;
}

export function Checkbox({ label, description, className, ...props }: CheckboxProps) {
  const id = useId();

  return (
    <div className="flex items-start gap-3 rounded-card border border-line-soft bg-surface p-3">
      <input
        id={id}
        type="checkbox"
        className={cn("mt-1 h-4 w-4 shrink-0 accent-[#005691]", className)}
        {...props}
      />
      <label htmlFor={id} className="cursor-pointer">
        <span className="label-ui block text-ink">{label}</span>
        {description ? (
          <span className="block text-sm text-muted">{description}</span>
        ) : null}
      </label>
    </div>
  );
}
