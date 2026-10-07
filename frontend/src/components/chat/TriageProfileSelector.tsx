"use client";

import React, { useState } from "react";
import { useGetProfiles } from "@/queries/useProfileQueries";
import { Activity, UserCircle2, ArrowRight, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useActiveProfileStore } from "@/store/useActiveProfileStore";

interface Props {
  onProfileSelected: (profileId: string | null) => void;
}

export function TriageProfileSelector({ onProfileSelected }: Props) {
  const { data: profiles, isLoading } = useGetProfiles();
  const [selectedProfileId, setSelectedProfileId] = useState<string | null>(null);
  const setActiveProfileId = useActiveProfileStore((state) => state.setActiveProfileId);
  const defaultProfileId = profiles?.find((profile) => profile.is_primary)?.id ?? profiles?.[0]?.id ?? null;
  const effectiveProfileId = selectedProfileId ?? defaultProfileId;

  const handleStart = () => {
    setActiveProfileId(effectiveProfileId);
    onProfileSelected(effectiveProfileId);
  };

  return (
    <div className="w-full max-w-2xl mx-auto space-y-6 pt-12 pb-24 px-4 font-sans h-full overflow-y-auto">
      <div className="text-center space-y-2">
        <div className="mx-auto w-16 h-16 rounded-3xl bg-sky-600 flex items-center justify-center text-white shadow-lg mb-4">
          <Activity className="w-8 h-8 stroke-[2.5]" />
        </div>
        <h2 className="text-2xl sm:text-3xl font-black text-foreground tracking-tight">
          Bắt đầu Phiên Triage
        </h2>
        <p className="text-muted-foreground font-medium">
          Chọn người bệnh để Trợ lý AI chuẩn bị không gian tư vấn.
        </p>
      </div>

      <div className="bg-card rounded-3xl border border-border/90 shadow-xl p-6 space-y-6">
        
        {/* Chọn Hồ sơ */}
        <div className="space-y-3">
          <label className="text-sm font-bold text-slate-700 uppercase tracking-wider dark:text-slate-200">
            Chọn Hồ sơ Y tế (Hoặc Khám Nhanh)
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {isLoading ? (
              <div className="col-span-full py-8 flex justify-center items-center text-slate-400">
                <Loader2 className="w-6 h-6 animate-spin" />
              </div>
            ) : (
              profiles?.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setSelectedProfileId(p.id)}
                  className={cn(
                    "flex items-center gap-3 p-4 rounded-2xl border-2 transition-all cursor-pointer text-left",
                    effectiveProfileId === p.id
                      ? "border-sky-500 bg-sky-50/50 shadow-md ring-2 ring-sky-500/20"
                      : "border-slate-100 bg-background hover:bg-muted/80 hover:border-border"
                  )}
                >
                  <UserCircle2 className={cn("w-6 h-6 shrink-0", effectiveProfileId === p.id ? "text-sky-600" : "text-slate-400")} />
                  <div>
                    <div className={cn("font-bold", effectiveProfileId === p.id ? "text-sky-900" : "text-slate-700 dark:text-slate-200")}>
                      {p.full_name}
                    </div>
                    <div className="text-xs text-muted-foreground font-medium">
                      {p.relationship_type} • {p.age} tuổi
                    </div>
                  </div>
                </button>
              ))
            )}

            {!isLoading && profiles?.length === 0 && (
              <div className="col-span-full rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm leading-6 text-amber-950">
                Chưa có hồ sơ y tế để đưa vào phiên Triage. Hãy tạo hồ sơ trước khi bắt đầu để AI
                có thể dùng đúng tuổi, giới tính, bệnh nền, dị ứng và thuốc đang dùng.
              </div>
            )}
          </div>
        </div>

        {/* Bắt đầu */}
        <button
          type="button"
          onClick={handleStart}
          disabled={!effectiveProfileId || isLoading}
          className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-sky-600 px-6 text-base font-bold text-white shadow-sm transition-colors hover:bg-sky-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          <span>Tiếp tục</span>
          <ArrowRight className="w-5 h-5" />
        </button>

      </div>
    </div>
  );
}
