import type { ReactNode } from "react";

import { AuthEmergencyStrip } from "@/components/auth/auth-emergency-strip";
import { AuthSidePanel } from "@/components/auth/auth-side-panel";
import { cardEnter } from "@/components/auth/auth-styles";
import { GuestGuard } from "@/components/auth/guest-guard";

interface AuthLayoutProps {
  children: ReactNode;
}

/**
 * Khung chung của đăng nhập, đăng ký, xác minh mã, quên mật khẩu và OAuth
 * callback. Thẻ biểu mẫu nổi lên khi tải trang (CSS, chạy cả trước khi
 * hydrate). Trên màn hình rộng có thêm một bảng thông tin tĩnh -- chỉ nêu
 * điều đúng với sản phẩm.
 *
 * Dải gọi 115 nằm chung khối với bảng thông tin: trên điện thoại bảng ẩn đi
 * nên dải nằm ngay dưới biểu mẫu; trên màn hình rộng dải nằm dưới bảng ở cột
 * trái, luôn thấy được mà không phải cuộn qua một biểu mẫu dài.
 *
 * Logo "AI Triage" không lặp lại ở đây: thanh điều hướng chung phía trên đã
 * hiển thị đúng bộ nhận diện đó trên mọi trang xác thực.
 */
export default function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <main className="flex flex-1 justify-center px-4 py-8 sm:px-6 sm:py-12 lg:items-center lg:px-8">
      {/* Lưới được kéo cao bằng màn hình; content-between đưa dải 115 xuống
          đáy màn hình điện thoại như bản thiết kế, từ sm trở lên thì cả khối
          nằm giữa theo chiều dọc. */}
      <div className="grid w-full max-w-5xl grid-cols-1 content-between gap-6 sm:content-center lg:grid-cols-[minmax(0,1fr)_minmax(0,28rem)] lg:items-center lg:gap-x-16">
        <div
          className="page-enter mx-auto w-full max-w-md sm:rounded-3xl sm:border sm:border-border sm:bg-card sm:p-8 sm:shadow-[0_16px_40px_-24px_rgb(15_23_42/0.22)] lg:max-w-none"
          style={cardEnter()}
        >
          <GuestGuard>{children}</GuestGuard>
        </div>

        <div className="mx-auto flex w-full max-w-md flex-col gap-6 lg:order-first lg:max-w-none">
          <AuthSidePanel />
          <AuthEmergencyStrip className="page-enter" style={cardEnter(3)} />
        </div>
      </div>
    </main>
  );
}
