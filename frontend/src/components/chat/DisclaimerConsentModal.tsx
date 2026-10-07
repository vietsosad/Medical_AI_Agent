"use client";

import React, { useState } from "react";
import { useTriageStore } from "@/store/useTriageStore";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Checkbox } from "@/components/ui/checkbox";
import { ShieldAlert, Bot, Scale, Siren, ArrowRight, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import { motion, type Variants } from "framer-motion";

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.1 },
  },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 15 },
  show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } },
};

/**
 * COMPONENT SCR-TRIAGE-01: MODAL CAM KẾT PHÁP LÝ Y ĐỨC
 * Giao diện Premium Clinical (Pristine Light Theme).
 */
export function DisclaimerConsentModal() {
  const { hasConsented, setConsent } = useTriageStore();
  const [isChecked, setIsChecked] = useState<boolean>(false);

  const handleStartSession = () => {
    if (isChecked) {
      setConsent(true);
    }
  };

  return (
    <Dialog open={!hasConsented}>
      <DialogContent
        hideCloseButton={true}
        onPointerDownOutside={(e) => e.preventDefault()}
        onEscapeKeyDown={(e) => e.preventDefault()}
        className="max-w-xl w-full p-0 bg-card/95 backdrop-blur-xl border border-border/60 shadow-[0_20px_60px_-15px_rgba(0,0,0,0.1)] text-slate-800 rounded-[2rem] font-sans overflow-hidden dark:text-slate-100"
      >
        {/* Subtle top gradient bar */}
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-sky-400 via-indigo-500 to-sky-400 opacity-90" />

        <DialogHeader className="px-6 pt-8 pb-5 border-b border-slate-100 bg-background/50">
          <div className="flex flex-col items-center text-center gap-4">
            <div className="relative">
              <div className="absolute inset-0 bg-amber-400 blur-xl opacity-20 rounded-full" />
              <div className="relative p-4 rounded-2xl bg-gradient-to-b from-white to-amber-50 border border-amber-200 shadow-sm">
                <ShieldAlert className="w-8 h-8 text-amber-500 stroke-[2.2]" />
              </div>
            </div>
            <div className="space-y-1.5">
              <DialogTitle className="text-xl sm:text-2xl font-black tracking-tight text-foreground">
                Cam Kết Y Đức Lâm Sàng
              </DialogTitle>
              <p className="text-sm text-muted-foreground font-medium max-w-[90%] mx-auto leading-relaxed">
                Xin vui lòng xác nhận các quy chuẩn an toàn trước khi sử dụng AI Triage.
              </p>
            </div>
          </div>
        </DialogHeader>

        <motion.div 
          variants={containerVariants}
          initial="hidden"
          animate="show"
          className="p-6 space-y-4 bg-card"
        >
          {/* Box 1 */}
          <motion.div variants={itemVariants} className="group flex gap-4 items-start p-4 rounded-2xl bg-background/50 border border-slate-100 hover:border-sky-200 hover:bg-sky-50/30 transition-all duration-300">
            <div className="p-2.5 rounded-xl bg-card border border-border shadow-sm shrink-0 group-hover:border-sky-300 group-hover:shadow-sky-100 transition-colors">
              <Bot className="w-5 h-5 text-sky-600 stroke-[2.2]" />
            </div>
            <div className="space-y-1">
              <h4 className="text-sm font-bold text-foreground tracking-tight">
                AI Hỗ Trợ Ghi Nhận
              </h4>
              <p className="text-[13px] text-slate-600 font-medium leading-relaxed dark:text-slate-300">
                Hệ thống sử dụng <span className="font-semibold text-slate-700 dark:text-slate-200">DeepAgent + Hybrid RAG</span> để thu thập triệu chứng và chuẩn bị đề xuất phân độ ESI cho nhân viên y tế thẩm định.
              </p>
            </div>
          </motion.div>

          {/* Box 2 */}
          <motion.div variants={itemVariants} className="group flex gap-4 items-start p-4 rounded-2xl bg-background/50 border border-slate-100 hover:border-indigo-200 hover:bg-indigo-50/30 transition-all duration-300">
            <div className="p-2.5 rounded-xl bg-card border border-border shadow-sm shrink-0 group-hover:border-indigo-300 group-hover:shadow-indigo-100 transition-colors">
              <Scale className="w-5 h-5 text-indigo-600 stroke-[2.2]" />
            </div>
            <div className="space-y-1">
              <h4 className="text-sm font-bold text-foreground tracking-tight">
                Không Thay Thế Bác Sĩ
              </h4>
              <p className="text-[13px] text-slate-600 font-medium leading-relaxed dark:text-slate-300">
                Đánh giá của AI <span className="font-bold text-rose-600 uppercase text-[11px] px-1.5 py-0.5 bg-rose-100 rounded-md mx-1">Tuyệt đối không</span> thay thế chẩn đoán y học chính thức hay y lệnh từ bác sĩ.
              </p>
            </div>
          </motion.div>

          {/* Box 3 */}
          <motion.div variants={itemVariants} className="group flex gap-4 items-start p-4 rounded-2xl bg-rose-50/30 border border-rose-100 hover:border-rose-200 hover:bg-rose-50/60 transition-all duration-300 relative overflow-hidden">
            <div className="absolute right-0 top-0 bottom-0 w-24 bg-gradient-to-l from-rose-100/50 to-transparent pointer-events-none" />
            <div className="p-2.5 rounded-xl bg-card border border-rose-200 shadow-sm shrink-0 group-hover:scale-110 transition-transform duration-300 relative z-10">
              <Siren className="w-5 h-5 text-rose-500 stroke-[2.2]" />
            </div>
            <div className="space-y-1 relative z-10">
              <h4 className="text-sm font-bold text-rose-900 tracking-tight">
                Phản Xạ Khẩn Cấp
              </h4>
              <p className="text-[13px] text-rose-700/90 font-medium leading-relaxed">
                Hệ thống tự động khóa chat và kích hoạt lệnh <strong className="text-rose-700">cấp cứu 115</strong> nếu phát hiện dấu hiệu đe dọa sinh mạng.
              </p>
            </div>
          </motion.div>
        </motion.div>

        <div className="px-6 py-5 border-t border-slate-100 bg-background/50 space-y-4 rounded-b-[2rem]">
          <div 
            className="flex items-start gap-3 p-3.5 rounded-xl border-2 border-transparent hover:bg-card hover:border-border transition-all cursor-pointer group"
            onClick={() => setIsChecked(!isChecked)}
          >
            <div className="shrink-0 mt-0.5">
              <Checkbox
                id="clinical-consent"
                checked={isChecked}
                onCheckedChange={(val) => setIsChecked(val === true)}
                className="rounded-md border-slate-300 data-[state=checked]:bg-sky-600 data-[state=checked]:border-sky-600 w-5 h-5 dark:border-slate-700"
              />
            </div>
            <label
              htmlFor="clinical-consent"
              className="text-sm font-semibold text-slate-700 leading-snug cursor-pointer select-none dark:text-slate-200"
              onClick={(e) => e.preventDefault()}
            >
              Tôi đã đọc kỹ và hoàn toàn đồng ý với các quy chuẩn an toàn lâm sàng nêu trên.
            </label>
          </div>

          <button
            type="button"
            disabled={!isChecked}
            onClick={handleStartSession}
            className={cn(
              "w-full h-14 rounded-xl font-bold text-[15px] flex items-center justify-center gap-2 transition-all duration-300 transform select-none relative overflow-hidden",
              {
                "bg-slate-900 text-white hover:bg-slate-800 shadow-lg shadow-slate-900/20 active:scale-[0.98]": isChecked,
                "bg-muted text-slate-400 cursor-not-allowed": !isChecked,
              }
            )}
          >
            {isChecked && (
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent translate-x-[-100%] animate-[shimmer_2s_infinite]" />
            )}
            <ShieldCheck className={cn("w-5 h-5 transition-transform duration-300", isChecked ? "scale-100" : "scale-90 opacity-50")} />
            <span>Tiến Vào Phòng Khám</span>
            <ArrowRight
              className={cn("w-5 h-5 transition-transform duration-300", {
                "translate-x-1": isChecked,
                "opacity-50": !isChecked,
              })}
            />
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
