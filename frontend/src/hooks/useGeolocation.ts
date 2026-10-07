"use client";

import { useCallback, useRef, useState } from "react";

/**
 * Lấy vị trí hiện tại của người dùng, **chỉ khi họ chủ động yêu cầu**.
 *
 * Hook này cố ý không có `useEffect` nào tự chạy: vị trí chỉ được xin sau một
 * hành động rõ ràng (bấm nút). Vị trí trong bối cảnh y tế là dữ liệu cá nhân
 * nhạy cảm, và một hộp thoại xin quyền bật lên ngay khi mở trang vừa là thói
 * quen xấu vừa khiến người dùng bấm "Chặn" theo phản xạ -- sau đó trình duyệt
 * ghi nhớ lựa chọn ấy cho cả tên miền.
 *
 * Toạ độ chỉ nằm trong state của React. Hook không ghi `localStorage`, không
 * ghi cookie và không gửi đi đâu; việc gửi lên máy chủ là quyết định riêng của
 * nơi gọi hook.
 */

export type GeolocationStatus =
  | "idle"
  | "locating"
  | "granted"
  /** Người dùng (hoặc chính sách trình duyệt) từ chối quyền. */
  | "denied"
  /** Thiết bị không định vị được, hoặc trang không chạy trên HTTPS. */
  | "unavailable"
  | "timeout";

export interface GeolocationFix {
  latitude: number;
  longitude: number;
  /** Sai số do trình duyệt báo, tính bằng mét. `null` khi không có. */
  accuracyMeters: number | null;
}

export interface UseGeolocationResult {
  status: GeolocationStatus;
  fix: GeolocationFix | null;
  /** Câu giải thích tiếng Việt cho trạng thái hỏng, `null` khi không có lỗi. */
  errorMessage: string | null;
  isLocating: boolean;
  request: () => void;
  reset: () => void;
}

/**
 * 12 giây. Định vị độ chính xác cao trên máy tính để bàn (dựa vào Wi-Fi) có thể
 * chậm; chờ quá lâu mà không phản hồi gì thì tệ hơn là báo hết giờ và mời người
 * dùng thử lại.
 */
const POSITION_TIMEOUT_MS = 12_000;

/** Chấp nhận một bản định vị đã có sẵn trong vòng 2 phút -- đủ mới cho việc tìm bệnh viện. */
const POSITION_MAX_AGE_MS = 120_000;

const MESSAGES: Record<Exclude<GeolocationStatus, "idle" | "locating" | "granted">, string> = {
  denied:
    "Trình duyệt đang chặn quyền vị trí cho trang này. Bạn có thể mở biểu tượng ổ khoá trên thanh địa chỉ để cho phép, hoặc dùng cách tìm thủ công bên dưới.",
  unavailable:
    "Thiết bị chưa xác định được vị trí. Hãy kiểm tra xem GPS hoặc dịch vụ vị trí đã bật chưa, hoặc dùng cách tìm thủ công bên dưới.",
  timeout:
    "Quá thời gian chờ xác định vị trí. Bạn có thể thử lại, hoặc dùng cách tìm thủ công bên dưới.",
};

export function useGeolocation(): UseGeolocationResult {
  const [status, setStatus] = useState<GeolocationStatus>("idle");
  const [fix, setFix] = useState<GeolocationFix | null>(null);

  // Chặn hai lần bấm liên tiếp cùng mở hai lời gọi định vị. Dùng ref chứ không
  // dùng state: giá trị cần đúng ngay trong cùng một lượt xử lý sự kiện.
  const inFlightRef = useRef(false);

  const request = useCallback(() => {
    if (inFlightRef.current) return;

    // Kiểm tra giá trị chứ không chỉ kiểm tra khoá có tồn tại: một số webview
    // nhúng và tiện ích chặn quyền riêng tư giữ nguyên thuộc tính
    // `navigator.geolocation` nhưng gán nó thành undefined. Chỉ dùng
    // `"geolocation" in navigator` sẽ lọt qua và văng lỗi ngay dòng dưới.
    const geolocation = typeof window === "undefined" ? undefined : navigator.geolocation;
    if (!geolocation) {
      setStatus("unavailable");
      return;
    }

    // Ngoài ngữ cảnh an toàn (HTTP không phải localhost), API vị trí bị chặn
    // hoặc im lặng không trả gì. Nói rõ ra còn hơn để người dùng chờ hết 12
    // giây rồi nhận một thông báo hết giờ không giải thích được vì sao.
    if (window.isSecureContext === false) {
      setStatus("unavailable");
      return;
    }

    inFlightRef.current = true;
    setStatus("locating");

    geolocation.getCurrentPosition(
      (position) => {
        inFlightRef.current = false;
        setFix({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracyMeters:
            typeof position.coords.accuracy === "number" ? position.coords.accuracy : null,
        });
        setStatus("granted");
      },
      (error) => {
        inFlightRef.current = false;
        setFix(null);
        if (error.code === error.PERMISSION_DENIED) {
          setStatus("denied");
        } else if (error.code === error.TIMEOUT) {
          setStatus("timeout");
        } else {
          setStatus("unavailable");
        }
      },
      {
        enableHighAccuracy: true,
        timeout: POSITION_TIMEOUT_MS,
        maximumAge: POSITION_MAX_AGE_MS,
      },
    );
  }, []);

  const reset = useCallback(() => {
    inFlightRef.current = false;
    setFix(null);
    setStatus("idle");
  }, []);

  const errorMessage =
    status === "denied" || status === "unavailable" || status === "timeout"
      ? MESSAGES[status]
      : null;

  return {
    status,
    fix,
    errorMessage,
    isLocating: status === "locating",
    request,
    reset,
  };
}
