"use client";

import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/field";
import { Modal } from "@/components/ui/modal";
import { inviteVendor } from "@/lib/api/vendors";
import { toApiError } from "@/lib/errors";
import { cn } from "@/lib/cn";
import { categoryLabel } from "@/lib/status";
import { VENDOR_CATEGORIES, type VendorCategory } from "@/lib/types";
import { toast } from "@/stores/toast-store";

interface InviteVendorModalProps {
  open: boolean;
  onClose: () => void;
  onInvited: () => void;
  /** Pre-tick categories with no coverage, when invited from a gap warning. */
  suggestedCategories?: VendorCategory[];
}

const DEFAULT_MAX_JOBS = 3;

export function InviteVendorModal({
  open,
  onClose,
  onInvited,
  suggestedCategories = [],
}: InviteVendorModalProps) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [categories, setCategories] = useState<VendorCategory[]>(suggestedCategories);
  const [maxJobs, setMaxJobs] = useState(String(DEFAULT_MAX_JOBS));
  const [error, setError] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const toggleCategory = (category: VendorCategory) =>
    setCategories((previous) =>
      previous.includes(category)
        ? previous.filter((value) => value !== category)
        : [...previous, category],
    );

  const handleClose = () => {
    if (saving) return;
    setName("");
    setEmail("");
    setPhone("");
    setCategories(suggestedCategories);
    setMaxJobs(String(DEFAULT_MAX_JOBS));
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
      await inviteVendor({
        name: name.trim(),
        email: email.trim(),
        phone: phone.trim() || null,
        categories: categories.length > 0 ? categories : null,
        max_concurrent_jobs: Number(maxJobs) || DEFAULT_MAX_JOBS,
      });

      toast.success(`Invite email sent to ${email.trim()}.`);
      onInvited();
      handleClose();
    } catch (submitError) {
      const { code, message } = toApiError(submitError);
      if (code === "DUPLICATE_EMAIL") {
        setEmailError("An account already uses this email address.");
      } else {
        setError(message);
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      open={open}
      title="Invite a vendor"
      description="Vendors added here become the pool the dispatch agent selects from."
      onClose={handleClose}
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
        {error ? <Alert tone="danger">{error}</Alert> : null}

        <Input
          label="Business or contact name"
          required
          value={name}
          onChange={(event) => setName(event.target.value)}
        />

        <Input
          label="Email"
          type="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          error={emailError}
          hint="Job offers are emailed here."
        />

        <Input
          label="Phone"
          type="tel"
          value={phone}
          onChange={(event) => setPhone(event.target.value)}
        />

        {/* Fixed vocabulary, not free text — the backend rejects anything off-list,
            and a mistyped category means this vendor is never matched. "other" is
            a ticket-only catch-all and is deliberately absent. */}
        <fieldset className="flex flex-col gap-2">
          <legend className="label-ui text-ink">
            Categories they cover
            <span className="ml-1.5 text-xs font-normal text-faint">
              Optional, but a vendor with none is never matched to a job
            </span>
          </legend>
          <div className="flex flex-wrap gap-2">
            {VENDOR_CATEGORIES.map((category) => {
              const selected = categories.includes(category);
              return (
                <button
                  key={category}
                  type="button"
                  aria-pressed={selected}
                  onClick={() => toggleCategory(category)}
                  className={cn(
                    "rounded-full border px-3 py-1.5 text-sm font-medium",
                    selected
                      ? "border-brand bg-brand text-white"
                      : "border-line bg-surface text-muted hover:bg-brand-soft hover:text-brand",
                  )}
                >
                  {categoryLabel(category)}
                </button>
              );
            })}
          </div>
        </fieldset>

        <Input
          label="Max concurrent jobs"
          type="number"
          min={1}
          value={maxJobs}
          onChange={(event) => setMaxJobs(event.target.value)}
          hint="A vendor already at this limit is skipped during dispatch."
        />

        <p className="text-sm text-muted">
          Rating starts at 5.0 and can&apos;t be set here. It decides which eligible
          vendor is picked first.
        </p>

        <div className="mt-2 flex justify-end gap-2">
          <Button variant="secondary" onClick={handleClose} disabled={saving}>
            Cancel
          </Button>
          <Button type="submit" loading={saving} disabled={!name.trim() || !email.trim()}>
            Send invite
          </Button>
        </div>
      </form>
    </Modal>
  );
}
