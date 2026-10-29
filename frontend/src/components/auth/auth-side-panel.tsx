import { History, MessagesSquare, Stethoscope, type LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

import { cardEnter, enterDelay } from "./auth-styles";

interface ProductPoint {
  id: string;
  icon: LucideIcon;
  title: string;
  body: string;
}

/**
 * Chỉ nêu điều đúng với luồng bệnh nhân đang chạy (simple_agent), không có
 * chỉ số hay nhãn tuân thủ nào chưa được đo:
 * - hệ thống hỏi thêm từng câu trước khi gợi ý mức ESI;
 * - phiên đã hoàn tất vào hàng đợi của điều dưỡng, nơi mức cuối cùng được chốt;
 * - lịch sử, hồ sơ gia đình và kênh nhắn với nhân viên y tế có trong tài khoản.
 */
const PRODUCT_POINTS: readonly ProductPoint[] = [
  {
    id: "conversation",
    icon: MessagesSquare,
    title: "Kể triệu chứng bằng lời của bạn",
    body: "Hệ thống hỏi thêm từng câu ngắn để hiểu rõ tình trạng trước khi gợi ý mức độ khẩn cấp.",
  },
  {
    id: "nurse-review",
    icon: Stethoscope,
    title: "Mức độ khẩn cấp là gợi ý, không phải chẩn đoán",
    body: "Phiên sàng lọc đã hoàn tất được chuyển tới điều dưỡng để xem xét và chốt mức độ.",
  },
  {
    id: "account",
    icon: History,
    title: "Xem lại và nhắn với nhân viên y tế",
    body: "Lịch sử sàng lọc, hồ sơ sức khỏe gia đình và tin nhắn với nhân viên y tế nằm trong tài khoản của bạn.",
  },
];

/** Bảng thông tin bên cạnh biểu mẫu, chỉ hiện trên màn hình rộng. */
export function AuthSidePanel({ className }: { className?: string }) {
  return (
    <aside
      aria-labelledby="auth-side-panel-title"
      className={cn(
        "page-enter hidden flex-col gap-8 rounded-3xl border border-brand-edge bg-brand-soft p-10 lg:flex",
        className,
      )}
      style={cardEnter(1)}
    >
      {/* Ngắt dòng sau dấu phẩy để không tách đôi cụm "khẩn cấp". */}
      <h2
        id="auth-side-panel-title"
        className="text-2xl font-extrabold leading-tight tracking-tight text-foreground"
      >
        <span className="block">Sàng lọc mức độ khẩn cấp,</span>{" "}
        <span className="block">có điều dưỡng xem lại</span>
      </h2>

      <ul className="flex flex-col gap-6">
        {PRODUCT_POINTS.map((point, index) => {
          const Icon = point.icon;
          return (
            <li key={point.id} className="page-enter flex gap-4" style={enterDelay(index + 2)}>
              <span className="flex h-6 shrink-0 items-center text-brand">
                <Icon className="size-5" aria-hidden="true" />
              </span>
              <div className="flex flex-col gap-2">
                <p className="text-base font-semibold text-brand-ink">{point.title}</p>
                <p className="text-sm leading-relaxed text-brand-ink/80">{point.body}</p>
              </div>
            </li>
          );
        })}
      </ul>

      <p className="border-t border-brand-edge pt-6 text-sm font-medium text-brand-ink/80">
        Hỗ trợ sàng lọc, không thay thế chẩn đoán của bác sĩ.
      </p>
    </aside>
  );
}
