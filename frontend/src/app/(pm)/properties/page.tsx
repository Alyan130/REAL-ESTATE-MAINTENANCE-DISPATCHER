"use client";

import { Building2, MapPin, Plus, Trash2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { AddPropertyModal } from "@/components/properties/add-property-modal";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardBody } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { FadeIn, StaggerItem, StaggerList } from "@/components/ui/motion-list";
import { PageHeader } from "@/components/ui/page-header";
import { RowsSkeleton } from "@/components/ui/skeleton";
import { deleteProperty, listProperties } from "@/lib/api/properties";
import { errorMessage } from "@/lib/errors";
import { formatDate } from "@/lib/format";
import type { Property } from "@/lib/types";
import { useAsync } from "@/lib/use-async";
import { toast } from "@/stores/toast-store";

export default function PropertiesPage() {
  const properties = useAsync(() => listProperties(), []);
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState<Property | null>(null);
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    if (!removing) return;
    setDeleting(true);

    try {
      await deleteProperty(removing.id);
      toast.success(`${removing.name} removed from your list.`);
      setRemoving(null);
      await properties.reload({ silent: true });
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setDeleting(false);
    }
  };

  const list = properties.data ?? [];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Properties"
        description="The top of the hierarchy — tenants and tickets both hang off a property."
        action={
          <Button icon={<Plus size={16} />} onClick={() => setAdding(true)}>
            Add property
          </Button>
        }
      />

      {properties.error ? <Alert tone="danger">{properties.error}</Alert> : null}

      {properties.loading && list.length === 0 ? <RowsSkeleton rows={3} /> : null}

      {!properties.loading && list.length === 0 ? (
        <FadeIn>
          <EmptyState
            icon={<Building2 size={22} />}
            title="Add your first property"
            description="This is step one. Once a property exists you can invite tenants to it, and their tickets will start arriving on your dashboard."
            action={
              <Button icon={<Plus size={16} />} onClick={() => setAdding(true)}>
                Add property
              </Button>
            }
          />
        </FadeIn>
      ) : null}

      {list.length > 0 ? (
        <StaggerList>
          {list.map((property) => (
            <StaggerItem key={property.id}>
              <Card className="hover:border-line transition-colors">
                <CardBody className="flex flex-wrap items-center justify-between gap-4">
                  <div className="min-w-0">
                    <Link
                      href={`/properties/${property.id}`}
                      className="font-bold text-ink-strong text-base hover:text-brand transition-colors"
                    >
                      {property.name}
                    </Link>
                    <p className="mt-1 flex items-center gap-1.5 text-xs text-muted font-medium">
                      <MapPin size={13} className="text-brand shrink-0" />
                      {property.address}
                    </p>
                    <p className="mt-1 text-technical text-faint text-xs">
                      Added {formatDate(property.created_at)}
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <Link href={`/properties/${property.id}`}>
                      <Button size="sm" variant="secondary">
                        Open
                      </Button>
                    </Link>
                    <Button
                      size="sm"
                      variant="ghost"
                      icon={<Trash2 size={14} />}
                      aria-label={`Remove ${property.name}`}
                      onClick={() => setRemoving(property)}
                    >
                      Remove
                    </Button>
                  </div>
                </CardBody>
              </Card>
            </StaggerItem>
          ))}
        </StaggerList>
      ) : null}

      <AddPropertyModal
        open={adding}
        onClose={() => setAdding(false)}
        onCreated={() => void properties.reload({ silent: true })}
      />

      <ConfirmDialog
        open={Boolean(removing)}
        title="Remove this property?"
        destructive
        confirmLabel="Remove property"
        loading={deleting}
        onCancel={() => setRemoving(null)}
        onConfirm={() => void handleDelete()}
        body={
          <>
            <p className="text-xs text-muted">
              <span className="font-semibold text-ink-strong">{removing?.name}</span> disappears from
              your list. Its tickets and tenant records are kept, so past history
              stays intact — but you won&apos;t be able to invite new tenants to it.
            </p>
            <p className="mt-3 text-xs text-muted">There is no way to restore it from this screen.</p>
          </>
        }
      />
    </div>
  );
}
