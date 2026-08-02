"use client";

import { HardHat, Mail, Phone, Send, Star, UserPlus } from "lucide-react";
import { useMemo, useState } from "react";

import { InviteVendorModal } from "@/components/vendors/invite-vendor-modal";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { FadeIn, StaggerItem, StaggerList } from "@/components/ui/motion-list";
import { PageHeader } from "@/components/ui/page-header";
import { RowsSkeleton } from "@/components/ui/skeleton";
import { listCategories } from "@/lib/api/categories";
import {
  deactivateVendor,
  listVendors,
  resendVendorInvite,
} from "@/lib/api/vendors";
import { errorMessage } from "@/lib/errors";
import { categoryLabel } from "@/lib/status";
import type { Vendor } from "@/lib/types";
import { useAsync } from "@/lib/use-async";
import { toast } from "@/stores/toast-store";

export default function VendorsPage() {
  const vendors = useAsync(() => listVendors(), []);
  // Coverage is measured against the PM's own categories, so a trade they
  // added themselves counts as a gap just like a built-in one.
  const categories = useAsync(() => listCategories(true), []);
  const [inviting, setInviting] = useState(false);
  const [suggested, setSuggested] = useState<string[]>([]);
  const [removing, setRemoving] = useState<Vendor | null>(null);
  const [deactivating, setDeactivating] = useState(false);
  const [resendingId, setResendingId] = useState<string | null>(null);

  const list = useMemo(() => vendors.data ?? [], [vendors.data]);

  const uncovered = useMemo(
    () =>
      (categories.data ?? [])
        .filter(
          (category) =>
            !list.some((vendor) => vendor.categories?.includes(category.name)),
        )
        .map((category) => category.name),
    [categories.data, list],
  );

  const handleResend = async (vendor: Vendor) => {
    setResendingId(vendor.id);
    try {
      await resendVendorInvite(vendor.id);
      toast.success(`New invite sent to ${vendor.email}. Older links no longer work.`);
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setResendingId(null);
    }
  };

  const handleDeactivate = async () => {
    if (!removing) return;
    setDeactivating(true);
    try {
      await deactivateVendor(removing.id);
      toast.success(`${removing.name} removed from dispatch.`);
      setRemoving(null);
      await vendors.reload({ silent: true });
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setDeactivating(false);
    }
  };

  const openInvite = (preselect: string[] = []) => {
    setSuggested(preselect);
    setInviting(true);
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Vendors"
        description="The pool the dispatch agent picks from. If it's thin or mis-tagged, tickets escalate instead of dispatching."
        action={
          <Button icon={<UserPlus size={16} />} onClick={() => openInvite()}>
            Invite vendor
          </Button>
        }
      />

      {vendors.error ? <Alert tone="danger">{vendors.error}</Alert> : null}

      {!vendors.loading && uncovered.length > 0 && list.length > 0 ? (
        <Alert tone="warn" title="Categories with no vendor">
          <p className="text-xs">
            Nobody covers{" "}
            <span className="font-semibold text-ink-strong">
              {uncovered.map((category) => categoryLabel(category)).join(", ")}
            </span>
            . Any ticket the AI classifies into one of these will fail to dispatch and
            land on your dashboard as needing attention.
          </p>
          <button
            type="button"
            onClick={() => openInvite(uncovered)}
            className="mt-2 text-xs font-semibold text-brand underline cursor-pointer"
          >
            Invite a vendor for these categories
          </button>
        </Alert>
      ) : null}

      {vendors.loading && list.length === 0 ? <RowsSkeleton rows={3} /> : null}

      {!vendors.loading && list.length === 0 ? (
        <FadeIn>
          <EmptyState
            icon={<HardHat size={22} />}
            title="No vendors yet"
            description="With an empty pool every approved ticket escalates back to you instead of reaching a contractor. Add at least one vendor per trade you expect to need."
            action={
              <Button icon={<UserPlus size={16} />} onClick={() => openInvite()}>
                Invite vendor
              </Button>
            }
          />
        </FadeIn>
      ) : null}

      {list.length > 0 ? (
        <StaggerList>
          {list.map((vendor) => {
            const pending = vendor.invite_status === "pending";
            const noCategories = !vendor.categories?.length;

            return (
              <StaggerItem key={vendor.id}>
                <Card className="hover:border-line transition-colors">
                  <CardBody className="flex flex-wrap items-center justify-between gap-4">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-bold text-ink-strong text-base">{vendor.name}</p>
                        <Badge tone={pending ? "warn" : "success"}>
                          {pending ? "Invite pending" : "Active"}
                        </Badge>
                      </div>

                      <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted font-medium">
                        {vendor.email ? (
                          <span className="inline-flex items-center gap-1.5">
                            <Mail size={13} className="text-brand shrink-0" />
                            {vendor.email}
                          </span>
                        ) : null}
                        {vendor.phone ? (
                          <span className="inline-flex items-center gap-1.5">
                            <Phone size={13} className="text-faint shrink-0" />
                            {vendor.phone}
                          </span>
                        ) : null}
                      </div>

                      <div className="mt-2 flex flex-wrap items-center gap-1.5">
                        {noCategories ? (
                          <Badge tone="danger">No categories — never matched</Badge>
                        ) : (
                          vendor.categories?.map((category) => (
                            <Badge key={category} tone="brand">
                              {categoryLabel(category)}
                            </Badge>
                          ))
                        )}
                      </div>

                      <div className="mt-2 flex flex-wrap items-center gap-x-4 text-technical text-faint text-xs">
                        <span className="inline-flex items-center gap-1">
                          <Star size={13} className="text-amber-500 fill-amber-500/20" />
                          {vendor.rating.toFixed(1)} rating
                        </span>
                        <span>{vendor.max_concurrent_jobs} concurrent jobs max</span>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                      {pending ? (
                        <Button
                          size="sm"
                          variant="secondary"
                          icon={<Send size={14} />}
                          loading={resendingId === vendor.id}
                          onClick={() => void handleResend(vendor)}
                        >
                          Resend invite
                        </Button>
                      ) : null}
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setRemoving(vendor)}
                      >
                        Deactivate
                      </Button>
                    </div>
                  </CardBody>
                </Card>
              </StaggerItem>
            );
          })}
        </StaggerList>
      ) : null}

      <InviteVendorModal
        key={suggested.join(",")}
        open={inviting}
        suggestedCategories={suggested}
        onClose={() => setInviting(false)}
        onInvited={() => void vendors.reload({ silent: true })}
      />

      <ConfirmDialog
        open={Boolean(removing)}
        title="Deactivate this vendor?"
        destructive
        confirmLabel="Deactivate"
        loading={deactivating}
        onCancel={() => setRemoving(null)}
        onConfirm={() => void handleDeactivate()}
        body={
          <>
            <p className="text-xs text-muted">
              <span className="font-semibold text-ink-strong">{removing?.name}</span> stops being
              offered new jobs and their login is switched off.
            </p>
            {removing?.categories?.length ? (
              <p className="mt-3 text-xs text-muted">
                They currently cover{" "}
                {removing.categories.map((c) => categoryLabel(c)).join(", ")} — check
                someone else does too, or those tickets will start escalating.
              </p>
            ) : null}
          </>
        }
      />
    </div>
  );
}
