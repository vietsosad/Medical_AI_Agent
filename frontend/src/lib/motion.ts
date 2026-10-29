/**
 * Quy chuẩn chuyển động dùng chung (bản thiết kế "Quy chuẩn chuyển động").
 *
 * Mỗi hoạt ảnh phải trả lời một câu hỏi của người dùng: cái gì vừa thay đổi,
 * hệ thống có đang nghe không, hay việc gì cần làm ngay. Không nảy, không đàn
 * hồi. Các giá trị ở đây khớp với keyframes trong globals.css (bản CSS dùng
 * cho phần phải chạy trước khi hydrate).
 *
 * Giảm chuyển động do MotionProvider lo (`reducedMotion="user"`): khi hệ điều
 * hành bật tùy chọn này, framer-motion bỏ mọi dịch chuyển, chỉ giữ độ mờ.
 */
import type { Transition, Variants } from "framer-motion";

/** Giây, vì framer-motion nhận giây. */
export const DURATION = {
  /** Phản hồi khi nhấn. */
  press: 0.12,
  /** Di chuột, bật tắt, đổi tab. */
  quick: 0.18,
  /** Tin nhắn, chip, chuyển trang. */
  base: 0.28,
  /** Thẻ, cảnh báo, kết quả. */
  gentle: 0.42,
  /** Biểu đồ mọc lên. */
  slow: 0.7,
} as const;

/** Vào: nhanh lúc đầu, đáp nhẹ ở cuối. */
export const EASE_OUT = [0.22, 1, 0.36, 1] as const;
/** Dời chỗ: sắp xếp lại hàng đợi, đổi bố cục. */
export const EASE_IN_OUT = [0.65, 0, 0.35, 1] as const;
/** Ra: ngắn hơn lúc vào, không níu mắt người dùng. */
export const EASE_IN = [0.4, 0, 1, 1] as const;

/** Khoảng cách giữa các phần tử vào lần lượt. Quá 6 phần tử thì phần còn lại
 * vào cùng lúc -- danh sách dài không được bắt người dùng chờ. */
export const STAGGER_SECONDS = 0.05;
export const MAX_STAGGERED_ITEMS = 6;

export function staggerDelay(index: number, base = 0): number {
  return base + Math.min(index, MAX_STAGGERED_ITEMS) * STAGGER_SECONDS;
}

export const enterTransition: Transition = { duration: DURATION.base, ease: EASE_OUT };
export const exitTransition: Transition = { duration: DURATION.base * 0.75, ease: EASE_IN };
export const layoutTransition: Transition = { duration: DURATION.base, ease: EASE_IN_OUT };

/** Nổi lên 8 px rồi rõ dần -- tin nhắn, thẻ, mục danh sách. */
export const riseVariants: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0, transition: enterTransition },
  exit: { opacity: 0, transition: exitTransition },
};

/** Cảnh báo trượt xuống từ trên. */
export const dropVariants: Variants = {
  hidden: { opacity: 0, y: -12 },
  visible: { opacity: 1, y: 0, transition: { duration: DURATION.gentle, ease: EASE_OUT } },
  exit: { opacity: 0, transition: exitTransition },
};

/** Mức ESI bật vào sau khi thẻ kết quả đã lên. */
export const popVariants: Variants = {
  hidden: { opacity: 0, scale: 0.6 },
  visible: { opacity: 1, scale: 1, transition: { duration: DURATION.base, ease: EASE_OUT } },
};
