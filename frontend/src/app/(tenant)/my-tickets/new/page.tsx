"use client";

/* eslint-disable @next/next/no-img-element -- Previews are local object URLs, which
   next/image cannot optimise. */

import { motion } from "motion/react";
import { ArrowLeft, Camera, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardBody } from "@/components/ui/card";
import { Checkbox, Input, Textarea } from "@/components/ui/field";
import { FadeIn } from "@/components/ui/motion-list";
import { createTicket } from "@/lib/api/tickets";
import { errorMessage } from "@/lib/errors";
import { toast } from "@/stores/toast-store";

interface Photo {
  file: File;
  previewUrl: string;
}

const MAX_PHOTOS = 6;

export default function SubmitTicketPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [permissionToEnter, setPermissionToEnter] = useState(false);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Object URLs are only freed on unmount; removing one photo frees its own URL.
  useEffect(() => {
    return () => {
      photos.forEach((photo) => URL.revokeObjectURL(photo.previewUrl));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const addPhotos = (files: FileList | null) => {
    if (!files?.length) return;

    const room = MAX_PHOTOS - photos.length;
    if (room <= 0) {
      toast.info(`You can attach up to ${MAX_PHOTOS} photos.`);
      return;
    }

    const accepted = Array.from(files)
      .filter((file) => file.type.startsWith("image/"))
      .slice(0, room)
      .map((file) => ({ file, previewUrl: URL.createObjectURL(file) }));

    setPhotos((previous) => [...previous, ...accepted]);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const removePhoto = (previewUrl: string) => {
    URL.revokeObjectURL(previewUrl);
    setPhotos((previous) =>
      previous.filter((photo) => photo.previewUrl !== previewUrl),
    );
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);

    if (!title.trim()) {
      setError("Give your report a short title so it can be identified.");
      return;
    }

    setSubmitting(true);
    try {
      const { id } = await createTicket({
        title: title.trim(),
        description: description.trim() || undefined,
        permission_to_enter: permissionToEnter,
        photos: photos.map((photo) => photo.file),
      });

      // The API answers as soon as the ticket exists; photos and classification
      // finish in the background, so there is nothing to wait on here.
      toast.success("Report received. We're on it.");
      router.replace(`/my-tickets/${id}`);
    } catch (submitError) {
      // Everything the user typed stays on screen so they can just retry.
      setError(errorMessage(submitError));
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6">
      <Link
        href="/my-tickets"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-muted hover:text-ink"
      >
        <ArrowLeft size={15} />
        My reports
      </Link>

      <FadeIn>
        <h1 className="text-[2.25rem] leading-tight font-bold">Report an issue</h1>
        <p className="mt-1 text-muted">
          A title and a photo is usually enough. Someone will be assigned without you
          having to chase anyone.
        </p>
      </FadeIn>

      <Card>
        <CardBody>
          <form onSubmit={handleSubmit} className="flex flex-col gap-5" noValidate>
            {error ? <Alert tone="danger">{error}</Alert> : null}

            <Input
              label="What's wrong?"
              required
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Kitchen tap won't stop dripping"
              maxLength={140}
            />

            <Textarea
              label="Any more detail?"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="When it started, how bad it is, anything you've tried."
              hint="Worth a sentence — this is what gets read to work out how urgent it is and who to send."
            />

            <div className="flex flex-col gap-2">
              <span className="label-ui text-ink">
                Photos
                <span className="ml-1.5 text-xs font-normal text-faint">
                  Up to {MAX_PHOTOS}
                </span>
              </span>

              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                multiple
                className="hidden"
                onChange={(event) => addPhotos(event.target.files)}
              />

              <Button
                variant="secondary"
                icon={<Camera size={16} />}
                onClick={() => fileInputRef.current?.click()}
                disabled={photos.length >= MAX_PHOTOS}
              >
                {photos.length > 0 ? "Add another photo" : "Add a photo"}
              </Button>

              {photos.length > 0 ? (
                <div className="mt-1 grid grid-cols-3 gap-3">
                  {photos.map((photo) => (
                    <motion.div
                      key={photo.previewUrl}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.24, ease: "easeOut" }}
                      className="relative overflow-hidden rounded-card border border-line-soft"
                    >
                      <img
                        src={photo.previewUrl}
                        alt={photo.file.name}
                        className="aspect-square w-full object-cover"
                      />
                      <button
                        type="button"
                        aria-label={`Remove ${photo.file.name}`}
                        onClick={() => removePhoto(photo.previewUrl)}
                        className="absolute top-1 right-1 rounded-full bg-shell-strong/70 p-1 text-white"
                      >
                        <X size={14} />
                      </button>
                    </motion.div>
                  ))}
                </div>
              ) : null}
            </div>

            {/* Affects scheduling directly, so it is asked here rather than chased
                later. */}
            <Checkbox
              label="A contractor may enter while I'm out"
              description="Without this, the visit has to be arranged for a time you're home."
              checked={permissionToEnter}
              onChange={(event) => setPermissionToEnter(event.target.checked)}
            />

            <Button type="submit" loading={submitting} fullWidth>
              Submit report
            </Button>
          </form>
        </CardBody>
      </Card>
    </div>
  );
}
