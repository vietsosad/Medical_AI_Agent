"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  Filter,
  X,
  RotateCcw,
  SlidersHorizontal,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useHistoryUIStore, type HistoryStatusFilter } from "@/store/useHistoryUIStore";
import type { EsiLevel } from "@/types/clinical-history";

export interface HistoryFilterControlProps {
  className?: string;
  totalResults?: number;
}

interface EsiChipConfig {
  level: EsiLevel;
  label: string;
  shortText: string;
  selectedClass: string;
}

const ESI_CHIPS_CONFIG: EsiChipConfig[] = [
  {
    level: 1,
    label: "ESI 1 - Tối Cấp Cứu",
    shortText: "ESI 1 • Cấp Cứu",
    selectedClass:
      "bg-rose-600 text-white border-rose-600 shadow-sm font-black animate-pulse",
  },
  {
    level: 2,
    label: "ESI 2 - Khẩn Cấp Cực Cao",
    shortText: "ESI 2 • Khẩn Cấp",
    selectedClass:
      "bg-orange-600 text-white border-orange-600 shadow-sm font-extrabold",
  },
  {
    level: 3,
    label: "ESI 3 - Ưu Tiên Thăm Khám",
    shortText: "ESI 3 • Ưu Tiên",
    selectedClass:
      "bg-amber-100 text-amber-950 border-amber-400 shadow-2xs font-extrabold",
  },
  {
    level: 4,
    label: "ESI 4 - Thăm Khám Chuẩn",
    shortText: "ESI 4 • Chuẩn Khoa",
    selectedClass:
      "bg-sky-100 text-sky-950 border-sky-400 shadow-2xs font-extrabold",
  },
  {
    level: 5,
    label: "ESI 5 - Tự Theo Dõi",
    shortText: "ESI 5 • Thường Quy",
    selectedClass:
      "bg-emerald-100 text-emerald-950 border-emerald-400 shadow-2xs font-extrabold",
  },
];

/**
 * ⭐ [SCR-HIST-01] Hệ Thống Thanh Control Tra Cứu & Bộ Lọc Nhanh (HistoryFilterControl)
 * Giao diện Sáng Hiện Đại Chuẩn Lâm Sàng (Pristine Light Mode).
 */
export const HistoryFilterControl: React.FC<HistoryFilterControlProps> = ({
  className,
  totalResults,
}) => {
  const {
    searchQuery,
    selectedEsiFilters,
    statusFilter,
    setSearchQuery,
    toggleEsiFilter,
    setStatusFilter,
    resetFilters,
  } = useHistoryUIStore();

  const isFilterActive =
    searchQuery.trim() !== "" || selectedEsiFilters.length > 0 || statusFilter !== "ALL";

  return (
    <div
      className={cn(
        "w-full bg-card border border-border/90 rounded-2xl p-4 md:p-5 shadow-sm space-y-4 text-slate-800 transition-all font-sans dark:text-slate-100",
        className
      )}
    >
      {/* --- ROW 1: SEARCH BAR + HITL STATUS SELECTOR + RESET BUTTON --- */}
      <div className="flex flex-col lg:flex-row items-stretch lg:items-center gap-3 justify-between">
        <div className="relative flex-1 max-w-xl">
          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
            <Search className="w-4 h-4 text-sky-600 stroke-[2.5]" />
          </div>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Tìm theo triệu chứng hoặc mã ca..."
            className="w-full pl-10 pr-9 py-2.5 rounded-xl bg-background border border-border text-foreground placeholder-slate-400 font-medium text-sm focus:bg-card focus:outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-500/20 transition-all duration-200 shadow-inner"
          />
          {searchQuery.length > 0 && (
            <button
              type="button"
              onClick={() => {
                setSearchQuery("");
              }}
              className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-700 transition-colors cursor-pointer dark:hover:text-slate-200"
              title="Xóa từ khóa"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        <div className="flex flex-wrap sm:flex-nowrap items-center gap-2.5">
          <div className="relative shrink-0 w-full sm:w-auto">
            <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none text-muted-foreground">
              <SlidersHorizontal className="w-3.5 h-3.5 text-sky-600 stroke-[2.5]" />
            </div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as HistoryStatusFilter)}
              aria-label="Lọc theo trạng thái HITL"
              className="w-full sm:w-64 pl-9 pr-8 py-2.5 rounded-xl bg-background border border-border text-slate-800 font-bold text-xs md:text-sm focus:bg-card focus:outline-none focus:border-sky-500 cursor-pointer transition-colors duration-200 appearance-none shadow-2xs dark:text-slate-100"
            >
              <option value="ALL">Tất cả trạng thái thẩm định</option>
              <option value="APPROVED">Bác sĩ trực đã duyệt (Approved)</option>
              <option value="OVERRIDDEN">Có can thiệp Override ESI</option>
              <option value="EMERGENCY_REJECTED">Ca báo động đỏ / chuyển cấp cứu</option>
              <option value="PENDING_REVIEW">Đang chờ Bác sĩ duyệt</option>
            </select>
            <div className="absolute inset-y-0 right-3 flex items-center pointer-events-none text-slate-400 text-xs">
              ▼
            </div>
          </div>

          <AnimatePresence>
            {isFilterActive && (
              <motion.button
                type="button"
                initial={{ opacity: 0, scale: 0.9, width: 0 }}
                animate={{ opacity: 1, scale: 1, width: "auto" }}
                exit={{ opacity: 0, scale: 0.9, width: 0 }}
                transition={{ duration: 0.2 }}
                onClick={resetFilters}
                className="shrink-0 px-3.5 py-2.5 rounded-xl bg-rose-50 hover:bg-rose-100 text-rose-800 border border-rose-300 text-xs font-bold transition-all flex items-center gap-1.5 shadow-2xs whitespace-nowrap overflow-hidden cursor-pointer"
                title="Khôi phục toàn bộ bộ lọc"
              >
                <RotateCcw className="w-3.5 h-3.5 stroke-[2.5]" />
                <span>Xóa Bộ Lọc</span>
              </motion.button>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* --- ROW 2: DẢI PHÍM CHỌN ESI SPECTRUM --- */}
      <div className="pt-3 border-t border-slate-100 flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5 mr-1">
            <Filter className="w-3.5 h-3.5 text-sky-600 stroke-[2.5]" />
            <span>Phân Độ ESI:</span>
          </span>

          {ESI_CHIPS_CONFIG.map((chip) => {
            const isSelected = selectedEsiFilters.includes(chip.level);

            return (
              <button
                type="button"
                key={chip.level}
                onClick={() => toggleEsiFilter(chip.level)}
                className={cn(
                  "px-3 py-1.5 rounded-full text-xs transition-all duration-200 border cursor-pointer select-none shrink-0 flex items-center gap-1.5 shadow-2xs",
                  isSelected
                    ? chip.selectedClass
                    : "bg-background text-slate-600 border-border hover:border-slate-300 hover:bg-muted/80 font-semibold dark:text-slate-300 dark:hover:border-slate-700"
                )}
                title={`Nhấp để lọc theo ${chip.label}`}
              >
                <span
                  className={cn(
                    "w-2 h-2 rounded-full shrink-0",
                    chip.level <= 2 ? "bg-rose-600" :
                    chip.level === 3 ? "bg-amber-500" :
                    chip.level === 4 ? "bg-sky-500" : "bg-emerald-500"
                  )}
                />
                <span>{chip.shortText}</span>
              </button>
            );
          })}
        </div>

        {typeof totalResults === "number" && (
          <div className="text-xs font-semibold text-muted-foreground flex items-center gap-1.5 self-end md:self-center shrink-0">
            <span>Hiển thị:</span>
            <span className="font-extrabold text-sky-900 bg-sky-100 border border-sky-200 px-2 py-0.5 rounded-md">
              {totalResults} ca
            </span>
            <span>phù hợp</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default HistoryFilterControl;
