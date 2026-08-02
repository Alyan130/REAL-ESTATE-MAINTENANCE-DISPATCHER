"use client";

import { Plus, Tags } from "lucide-react";
import { useMemo, useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/field";
import { Modal } from "@/components/ui/modal";
import { FadeIn, StaggerItem, StaggerList } from "@/components/ui/motion-list";
import { PageHeader } from "@/components/ui/page-header";
import { RowsSkeleton } from "@/components/ui/skeleton";
import {
  createCategory,
  deleteCategory,
  listCategories,
  updateCategory,
} from "@/lib/api/categories";
import { errorMessage, toApiError } from "@/lib/errors";
import type { CategorySetting } from "@/lib/types";
import { useAsync } from "@/lib/use-async";
import { toast } from "@/stores/toast-store";

/**
 * "" → null, so clearing a field turns the price off rather than sending 0.
 * Anything else that isn't a non-negative number is `invalid` rather than null
 * — silently discarding a mistyped price and reporting success would be worse
 * than refusing to save it.
 */
type ParsedPrice = { ok: true; value: number | null } | { ok: false };

function parsePrice(value: string): ParsedPrice {
  const trimmed = value.trim();
  if (!trimmed) return { ok: true, value: null };
  const parsed = Number(trimmed);
  if (!Number.isFinite(parsed) || parsed < 0) return { ok: false };
  return { ok: true, value: parsed };
}

function priceToInput(value: number | null): string {
  return value === null ? "" : String(value);
}

export default function CategoriesPage() {
  const categories = useAsync(() => listCategories(), []);
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState<CategorySetting | null>(null);
  const [deleting, setDeleting] = useState(false);

  const list = useMemo(() => categories.data ?? [], [categories.data]);
  const withoutCeiling = useMemo(
    () => list.filter((c) => c.max_price === null && c.is_vendor_selectable),
    [list],
  );

  const handleDelete = async () => {
    if (!removing) return;
    setDeleting(true);
    try {
      await deleteCategory(removing.id);
      toast.success(`${removing.label} removed.`);
      setRemoving(null);
      await categories.reload({ silent: true });
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Categories & pricing"
        description="What the AI classifies tickets into, and what you'll pay for each trade. The ceiling is the only number that spends money without asking you."
        action={
          <Button icon={<Plus size={16} />} onClick={() => setAdding(true)}>
            Add category
          </Button>
        }
      />

      {categories.error ? <Alert tone="danger">{categories.error}</Alert> : null}

      {!categories.loading && withoutCeiling.length > 0 ? (
        <Alert tone="info" title="No auto-approve ceiling set">
          <p className="text-xs">
            Every quote in{" "}
            <span className="font-semibold text-ink-strong">
              {withoutCeiling.map((c) => c.label).join(", ")}
            </span>{" "}
            will come to you for a decision. That&apos;s the safe default — set a
            ceiling on a category once you know what a normal job costs, and
            quotes under it get approved without interrupting you.
          </p>
        </Alert>
      ) : null}

      {categories.loading && list.length === 0 ? <RowsSkeleton rows={4} /> : null}

      {!categories.loading && list.length === 0 ? (
        <FadeIn>
          <EmptyCategories onAdd={() => setAdding(true)} />
        </FadeIn>
      ) : null}

      {list.length > 0 ? (
        <StaggerList>
          {list.map((category) => (
            <StaggerItem key={category.id}>
              <CategoryRow
                category={category}
                onSaved={() => void categories.reload({ silent: true })}
                onRemove={() => setRemoving(category)}
              />
            </StaggerItem>
          ))}
        </StaggerList>
      ) : null}

      <AddCategoryModal
        open={adding}
        onClose={() => setAdding(false)}
        onCreated={() => void categories.reload({ silent: true })}
      />

      <ConfirmDialog
        open={Boolean(removing)}
        title="Remove this category?"
        destructive
        confirmLabel="Remove"
        loading={deleting}
        onCancel={() => setRemoving(null)}
        onConfirm={() => void handleDelete()}
        body={
          <p className="text-xs text-muted">
            The AI stops classifying new tickets as{" "}
            <span className="font-semibold text-ink-strong">{removing?.label}</span>.
            Existing tickets keep their category, and vendors tagged with it stay
            tagged — nothing in your history changes.
          </p>
        }
      />
    </div>
  );
}

/* ─── Row ──────────────────────────────────────────────────────────────────── */

function CategoryRow({
  category,
  onSaved,
  onRemove,
}: {
  category: CategorySetting;
  onSaved: () => void;
  onRemove: () => void;
}) {
  const [target, setTarget] = useState(priceToInput(category.target_price));
  const [ceiling, setCeiling] = useState(priceToInput(category.max_price));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const dirty =
    target !== priceToInput(category.target_price) ||
    ceiling !== priceToInput(category.max_price);

  const handleSave = async () => {
    const parsedTarget = parsePrice(target);
    const parsedCeiling = parsePrice(ceiling);

    if (!parsedTarget.ok || !parsedCeiling.ok) {
      setError("Prices must be a number, or blank to clear.");
      return;
    }

    const nextTarget = parsedTarget.value;
    const nextCeiling = parsedCeiling.value;

    if (nextTarget !== null && nextCeiling !== null && nextCeiling < nextTarget) {
      setError("The ceiling can't be below the target price.");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await updateCategory(category.id, {
        target_price: nextTarget,
        max_price: nextCeiling,
      });
      toast.success(`${category.label} updated.`);
      onSaved();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card>
      <CardBody className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-bold text-ink-strong text-base">{category.label}</p>
            <span className="text-technical text-xs text-faint">{category.name}</span>
            {!category.is_vendor_selectable ? (
              <Badge tone="warn">Fallback — no vendor covers this</Badge>
            ) : null}
            {category.max_price === null ? (
              <Badge tone="neutral">Always asks you</Badge>
            ) : null}
          </div>

          <div className="mt-3 flex flex-wrap items-end gap-3">
            <div className="w-36">
              <Input
                label="Target"
                type="number"
                min={0}
                step="1"
                inputMode="decimal"
                placeholder="—"
                hint="What it usually costs"
                value={target}
                onChange={(e) => setTarget(e.target.value)}
              />
            </div>
            <div className="w-36">
              <Input
                label="Auto-approve up to"
                type="number"
                min={0}
                step="1"
                inputMode="decimal"
                placeholder="—"
                hint="Blank = always ask"
                value={ceiling}
                onChange={(e) => setCeiling(e.target.value)}
              />
            </div>
          </div>

          {error ? (
            <p role="alert" className="mt-2 text-xs font-medium text-danger">
              {error}
            </p>
          ) : null}
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            loading={saving}
            disabled={!dirty}
            onClick={() => void handleSave()}
          >
            Save
          </Button>
          {category.is_vendor_selectable ? (
            <Button size="sm" variant="ghost" onClick={onRemove}>
              Remove
            </Button>
          ) : null}
        </div>
      </CardBody>
    </Card>
  );
}

/* ─── Add modal ────────────────────────────────────────────────────────────── */

function AddCategoryModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [label, setLabel] = useState("");
  const [target, setTarget] = useState("");
  const [ceiling, setCeiling] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [labelError, setLabelError] = useState<string | null>(null);

  const handleClose = () => {
    if (saving) return;
    setLabel("");
    setTarget("");
    setCeiling("");
    setError(null);
    setLabelError(null);
    onClose();
  };

  const handleSubmit = async () => {
    if (!label.trim()) {
      setLabelError("Give the category a name.");
      return;
    }

    const parsedTarget = parsePrice(target);
    const parsedCeiling = parsePrice(ceiling);
    if (!parsedTarget.ok || !parsedCeiling.ok) {
      setError("Prices must be a number, or blank to leave unset.");
      return;
    }

    setSaving(true);
    setError(null);
    setLabelError(null);
    try {
      await createCategory({
        label: label.trim(),
        target_price: parsedTarget.value,
        max_price: parsedCeiling.value,
      });
      toast.success(`${label.trim()} added.`);
      onCreated();
      handleClose();
    } catch (err) {
      const apiError = toApiError(err);
      if (apiError.code === "DUPLICATE_CATEGORY") {
        setLabelError("You already have a category with that name.");
      } else {
        setError(apiError.message);
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      open={open}
      title="Add a category"
      description="The AI can only classify a ticket into a category you've created — and it can only reach a vendor tagged with the same one."
      onClose={handleClose}
      footer={
        <>
          <Button variant="secondary" onClick={handleClose} disabled={saving}>
            Cancel
          </Button>
          <Button loading={saving} onClick={() => void handleSubmit()}>
            Add category
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {error ? <Alert tone="danger">{error}</Alert> : null}

        <Input
          label="Name"
          placeholder="Landscaping"
          required
          value={label}
          error={labelError}
          onChange={(e) => setLabel(e.target.value)}
        />

        <div className="flex flex-wrap gap-3">
          <div className="w-40">
            <Input
              label="Target price"
              type="number"
              min={0}
              step="1"
              inputMode="decimal"
              placeholder="—"
              hint="Optional"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
            />
          </div>
          <div className="w-40">
            <Input
              label="Auto-approve up to"
              type="number"
              min={0}
              step="1"
              inputMode="decimal"
              placeholder="—"
              hint="Blank = always ask"
              value={ceiling}
              onChange={(e) => setCeiling(e.target.value)}
            />
          </div>
        </div>

        <p className="text-xs text-muted">
          Remember to tag a vendor with this category too — a category nobody
          covers sends its tickets straight back to you.
        </p>
      </div>
    </Modal>
  );
}

/* ─── Empty ────────────────────────────────────────────────────────────────── */

function EmptyCategories({ onAdd }: { onAdd: () => void }) {
  return (
    <EmptyState
      icon={<Tags size={22} />}
      title="No categories yet"
      description="Categories are how the AI sorts tickets and finds the right vendor. You should have a starter set already — if this stays empty, reload the page."
      action={
        <Button icon={<Plus size={16} />} onClick={onAdd}>
          Add category
        </Button>
      }
    />
  );
}
