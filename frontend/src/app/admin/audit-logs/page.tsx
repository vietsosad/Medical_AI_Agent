import { FileText } from "lucide-react";

import { AdminNotConnectedPanel } from "@/components/admin/AdminNotConnectedPanel";

/** Nhật ký kiểm toán. Chưa có màn hình đọc nhật ký thật -- xem `AdminNotConnectedPanel`. */
export default function AdminAuditLogsPage() {
  return (
    <AdminNotConnectedPanel
      icon={FileText}
      title="Nhật ký kiểm toán"
      summary="Chưa có màn hình đọc nhật ký kiểm toán thật, nên trang này không hiển thị sự kiện nào."
      facts={[
        "Quyết định của điều dưỡng -- giữ nguyên hay điều chỉnh mức ESI, kèm lý do bắt buộc khi điều chỉnh -- được lưu cùng hồ sơ ca và hiển thị ở màn thẩm định ca.",
      ]}
    />
  );
}
