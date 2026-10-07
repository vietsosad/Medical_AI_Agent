"use client";

import React from "react";
import { PhoneCall, Siren } from "lucide-react";

/**
 * COMPONENT: NÚT SOS 115 CỐ ĐỊNH (EmergencyFloatingButton) - SCR-TRIAGE-03
 * Gắn nhô vững chắc tại góc dưới bên phải màn hình.
 * Đây là lối tắt liên hệ do người dùng chủ động chọn, không phải bộ phát hiện
 * red-flag phía client và không thay đổi clinical session state.
 * Tuân thủ quy tắc 3.3: 100% sử dụng Lucide vector icons, cấm emoji.
 */
export function EmergencyFloatingButton() {
  return (
    <div className="fixed bottom-24 right-4 z-50 sm:right-6">
      <a
        href="tel:115"
        className="group relative flex min-h-12 items-center gap-2.5 rounded-full border-2 border-rose-400 bg-rose-700 px-4 py-3.5 font-extrabold text-white shadow-lg transition-colors hover:bg-rose-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-600 focus-visible:ring-offset-2 sm:px-5 sm:py-4"
        aria-label="Gọi Tổng đài Cấp cứu Quốc gia 115"
      >
        {/* Vầng sáng nhấp nháy (Ping alert ring) */}
        <span className="absolute -top-1 -left-1 flex h-3.5 w-3.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-80"></span>
          <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-rose-500 border border-white"></span>
        </span>

        {/* Lucide Vector Icons (Cấm Emoji) */}
        <div className="p-1 rounded-full bg-red-800/80 border border-red-500 shrink-0">
          <PhoneCall className="w-5 h-5 sm:w-6 sm:h-6 text-white animate-bounce" />
        </div>

        {/* Lời gọi Báo Động Đỏ */}
        <div className="flex flex-col text-left leading-none">
          <span className="text-[10px] uppercase font-mono tracking-wider text-rose-200 font-bold">
            Hỗ trợ khẩn cấp
          </span>
          <span className="text-xs sm:text-base tracking-tight uppercase font-mono font-black mt-0.5">
            SOS 115 KHẨN CẤP
          </span>
        </div>

        <Siren className="w-5 h-5 text-rose-300 ml-1 opacity-90 group-hover:rotate-12 transition-transform hidden sm:inline-block" />
      </a>
    </div>
  );
}
