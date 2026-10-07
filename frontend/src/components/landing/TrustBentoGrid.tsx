"use client";

import React, { useState } from "react";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import {
  ShieldCheck,
  Database,
  CheckCircle2,
  RefreshCw,
  Scale,
  FileText,
  UserRoundCheck,
  Search,
  HelpCircle,
} from "lucide-react";

/**
 * KHỐI CAM KẾT AN TOÀN -- QUY TẮC NỘI DUNG
 *
 * Chỉ được nêu ở đây những hành vi có thể chỉ thẳng ra trong mã nguồn:
 *
 * - "Thiếu căn cứ thì không kết luận": src/simple_agent/pg_corpus.py chặn
 *   khởi động khi kho phác đồ trống, và lượt kết thúc RETURN_INCOMPLETE trả
 *   về đúng thông điệp chưa đủ dữ liệu thay vì một mức ESI tự nghĩ ra.
 * - "Đối chiếu tất định": decision.py evaluate_atoms/atom_status so khớp
 *   từng tiêu chí bằng toán tử (EQ/GT/GTE/...), không nhờ mô hình phán đoán.
 * - "Trích dẫn kèm theo": sbar.py _citation_entries trả về đúng atom đã thỏa
 *   cùng danh sách satisfied_requirements (giá trị mong đợi vs giá trị bệnh
 *   nhân khai báo).
 * - Các con số kho dữ liệu là số bản ghi thật trong các bảng simple_agent_*.
 *
 * TUYỆT ĐỐI KHÔNG thêm lại: chỉ số độ trễ (ms), % độ chính xác, FPS, hay
 * nhãn tuân thủ HIPAA/ISO khi chưa có phép đo và chứng nhận thật.
 */

const KNOWLEDGE_BASE_STATS = [
  { value: "1.768", label: "Tiêu chí phác đồ có thể đối chiếu" },
  { value: "1.314", label: "Tài liệu phác đồ ESI trong kho" },
  { value: "1.132", label: "Khái niệm lâm sàng đã chuẩn hóa" },
  { value: "243", label: "Trường dữ kiện lâm sàng được hỏi" },
] as const;

const EVIDENCE_GATE_FEATURES = [
  "Chỉ kết luận khi truy xuất được phác đồ làm căn cứ",
  "Nêu rõ tiêu chí nào đã thỏa và bạn khai báo giá trị gì",
  "Toàn bộ hội thoại được lưu lại để nhân viên y tế rà soát",
] as const;

export const TrustBentoGrid: React.FC = () => {
  // Hai kết cục có thật của một lượt kết thúc trong src/simple_agent:
  // RETURN_MATCH (đủ căn cứ) và RETURN_INCOMPLETE (chưa đủ dữ kiện).
  const [outcome, setOutcome] = useState<"matched" | "incomplete">("matched");

  return (
    <section
      id="an-toan-lam-sang"
      className="scroll-mt-24 py-20 bg-slate-100 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-sky-100 dark:bg-sky-950/80 text-sky-800 dark:text-sky-300 font-mono font-bold text-sm mb-4 border border-sky-300 dark:border-sky-800">
            <ShieldCheck className="w-4 h-4 text-sky-600 dark:text-sky-400 stroke-[2.2]" />
            <span>NGUYÊN TẮC AN TOÀN LÂM SÀNG</span>
          </div>
          <h2 className="font-heading text-3xl sm:text-4xl lg:text-5xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Thà Nói Chưa Đủ Dữ Liệu <br className="hidden sm:inline" />
            <span className="text-sky-600 dark:text-sky-400">Còn Hơn Đoán Một Mức ESI</span>
          </h2>
          <p className="mt-4 text-base sm:text-lg font-medium text-slate-600 dark:text-slate-300 leading-relaxed">
            Kết luận sàng lọc được rút ra bằng cách đối chiếu dữ kiện bạn cung cấp với tiêu chí phác đồ,
            không phải bằng phán đoán tự do của mô hình ngôn ngữ.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">

          {/* THẺ 1: CỔNG KIỂM CHỨNG BẰNG CHỨNG */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="glow-frame glow-sky flex flex-col justify-between bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 sm:p-8 shadow-sm hover:shadow-lg hover:border-sky-400/60 hover:-translate-y-1 motion-reduce:hover:translate-y-0 transition-[transform,box-shadow,border-color] duration-300 ease-out"
          >
            <div className="relative z-10">
              <div className="flex items-center justify-between gap-3 mb-6">
                <div className="w-14 h-14 rounded-2xl bg-sky-50 dark:bg-sky-950/60 border border-sky-200 dark:border-sky-800 flex items-center justify-center text-sky-600 dark:text-sky-400 shrink-0">
                  <ShieldCheck className="w-8 h-8 stroke-[2.2]" />
                </div>
                <span className="px-3 py-1 rounded-lg bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300 font-mono font-bold text-sm border border-emerald-300 dark:border-emerald-800 flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>Có căn cứ</span>
                </span>
              </div>

              <h3 className="font-heading text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight mb-3">
                Không Có Phác Đồ Thì Không Kết Luận
              </h3>
              <p className="text-base font-medium text-slate-600 dark:text-slate-300 leading-relaxed">
                Khi không truy xuất được phác đồ phù hợp làm căn cứ, hệ thống trả lời thẳng rằng chưa đủ
                dữ liệu để phân loại. Đây là hành vi cố ý được thiết kế sẵn, không phải lỗi.
              </p>

              <div className="mt-6 space-y-3 pt-6 border-t border-slate-100 dark:border-slate-800/80 text-sm font-semibold text-slate-700 dark:text-slate-200">
                {EVIDENCE_GATE_FEATURES.map((feature) => (
                  <div key={feature} className="flex items-start gap-2.5">
                    <div className="w-2 h-2 rounded-full bg-sky-500 shrink-0 mt-1.5" />
                    <span className="leading-relaxed">{feature}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-8 relative z-10 overflow-hidden rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 flex items-center justify-center h-48 sm:h-56">
              <Image
                src="/IMG-02.png"
                alt="Biểu tượng khiên bảo vệ an toàn dữ liệu lâm sàng"
                width={300}
                height={300}
                className="w-auto h-full max-h-44 object-contain"
              />
            </div>
          </motion.div>

          {/* THẺ 2: HAI KẾT CỤC CÓ THẬT CỦA MỘT PHIÊN */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1, ease: "easeOut" }}
            className="glow-frame glow-sky flex flex-col justify-between rounded-2xl p-6 sm:p-8 bg-slate-900 border border-slate-800 text-white shadow-md hover:shadow-xl hover:border-sky-700 hover:-translate-y-1 motion-reduce:hover:translate-y-0 transition-[transform,box-shadow,border-color] duration-300 ease-out"
          >
            <div className="relative z-10">
              <div className="flex items-center justify-between gap-3 mb-6">
                <div className="w-14 h-14 rounded-2xl bg-slate-800 border border-slate-700 text-sky-400 flex items-center justify-center shrink-0">
                  <Scale className="w-8 h-8 stroke-[2.2]" />
                </div>
                <span className="px-3 py-1 rounded-lg bg-sky-950/80 text-sky-300 border border-sky-800 font-mono font-bold text-sm">
                  Tất định
                </span>
              </div>

              <h3 className="font-heading text-2xl font-extrabold tracking-tight mb-3">
                Đối Chiếu Từng Tiêu Chí, Không Phán Đoán
              </h3>
              <p className="text-base font-medium leading-relaxed text-slate-300">
                Mỗi tiêu chí phác đồ được so khớp bằng phép so sánh tường minh trên dữ kiện đã thu thập.
                Cùng một bộ dữ kiện luôn cho ra cùng một kết luận.
              </p>

              <div className="mt-6 pt-5 border-t border-slate-800">
                <div className="text-xs font-mono font-bold text-slate-400 uppercase tracking-wider mb-3">
                  Hai kết cục có thể xảy ra
                </div>

                <div className="grid grid-cols-2 gap-2 mb-4">
                  <button
                    type="button"
                    onClick={() => setOutcome("matched")}
                    aria-pressed={outcome === "matched"}
                    className={`glow-soft glow-sky min-h-11 rounded-xl px-3 text-sm font-bold ${
                      outcome === "matched"
                        ? "bg-sky-600 text-white"
                        : "bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-700"
                    }`}
                  >
                    Đủ căn cứ
                  </button>
                  <button
                    type="button"
                    onClick={() => setOutcome("incomplete")}
                    aria-pressed={outcome === "incomplete"}
                    className={`min-h-11 rounded-xl px-3 text-sm font-bold transition-colors ${
                      outcome === "incomplete"
                        ? "bg-amber-600 text-white"
                        : "bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-700"
                    }`}
                  >
                    Chưa đủ dữ liệu
                  </button>
                </div>

                <AnimatePresence mode="wait">
                  {outcome === "matched" ? (
                    <motion.div
                      key="matched"
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -8 }}
                      transition={{ duration: 0.2 }}
                      className="rounded-xl border border-sky-700/70 bg-sky-950/60 p-4"
                    >
                      <div className="flex items-center gap-2 text-sky-200 font-bold text-sm mb-2">
                        <FileText className="w-4 h-4 shrink-0" aria-hidden="true" />
                        <span>Kết luận kèm trích dẫn phác đồ</span>
                      </div>
                      <p className="text-sm leading-relaxed text-slate-300">
                        Hệ thống nêu mức ESI đề xuất, kèm tiêu chí đã thỏa và giá trị bạn đã khai báo cho
                        từng tiêu chí đó.
                      </p>
                    </motion.div>
                  ) : (
                    <motion.div
                      key="incomplete"
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -8 }}
                      transition={{ duration: 0.2 }}
                      className="rounded-xl border border-amber-700/70 bg-amber-950/50 p-4"
                    >
                      <div className="flex items-center gap-2 text-amber-200 font-bold text-sm mb-2">
                        <HelpCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
                        <span>Nói rõ là chưa đủ dữ liệu</span>
                      </div>
                      <p className="text-sm leading-relaxed text-slate-300">
                        Không đủ căn cứ thì hệ thống dừng lại và nói rõ, thay vì đưa ra một mức ESI không
                        dựa trên phác đồ nào.
                      </p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>

            <div className="relative z-10 mt-6 pt-4 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setOutcome(outcome === "matched" ? "incomplete" : "matched")}
                className="glow-soft glow-sky group/swap w-full min-h-12 px-5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-600 text-slate-200 font-bold text-base flex items-center justify-center gap-2.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
              >
                <RefreshCw
                  className="w-5 h-5 text-sky-400 shrink-0 transition-transform duration-500 ease-out group-hover/swap:rotate-180 motion-reduce:group-hover/swap:rotate-0"
                  aria-hidden="true"
                />
                <span>Xem kết cục còn lại</span>
              </button>
            </div>
          </motion.div>

          {/* THẺ 3: KHO PHÁC ĐỒ & THẨM ĐỊNH BỞI NGƯỜI */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.2, ease: "easeOut" }}
            className="glow-frame glow-emerald flex flex-col justify-between bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 sm:p-8 shadow-sm hover:shadow-lg hover:border-emerald-400/60 hover:-translate-y-1 motion-reduce:hover:translate-y-0 transition-[transform,box-shadow,border-color] duration-300 ease-out"
          >
            <div className="relative z-10">
              <div className="flex items-center justify-between gap-3 mb-6">
                <div className="w-14 h-14 rounded-2xl bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 flex items-center justify-center text-emerald-600 dark:text-emerald-400 shrink-0">
                  <Database className="w-8 h-8 stroke-[2.2]" />
                </div>
                <span className="px-3 py-1 rounded-lg bg-sky-100 dark:bg-sky-950/80 text-sky-800 dark:text-sky-300 font-mono font-bold text-sm border border-sky-300 dark:border-sky-800 flex items-center gap-1.5">
                  <Search className="w-4 h-4 shrink-0" />
                  <span>Tìm kiếm ngữ nghĩa</span>
                </span>
              </div>

              <h3 className="font-heading text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight mb-3">
                Kho Phác Đồ Riêng &amp; Người Thẩm Định Cuối
              </h3>
              <p className="text-base font-medium text-slate-600 dark:text-slate-300 leading-relaxed">
                Câu chữ của bạn được đối chiếu ngữ nghĩa với kho phác đồ ESI đã được chuẩn hóa trong hệ
                thống. Kết quả sau đó chuyển sang điều dưỡng và bác sĩ để thẩm định.
              </p>

              <dl className="mt-6 pt-6 border-t border-slate-100 dark:border-slate-800/80 grid grid-cols-2 gap-3">
                {KNOWLEDGE_BASE_STATS.map((stat) => (
                  <div
                    key={stat.label}
                    className="p-3 bg-slate-50 dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800"
                  >
                    <dt className="sr-only">{stat.label}</dt>
                    <dd>
                      <div className="text-2xl font-black text-slate-900 dark:text-white font-heading">
                        {stat.value}
                      </div>
                      <div className="text-xs font-semibold text-slate-600 dark:text-slate-400 mt-1 leading-snug">
                        {stat.label}
                      </div>
                    </dd>
                  </div>
                ))}
              </dl>
            </div>

            <div className="relative z-10 mt-8 flex items-start gap-3 rounded-xl border border-emerald-200 dark:border-emerald-800/60 bg-emerald-50/70 dark:bg-emerald-950/40 p-4">
              <UserRoundCheck
                className="size-5 shrink-0 text-emerald-600 dark:text-emerald-400 stroke-[2.3] mt-0.5"
                aria-hidden="true"
              />
              <p className="text-sm font-semibold leading-relaxed text-emerald-950 dark:text-emerald-200">
                Không có kết quả nào trở thành chính thức nếu chưa qua tay nhân viên y tế. Điều dưỡng có
                thể giữ nguyên hoặc thay đổi mức ESI mà AI đề xuất.
              </p>
            </div>
          </motion.div>

        </div>

      </div>
    </section>
  );
};
