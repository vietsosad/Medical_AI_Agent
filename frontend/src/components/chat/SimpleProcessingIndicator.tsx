"use client";

import React, { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { Bot, ClipboardCheck, MessagesSquare, Scale } from "lucide-react";

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
 * Về hình thức: khối này cố ý dựng đúng khung của một bong bóng trợ lý
 * (avatar bên trái + bong bóng bo góc) thay vì một hộp thông báo rời, để lượt
 * chờ trông như trợ lý đang soạn câu trả lời chứ không phải hệ thống bị treo.
 */

const STAGES = [
  { icon: MessagesSquare, label: "Đang đọc câu trả lời của bạn" },
  { icon: Scale, label: "Đang đối chiếu với tiêu chí phác đồ" },
  { icon: ClipboardCheck, label: "Đang cập nhật thông tin phiên khám" },
] as const;

const STAGE_INTERVAL_MS = 2200;

export function SimpleProcessingIndicator() {
  const [stageIndex, setStageIndex] = useState(0);
  const shouldReduceMotion = useReducedMotion();

  useEffect(() => {
    const id = setInterval(() => {
      setStageIndex((i) => (i + 1) % STAGES.length);
    }, STAGE_INTERVAL_MS);
    return () => clearInterval(id);
  }, []);

  const stage = STAGES[stageIndex];
  const StageIcon = stage.icon;

  return (
    <motion.div
      role="status"
      aria-live="polite"
      aria-label="Trợ lý sàng lọc đang xử lý câu trả lời của bạn"
      initial={shouldReduceMotion ? false : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: shouldReduceMotion ? 0 : 0.25, ease: "easeOut" }}
      className="my-4 flex w-full min-w-0 justify-start gap-4 font-sans"
    >
      {/* Avatar khớp với MessageItem để lượt chờ nằm đúng mạch hội thoại */}
      <div className="flex shrink-0 flex-col items-center">
        <span className="relative flex size-14 items-center justify-center rounded-2xl border border-sky-200/80 bg-gradient-to-br from-sky-50 to-white text-sky-700 shadow-xs dark:border-sky-800 dark:from-sky-950 dark:to-zinc-900 dark:text-sky-300">
          <Bot className="size-6" aria-hidden="true" />
          {!shouldReduceMotion && (
            <motion.span
              aria-hidden="true"
              className="absolute inset-0 rounded-2xl border-2 border-sky-400/50"
              animate={{ opacity: [0.15, 0.6, 0.15], scale: [1, 1.06, 1] }}
              transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
            />
          )}
        </span>
        <span className="mt-2 text-sm font-bold text-slate-500 dark:text-slate-400">AI Triage</span>
      </div>

      <div className="flex min-w-0 max-w-3xl flex-col gap-3 rounded-3xl rounded-tl-sm border border-slate-200/90 bg-white px-5 py-4 shadow-xs dark:border-slate-800 dark:bg-zinc-900">
        {/* Ba chấm gõ phím -- tín hiệu quen thuộc rằng phía kia đang soạn trả lời */}
        <div className="flex items-center gap-1.5" aria-hidden="true">
          {[0, 1, 2].map((dot) => (
            <motion.span
              key={dot}
              className="size-2.5 rounded-full bg-sky-500"
              animate={shouldReduceMotion ? undefined : { opacity: [0.25, 1, 0.25], y: [0, -3, 0] }}
              transition={{
                duration: 1.1,
                repeat: Infinity,
                ease: "easeInOut",
                delay: dot * 0.16,
              }}
            />
          ))}
        </div>

        <motion.p
          key={stage.label}
          initial={shouldReduceMotion ? false : { opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, ease: "easeOut" }}
          className="flex items-center gap-2.5 text-base font-semibold text-slate-700 dark:text-slate-200"
        >
          <StageIcon className="size-4.5 shrink-0 text-sky-600 dark:text-sky-400" aria-hidden="true" />
          <span>{stage.label}</span>
        </motion.p>
      </div>
    </motion.div>
  );
}
