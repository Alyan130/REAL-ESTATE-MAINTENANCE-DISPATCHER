"use client";

import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/field";
import { Modal } from "@/components/ui/modal";
import { createProperty } from "@/lib/api/properties";
import { errorMessage } from "@/lib/errors";
import type { Property } from "@/lib/types";
import { toast } from "@/stores/toast-store";

interface AddPropertyModalProps {
  open: boolean;
  onClose: () => void;
  onCreated: (property: Property) => void;
}

export function AddPropertyModal({ open, onClose, onCreated }: AddPropertyModalProps) {
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const reset = () => {
    setName("");
    setAddress("");
    setError(null);
  };

  const handleClose = () => {
    if (saving) return;
    reset();
    onClose();
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setSaving(true);

    try {
      const property = await createProperty({
        name: name.trim(),
        address: address.trim(),
      });
      toast.success(`${property.name} added.`);
      onCreated(property);
      reset();
      onClose();
    } catch (submitError) {
      // Input is kept so the user can fix and resubmit rather than retype.
      setError(errorMessage(submitError));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      open={open}
      title="Add a property"
      description="Tenants and tickets both attach to a property."
      onClose={handleClose}
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
        {error ? <Alert tone="danger">{error}</Alert> : null}

        <Input
          label="Property name"
          required
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Maple Court"
        />

        <Input
          label="Address"
          required
          value={address}
          onChange={(event) => setAddress(event.target.value)}
          placeholder="118 Maple Street, Springfield"
        />

        <div className="mt-2 flex justify-end gap-2">
          <Button variant="secondary" onClick={handleClose} disabled={saving}>
            Cancel
          </Button>
          <Button
            type="submit"
            loading={saving}
            disabled={!name.trim() || !address.trim()}
          >
            Add property
          </Button>
        </div>
      </form>
    </Modal>
  );
}
