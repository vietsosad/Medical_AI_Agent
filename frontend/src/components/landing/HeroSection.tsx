"use client";

import React from "react";
import Link from "next/link";
import { patientEntryHref } from "@/lib/auth-routing";
import { useAuthStore } from "@/store/useAuthStore";
import Image from "next/image";
import { motion } from "framer-motion";
import {
  Siren,
  Stethoscope,
  Sparkles,
  ShieldCheck,
  ArrowRight,
  HeartPulse,
  CheckCircle2,
  FileText,
  MessagesSquare,
  Scale,
  UserRoundCheck,
} from "lucide-react";

/**
 * Mọi con số và tuyên bố trong khối này phải kiểm chứng được từ chính hệ
 * thống. Không đặt lại các chỉ số hiệu năng (độ trễ mili-giây, % độ chính
 * xác, FPS) hay nhãn tuân thủ (HIPAA/ISO) khi chưa có phép đo và chứng nhận
 * thật -- đây là sản phẩm y tế, một câu quảng cáo sai là một rủi ro lâm sàng.
 *
 * Bốn bước trong bảng bên phải phản ánh đúng luồng xử lý thật của
 * `src/simple_agent`: hỏi thu thập dữ kiện (decision.py rank_question_targets)
 * -> đối chiếu tiêu chí phác đồ một cách tất định (evaluate_atoms/atom_status)
 * -> kết luận kèm trích dẫn (sbar.py _citation_entries) -> điều dưỡng thẩm
 * định (routes_nurse_simple.py).
 */

const PIPELINE_STEPS = [
  {
    icon: MessagesSquare,
    title: "Hỏi đúng dữ kiện còn thiếu",
    detail: "Chỉ hỏi thông tin phác đồ thực sự cần, không hỏi lại điều bạn đã nói",
  },
  {
    icon: Scale,
    title: "Đối chiếu tiêu chí phác đồ",
    detail: "So khớp tất định từng tiêu chí, không để mô hình tự đoán mức độ",
  },
  {
    icon: FileText,
    title: "Kết luận kèm trích dẫn",
    detail: "Nêu rõ tiêu chí nào đã thỏa và bạn đã khai báo giá trị gì",
  },
  {
    icon: UserRoundCheck,
    title: "Điều dưỡng thẩm định",
    detail: "Kết quả chỉ thành chính thức sau khi nhân viên y tế chốt",
  },
] as const;

export const HeroSection: React.FC = () => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  return (
    <section className="relative w-full overflow-hidden bg-slate-950 text-white pt-8 pb-24 md:pt-16 md:pb-32 border-b border-slate-800">
      {/* VIDEO BACKGROUND LOOP (VID-01) WITH DUAL-LAYER GRADIENT OVERLAY */}
      <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden">
        <video
          autoPlay
          loop
          muted
          playsInline
          className="w-full h-full object-cover opacity-35 filter contrast-125"
          src="/VID-01.mp4"
        />
        <div
          className="absolute inset-0 bg-gradient-to-r from-slate-950/95 via-sky-950/85 to-slate-950/70"
          aria-hidden="true"
        />
        <div
          className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,_var(--tw-gradient-stops))] from-sky-600/20 via-transparent to-transparent opacity-60"
          aria-hidden="true"
        />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-10 items-center">

          {/* CỘT TRÁI: ĐỊNH VỊ SẢN PHẨM, TIÊU ĐỀ, CTA */}
          <div className="lg:col-span-7 flex flex-col items-start text-left space-y-6">

            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease: "easeOut" }}
              className="inline-flex flex-wrap items-center gap-2 px-4 py-2 rounded-full bg-slate-900/90 border border-sky-500/30 shadow-[0_0_15px_rgba(2,132,199,0.15)] backdrop-blur-md"
            >
              <Sparkles className="w-5 h-5 text-sky-400 shrink-0" />
              <span className="text-sm font-bold text-sky-200 tracking-wide">
                Sàng lọc mức độ khẩn cấp theo thang ESI 5 cấp
              </span>
              <span className="px-2.5 py-0.5 rounded-lg bg-sky-500/20 border border-sky-400/30 text-sky-300 font-mono font-extrabold text-sm uppercase">
                RAG phác đồ
              </span>
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1, ease: "easeOut" }}
              className="font-heading text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-[1.15] sm:leading-[1.12]"
            >
              Sàng Lọc Lâm Sàng Bằng AI{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-sky-400 via-blue-300 to-emerald-400">
                Có Trích Dẫn Phác Đồ
              </span>
            </motion.h1>

            <motion.h2
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2, ease: "easeOut" }}
              className="text-base sm:text-lg lg:text-xl font-medium text-slate-300 max-w-2xl leading-relaxed font-sans"
            >
              Hệ thống hỏi bạn từng dữ kiện lâm sàng cần thiết, rồi{" "}
              <span className="text-sky-300 font-bold">
                đối chiếu với phác đồ ESI để đề xuất mức độ khẩn cấp
              </span>
              . Không truy xuất được phác đồ làm căn cứ thì hệ thống nói thẳng là chưa đủ dữ liệu,
              chứ không tự suy diễn ra một mức ESI.
            </motion.h2>

            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3, ease: "easeOut" }}
              className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4 w-full sm:w-auto pt-2"
            >
              <Link
                href={patientEntryHref("/triage", isAuthenticated)}
                className="group relative inline-flex items-center justify-center min-h-[52px] min-w-[44px] px-8 py-3.5 text-base sm:text-lg font-bold text-white bg-gradient-to-r from-sky-600 to-blue-600 hover:from-sky-500 hover:to-blue-500 rounded-xl shadow-[0_0_25px_rgba(2,132,199,0.4)] hover:shadow-[0_0_35px_rgba(2,132,199,0.6)] transition-all duration-200 transform hover:scale-[1.02] active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950"
              >
                <div className="flex items-center gap-3 relative z-10">
                  <Siren className="w-6 h-6 text-rose-300 shrink-0 stroke-[2.2]" />
                  <span className="tracking-tight font-bold">Bắt Đầu Phiên Sàng Lọc</span>
                  <ArrowRight className="w-5 h-5 text-sky-200 group-hover:translate-x-1.5 transition-transform stroke-[2.2]" />
                </div>
              </Link>
            </motion.div>

            {/* BA CAM KẾT KIỂM CHỨNG ĐƯỢC TỪ CHÍNH HỆ THỐNG */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.45, ease: "easeOut" }}
              className="pt-4 flex flex-wrap items-center gap-x-6 gap-y-3 text-sm sm:text-base font-semibold text-slate-300 border-t border-slate-800/80 w-full"
            >
              <div className="flex items-center gap-2">
                <HeartPulse className="w-5 h-5 text-rose-400 shrink-0 stroke-[2.2]" />
                <span>Phân loại theo thang ESI 5 cấp</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-sky-400 shrink-0 stroke-[2.2]" />
                <span>Mỗi kết luận đều kèm trích dẫn phác đồ</span>
              </div>
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0 stroke-[2.2]" />
                <span>Điều dưỡng thẩm định trước khi chốt</span>
              </div>
            </motion.div>
          </div>

          {/* CỘT PHẢI: LUỒNG XỬ LÝ THẬT (thay cho bảng telemetry mô phỏng) */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, delay: 0.25, ease: "easeOut" }}
            className="lg:col-span-5 relative flex items-center justify-center pt-6 lg:pt-0"
          >
            <div
              className="absolute inset-0 -m-6 bg-gradient-to-tr from-sky-600/25 via-blue-500/15 to-emerald-500/25 rounded-3xl blur-2xl pointer-events-none"
              aria-hidden="true"
            />

            <div className="glow-frame glow-sky relative w-full overflow-hidden rounded-2xl bg-slate-900/85 border-2 border-slate-700/80 shadow-[0_20px_50px_rgba(0,0,0,0.6)] backdrop-blur-xl">

              <div className="relative z-10 flex items-center gap-2.5 px-5 py-3 bg-slate-950/80 border-b border-slate-800">
                <Stethoscope className="w-4.5 h-4.5 text-sky-400 shrink-0 stroke-[2.3]" aria-hidden="true" />
                <span className="text-sm font-bold text-slate-200 tracking-tight">
                  Một phiên sàng lọc diễn ra thế nào
                </span>
              </div>

              <div className="relative z-10 overflow-hidden">
                <Image
                  src="/IMG-01.png"
                  alt="Giao diện lâm sàng hiển thị dữ liệu người bệnh trong phiên sàng lọc"
                  width={1200}
                  height={900}
                  priority
                  className="w-full h-36 sm:h-44 object-cover opacity-70"
                />
                <div className="absolute inset-0 bg-gradient-to-b from-slate-900/40 to-slate-900" aria-hidden="true" />
              </div>

              <ol className="relative z-10 p-5 space-y-2">
                {PIPELINE_STEPS.map((step, index) => {
                  const StepIcon = step.icon;
                  return (
                    <li
                      key={step.title}
                      className="group/step glow-soft glow-sky flex items-start gap-3.5 rounded-xl border border-transparent p-1.5 hover:border-sky-500/40 hover:bg-sky-500/5"
                    >
                      <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-sky-500/15 border border-sky-400/30 text-sky-300 transition-[background-color,color] duration-300 group-hover/step:bg-sky-500 group-hover/step:text-white">
                        <StepIcon className="w-4.5 h-4.5 stroke-[2.3]" aria-hidden="true" />
                      </span>
                      <div className="min-w-0">
                        <div className="flex items-baseline gap-2">
                          <span className="font-mono text-xs font-bold text-slate-500 shrink-0">
                            {String(index + 1).padStart(2, "0")}
                          </span>
                          <span className="text-sm font-bold text-white leading-snug">{step.title}</span>
                        </div>
                        <p className="mt-0.5 text-sm leading-relaxed text-slate-400">{step.detail}</p>
                      </div>
                    </li>
                  );
                })}
              </ol>

              <div className="relative z-10 px-5 py-3.5 bg-slate-950/70 border-t border-slate-800 flex items-start gap-2.5">
                <ShieldCheck className="w-4.5 h-4.5 text-emerald-400 shrink-0 stroke-[2.3] mt-0.5" aria-hidden="true" />
                <p className="text-sm font-medium leading-relaxed text-slate-300">
                  Đây là công cụ hỗ trợ sàng lọc ban đầu, không thay thế chẩn đoán của nhân viên y tế.
                </p>
              </div>
            </div>
          </motion.div>

        </div>
      </div>
    </section>
  );
};
