"use client";

import React, { useEffect, useRef } from "react";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { useClinicalSocket, type ClinicalRealtimeEvent } from "@/lib/realtime/useClinicalSocket";
import { TRIAGE_QUERY_KEYS } from "@/queries/useTriageQueries";

export function PatientRealtimeNotification() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const currentSessionId = searchParams.get("session_id");

  // Keep ref of current session to avoid stale closure in socket handler
  const currentSessionIdRef = useRef(currentSessionId);
  useEffect(() => {
    currentSessionIdRef.current = currentSessionId;
  }, [currentSessionId]);

  const handleEvent = (event: ClinicalRealtimeEvent) => {
    if (event.event === "message.created" && event.payload) {
      const payload = event.payload as {
        case_id: string;
        sender: string;
        sender_name: string;
      };

      if (payload.sender === "NURSE") {
        const isCurrentlyViewing = 
          pathname.includes("/triage") && 
          currentSessionIdRef.current === payload.case_id;

        if (isCurrentlyViewing) {
          // If already looking at this case, just invalidate to load the message
          queryClient.invalidateQueries({ queryKey: TRIAGE_QUERY_KEYS.messages(payload.case_id) });
          // Optional: A soft toast since they are already looking at it
          toast.info("Có tin nhắn mới từ nhân viên y tế.");
        } else {
          // If on a different page or different case, show a redirect toast
          toast(
            <div className="flex flex-col gap-2">
              <span className="font-semibold text-sky-900">
                Tin nhắn mới từ {payload.sender_name}
              </span>
              <span className="text-sm text-slate-600 dark:text-slate-300">
                Nhân viên y tế vừa gửi tin nhắn cho bạn.
              </span>
              <button
                onClick={() => {
                  toast.dismiss();
                  router.push(`/triage?session_id=${payload.case_id}`);
                }}
                className="mt-2 rounded-lg bg-sky-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-sky-700"
              >
                Xem ngay
              </button>
            </div>,
            { duration: 10000 }
          );
        }
        
        // Luôn luôn invalidate lịch sử để quả chuông (notification bell) tự động cập nhật số lượng
        queryClient.invalidateQueries({ queryKey: TRIAGE_QUERY_KEYS.history() });
      }
    }
  };

  // Connect to the patient's private realtime channel
  useClinicalSocket({
    path: "/ws/patient",
    onEvent: handleEvent,
    enabled: true,
  });

  return null; // This is a logic-only component
}
