"use client";

import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

import { EmergencyCallHint } from "@/components/chat/EmergencyCallHint";

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
    <div role="alert" className="flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm leading-6 text-rose-900">
      <AlertTriangle className="mt-0.5 size-5 shrink-0 text-rose-700" aria-hidden="true" />
      <div className="flex-1">
        <p className="font-semibold">{message}</p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 inline-flex min-h-11 items-center gap-2 rounded-lg border border-rose-300 bg-card px-4 text-sm font-semibold text-rose-800 transition-colors hover:bg-rose-100"
        >
          <RefreshCw className="size-4" aria-hidden="true" />
          Gửi lại
        </button>
        <EmergencyCallHint className="mt-4" />
      </div>
    </div>
  );
}
