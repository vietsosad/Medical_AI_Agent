"use client";

import React from "react";
import { motion } from "framer-motion";
import { RefreshCw, WifiOff } from "lucide-react";

import { EmergencyCallHint } from "@/components/chat/EmergencyCallHint";
import { dropVariants } from "@/lib/motion";

/**
 * Visible, in-transcript failure state for a pilot turn -- a toast alone
 * (see simple-triage.service.ts's handlePilotApiError) is easy to miss, and
 * a failed send otherwise leaves the chat looking like nothing happened at
 * all (real incident: a transient openai.APIConnectionError from inside the
 * backend container surfaced only as a corner toast, with the patient
 * seeing no response and no obvious way to tell what to do next).
 *
 * The failed turn may be the one describing an emergency, so the 115 route
 * sits right next to "Gửi lại" instead of waiting on a retry that may also fail.
 */

interface Props {
  message: string;
  onRetry: () => void;
}

export function SimpleTurnErrorCard({ message, onRetry }: Props) {
  return (
    <motion.div
      variants={dropVariants}
      initial="hidden"
      animate="visible"
      role="alert"
      className="rounded-2xl border border-amber-300 bg-card p-4 dark:border-amber-800"
    >
      <p className="flex items-center gap-2 text-base font-bold text-amber-900 dark:text-amber-200">
        <WifiOff className="size-5 shrink-0" aria-hidden="true" />
        Chưa gửi được tin nhắn
      </p>
      <p className="mt-2 text-base leading-7 text-foreground">{message}</p>
      <motion.button
        type="button"
        onClick={onRetry}
        whileTap={{ scale: 0.97 }}
        className="mt-4 flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-brand px-4 text-base font-bold text-brand-foreground transition-colors hover:bg-brand-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 sm:w-auto"
      >
        <RefreshCw className="size-5" aria-hidden="true" />
        Gửi lại
      </motion.button>
      <EmergencyCallHint className="mt-4 border-t border-border pt-4" />
    </motion.div>
  );
}
