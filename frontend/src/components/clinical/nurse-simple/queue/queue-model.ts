/**
 * Mô hình dùng chung của bảng điều phối Triage Agent: các góc nhìn (tab), quy
 * tắc mức khẩn và màu chữ phụ trợ. Màu chip ESI lấy thẳng từ `esi-theme.ts`
 * (đã có bản tối) để mọi màn hình tô một mức độ bằng cùng một màu.
 *
 * Không có gì ở đây gọi mạng hay giữ state -- chỉ là quy tắc thuần, để hàng
 * đợi, thanh điều phối và cảnh báo toàn cục đọc cùng một định nghĩa.
 */
import type {
  SimpleNurseQueueBucket,
  SimpleNurseQueueItemDTO,
  SimpleNurseQueueParams,
} from "@/types/simple-nurse";
import { WAIT_CRITICAL_MINUTES, WAIT_WARNING_MINUTES, formatWait } from "@/components/clinical/nurse-simple/wait-time";

export const QUEUE_PAGE_SIZE = 20;

/**
 * Lời gọi mặc định của màn hàng đợi (tab "Đang chờ", chưa lọc, trang 1). Thanh
 * điều phối và bộ đếm của màn hàng đợi dùng đúng bộ tham số này, nên TanStack
 * Query gộp chúng thành một request duy nhất thay vì mỗi nơi tự gọi một lần.
 */
export const SHARED_QUEUE_PARAMS: SimpleNurseQueueParams = {
  bucket: "QUEUE",
  mineOnly: false,
  page: 1,
  pageSize: QUEUE_PAGE_SIZE,
};

/** Như trên, cho mục "Tạm gác" -- trùng khóa với lời gọi mặc định của tab đó. */
export const SHARED_PARKED_PARAMS: SimpleNurseQueueParams = {
  bucket: "PARKED",
  mineOnly: false,
  page: 1,
  pageSize: QUEUE_PAGE_SIZE,
};

/** Giá trị của `?tab=` -- giữ nguyên vì thanh điều phối và các màn khác trỏ vào đây. */
export type QueueTab = "queue" | "mine" | "parked" | "decided";

/** Ba nhóm ca trên thanh chọn; "mine" là nhóm "queue" có bật "Chỉ ca của tôi". */
export type QueueBucketKey = "queue" | "parked" | "decided";

export interface QueueView {
  tab: QueueTab;
  bucketKey: QueueBucketKey;
  bucket: SimpleNurseQueueBucket;
  mineOnly: boolean;
  description: string;
}

const URGENCY_ORDER = "khẩn nhất ở trên: dấu hiệu nguy kịch và ESI 1 trước, rồi theo mức ESI và thời gian chờ.";

export const QUEUE_VIEWS: Record<QueueTab, QueueView> = {
  queue: {
    tab: "queue",
    bucketKey: "queue",
    bucket: "QUEUE",
    mineOnly: false,
    description: `Ca chưa ai nhận, ${URGENCY_ORDER}`,
  },
  mine: {
    tab: "mine",
    bucketKey: "queue",
    bucket: "QUEUE",
    mineOnly: true,
    description: `Ca bạn đang phụ trách, ${URGENCY_ORDER}`,
  },
  parked: {
    tab: "parked",
    bucketKey: "parked",
    bucket: "PARKED",
    mineOnly: false,
    description: "Ca đã tạm gác, chờ bổ sung thông tin trước khi xử lý tiếp. Ca khẩn nhất ở trên.",
  },
  decided: {
    tab: "decided",
    bucketKey: "decided",
    bucket: "DECIDED",
    mineOnly: false,
    description: "Ca đã có quyết định phân luồng cuối cùng, ca chốt gần nhất ở trên.",
  },
};

export function parseQueueTab(value: string | null): QueueTab {
  return value === "mine" || value === "parked" || value === "decided" ? value : "queue";
}

/**
 * Hạng khẩn của một ca, cùng quy tắc với backend (`_urgency_rank` trong
 * `routes_nurse_simple.py`): ca bị sàng lọc cấp cứu gắn cờ xếp ngang ESI 1,
 * ca chưa có ESI xếp cuối. Cờ là lý do để xem ngay, không phải một mức ESI.
 */
export function urgencyRank(item: SimpleNurseQueueItemDTO): number {
  const rank = item.ai_proposed_esi ?? 6;
  return item.attention_required ? Math.min(rank, 1) : rank;
}

/** Hạng 1: hồi sức hoặc đang bị gắn cờ "Cần xem ngay". */
export function isCriticalCase(item: SimpleNurseQueueItemDTO): boolean {
  return urgencyRank(item) === 1;
}

/** Hạng 1-2: đủ khẩn để thanh điều phối báo bằng màu đỏ. */
export function isUrgentCase(item: SimpleNurseQueueItemDTO): boolean {
  return urgencyRank(item) <= 2;
}

/** "Nguyễn Minh Anh" -> "MA": hai chữ đầu của tên gọi, cách người Việt viết tắt. */
export function initialsOf(name: string | null | undefined): string {
  const words = (name ?? "").trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "?";
  const picked = words.length === 1 ? words : words.slice(-2);
  return picked.map((word) => word.charAt(0).toLocaleUpperCase("vi")).join("");
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "";
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return "";
  return parsed.toLocaleString("vi-VN", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

/** "Chờ dưới 1 phút" / "Chờ 45 phút" -- `formatWait` viết hoa chữ đầu cho câu đứng riêng. */
export function waitLabel(minutes: number): string {
  const text = formatWait(minutes);
  return `Chờ ${text.charAt(0).toLocaleLowerCase("vi")}${text.slice(1)}`;
}

/** Màu chữ của thời gian chờ, cắt ở đúng hai mốc của `wait-time.ts`. */
export function waitTone(minutes: number): string {
  if (minutes >= WAIT_CRITICAL_MINUTES) return "text-rose-700 dark:text-rose-300";
  if (minutes >= WAIT_WARNING_MINUTES) return "text-amber-700 dark:text-amber-300";
  return "text-slate-600 dark:text-slate-300";
}

/**
 * Màu chữ theo mức ESI cho dòng "Cấp cứu · AI đề xuất". Cùng sắc với
 * `esi-theme.ts`, đậm hơn một bậc để chữ nhỏ vẫn đạt tương phản AA.
 */
const ESI_INK: Record<number, string> = {
  1: "text-rose-800 dark:text-rose-300",
  2: "text-orange-800 dark:text-orange-300",
  3: "text-amber-800 dark:text-amber-300",
  4: "text-emerald-800 dark:text-emerald-300",
  5: "text-sky-800 dark:text-sky-300",
};

export function esiInk(esi: number | null | undefined): string {
  return (esi && ESI_INK[esi]) || "text-slate-600 dark:text-slate-300";
}
