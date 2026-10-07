"use client";

import React, { createContext, useCallback, useContext, useMemo, useState } from "react";

import { useClinicalQueueRealtime } from "@/hooks/queries/use-clinical-hitl";
import type { ClinicalSocketStatus } from "@/lib/realtime/useClinicalSocket";

/**
 * ============================================================================
 * [CLINICAL REALTIME] MỘT KÊNH DUY NHẤT CHO CẢ TRẠM TRỰC
 * ============================================================================
 * Kênh được mở ở cấp workspace, không phải trong màn hình chi tiết ca. Nhờ vậy
 * nhân viên nhận được việc dù đang ở hàng đợi, đang mở một ca khác hay đang xem
 * bất kỳ màn hình nào — không phải mở hồ sơ bệnh nhân trước.
 *
 * Đặt ở đây cũng đảm bảo mỗi tab chỉ giữ **một** kết nối: thanh điều phối, hộp
 * thư và hàng đợi đều đọc chung trạng thái này thay vì tự mở socket riêng.
 */

interface ClinicalRealtimeValue {
  status: ClinicalSocketStatus;
  /** Case vừa được yêu cầu mở nhanh hội thoại, do hộp thư hoặc toast đặt. */
  quickChatCaseId: string | null;
  openQuickChat: (caseId: string) => void;
  closeQuickChat: () => void;
}

const ClinicalRealtimeContext = createContext<ClinicalRealtimeValue>({
  status: "closed",
  quickChatCaseId: null,
  openQuickChat: () => {},
  closeQuickChat: () => {},
});

export function useClinicalRealtime(): ClinicalRealtimeValue {
  return useContext(ClinicalRealtimeContext);
}

export function ClinicalRealtimeProvider({ children }: { children: React.ReactNode }) {
  const [quickChatCaseId, setQuickChatCaseId] = useState<string | null>(null);

  const openQuickChat = useCallback((caseId: string) => setQuickChatCaseId(caseId), []);
  const closeQuickChat = useCallback(() => setQuickChatCaseId(null), []);

  const status = useClinicalQueueRealtime();

  const value = useMemo(
    () => ({ status, quickChatCaseId, openQuickChat, closeQuickChat }),
    [status, quickChatCaseId, openQuickChat, closeQuickChat],
  );

  return (
    <ClinicalRealtimeContext.Provider value={value}>{children}</ClinicalRealtimeContext.Provider>
  );
}

export default ClinicalRealtimeProvider;
