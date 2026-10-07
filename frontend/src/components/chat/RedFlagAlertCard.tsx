"use client";

import { motion, useReducedMotion } from "framer-motion";
import { AlertTriangle, PhoneCall, Users, X } from "lucide-react";

import { useEmergencyContacts } from "@/hooks/queries/use-clinical-profile";
import { useTriageStore } from "@/store/useTriageStore";

/** Build a dialable href from a stored contact number, or null when unusable. */
function telephoneHref(phoneNumber: string): string | null {
  const trimmed = phoneNumber.trim();
  const digits = trimmed.replace(/\D/g, "");
  if (digits.length < 3) return null;
  return `tel:${trimmed.startsWith("+") ? "+" : ""}${digits}`;
}

/**
 * ============================================================================
 * [RED FLAG ALERT CARD] CẢNH BÁO KHẨN CẤP NGAY TRONG KHUNG HỘI THOẠI
 * ============================================================================
 * Thay cho màn hình đỏ toàn màn hình trước đây: cảnh báo nằm trong dòng chảy
 * hội thoại, không che tin nhắn cũ, không khóa trang, đóng/mở được.
 *
 * Thành phần này chỉ TRÌNH BÀY tín hiệu mà backend đã xác nhận. Nó không phát
 * hiện, không suy luận và không hạ cấp bất kỳ cảnh báo nào.
 */
export function RedFlagAlertCard() {
  const redFlagTriggered = useTriageStore((state) => state.redFlagTriggered);
  const redFlagAlertOpen = useTriageStore((state) => state.redFlagAlertOpen);
  const dismissRedFlagAlert = useTriageStore((state) => state.dismissRedFlagAlert);
  const reopenRedFlagAlert = useTriageStore((state) => state.reopenRedFlagAlert);
  const { data: contacts } = useEmergencyContacts();
  const shouldReduceMotion = useReducedMotion();

  if (!redFlagTriggered) return null;

  // Trạng thái thu gọn: vẫn giữ dấu hiệu phiên đang có cảnh báo khẩn cấp
  // và cho phép người bệnh mở lại thẻ bất cứ lúc nào.
  if (!redFlagAlertOpen) {
    return (
      <div className="my-3 flex justify-center px-1">
        <button
          type="button"
          onClick={reopenRedFlagAlert}
          aria-expanded={false}
          className="flex min-h-11 items-center gap-2 rounded-full border border-rose-300 bg-rose-50 px-4 py-2 text-sm font-semibold text-rose-800 transition-colors hover:bg-rose-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600 focus-visible:ring-offset-2"
        >
          <AlertTriangle className="size-4 shrink-0" aria-hidden="true" />
          <span>Khuyến nghị khẩn cấp — xem lại hướng dẫn</span>
        </button>
      </div>
    );
  }

  const primaryContact = contacts?.find((contact) => contact.is_primary) ?? contacts?.[0];
  const contactHref = primaryContact ? telephoneHref(primaryContact.phone_number) : null;

  return (
    <motion.section
      role="alert"
      aria-live="assertive"
      aria-labelledby="red-flag-alert-title"
      initial={shouldReduceMotion ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: shouldReduceMotion ? 0 : 0.2, ease: "easeOut" }}
      className="my-4 w-full overflow-hidden rounded-2xl border border-rose-300 bg-card shadow-sm"
    >
      <header className="flex items-start gap-3 border-b border-rose-200 bg-rose-50 px-4 py-3.5 sm:px-5">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-rose-600 text-white">
          <AlertTriangle className="size-5 stroke-[2.4]" aria-hidden="true" />
        </span>

        <div className="min-w-0 flex-1 space-y-1">
          <h2
            id="red-flag-alert-title"
            className="text-base font-bold leading-6 tracking-tight text-rose-950 sm:text-lg"
          >
            Phát hiện dấu hiệu cần đánh giá khẩn cấp
          </h2>
          <p className="text-sm leading-6 text-rose-900">
            Một số triệu chứng bạn mô tả có thể cần được nhân viên y tế đánh giá trực tiếp ngay.
          </p>
        </div>

        <button
          type="button"
          onClick={dismissRedFlagAlert}
          aria-label="Đóng cảnh báo khẩn cấp"
          className="flex size-11 shrink-0 items-center justify-center rounded-xl text-rose-700 transition-colors hover:bg-rose-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600"
        >
          <X className="size-5" aria-hidden="true" />
        </button>
      </header>

      <div className="space-y-4 px-4 py-4 sm:px-5">
        <p className="text-sm font-semibold leading-6 text-foreground">
          Khuyến nghị: gọi 115 hoặc nhờ người bên cạnh hỗ trợ ngay.
        </p>

        <div className="flex flex-col gap-2.5 sm:flex-row sm:flex-wrap sm:items-center">
          <a
            href="tel:115"
            aria-label="Gọi cấp cứu 115"
            className="flex min-h-12 flex-1 items-center justify-center gap-2.5 rounded-xl bg-rose-600 px-5 text-base font-bold text-white transition-colors hover:bg-rose-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600 focus-visible:ring-offset-2 sm:flex-none"
          >
            <PhoneCall className="size-5 shrink-0" aria-hidden="true" />
            <span>Gọi 115</span>
          </a>

          {primaryContact && contactHref && (
            <a
              href={contactHref}
              aria-label={`Gọi người liên hệ khẩn cấp ${primaryContact.full_name}`}
              className="flex min-h-12 flex-1 items-center justify-center gap-2.5 rounded-xl border border-slate-300 bg-card px-5 text-sm font-semibold text-slate-800 transition-colors hover:bg-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-600 focus-visible:ring-offset-2 sm:flex-none dark:text-slate-100 dark:border-slate-700"
            >
              <Users className="size-5 shrink-0" aria-hidden="true" />
              <span className="min-w-0 truncate">
                Gọi {primaryContact.full_name}: {primaryContact.phone_number}
              </span>
            </a>
          )}

          <button
            type="button"
            onClick={dismissRedFlagAlert}
            className="flex min-h-12 flex-1 items-center justify-center rounded-xl border border-slate-300 bg-card px-5 text-sm font-semibold text-slate-700 transition-colors hover:bg-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-600 focus-visible:ring-offset-2 sm:flex-none dark:text-slate-200 dark:border-slate-700"
          >
            Tôi đã biết
          </button>
        </div>

        <div className="rounded-xl border border-border bg-background p-4">
          <h3 className="text-sm font-bold text-foreground">Trong khi chờ hỗ trợ</h3>
          <ol className="mt-2 list-decimal space-y-1.5 pl-5 text-sm leading-6 text-slate-700 marker:font-semibold marker:text-rose-700 dark:text-slate-200">
            <li>Nhờ người ở gần ở lại cùng bạn và gọi 115 nếu bạn chưa thể tự gọi.</li>
            <li>Không tự lái xe. Chờ phương tiện cấp cứu hoặc người khác đưa đến nơi đánh giá.</li>
            <li>Làm theo hướng dẫn trực tiếp của nhân viên cấp cứu qua điện thoại.</li>
          </ol>
        </div>
      </div>
    </motion.section>
  );
}

export default RedFlagAlertCard;
