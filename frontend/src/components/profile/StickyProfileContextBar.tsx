"use client";

import React from "react";
import { useGetProfiles } from "@/queries/useProfileQueries";
import { useActiveProfileStore } from "@/store/useActiveProfileStore";
import { User, Baby, ShieldAlert, Heart, ShieldCheck, RefreshCw, Activity, Layers } from "lucide-react";

// ============================================================================
// 1. HELPER: BẢNG TUÂN THỦ MÀU SẮC LÂM SÀNG NAVY TỐI GIẢN (ZERO REDS/YELLOWS)
// Mọi cảnh báo nhức nhối được làm dịu thành các sắc thái Xanh Navy, Blue và Teal.
// ============================================================================
function getContextTheme(relationship: string, age: number | null) {
  if (relationship === "CHILD" || (age !== null && age < 16)) {
    return {
      title: "Đang khám cho trẻ",
      badge: "Ngữ cảnh nhi khoa",
      badgeColor: "bg-sky-500 text-white border-sky-400 font-extrabold",
      bgStyle: "bg-sky-950 border-sky-800 shadow-xl shadow-sky-950/20 text-white",
      icon: Baby,
    };
  }
  if (relationship === "PARENT" || (age !== null && age >= 65)) {
    return {
      title: "Đang khám cho người cao tuổi",
      badge: "Ngữ cảnh lão khoa",
      badgeColor: "bg-blue-600 text-white border-blue-400 font-extrabold",
      bgStyle: "bg-slate-900 border-slate-800 shadow-xl shadow-slate-900/30 text-white",
      icon: ShieldAlert,
    };
  }
  if (relationship === "SPOUSE") {
    return {
      title: "Đang khám cho vợ / chồng",
      badge: "Hồ sơ vợ / chồng",
      badgeColor: "bg-teal-600 text-white border-teal-400 font-extrabold",
      bgStyle: "bg-slate-900 border-teal-900/60 shadow-xl shadow-slate-900/30 text-white",
      icon: Heart,
    };
  }
  return {
    title: "Đang khám cho bạn",
    badge: "Hồ sơ chính chủ",
    badgeColor: "bg-blue-600 text-white border-blue-500 font-extrabold",
    bgStyle: "bg-slate-900 border-slate-800 shadow-xl shadow-slate-900/30 text-white",
    icon: User,
  };
}

// ============================================================================
// 2. COMPONENT CHÍNH: THANH NGỮ CẢNH HỒ SƠ (NAVY BLUE STICKY BANNER)
// Tuân thủ Cognitiuve Load < 3s, typography rõ ràng, viền mềm mượt
// ============================================================================
export default function StickyProfileContextBar({ lockedProfileId }: { lockedProfileId?: string | null }) {
  const { data: profiles } = useGetProfiles();
  const { activeProfileId, setActiveProfileId, isProfileSwitcherOpen, toggleProfileSwitcher } = useActiveProfileStore();

  // Xác định hồ sơ đang được chọn (hoặc fallback chính chủ)
  const currentProfile = profiles?.find((p) => p.id === lockedProfileId)
    || profiles?.find((p) => p.id === activeProfileId)
    || profiles?.find((p) => p.is_primary)
    || profiles?.[0];
  const isProfileLocked = Boolean(lockedProfileId);

  if (!currentProfile) return null;

  const theme = getContextTheme(currentProfile.relationship_type, currentProfile.age);
  const Icon = theme.icon;
  const hasAllergies = currentProfile.allergies && currentProfile.allergies.length > 0;
  const hasChronic = currentProfile.chronic_conditions && currentProfile.chronic_conditions.length > 0;

  const genderLabel =
    currentProfile.gender === "MALE" ? "Nam" : currentProfile.gender === "FEMALE" ? "Nữ" : "Khác";

  return (
    <div className="relative w-full z-40 my-4 font-sans">
      {/* THANH NGỮ CẢNH BỆNH NHÂN
          Bố cục cũ bị bóp thành một cột chữ dọc trong khung chat (max-w-3xl):
          khối hành động bên phải đặt `shrink-0` mà lại chứa nhãn dài, nên nó
          giữ nguyên bề rộng nội tại và ép khối thông tin bên trái xuống còn
          vài trăm px; khối trái lại thiếu `min-w-0` nên không co được, buộc
          từng chữ phải xuống dòng.
          Bố cục mới: xếp dọc theo mặc định rồi mới chuyển sang hàng ngang từ
          lg trở lên, `min-w-0` ở mọi nhánh flex có chữ, và không khối nào
          được `shrink-0` ngoài các icon. */}
      <div className={`rounded-3xl border-2 p-4 sm:p-5 transition-all duration-300 ${theme.bgStyle}`}>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">

          {/* KHỐI DANH TÍNH */}
          <div className="flex min-w-0 items-start gap-3.5">
            <div className="flex size-12 shrink-0 items-center justify-center rounded-2xl border border-white/15 bg-card/10 text-white shadow-sm">
              <Icon className="size-6 stroke-[2.3]" aria-hidden="true" />
            </div>

            <div className="min-w-0 flex-1">
              <div className="text-[11px] font-extrabold uppercase tracking-wider text-slate-300">
                {theme.title}
              </div>

              <div className="mt-1 flex flex-wrap items-center gap-x-2.5 gap-y-1.5">
                <span className="min-w-0 break-words text-lg font-black tracking-tight text-white sm:text-xl">
                  {currentProfile.full_name}
                </span>
                {currentProfile.age !== null && (
                  <span className="shrink-0 rounded-lg border border-white/20 bg-card/15 px-2.5 py-0.5 text-sm font-bold text-white">
                    {currentProfile.age} tuổi &middot; {genderLabel}
                  </span>
                )}
              </div>

              {/* DỊ ỨNG & BỆNH NỀN */}
              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-2 text-sm font-semibold">
                {hasAllergies ? (
                  <span className="flex min-w-0 items-center gap-1.5 rounded-xl border border-blue-500 bg-blue-900 px-2.5 py-1 font-bold text-blue-100">
                    <Layers className="size-4 shrink-0 text-blue-300 stroke-[2.5]" aria-hidden="true" />
                    <span className="min-w-0 break-words">Dị ứng: {currentProfile.allergies?.join(", ")}</span>
                  </span>
                ) : (
                  <span className="flex items-center gap-1.5 text-slate-300">
                    <ShieldCheck className="size-4 shrink-0 text-teal-400 stroke-[2.5]" aria-hidden="true" />
                    <span>Không có ghi nhận dị ứng thuốc</span>
                  </span>
                )}

                {hasChronic && (
                  <span className="flex min-w-0 items-center gap-1.5 text-slate-200">
                    <Activity className="size-4 shrink-0 text-sky-400 stroke-[2.5]" aria-hidden="true" />
                    <span className="text-slate-400">Bệnh nền:</span>
                    <span className="min-w-0 break-words font-bold text-sky-300">
                      {currentProfile.chronic_conditions?.join(", ")}
                    </span>
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* KHỐI TRẠNG THÁI & HÀNH ĐỘNG -- được phép co và xuống dòng */}
          <div className="flex flex-wrap items-center gap-2.5 border-t border-white/10 pt-3.5 lg:justify-end lg:border-t-0 lg:pt-0">
            <span
              className={`rounded-full border px-3 py-1 text-[11px] uppercase tracking-wider shadow-xs ${theme.badgeColor}`}
            >
              {theme.badge}
            </span>
            {isProfileLocked ? (
              <span className="flex min-h-11 items-center rounded-xl border border-white/20 bg-card/10 px-3.5 text-sm font-bold text-white">
                Cố định trong phiên
              </span>
            ) : (
              <button
                type="button"
                onClick={toggleProfileSwitcher}
                id="btn-switch-active-profile"
                aria-expanded={isProfileSwitcherOpen}
                className="flex min-h-11 items-center gap-2 rounded-xl border border-blue-400/30 bg-blue-600 px-3.5 text-sm font-bold text-white shadow-sm transition-colors hover:bg-blue-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
              >
                <RefreshCw
                  className={`size-4.5 transition-transform duration-300 ${isProfileSwitcherOpen ? "rotate-180" : ""}`}
                  aria-hidden="true"
                />
                <span>Đổi bệnh nhân</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* DROPDOWN CHỌN NHANH TRONG PHÒNG KHÁM CẤP BÁCH (NAVY MINIMALIST THEME) */}
      {!isProfileLocked && isProfileSwitcherOpen && (
        <div className="absolute top-full right-0 left-0 md:left-auto md:w-96 mt-3 p-3.5 bg-slate-900 border-2 border-slate-700 rounded-3xl shadow-2xl z-50 animate-in fade-in slide-in-from-top-2 duration-200 backdrop-blur-2xl text-white">
          <header className="flex items-center justify-between pb-3 mb-2 border-b border-slate-800 px-1.5">
            <span className="text-xs font-extrabold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-blue-500 inline-block"></span>
              Danh Sách Người Thân
            </span>
            <button
              type="button"
              onClick={toggleProfileSwitcher}
              className="text-xs text-blue-400 hover:text-white font-bold px-2 py-1 min-h-[44px] flex items-center transition-colors"
            >
              Đóng [X]
            </button>
          </header>
          <div className="flex flex-col gap-2 max-h-80 overflow-y-auto pr-1">
            {profiles?.map((p) => {
              const isSelected = p.id === currentProfile.id;
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => {
                    setActiveProfileId(p.id);
                    toggleProfileSwitcher();
                  }}
                  className={`flex items-center justify-between p-3.5 min-h-[56px] rounded-2xl text-left font-sans transition-all duration-150 ${
                    isSelected
                      ? "bg-blue-600 text-white font-extrabold border-2 border-blue-400 shadow-md shadow-blue-900/40"
                      : "bg-slate-800/80 hover:bg-slate-800 text-slate-200 border border-slate-700/80 hover:border-slate-500"
                  }`}
                >
                  <div className="flex flex-col">
                    <span className="text-base font-bold line-clamp-1">{p.full_name}</span>
                    <span className="text-xs text-slate-400 mt-0.5">
                      {p.relationship_type === "SELF" ? "Bản thân" : p.relationship_type} &middot; {p.age ?? "N/A"} tuổi
                    </span>
                  </div>
                  {isSelected && (
                    <span className="px-2.5 py-1 bg-card text-blue-900 font-black text-xs rounded-xl uppercase tracking-tight shadow-2xs">
                      Đang khám
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
