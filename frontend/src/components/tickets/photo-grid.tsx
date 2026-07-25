"use client";

/* eslint-disable @next/next/no-img-element -- Photos are Supabase Storage URLs on a
   host that isn't known at build time, so next/image's remotePatterns can't cover them. */

import { motion } from "motion/react";
import { useState } from "react";

import { Modal } from "@/components/ui/modal";

interface PhotoGridProps {
  urls: string[];
  /** Shown as alt text context, e.g. the ticket title. */
  context: string;
}

export function PhotoGrid({ urls, context }: PhotoGridProps) {
  const [openUrl, setOpenUrl] = useState<string | null>(null);

  return (
    <>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {urls.map((url, index) => (
          <motion.button
            key={url}
            type="button"
            onClick={() => setOpenUrl(url)}
            whileHover={{ y: -2 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="overflow-hidden rounded-card border border-line-soft bg-sunken"
          >
            <img
              src={url}
              alt={`${context} — photo ${index + 1}`}
              loading="lazy"
              className="aspect-4/3 w-full object-cover"
            />
          </motion.button>
        ))}
      </div>

      <Modal
        open={Boolean(openUrl)}
        title="Photo"
        onClose={() => setOpenUrl(null)}
      >
        {openUrl ? (
          <img
            src={openUrl}
            alt={`${context} — full size`}
            className="max-h-[70dvh] w-full rounded-card object-contain"
          />
        ) : null}
      </Modal>
    </>
  );
}
