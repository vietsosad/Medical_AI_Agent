"use client";

import React, { useState } from "react";
import Image from "next/image";
import { patientEntryHref } from "@/lib/auth-routing";
import { useAuthStore } from "@/store/useAuthStore";
import { motion, AnimatePresence } from "framer-motion";
import { 
  User, 
  Stethoscope, 
  ArrowRight, 
  CheckCircle2, 
  Activity, 
  MessageSquare, 
  Layers
} from "lucide-react";

export const DynamicTriagePreview: React.FC = () => {
  // Trạng thái chuyển giữa 2 chế độ góc nhìn: patient (bệnh nhân) vs clinician (bác sĩ)
  const [activeTab, setActiveTab] = useState<"patient" | "clinician">("patient");
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  return (
    <section
      id="trai-nghiem-triage"
      className="scroll-mt-20 py-24 bg-white dark:bg-slate-950 border-b border-slate-200 dark:border-slate-800 overflow-hidden"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* SECTION TITLE */}
        <div className="text-center max-w-3xl mx-auto mb-12">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-slate-100 dark:bg-slate-900 text-slate-800 dark:text-slate-200 font-mono font-bold text-sm mb-4 border border-slate-300 dark:border-slate-700">
            <Layers className="w-4 h-4 text-sky-600 dark:text-sky-400 stroke-[2.2]" />
            <span>MÔ PHỞNG GIAO DIỆN HỢP BỆNH SĨ TOÀN CỰC</span>
          </div>
          <h2 className="font-heading text-3xl sm:text-4xl lg:text-5xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Trải Nghiệm Triage Động <br className="hidden sm:inline" />
            <span className="text-sky-600 dark:text-sky-400">Góc Nhìn Kép Hiệp Lực Y Khoa</span>
          </h2>
          <p className="mt-4 text-base sm:text-lg font-medium text-slate-600 dark:text-slate-300 leading-relaxed">
            Chuyển đổi tức thời giữa trải nghiệm hỏi bệnh trực chiến chữ to siêu nét cho Người bệnh mệt mỏi, và trạm kiểm duyệt Kanban đầy đủ tham số cho Bác sĩ thẩm định.
          </p>

          {/* TOUCH-COMPLIANT TAB SWITCHER (MIN 44PX HEIGHT) */}
          <div className="mt-8 flex items-center justify-center">
            <div className="inline-flex p-1.5 bg-slate-100 dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 max-w-md w-full sm:w-auto shadow-inner">
              <button
                type="button"
                onClick={() => setActiveTab("patient")}
                className={`min-h-[48px] min-w-[44px] flex-1 sm:flex-initial px-6 py-2.5 rounded-xl text-sm sm:text-base font-bold transition-all flex items-center justify-center gap-2.5 ${
                  activeTab === "patient"
                    ? "bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-sm border border-slate-200 dark:border-slate-700"
                    : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
                }`}
              >
                <User className="w-5 h-5 text-sky-600 dark:text-sky-400 shrink-0 stroke-[2.2]" />
                <span>Góc Nhìn Người Bệnh</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab("clinician")}
                className={`min-h-[48px] min-w-[44px] flex-1 sm:flex-initial px-6 py-2.5 rounded-xl text-sm sm:text-base font-bold transition-all flex items-center justify-center gap-2.5 ${
                  activeTab === "clinician"
                    ? "bg-slate-900 text-white shadow-md dark:bg-sky-600 dark:text-white"
                    : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
                }`}
              >
                <Stethoscope className="w-5 h-5 text-emerald-400 shrink-0 stroke-[2.2]" />
                <span>Góc Nhìn Điều Dưỡng (HITL)</span>
              </button>
            </div>
          </div>
        </div>

        {/* TABBED INTERACTIVE CONTENT DISPLAY - SMOOTH AMBIENT FRAMER MOTION */}
        <div className="mt-12">
          <AnimatePresence mode="wait">
            {activeTab === "patient" ? (
              /* TAB 1: PATIENT VIEW (SYMPTOM CHATBOT & INTAKE - IMG-04) */
              <motion.div
                key="patient-tab"
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -16 }}
                transition={{ duration: 0.4, ease: "easeOut" }}
                className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center bg-slate-50 dark:bg-slate-900/60 rounded-3xl p-6 sm:p-10 border border-slate-200 dark:border-slate-800/80 shadow-md"
              >
                {/* Left Text & Features */}
                <div className="lg:col-span-6 space-y-6 text-left">
                  <div className="inline-flex items-center gap-2 px-3 py-1 bg-sky-100 dark:bg-sky-900/50 text-sky-800 dark:text-sky-300 font-extrabold text-sm rounded-lg border border-sky-300 dark:border-sky-800">
                    <MessageSquare className="w-4 h-4 text-sky-600 dark:text-sky-400" />
                    <span>CHẾ ĐỘ TIẾP NHẬN BỆNH NHÂN (PATIENT INTAKE)</span>
                  </div>
                  
                  <h3 className="font-heading text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white leading-tight">
                    Trao Đổi Triệu Chứng Rõ Ràng, <br />
                    <span className="text-sky-600 dark:text-sky-400">Từng Bước Một</span>
                  </h3>
                  
                  <p className="text-base sm:text-lg font-medium text-slate-600 dark:text-slate-300 leading-relaxed">
                    Bạn chỉ cần mô tả điều mình đang gặp bằng lời tự nhiên. Trợ lý sẽ hỏi lần lượt để làm rõ thông tin; bạn có thể trả lời theo cách của mình.
                  </p>

                  <div className="space-y-4 pt-4 border-t border-slate-200 dark:border-slate-800 font-semibold text-sm sm:text-base text-slate-800 dark:text-slate-200">
                    <div className="flex items-start gap-3">
                      <CheckCircle2 className="w-5 h-5 text-sky-600 dark:text-sky-400 shrink-0 mt-0.5" />
                      <span><strong>Nhắn tin bằng ngôn ngữ tự nhiên:</strong> Mô tả triệu chứng như khi đang trao đổi với nhân viên y tế, không cần làm trắc nghiệm.</span>
                    </div>
                    <div className="flex items-start gap-3">
                      <CheckCircle2 className="w-5 h-5 text-sky-600 dark:text-sky-400 shrink-0 mt-0.5" />
                      <span><strong>Câu hỏi tiếp theo dựa trên cuộc trò chuyện:</strong> Trợ lý ghi nhận câu trả lời đã có và hỏi thêm điều cần làm rõ.</span>
                    </div>
                    <div className="flex items-start gap-3">
                      <CheckCircle2 className="w-5 h-5 text-sky-600 dark:text-sky-400 shrink-0 mt-0.5" />
                      <span><strong>Hồ sơ sức khỏe do bạn cung cấp:</strong> Thông tin đã lưu giúp bạn chuẩn bị khi trao đổi, và vẫn cần được xác nhận lại khi cần.</span>
                    </div>
                  </div>

                  <div className="pt-4">
                    <a
                      href={patientEntryHref("/triage", isAuthenticated)}
                      className="inline-flex items-center justify-center min-h-[48px] px-8 py-3.5 text-base font-bold text-white bg-sky-600 hover:bg-sky-700 rounded-xl shadow-md transition-all transform hover:scale-[1.01]"
                    >
                      <span>Bắt đầu trao đổi triệu chứng</span>
                      <ArrowRight className="w-5 h-5 ml-2.5" />
                    </a>
                  </div>
                </div>

                {/* Right Image Illustration (IMG-04) */}
                <div className="lg:col-span-6 flex items-center justify-center">
                  <div className="relative w-full max-w-lg overflow-hidden rounded-2xl bg-white dark:bg-slate-950 p-3 border border-slate-200 dark:border-slate-800 shadow-xl group">
                    <div className="absolute inset-0 bg-radial from-sky-500/10 via-transparent to-transparent opacity-60 pointer-events-none" />
                    <Image
                      src="/IMG-04.png"
                      alt="Đồ họa Isometric mô tả bệnh nhân tương tác mượt mà với chatbot trợ lý ảo Triage trên điện thoại với nút bấm chữ to"
                      width={600}
                      height={600}
                      className="w-full h-auto object-cover rounded-xl transform group-hover:scale-102 transition-transform duration-500"
                    />
                    <div className="absolute top-6 left-6 p-3 bg-white/95 dark:bg-slate-900/95 rounded-xl border border-sky-400/40 shadow-lg backdrop-blur-md max-w-[240px]">
                      <div className="text-xs font-mono font-bold text-sky-600 dark:text-sky-400 uppercase">Trạng thái Bệnh nhân</div>
                      <div className="text-sm font-bold text-slate-900 dark:text-white mt-0.5">Trao đổi từng bước • Chữ rõ, dễ đọc</div>
                    </div>
                  </div>
                </div>
              </motion.div>
            ) : (
              /* TAB 2: CLINICIAN VIEW (NURSE QUEUE + CASE REVIEW - IMG-03).
                 Chỉ mô tả màn hình đang chạy thật: hàng đợi, màn thẩm định ca
                 và bàn quyết định của điều dưỡng. */
              <motion.div
                key="clinician-tab"
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -16 }}
                transition={{ duration: 0.4, ease: "easeOut" }}
                className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center bg-slate-900 rounded-3xl p-6 sm:p-10 border-2 border-slate-800 text-white shadow-2xl"
              >
                {/* Left Text & Features */}
                <div className="lg:col-span-6 space-y-6 text-left">
                  <div className="inline-flex items-center gap-2 px-3 py-1 bg-emerald-950/80 text-emerald-300 font-extrabold text-sm rounded-lg border border-emerald-800">
                    <Stethoscope className="w-4 h-4 text-emerald-400" />
                    <span>TRẠM THẨM ĐỊNH CỦA ĐIỀU DƯỠNG (HITL)</span>
                  </div>

                  <h3 className="font-heading text-2xl sm:text-3xl font-extrabold text-white leading-tight">
                    Phiếu SBAR &amp; <br />
                    <span className="text-emerald-400">Quyết Định Của Điều Dưỡng</span>
                  </h3>

                  <p className="text-base sm:text-lg font-medium text-slate-300 leading-relaxed">
                    AI gom lời kể của người bệnh thành phiếu tóm tắt SBAR (Situation - Background - Assessment - Recommendation) kèm mức ESI đề xuất. Điều dưỡng xem toàn bộ hồ sơ và là người chốt hoặc điều chỉnh mức ESI.
                  </p>

                  <div className="space-y-4 pt-4 border-t border-slate-800 font-semibold text-sm sm:text-base text-slate-200">
                    <div className="flex items-start gap-3">
                      <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                      <span><strong>Hàng đợi theo mức ESI 1–5:</strong> Lọc ca theo mức độ, kèm thời gian chờ tiếp nhận và tín hiệu riêng cho ca ESI 1–2.</span>
                    </div>
                    <div className="flex items-start gap-3">
                      <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                      <span><strong>Màn thẩm định ca:</strong> Phiếu SBAR, từng tiêu chí phác đồ đã đối chiếu kèm giá trị người bệnh khai, và toàn bộ hội thoại với AI.</span>
                    </div>
                    <div className="flex items-start gap-3">
                      <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                      <span><strong>Quyết định có lý do:</strong> Giữ nguyên hoặc điều chỉnh mức ESI, bắt buộc ghi lý do khi điều chỉnh.</span>
                    </div>
                  </div>

                </div>

                {/* Right Image Illustration (IMG-03) */}
                <div className="lg:col-span-6 flex items-center justify-center">
                  <div className="relative w-full max-w-lg overflow-hidden rounded-2xl bg-slate-950 p-3 border border-slate-800 shadow-2xl group">
                    <div className="absolute inset-0 bg-radial from-emerald-500/10 via-transparent to-transparent opacity-60 pointer-events-none" />
                    <Image
                      src="/IMG-03.png"
                      alt="Bác sĩ cấp cứu hiện đại thao tác trên iPad hiển thị bảng phân chia cấp độ y tế ESI tại bệnh viện"
                      width={800}
                      height={533}
                      className="w-full h-auto object-cover rounded-xl transform group-hover:scale-102 transition-transform duration-500"
                    />
                    <div className="absolute bottom-6 left-6 right-6 p-4 bg-slate-950/95 rounded-xl border border-emerald-500/40 shadow-lg backdrop-blur-md flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Activity className="w-5 h-5 text-emerald-400 animate-pulse shrink-0" />
                        <div>
                          <div className="text-xs font-mono text-slate-400 font-bold uppercase">HITL OVERSIGHT ACTIVE</div>
                          <div className="text-sm font-bold text-white">BS. Trần Thẩm Định • Đang trực chiến</div>
                        </div>
                      </div>
                      <span className="px-3 py-1 rounded-md bg-emerald-500/20 text-emerald-300 font-extrabold text-xs border border-emerald-500/40">
                        SBAR SIGNED
                      </span>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

      </div>
    </section>
  );
};
