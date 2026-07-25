"use client";

import { Mail, Send, UserPlus, Users } from "lucide-react";
import { useMemo, useState } from "react";

import { InviteTenantModal } from "@/components/tenants/invite-tenant-modal";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { FadeIn, StaggerItem, StaggerList } from "@/components/ui/motion-list";
import { PageHeader } from "@/components/ui/page-header";
import { RowsSkeleton } from "@/components/ui/skeleton";
import { listProperties } from "@/lib/api/properties";
import {
  deactivateTenant,
  listTenants,
  resendTenantInvite,
} from "@/lib/api/tenants";
import { errorMessage } from "@/lib/errors";
import { formatDate } from "@/lib/format";
import type { Tenant } from "@/lib/types";
import { useAsync } from "@/lib/use-async";
import { toast } from "@/stores/toast-store";

export default function TenantsPage() {
  const [propertyFilter, setPropertyFilter] = useState("");
  const [inviting, setInviting] = useState(false);
  const [removing, setRemoving] = useState<Tenant | null>(null);
  const [deactivating, setDeactivating] = useState(false);
  const [resendingId, setResendingId] = useState<string | null>(null);

  const properties = useAsync(() => listProperties(), []);
  const tenants = useAsync(
    () => listTenants(propertyFilter || undefined),
    [propertyFilter],
  );

  const propertyNames = useMemo(() => {
    const map = new Map<string, string>();
    properties.data?.forEach((property) => map.set(property.id, property.name));
    return map;
  }, [properties.data]);

  const handleResend = async (tenant: Tenant) => {
    setResendingId(tenant.id);
    try {
      await resendTenantInvite(tenant.id);
      toast.success(`New invite sent to ${tenant.email}. Older links no longer work.`);
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
      await deactivateTenant(removing.id);
      toast.success(`${removing.name ?? removing.email} deactivated.`);
      setRemoving(null);
      await tenants.reload({ silent: true });
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setDeactivating(false);
    }
  };

  const list = tenants.data ?? [];
  const pendingCount = list.filter(
    (tenant) => tenant.invite_status === "pending",
  ).length;
  const hasProperties = (properties.data?.length ?? 0) > 0;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Tenants"
        description="Everyone who can file a ticket, and whether their account is live yet."
        action={
          <Button
            icon={<UserPlus size={16} />}
            onClick={() => setInviting(true)}
            disabled={!hasProperties}
          >
            Invite tenant
          </Button>
        }
      />

      {properties.error ? <Alert tone="danger">{properties.error}</Alert> : null}
      {tenants.error ? <Alert tone="danger">{tenants.error}</Alert> : null}

      {pendingCount > 0 ? (
        <Alert tone="warn" title={`${pendingCount} tenant${pendingCount === 1 ? "" : "s"} haven't accepted their invite`}>
          A pending tenant can&apos;t sign in and can&apos;t file a ticket. Resend the
          invite if they never got the first email.
        </Alert>
      ) : null}

      {hasProperties ? (
        <div className="flex flex-wrap items-center gap-2">
          <label htmlFor="tenant-property-filter" className="text-sm text-muted">
            Property
          </label>
          <select
            id="tenant-property-filter"
            className="h-9 rounded-card border border-line bg-surface px-2.5 text-sm text-ink"
            value={propertyFilter}
            onChange={(event) => setPropertyFilter(event.target.value)}
          >
            <option value="">All properties</option>
            {properties.data?.map((property) => (
              <option key={property.id} value={property.id}>
                {property.name}
              </option>
            ))}
          </select>
        </div>
      ) : null}

      {tenants.loading && list.length === 0 ? <RowsSkeleton rows={3} /> : null}

      {!tenants.loading && !properties.loading && list.length === 0 ? (
        <FadeIn>
          <EmptyState
            icon={<Users size={22} />}
            title={hasProperties ? "No tenants yet" : "Add a property first"}
            description={
              hasProperties
                ? "Invite a tenant and they'll get an email to set a password. Until they accept, they can't report anything."
                : "Tenants are invited to a specific property, so you need at least one property before you can add anyone."
            }
            action={
              hasProperties ? (
                <Button icon={<UserPlus size={16} />} onClick={() => setInviting(true)}>
                  Invite tenant
                </Button>
              ) : undefined
            }
          />
        </FadeIn>
      ) : null}

      {list.length > 0 ? (
        <StaggerList>
          {list.map((tenant) => {
            const pending = tenant.invite_status === "pending";
            return (
              <StaggerItem key={tenant.id}>
                <Card>
                  <CardBody className="flex flex-wrap items-start justify-between gap-4">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-semibold text-ink-strong">
                          {tenant.name ?? "Unnamed tenant"}
                        </p>
                        <Badge tone={pending ? "warn" : "success"}>
                          {pending ? "Invite pending" : "Active"}
                        </Badge>
                      </div>

                      <p className="mt-1 inline-flex items-center gap-1.5 text-sm text-muted">
                        <Mail size={14} />
                        {tenant.email}
                      </p>

                      <p className="mt-1 text-sm text-muted">
                        {propertyNames.get(tenant.property_id) ?? "Unknown property"}
                        {tenant.unit_number ? ` · Unit ${tenant.unit_number}` : ""}
                      </p>

                      {tenant.lease_start || tenant.lease_end ? (
                        <p className="mt-1 text-technical text-faint">
                          Lease {formatDate(tenant.lease_start)} –{" "}
                          {formatDate(tenant.lease_end)}
                        </p>
                      ) : null}
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                      {pending ? (
                        <Button
                          size="sm"
                          variant="secondary"
                          icon={<Send size={15} />}
                          loading={resendingId === tenant.id}
                          onClick={() => void handleResend(tenant)}
                        >
                          Resend invite
                        </Button>
                      ) : null}
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setRemoving(tenant)}
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

      <InviteTenantModal
        open={inviting}
        properties={properties.data ?? []}
        onClose={() => setInviting(false)}
        onInvited={() => void tenants.reload({ silent: true })}
      />

      <ConfirmDialog
        open={Boolean(removing)}
        title="Deactivate this tenant?"
        destructive
        confirmLabel="Deactivate"
        loading={deactivating}
        onCancel={() => setRemoving(null)}
        onConfirm={() => void handleDeactivate()}
        body={
          <>
            <p>
              <span className="font-semibold">
                {removing?.name ?? removing?.email}
              </span>{" "}
              loses access immediately — their tenant record and their login are both
              switched off.
            </p>
            <p className="mt-3">
              There is no reactivate action. Getting them back means inviting them
              again with a different email address.
            </p>
          </>
        }
      />
    </div>
  );
}
