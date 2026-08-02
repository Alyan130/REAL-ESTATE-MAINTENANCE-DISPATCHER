"use client";

import { Send } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";

/**
 * The vendor's reply box.
 *
 * Enter sends, Shift+Enter breaks the line — the convention every messaging app
 * has trained people on. The text is retained when a send fails, per
 * docs/rules/error-handling.md: a contractor who typed a quote on a phone
 * should never have to type it twice.
 */
export function MessageComposer({
  onSend,
  disabled = false,
  placeholder = "Type your reply…",
}: {
  onSend: (body: string) => Promise<void>;
  disabled?: boolean;
  placeholder?: string;
}) {
  const [value, setValue] = useState("");
  const [sending, setSending] = useState(false);

  const submit = async () => {
    const body = value.trim();
    if (!body || sending || disabled) return;

    setSending(true);
    try {
      await onSend(body);
      setValue(""); // cleared only on success
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex items-end gap-2 border-t border-line-soft pt-3">
      <textarea
        aria-label="Your message"
        rows={2}
        value={value}
        disabled={disabled}
        placeholder={placeholder}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            void submit();
          }
        }}
        className="min-h-[3rem] flex-1 resize-none rounded-2xl border border-line-soft bg-surface px-4 py-2.5 text-sm text-ink placeholder:text-faint focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20 disabled:cursor-not-allowed disabled:opacity-60"
      />
      <Button
        icon={<Send size={16} />}
        loading={sending}
        disabled={disabled || !value.trim()}
        onClick={() => void submit()}
      >
        Send
      </Button>
    </div>
  );
}
