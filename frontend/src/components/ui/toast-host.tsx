"use client";

import { AnimatePresence, motion } from "motion/react";
import { CircleCheck, Info, TriangleAlert, X } from "lucide-react";

import { cn } from "@/lib/cn";
import { useToastStore, type ToastTone } from "@/stores/toast-store";

const TONE_CLASSES: Record<ToastTone, string> = {
  success: "border-success/30 bg-surface shadow-lift text-ink",
  error: "border-danger/30 bg-surface shadow-lift text-ink",
  info: "border-brand/30 bg-surface shadow-lift text-ink",
};

const TONE_ICON_CLASSES: Record<ToastTone, string> = {
  success: "text-success",
  error: "text-danger",
  info: "text-brand",
};

function ToneIcon({ tone }: { tone: ToastTone }) {
  if (tone === "success") return <CircleCheck size={18} />;
  if (tone === "error") return <TriangleAlert size={18} />;
  return <Info size={18} />;
}

/** Mounted once in the root layout. z-500 per the design system's z-index contract. */
export function ToastHost() {
  const toasts = useToastStore((state) => state.toasts);
  const dismiss = useToastStore((state) => state.dismiss);

  return (
    <div
      aria-live="polite"
      className="pointer-events-none fixed inset-x-0 bottom-0 z-[500] flex flex-col items-center gap-2.5 p-4 sm:items-end sm:p-6"
    >
      <AnimatePresence initial={false}>
        {toasts.map((toastItem) => (
          <motion.div
            key={toastItem.id}
            layout
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            transition={{ duration: 0.24, ease: "easeOut" }}
            className={cn(
              "pointer-events-auto flex w-full max-w-sm items-center gap-3 rounded-full border px-4 py-3 shadow-lift backdrop-blur-md",
              TONE_CLASSES[toastItem.tone],
            )}
          >
            <span className={cn("shrink-0", TONE_ICON_CLASSES[toastItem.tone])}>
              <ToneIcon tone={toastItem.tone} />
            </span>
            <p className="min-w-0 flex-1 text-xs font-semibold text-ink-strong">{toastItem.message}</p>
            <button
              type="button"
              aria-label="Dismiss"
              onClick={() => dismiss(toastItem.id)}
              className="shrink-0 rounded-full p-1 text-muted hover:bg-sunken hover:text-ink"
            >
              <X size={14} />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
