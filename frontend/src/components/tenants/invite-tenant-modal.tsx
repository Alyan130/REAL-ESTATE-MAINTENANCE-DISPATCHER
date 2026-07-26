"use client";

import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/field";
import { Modal } from "@/components/ui/modal";
import { inviteTenant } from "@/lib/api/tenants";
import { toApiError } from "@/lib/errors";
import type { Property } from "@/lib/types";
import { toast } from "@/stores/toast-store";

interface InviteTenantModalProps {
  open: boolean;
  properties: Property[];
  /** Pre-selects and locks the property (used from a property's own page). */
  lockedPropertyId?: string;
  onClose: () => void;
  onInvited: () => void;
}

interface FormState {
  name: string;
  email: string;
  propertyId: string;
  unitNumber: string;
  leaseStart: string;
  leaseEnd: string;
}

const EMPTY_FORM: FormState = {
  name: "",
  email: "",
  propertyId: "",
  unitNumber: "",
  leaseStart: "",
  leaseEnd: "",
};

export function InviteTenantModal({
  open,
  properties,
  lockedPropertyId,
  onClose,
  onInvited,
}: InviteTenantModalProps) {
  const [form, setForm] = useState<FormState>({
    ...EMPTY_FORM,
    propertyId: lockedPropertyId ?? "",
  });
  const [error, setError] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const update = (patch: Partial<FormState>) =>
    setForm((previous) => ({ ...previous, ...patch }));

  const handleClose = () => {
    if (saving) return;
    setForm({ ...EMPTY_FORM, propertyId: lockedPropertyId ?? "" });
    setError(null);
    setEmailError(null);
    onClose();
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setEmailError(null);
    setSaving(true);

    try {
      await inviteTenant({
        name: form.name.trim(),
        email: form.email.trim(),
        property_id: form.propertyId,
        unit_number: form.unitNumber.trim() || null,
        lease_start: form.leaseStart || null,
        lease_end: form.leaseEnd || null,
      });

      toast.success(`Invite email sent to ${form.email.trim()}.`);
      setForm({ ...EMPTY_FORM, propertyId: lockedPropertyId ?? "" });
      onInvited();
      onClose();
    } catch (submitError) {
      const { code, message } = toApiError(submitError);
      // One account per email address across all three roles — by far the most
      // common failure here, so it is pinned to the field that caused it.
      if (code === "DUPLICATE_EMAIL") {
        setEmailError(
          "An account already uses this email. Every address can only belong to one person, across tenants, vendors, and managers.",
        );
      } else {
        setError(message);
      }
    } finally {
      setSaving(false);
    }
  };

  const propertyLocked = Boolean(lockedPropertyId);
  const lockedProperty = properties.find(
    (property) => property.id === lockedPropertyId,
  );

  return (
    <Modal
      open={open}
      title="Invite a tenant"
      description="They'll get an email with a link to set a password."
      onClose={handleClose}
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
        {error ? <Alert tone="danger">{error}</Alert> : null}

        <Input
          label="Full name"
          required
          value={form.name}
          onChange={(event) => update({ name: event.target.value })}
        />

        <Input
          label="Email"
          type="email"
          required
          value={form.email}
          onChange={(event) => update({ email: event.target.value })}
          error={emailError}
        />

        {propertyLocked ? (
          <div className="rounded-card border border-line-soft bg-sunken px-3 py-2.5">
            <p className="label-ui text-muted">Property</p>
            <p className="text-ink">{lockedProperty?.name ?? "This property"}</p>
          </div>
        ) : (
          <Select
            label="Property"
            required
            value={form.propertyId}
            onChange={(event) => update({ propertyId: event.target.value })}
          >
            <option value="">Choose a property…</option>
            {properties.map((property) => (
              <option key={property.id} value={property.id}>
                {property.name}
              </option>
            ))}
          </Select>
        )}

        <Input
          label="Unit number"
          value={form.unitNumber}
          onChange={(event) => update({ unitNumber: event.target.value })}
          placeholder="4B"
        />

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Input
            label="Lease start"
            type="date"
            value={form.leaseStart}
            onChange={(event) => update({ leaseStart: event.target.value })}
          />
          <Input
            label="Lease end"
            type="date"
            value={form.leaseEnd}
            onChange={(event) => update({ leaseEnd: event.target.value })}
          />
        </div>

        <div className="mt-2 flex justify-end gap-2">
          <Button variant="secondary" onClick={handleClose} disabled={saving}>
            Cancel
          </Button>
          <Button
            type="submit"
            loading={saving}
            disabled={!form.name.trim() || !form.email.trim() || !form.propertyId}
          >
            Send invite
          </Button>
        </div>
      </form>
    </Modal>
  );
}
