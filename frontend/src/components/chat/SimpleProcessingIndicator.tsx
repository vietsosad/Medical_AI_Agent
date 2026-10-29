"use client";

import React, { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

import { AgentAvatar } from "@/components/chat/pilot/ChatBubbles";
import { DURATION, EASE_OUT, riseVariants } from "@/lib/motion";

/**
 * Trạng thái chờ giữa hai lượt hội thoại.
 *
 * `simple_agent` chạy một request/response chặn cho mỗi lượt (không có luồng
 * SSE/WebSocket báo pha như `AgentActivityCard` của production), nên không có
 * tín hiệu thật cho biết đang ở bước nào. Ba nhãn dưới đây mô tả trung thực
 * những việc một lượt thực sự làm (gọi công cụ Phase A, đối chiếu phác đồ
 * Phase B, ghi lại phiên) và xoay vòng theo đồng hồ -- KHÔNG được trình bày
 * như một thanh tiến trình có thật hay kèm phần trăm/thời gian còn lại.
 *
 * Về hình thức: dựng đúng khung một bong bóng trợ lý (avatar + bong bóng) với
 * ba chấm gõ phím, để lượt chờ trông như trợ lý đang soạn câu trả lời chứ
 * không phải hệ thống bị treo.
 */

const STAGES = [
  "Đang đọc câu trả lời của bạn",
  "Đang đối chiếu với tiêu chí phác đồ",
  "Đang cập nhật thông tin phiên khám",
] as const;

const STAGE_INTERVAL_MS = 2200;

export function SimpleProcessingIndicator() {
  const [stageIndex, setStageIndex] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setStageIndex((i) => (i + 1) % STAGES.length);
    }, STAGE_INTERVAL_MS);
    return () => clearInterval(id);
  }, []);

  return (
    <motion.li
      variants={riseVariants}
      initial="hidden"
      animate="visible"
      role="status"
      aria-live="polite"
      aria-label="Trợ lý sàng lọc đang xử lý câu trả lời của bạn"
      className="flex items-start gap-2 sm:gap-4"
    >
      <AgentAvatar />
      <div className="flex min-w-0 flex-col gap-2">
        <span className="flex h-11 w-fit items-center gap-2 rounded-2xl rounded-tl-md bg-muted px-4" aria-hidden="true">
          {[0, 1, 2].map((dot) => (
            <span
              key={dot}
              className="typing-dot size-2 rounded-full bg-muted-foreground"
              style={{ animationDelay: `${dot * 150}ms` }}
            />
          ))}
        </span>
        <span className="relative h-6 overflow-hidden text-sm text-muted-foreground">
          <AnimatePresence mode="wait" initial={false}>
            <motion.span
              key={stageIndex}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: DURATION.quick, ease: EASE_OUT }}
              className="block"
            >
              {STAGES[stageIndex]}
            </motion.span>
          </AnimatePresence>
        </span>
      </div>
    </motion.li>
  );
}
