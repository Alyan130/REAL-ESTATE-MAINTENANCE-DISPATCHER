"use client";

import { Bot, User } from "lucide-react";
import { useEffect, useRef } from "react";

import { formatDateTime } from "@/lib/format";
import type { NegotiationMessage } from "@/lib/types";

/**
 * The negotiation transcript.
 *
 * Used unchanged on both sides — the vendor's chat page and the PM's decision
 * card read the same rows, so the two never disagree about what was said. Only
 * the surrounding chrome differs.
 */

function MessageBubble({ message }: { message: NegotiationMessage }) {
  // "ai" is us. From the vendor's seat it is the outbound side; from the PM's
  // seat it is still the platform speaking on their behalf. Same alignment
  // either way, which is why this component needs no viewer prop.
  const isOutbound = message.sender === "ai";
  const isSystem = message.sender === "system";

  if (isSystem) {
    return (
      <div className="flex justify-center py-1">
        <p className="rounded-full bg-surface-muted px-3 py-1 text-[0.6875rem] font-medium text-muted">
          {message.body}
        </p>
      </div>
    );
  }

  return (
    <div className={`flex gap-2.5 ${isOutbound ? "justify-end" : "justify-start"}`}>
      {!isOutbound ? (
        <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-surface-muted text-muted">
          <User size={14} />
        </div>
      ) : null}

      <div className={`flex max-w-[80%] flex-col gap-1 ${isOutbound ? "items-end" : "items-start"}`}>
        <div
          className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap ${
            isOutbound
              ? "bg-brand text-white rounded-br-md"
              : "bg-surface-muted text-ink rounded-bl-md"
          }`}
        >
          {message.body}
        </div>
        <time className="px-1 text-[0.6875rem] text-faint">
          {formatDateTime(message.created_at)}
        </time>
      </div>

      {isOutbound ? (
        <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-soft text-brand">
          <Bot size={14} />
        </div>
      ) : null}
    </div>
  );
}

export function MessageThread({
  messages,
  emptyHint = "No messages yet.",
}: {
  messages: NegotiationMessage[];
  emptyHint?: string;
}) {
  const endRef = useRef<HTMLDivElement>(null);

  // Scroll on message count rather than on the array identity: polling replaces
  // the array every few seconds, and scrolling on every poll would fight a user
  // who has scrolled up to re-read something.
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length]);

  if (!messages.length) {
    return <p className="py-8 text-center text-xs text-muted">{emptyHint}</p>;
  }

  return (
    <div className="flex max-h-[26rem] flex-col gap-3 overflow-y-auto px-1 py-2">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
      <div ref={endRef} />
    </div>
  );
}
