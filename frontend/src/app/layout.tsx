import type { Metadata } from "next";
import { Be_Vietnam_Pro } from "next/font/google";
import "./globals.css";
import { MotionProvider } from "@/components/motion/MotionProvider";
import { QueryProvider } from "@/components/providers/query-provider";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { ClinicalNavbar } from "@/components/shared/ClinicalNavbar";
import { themeBootstrapScript } from "@/lib/theme";

export const metadata: Metadata = {
  title: "AI20K Clinical Triage Engine | Sàng Lọc Lâm Sàng & Thẩm Định Y Khoa",
  description:
    "Hệ thống sàng lọc lâm sàng theo thang ESI 5 cấp: đối chiếu dữ kiện người bệnh với phác đồ, luôn kèm trích dẫn và có nhân viên y tế thẩm định trước khi chốt.",
};

// Be Vietnam Pro được vẽ riêng cho tiếng Việt: dấu thanh và dấu mũ chồng nhau
// (ệ, ổ, ữ) vẫn tách bạch ở cỡ chữ nhỏ, điều Inter không bảo đảm.
const beVietnamPro = Be_Vietnam_Pro({
  subsets: ["latin", "vietnamese"],
  weight: ["400", "500", "600", "700", "800"],
  display: "swap",
  variable: "--font-be-vietnam",
});

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="vi"
      // Đoạn mã nội tuyến bên dưới sửa class và style của chính thẻ này trước
      // khi React hydrate, nên React sẽ thấy thuộc tính khác với HTML do máy
      // chủ sinh ra. Đây là sai lệch có chủ đích và chỉ nằm ở thẻ <html>.
      suppressHydrationWarning
      // Dùng token thay vì màu cố định: `bg-background`/`text-foreground` lấy
      // giá trị từ :root ở chế độ sáng và từ .dark ở chế độ tối, nên nền trang
      // luôn khớp đúng với nền mà các thẻ con đang dùng.
      className={`${beVietnamPro.variable} h-full bg-background font-sans text-foreground antialiased`}
    >
      <head>
        {/*
          Chạy TRƯỚC khung hình đầu tiên. Không có nó, người dùng đang ở chế độ
          tối sẽ bị một cú chớp trắng: trang vẽ ở chế độ sáng rồi mới nhảy sang
          tối khi React hydrate xong. Nội dung đoạn mã được sinh từ chính các
          hằng số trong @/lib/theme nên không thể lệch với phần còn lại.
        */}
        <script dangerouslySetInnerHTML={{ __html: themeBootstrapScript() }} />
      </head>
      <body className="min-h-full flex flex-col font-sans antialiased selection:bg-slate-200 selection:text-slate-900 dark:selection:bg-slate-700 dark:selection:text-white">
        <ThemeProvider>
          <QueryProvider>
            <MotionProvider>
              <ClinicalNavbar />
              <div className="flex-1 flex flex-col">{children}</div>
            </MotionProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
