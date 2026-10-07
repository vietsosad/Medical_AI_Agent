import type { Metadata } from "next";
import { RoleHomeRedirect } from "@/components/auth/role-home-redirect";
import ClinicalLandingClient from "@/components/landing/ClinicalLandingClient";

// Metadata phải mô tả đúng năng lực thật của hệ thống. Không đặt lại các chỉ
// số hiệu năng chưa đo được (độ trễ mili-giây, % độ chính xác) hay nhãn tuân
// thủ chưa được cấp chứng nhận -- xem ghi chú đầu HeroSection.tsx.
const SHARED_DESCRIPTION =
  "Hệ thống sàng lọc mức độ khẩn cấp theo thang ESI 5 cấp: hỏi từng dữ kiện lâm sàng cần thiết, đối chiếu với phác đồ và luôn kèm trích dẫn. Chưa đủ căn cứ thì báo rõ thay vì suy diễn, và kết quả chỉ chính thức sau khi nhân viên y tế thẩm định.";

export const metadata: Metadata = {
  title: "AI20K Clinical Triage Engine | Sàng Lọc Lâm Sàng ESI Có Trích Dẫn Phác Đồ",
  description: SHARED_DESCRIPTION,
  keywords: [
    "Clinical AI",
    "Sàng lọc lâm sàng",
    "Phân loại ESI",
    "ESI 5 cấp",
    "RAG phác đồ y khoa",
    "Human-in-the-Loop",
    "Thẩm định điều dưỡng",
    "SBAR",
  ],
  authors: [{ name: "AI20K Clinical Engineering Team" }],
  openGraph: {
    title: "AI20K Clinical Triage Engine | Sàng Lọc Lâm Sàng Có Trích Dẫn",
    description: SHARED_DESCRIPTION,
    type: "website",
    locale: "vi_VN",
    siteName: "AI20K Clinical Triage System",
  },
  twitter: {
    card: "summary_large_image",
    title: "AI20K Clinical Triage Engine | Sàng Lọc Lâm Sàng ESI",
    description:
      "Mỗi mức ESI đề xuất đều kèm tiêu chí phác đồ đã thỏa, và phải qua thẩm định của nhân viên y tế trước khi thành chính thức.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function LandingPage() {
  return (
    <RoleHomeRedirect>
      <ClinicalLandingClient />
    </RoleHomeRedirect>
  );
}
