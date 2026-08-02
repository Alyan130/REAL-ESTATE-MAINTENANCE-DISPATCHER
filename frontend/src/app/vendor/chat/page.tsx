"use client";

import { Building2, Clock, Wrench } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { MessageComposer } from "@/components/chat/message-composer";
import { MessageThread } from "@/components/chat/message-thread";
import { PhotoGrid } from "@/components/tickets/photo-grid";
import { Alert } from "@/components/ui/alert";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { DetailSkeleton } from "@/components/ui/skeleton";
import { getVendorChat, postVendorMessage } from "@/lib/api/negotiation";
import { toApiError } from "@/lib/errors";
import type { VendorChat } from "@/lib/types";
import { useAsync, usePolling } from "@/lib/use-async";
import { toast } from "@/stores/toast-store";

/**
 * The vendor's negotiation thread.
 *
 * Unauthenticated by design — the token in the URL is the credential, exactly
 * like accept-invite. `AuthGuard` is applied inside `app/vendor/page.tsx`
 * itself rather than in a layout, so this sibling route is public by default;
 * that is deliberate, not an oversight.
 *
 * One divergence from accept-invite: this validates on **mount** rather than on
 * submit. A vendor arriving at a dead link should be told immediately, not
 * after typing out a quote.
 */

interface ChatFailure {
  title: string;
  message: string;
  tone: "danger" | "warn";
}

function describeChatFailure(error: unknown): ChatFailure {
  const { status, code, message, isNetworkError } = toApiError(error);

  if (isNetworkError) {
    return { title: "Can't reach the server", message, tone: "danger" };
  }

  switch (code) {
    case "CHAT_LINK_EXPIRED":
      return {
        title: "This link has expired",
        message:
          "Job links stay open for 14 days. Ask the property manager to send a new one if the job is still going.",
        tone: "warn",
      };
    case "CHAT_CLOSED":
      return {
        title: "This job is closed",
        message:
          "It was either given to another contractor or withdrawn. Nothing further is needed from you.",
        tone: "warn",
      };
    case "INVALID_TOKEN":
      return {
        title: "This link isn't valid",
        message:
          "Check you opened the full link from the message — links often get cut short when forwarded.",
        tone: "danger",
      };
    case "NOT_FOUND":
      return {
        title: "We couldn't find this job",
        message: "It may have been removed. Contact the property manager directly.",
        tone: "danger",
      };
  }

  if (status === 410) {
    return {
      title: "This job is no longer open",
      message: "Nothing further is needed from you.",
      tone: "warn",
    };
  }

  return { title: "Something went wrong", message, tone: "danger" };
}

/** Loaded state, or a described failure — never a bare message. */
type ChatResult =
  | { ok: true; chat: VendorChat }
  | { ok: false; failure: ChatFailure };

function VendorChatView() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [lastSentAt, setLastSentAt] = useState(0);

  // The loader resolves with the failure rather than rejecting. `useAsync`
  // flattens a rejection to a message string, which would throw away the `code`
  // that distinguishes "expired" from "closed" from "invalid" — and those three
  // need visibly different copy.
  const chat = useAsync<ChatResult>(async () => {
    try {
      return { ok: true, chat: await getVendorChat(token) };
    } catch (error) {
      return { ok: false, failure: describeChatFailure(error) };
    }
  }, [token]);

  const result = chat.data;
  const data = result?.ok ? result.chat : null;

  // Poll for the AI's reply. `resetKey` restarts the budget on every send, so a
  // long conversation doesn't run out of ticks partway through.
  usePolling(
    Boolean(data?.can_reply),
    () => void chat.reload({ silent: true }),
    { intervalMs: 4000, maxTicks: 45, resetKey: lastSentAt },
  );

  if (!token) {
    return (
      <Alert tone="danger" title="No job token in this link">
        Open the link straight from your email — it carries a token this page
        needs. If you typed the address by hand, that token is missing.
      </Alert>
    );
  }

  if (chat.loading && !result) return <DetailSkeleton />;

  if (result && !result.ok) {
    return (
      <Alert tone={result.failure.tone} title={result.failure.title}>
        {result.failure.message}
      </Alert>
    );
  }

  if (!data) return null;

  const handleSend = async (body: string) => {
    try {
      await postVendorMessage(token, body);
      setLastSentAt(Date.now());
      await chat.reload({ silent: true });
    } catch (error) {
      const { code, message } = toApiError(error);
      toast.error(
        code === "MESSAGE_TOO_FAST"
          ? "Just a moment — that message is still sending."
          : message,
      );
      throw error; // keeps the composer's text so nothing is retyped
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-[1.75rem] font-bold leading-tight text-ink-strong">
          {data.ticket_title}
        </h1>
        <p className="mt-1 text-technical text-muted">
          For {data.vendor_name}
        </p>
      </div>

      <Card>
        <CardHeader title="The job" icon={<Wrench size={18} />} />
        <CardBody className="flex flex-col gap-4">
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink">
            {data.ticket_summary || "No further detail was given."}
          </p>

          <dl className="grid gap-3 border-t border-line-soft/80 pt-3 text-xs sm:grid-cols-3">
            <div>
              <dt className="text-muted">Trade</dt>
              <dd className="mt-0.5 font-semibold text-ink">{data.category_label}</dd>
            </div>
            <div>
              <dt className="flex items-center gap-1 text-muted">
                <Clock size={12} /> Urgency
              </dt>
              <dd className="mt-0.5 font-semibold text-ink">{data.priority_label}</dd>
            </div>
            <div>
              <dt className="flex items-center gap-1 text-muted">
                <Building2 size={12} /> Location
              </dt>
              {/* Property name only. The full address arrives by email once the
                  job is confirmed — this page is reachable by anyone holding a
                  forwarded link. */}
              <dd className="mt-0.5 font-semibold text-ink">{data.property_label}</dd>
            </div>
          </dl>

          <p className="rounded-xl border border-line-soft bg-surface-muted p-3 text-xs text-muted">
            {data.access_note}
          </p>

          {data.media_urls.length ? (
            <PhotoGrid urls={data.media_urls} context={data.ticket_title} />
          ) : null}
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Messages"
          description={
            data.can_reply
              ? "Reply with your total for the job and a day you could attend."
              : undefined
          }
        />
        <CardBody className="flex flex-col gap-2">
          {!data.can_reply ? (
            <Alert tone="success" title="This job is confirmed">
              The property manager has approved your quote and the details have
              been emailed to you. This thread is now read-only.
            </Alert>
          ) : null}

          <MessageThread
            messages={data.messages}
            emptyHint="The property manager's coordinator will be in touch shortly."
          />

          {data.can_reply ? (
            <MessageComposer
              onSend={handleSend}
              placeholder="e.g. I can do it for $180, Tuesday afternoon"
            />
          ) : null}
        </CardBody>
      </Card>
    </div>
  );
}

export default function VendorChatPage() {
  return (
    <main className="mx-auto w-full max-w-3xl px-6 py-10">
      <Suspense fallback={<DetailSkeleton />}>
        <VendorChatView />
      </Suspense>
    </main>
  );
}
