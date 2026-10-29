"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { ArrowRight, Bot, Scale, ShieldCheck, Siren } from "lucide-react";

import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { DURATION, EASE_OUT, STAGGER_SECONDS } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { useTriageStore } from "@/store/useTriageStore";

const list = {
  hidden: {},
  visible: { transition: { staggerChildren: STAGGER_SECONDS * 2, delayChildren: 0.1 } },
};

const item = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0, transition: { duration: DURATION.base, ease: EASE_OUT } },
};

const POINTS = [
  {
    icon: Bot,
    title: "Trợ lý AI hỗ trợ ghi nhận",
    body: "Mô hình ngôn ngữ đọc lời bạn kể để ghi nhận triệu chứng. Mức ESI đề xuất được đối chiếu với tiêu chí phác đồ, rồi chuyển cho nhân viên y tế thẩm định.",
  },
  {
    icon: Scale,
    title: "Không thay thế bác sĩ",
    body: "Đánh giá của AI không thay thế chẩn đoán y học chính thức hay y lệnh của bác sĩ.",
  },
] as const;

/**
 * Lưu ý trước phiên sàng lọc, hiện một lần mỗi lần mở trang khám.
 *
 * Trên điện thoại hộp thoại tự cuộn bên trong (không tràn khỏi màn hình), và
 * ô đồng ý + nút bắt đầu luôn ghim ở đáy hộp thoại để không bị khuất.
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
        className="flex max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-lg flex-col gap-0 overflow-hidden rounded-3xl border border-border bg-card p-0 text-foreground shadow-2xl"
      >
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
          <DialogHeader className="gap-2 px-6 pt-6 text-left">
            <span className="mb-2 flex size-12 items-center justify-center rounded-2xl bg-brand-soft text-brand" aria-hidden="true">
              <ShieldCheck className="size-6" />
            </span>
            <DialogTitle className="text-2xl font-extrabold tracking-tight text-foreground">Trước khi bắt đầu</DialogTitle>
            <DialogDescription className="text-base leading-7 text-muted-foreground">
              Ba điều bạn cần biết về trợ lý sàng lọc.
            </DialogDescription>
          </DialogHeader>

          <motion.ul variants={list} initial="hidden" animate="visible" className="flex flex-col gap-2 px-6 py-6">
            {POINTS.map(({ icon: Icon, title, body }) => (
              <motion.li key={title} variants={item} className="flex items-start gap-4 rounded-2xl bg-muted/60 p-4">
                <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-card text-brand" aria-hidden="true">
                  <Icon className="size-5" />
                </span>
                <span>
                  <span className="block text-base font-bold text-foreground">{title}</span>
                  <span className="mt-1 block text-sm leading-6 text-muted-foreground">{body}</span>
                </span>
              </motion.li>
            ))}
            {/* Không hứa điều hệ thống không làm: ứng dụng chỉ hiện nút gọi
                115 cho kết quả khẩn, không tự gọi hay điều xe thay ai. */}
            <motion.li
              variants={item}
              className="flex items-start gap-4 rounded-2xl border border-rose-200 bg-rose-50 p-4 dark:border-rose-900 dark:bg-rose-950/40"
            >
              <span
                className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-card text-rose-700 dark:text-rose-300"
                aria-hidden="true"
              >
                <Siren className="size-5" />
              </span>
              <span>
                <span className="block text-base font-bold text-rose-950 dark:text-rose-100">Khi có dấu hiệu nguy kịch</span>
                <span className="mt-1 block text-sm leading-6 text-rose-900 dark:text-rose-200">
                  Hệ thống <strong>không tự gọi 115</strong> thay bạn. Với kết quả ở mức khẩn cấp, màn hình hiện nút gọi
                  115 để bạn bấm. Nếu thấy nguy kịch, hãy gọi 115 ngay, không chờ AI trả lời.
                </span>
              </span>
            </motion.li>
          </motion.ul>
        </div>

        <div className="flex shrink-0 flex-col gap-4 border-t border-border bg-card px-6 py-4">
          <div className="flex items-start gap-4">
            <Checkbox
              id="clinical-consent"
              checked={isChecked}
              onCheckedChange={(val) => setIsChecked(val === true)}
              className="mt-1 size-5 rounded-md border-border bg-card data-[state=checked]:border-brand data-[state=checked]:bg-none data-[state=checked]:bg-brand focus-visible:ring-brand focus-visible:ring-offset-card"
            />
            <label htmlFor="clinical-consent" className="cursor-pointer select-none text-base leading-7 text-foreground">
              Tôi đã đọc và đồng ý với các lưu ý trên.
            </label>
          </div>

          <motion.button
            type="button"
            disabled={!isChecked}
            onClick={handleStartSession}
            whileTap={isChecked ? { scale: 0.97 } : undefined}
            className={cn(
              "flex min-h-12 w-full items-center justify-center gap-2 rounded-xl text-base font-bold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-card",
              isChecked
                ? "bg-brand text-brand-foreground hover:bg-brand-strong"
                : "cursor-not-allowed bg-muted text-muted-foreground",
            )}
          >
            Bắt đầu sàng lọc
            <ArrowRight
              className={cn("size-5 transition-transform duration-200", isChecked && "translate-x-1")}
              aria-hidden="true"
            />
          </motion.button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
