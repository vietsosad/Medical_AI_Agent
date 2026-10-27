import { ShieldCheck } from "lucide-react";

import { AdminNotConnectedPanel } from "@/components/admin/AdminNotConnectedPanel";

/**
 * Lớp an toàn. Các lớp này nằm trong mã nguồn, không chỉnh được từ giao diện,
 * nên trang chỉ mô tả chúng -- xem `AdminNotConnectedPanel`.
 */
export default function AdminGuardrailsPage() {
  return (
    <AdminNotConnectedPanel
      icon={ShieldCheck}
      title="Lớp an toàn của Triage Agent"
      summary="Các lớp an toàn được cài đặt trong mã nguồn và không chỉnh được từ giao diện này."
      facts={[
        "Câu dò hỏi system prompt bị chặn bằng luật tất định trước mọi lời gọi mô hình.",
        "Lời người bệnh được sàng lọc dấu hiệu nguy kịch bằng luật tất định trước mọi lời gọi mô hình. Khi phát hiện, màn hình hiện nút gọi 115 và ca được đưa lên hàng đợi điều dưỡng; sàng lọc này không tự gán mức ESI.",
        "Câu trả lời gửi người bệnh đi qua bộ lọc tất định chặn khẳng định chẩn đoán và kê đơn thuốc.",
        "Mức ESI do mã nguồn đối chiếu với tiêu chí phác đồ quyết định, không do mô hình ngôn ngữ tự chọn.",
        "Không truy xuất được tiêu chí phác đồ làm căn cứ thì hệ thống trả lời là chưa đủ dữ liệu, không đoán một mức ESI.",
        "Mọi kết quả của AI chỉ là đề xuất, chờ điều dưỡng thẩm định.",
      ]}
    />
  );
}
