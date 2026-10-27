import { Database } from "lucide-react";

import { AdminNotConnectedPanel } from "@/components/admin/AdminNotConnectedPanel";

/** Kho phác đồ. Chưa đọc trạng thái kho từ máy chủ -- xem `AdminNotConnectedPanel`. */
export default function AdminRagDatabasePage() {
  return (
    <AdminNotConnectedPanel
      icon={Database}
      title="Kho phác đồ"
      summary="Trang này chưa đọc trạng thái kho phác đồ từ máy chủ, và không có thao tác dựng lại chỉ mục nào ở đây."
      facts={[
        "Kho phác đồ nằm trong PostgreSQL, ở các bảng simple_agent_*, được nạp từ gói migration trong repo.",
        "Truy xuất dùng vector text-embedding-3-small (1536 chiều) lưu cùng các bảng đó.",
        "Máy chủ từ chối khởi động Triage Agent nếu các bảng kho phác đồ trống, thay vì chạy với kho rỗng.",
      ]}
    />
  );
}
