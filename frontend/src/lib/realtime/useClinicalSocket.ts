"use client";

import { useEffect, useRef, useState } from "react";

/**
 * ============================================================================
 * [REALTIME] KÊNH WEBSOCKET CHO HÀNG ĐỢI LÂM SÀNG VÀ HỘI THOẠI CỦA CA
 * ============================================================================
 * Kênh này chỉ mang tín hiệu "có thay đổi, hãy đọc lại". Nội dung lâm sàng luôn
 * được lấy lại qua REST, nên một sự kiện rơi mất chỉ làm giao diện chậm cập
 * nhật chứ không bao giờ làm sai dữ liệu đang hiển thị.
 *
 * Vì lý do đó, mất kết nối được báo cho người dùng nhưng không xoá gì trên màn
 * hình: hội thoại đã tải vẫn ở nguyên đó trong lúc kênh tự kết nối lại.
 */

export type ClinicalSocketStatus = "connecting" | "open" | "reconnecting" | "closed";

export interface ClinicalRealtimeEvent {
  event: string;
  topic?: string;
  payload?: Record<string, unknown>;
  emitted_at?: string;
}

interface UseClinicalSocketOptions {
  /** Đường dẫn kênh, ví dụ `/ws/clinical` hoặc `/ws/case/{id}`. Null để tắt kênh. */
  path: string | null;
  onEvent: (event: ClinicalRealtimeEvent) => void;
  enabled?: boolean;
}

const BASE_RECONNECT_MS = 1_000;
const MAX_RECONNECT_MS = 15_000;

/** Đổi http(s) của API sang ws(s), giữ nguyên host và cổng đang dùng. */
export function clinicalSocketUrl(path: string, token: string | null): string {
  const apiBase =
    process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "") ?? "http://localhost:8000";
  const wsBase = apiBase.replace(/^http/, "ws");
  const url = new URL(`${wsBase}/api/v1${path}`);
  // Trình duyệt không cho đặt header Authorization khi mở WebSocket. Cookie phiên
  // được ưu tiên ở backend; token chỉ là đường lùi cho môi trường khác origin.
  if (token) url.searchParams.set("token", token);
  return url.toString();
}

function readAccessToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|;\s*)ai20k_access_token=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export function useClinicalSocket({
  path,
  onEvent,
  enabled = true,
}: UseClinicalSocketOptions): { status: ClinicalSocketStatus } {
  // Chỉ ghi nhận những gì WebSocket thực sự báo về. Trạng thái hiển thị được
  // suy ra bên dưới, nên không có lần đặt state nào chạy đồng bộ trong effect.
  const [phase, setPhase] = useState<"idle" | "open" | "down">("idle");

  // Giữ callback trong ref để đổi handler không làm kênh phải kết nối lại.
  const handlerRef = useRef(onEvent);
  useEffect(() => {
    handlerRef.current = onEvent;
  }, [onEvent]);

  const active = enabled && Boolean(path) && typeof window !== "undefined";

  useEffect(() => {
    if (!active || !path) return;

    let socket: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let attempt = 0;
    let disposed = false;

    const connect = () => {
      if (disposed) return;
      try {
        socket = new WebSocket(clinicalSocketUrl(path, readAccessToken()));
      } catch {
        scheduleRetry();
        return;
      }

      socket.onopen = () => {
        if (disposed) return;
        attempt = 0;
        setPhase("open");
      };

      socket.onmessage = (message) => {
        if (disposed) return;
        try {
          const parsed = JSON.parse(message.data as string) as ClinicalRealtimeEvent;
          // Nhịp giữ kết nối không phải là thay đổi dữ liệu.
          if (!parsed?.event || parsed.event === "heartbeat") return;
          handlerRef.current(parsed);
        } catch {
          // Gói tin hỏng không được làm sập kênh đang phục vụ ca bệnh.
        }
      };

      socket.onerror = () => {
        socket?.close();
      };

      socket.onclose = () => {
        if (disposed) return;
        scheduleRetry();
      };
    };

    const scheduleRetry = () => {
      if (disposed) return;
      setPhase("down");
      // Lùi dần theo cấp số nhân để một backend đang khởi động lại không bị hàng
      // chục trạm lâm sàng dồn kết nối cùng lúc.
      const delay = Math.min(BASE_RECONNECT_MS * 2 ** attempt, MAX_RECONNECT_MS);
      attempt += 1;
      retryTimer = setTimeout(connect, delay);
    };

    connect();

    return () => {
      disposed = true;
      if (retryTimer) clearTimeout(retryTimer);
      if (socket) {
        socket.onclose = null;
        socket.onerror = null;
        socket.close();
      }
    };
  }, [path, active]);

  const status: ClinicalSocketStatus = !active
    ? "closed"
    : phase === "open"
      ? "open"
      : phase === "down"
        ? "reconnecting"
        : "connecting";

  return { status };
}

/** Câu chữ hiển thị cho từng trạng thái kênh. */
export function realtimeStatusLabel(status: ClinicalSocketStatus): string {
  switch (status) {
    case "open":
      return "Đang kết nối thời gian thực";
    case "connecting":
      return "Đang mở kênh thời gian thực...";
    case "reconnecting":
      return "Mất kết nối realtime. Đang kết nối lại...";
    default:
      return "Kênh thời gian thực đã tắt";
  }
}
