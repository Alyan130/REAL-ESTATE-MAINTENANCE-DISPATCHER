"use client";

import { Check, MessageSquare, SkipForward, Star } from "lucide-react";
import { useState } from "react";

import { MessageThread } from "@/components/chat/message-thread";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/field";
import { Modal } from "@/components/ui/modal";
import { decideNegotiation } from "@/lib/api/negotiation";
import { errorMessage, toApiError } from "@/lib/errors";
import type { Negotiation } from "@/lib/types";
import { toast } from "@/stores/toast-store";

/**
 * The PM's view of a live negotiation, and the three decisions they can make.
 *
 * Lives in the ticket detail's **main** column: a transcript needs the wider
 * measure, and the side column is for glanceable facts.
 */

function money(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `$${value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function NegotiationCard({
  ticketId,
  negotiation,
  onChanged,
}: {
  ticketId: string;
  negotiation: Negotiation;
  onChanged: () => void;
}) {
  const [counterOpen, setCounterOpen] = useState(false);
  const [counterPrice, setCounterPrice] = useState(
    negotiation.suggested_counter?.toString() ?? "",
  );
  const [busy, setBusy] = useState<string | null>(null);

  const decide = async (action: "accept" | "counter" | "next_vendor", price?: number) => {
    setBusy(action);
    try {
      await decideNegotiation(ticketId, action, price ?? null);
      toast.success(
        action === "accept"
          ? "Quote accepted. The vendor has been confirmed."
          : action === "counter"
            ? "Counter sent to the vendor."
            : "Moving on to the next vendor.",
      );
      setCounterOpen(false);
      onChanged();
    } catch (error) {
      const { code } = toApiError(error);
      toast.error(
        code === "COUNTER_LIMIT_REACHED"
          ? "You've already countered this vendor once — that's the limit."
          : errorMessage(error),
      );
    } finally {
      setBusy(null);
    }
  };

  const parsedCounter = Number(counterPrice);
  const counterValid = Number.isFinite(parsedCounter) && parsedCounter > 0;
  const quoted = negotiation.quoted_price;
  const counterAboveQuote =
    counterValid && quoted !== null && parsedCounter >= quoted;

  return (
    <>
      <Card>
        <CardHeader
          title="Vendor negotiation"
          icon={<MessageSquare size={18} />}
          description={negotiation.vendor_name}
        />
        <CardBody className="flex flex-col gap-4">
          {negotiation.vendor_rating !== null ? (
            <p className="flex items-center gap-1 text-xs text-muted">
              <Star size={12} className="text-warn" />
              {negotiation.vendor_rating.toFixed(1)} rating
            </p>
          ) : null}

          {negotiation.awaiting_decision ? (
            <>
              <dl className="grid gap-3 rounded-xl border border-line-soft bg-surface-muted p-4 text-xs sm:grid-cols-3">
                <div>
                  <dt className="text-muted">Quoted</dt>
                  <dd className="mt-0.5 text-base font-bold text-ink-strong">
                    {money(quoted)}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted">Your target</dt>
                  <dd className="mt-0.5 font-semibold text-ink">
                    {money(negotiation.target_price)}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted">Your ceiling</dt>
                  <dd className="mt-0.5 font-semibold text-ink">
                    {money(negotiation.max_price)}
                  </dd>
                </div>
              </dl>

              {negotiation.availability ? (
                <p className="text-xs text-muted">
                  <span className="font-semibold text-ink">Available:</span>{" "}
                  {negotiation.availability}
                </p>
              ) : null}

              {negotiation.decision_reason ? (
                <Alert tone="warn">{negotiation.decision_reason}</Alert>
              ) : null}

              <div className="flex flex-wrap gap-2">
                <Button
                  icon={<Check size={16} />}
                  loading={busy === "accept"}
                  disabled={busy !== null}
                  onClick={() => void decide("accept")}
                >
                  Accept {money(quoted)}
                </Button>
                <Button
                  variant="secondary"
                  disabled={busy !== null || !negotiation.counter_allowed}
                  onClick={() => setCounterOpen(true)}
                >
                  {negotiation.counter_allowed
                    ? "Counter…"
                    : "Counter used"}
                </Button>
                <Button
                  variant="secondary"
                  icon={<SkipForward size={16} />}
                  loading={busy === "next_vendor"}
                  disabled={busy !== null}
                  onClick={() => void decide("next_vendor")}
                >
                  Try another vendor
                </Button>
              </div>
            </>
          ) : (
            <p className="text-xs leading-relaxed text-muted">
              {negotiation.status === "APPROVED"
                ? `Confirmed at ${money(quoted)}. The vendor has the job details.`
                : "The coordinator is talking to the vendor. You'll be asked to decide once there's a price."}
            </p>
          )}

          <div className="border-t border-line-soft/80 pt-2">
            <MessageThread
              messages={negotiation.messages}
              emptyHint="No messages yet."
            />
          </div>
        </CardBody>
      </Card>

      <Modal
        open={counterOpen}
        title="Counter this quote"
        description={`${negotiation.vendor_name} quoted ${money(quoted)}.`}
        onClose={() => setCounterOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setCounterOpen(false)}>
              Cancel
            </Button>
            <Button
              loading={busy === "counter"}
              disabled={!counterValid}
              onClick={() => void decide("counter", parsedCounter)}
            >
              Send counter
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-3">
          {/* The cap is enforced server-side in three places, but a PM who only
              discovers it by hitting a 409 will read it as the product breaking. */}
          <Alert tone="warn">
            You get one counter per vendor. After this, whatever the vendor says
            is their final answer — you can accept it or move to another vendor.
          </Alert>

          <Input
            label="Your counter-offer"
            type="number"
            min={1}
            step="5"
            value={counterPrice}
            onChange={(event) => setCounterPrice(event.target.value)}
            hint={
              negotiation.suggested_counter !== null
                ? `Suggested: ${money(negotiation.suggested_counter)}, based on what similar jobs have settled at.`
                : undefined
            }
            error={
              counterAboveQuote
                ? "That's at or above what they already quoted — there's nothing to gain."
                : null
            }
          />
        </div>
      </Modal>
    </>
  );
}
