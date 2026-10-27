import { Activity } from "lucide-react";

import { AdminNotConnectedPanel } from "@/components/admin/AdminNotConnectedPanel";

/**
 * Tổng quan quản trị. Trang này chưa nối với dữ liệu thật nên không hiện chỉ
 * số nào -- xem `AdminNotConnectedPanel` cho lý do.
 */
export default function AdminDashboardPage() {
  return (
    <AdminNotConnectedPanel
      icon={Activity}
      title="Tổng quan hệ thống"
      summary="Trang quản trị chưa nối với dữ liệu thật, nên chưa có số liệu đo nào được hiển thị ở đây."
      facts={[
        "Số liệu đếm trực tiếp trên các ca đã sàng lọc -- phân bố mức ESI, thời gian chờ tiếp nhận, điều dưỡng giữ nguyên hay điều chỉnh đề xuất của AI -- nằm ở bảng số liệu của trạm điều dưỡng.",
        "Hệ thống chưa có nhãn chuẩn để đối chiếu, nên không có con số nào về độ chính xác của AI.",
      ]}
    />
  );
}
