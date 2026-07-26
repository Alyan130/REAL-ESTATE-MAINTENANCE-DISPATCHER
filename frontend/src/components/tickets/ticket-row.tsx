"use client";

import { motion } from "motion/react";
import { Building2, Clock } from "lucide-react";
import Link from "next/link";

import {
  CategoryBadge,
  PriorityBadge,
  StatusBadge,
} from "@/components/tickets/status-badge";
import { formatRelative } from "@/lib/format";
import type { Ticket } from "@/lib/types";

interface TicketRowProps {
  ticket: Ticket;
  propertyName?: string;
}

/** One ticket in the PM's list. The whole row is the link target. */
export function TicketRow({ ticket, propertyName }: TicketRowProps) {
  return (
    <motion.div
      whileHover={{ y: -2, boxShadow: "0 6px 20px rgba(0,0,0,0.08)" }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      className="rounded-2xl border border-line-soft bg-surface shadow-card transition-colors hover:border-line"
    >
      <Link
        href={`/tickets/${ticket.id}`}
        className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between"
      >
        <div className="min-w-0 flex-1">
          <p className="font-bold text-ink-strong text-base">{ticket.title}</p>

          {ticket.ai_summary ? (
            <p className="mt-1 line-clamp-2 text-xs font-medium text-muted leading-relaxed">
              {ticket.ai_summary}
            </p>
          ) : (
            <p className="mt-1 text-xs text-faint italic">
              {ticket.status === "PENDING_UPLOAD"
                ? "Classifying — summary appears in a few seconds"
                : "No AI summary yet"}
            </p>
          )}

          <div className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
            <span className="inline-flex items-center gap-1.5 font-medium">
              <Building2 size={13} className="text-brand" />
              {propertyName ?? "Unknown property"}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Clock size={13} className="text-faint" />
              <span className="text-technical">{formatRelative(ticket.created_at)}</span>
            </span>
          </div>
        </div>

        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {ticket.priority ? <PriorityBadge priority={ticket.priority} /> : null}
          {ticket.category ? <CategoryBadge category={ticket.category} /> : null}
          <StatusBadge status={ticket.status} />
        </div>
      </Link>
    </motion.div>
  );
}
