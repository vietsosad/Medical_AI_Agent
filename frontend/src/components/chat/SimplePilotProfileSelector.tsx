"use client";

import React, { useState } from "react";
import { Loader2, UserCircle2, UserX } from "lucide-react";
import { cn } from "@/lib/utils";
import { useGetProfiles } from "@/queries/useProfileQueries";

/**
 * Pilot-only identity gate for `/triage-pilot`, shown before the very first
 * message: "chọn thẻ của tôi", "chọn thẻ người thân", or "ẩn danh / người
 * mới". Reads the same account-level `useGetProfiles()` the production
 * `/triage` picker (`TriageProfileSelector.tsx`) uses -- read-only, no write,
 * no auth surface touched -- but is otherwise a separate, simpler component:
 * this one also offers an explicit anonymous option, and always lets the
 * pilot page proceed (never blocks on "no profiles yet" the way production
 * does), since anonymous is a fully supported path here.
 *
 * The chosen `profileId` (or `null` for anonymous) only matters for whichever
 * fact targets carry `requires_sex` in `fact_targets.jsonl` (see agent.py's
 * `_sex_compatible`) -- e.g. it stops a male patient/card from being asked
 * about pregnancy. Nothing else in the pilot conversation depends on it.
 */

interface Props {
  onProfileChosen: (profileId: string | null) => void;
}

export function SimplePilotProfileSelector({ onProfileChosen }: Props) {
  const { data: profiles, isLoading } = useGetProfiles();
  const [selectedId, setSelectedId] = useState<string | null | undefined>(undefined);

  const canContinue = selectedId !== undefined;

  return (
    <div className="rounded-2xl border border-border bg-card p-5">
      <label className="text-sm font-bold uppercase tracking-wider text-slate-700 dark:text-slate-200">
        Đang khám cho ai?
      </label>
      <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">
        Chọn một hồ sơ để AI biết đúng tuổi/giới tính khi hỏi, hoặc chọn ẩn danh nếu không muốn
        gắn với hồ sơ nào.
      </p>

      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
        {isLoading ? (
          <div className="col-span-full flex items-center justify-center py-6 text-slate-400">
            <Loader2 className="size-6 animate-spin" aria-hidden="true" />
          </div>
        ) : (
          profiles?.map((profile) => (
            <button
              key={profile.id}
              type="button"
              onClick={() => setSelectedId(profile.id)}
              className={cn(
                "flex items-center gap-3 rounded-xl border-2 p-3 text-left transition-colors",
                selectedId === profile.id
                  ? "border-sky-500 bg-sky-50/60 ring-2 ring-sky-500/20"
                  : "border-slate-100 bg-background hover:bg-muted/80 hover:border-border",
              )}
            >
              <UserCircle2
                className={cn("size-6 shrink-0", selectedId === profile.id ? "text-sky-600" : "text-slate-400")}
                aria-hidden="true"
              />
              <div>
                <div className={cn("font-bold", selectedId === profile.id ? "text-sky-900" : "text-slate-700 dark:text-slate-200")}>
                  {profile.full_name}
                </div>
                <div className="text-xs font-medium text-muted-foreground">
                  {profile.relationship_type}
                  {profile.age != null ? ` • ${profile.age} tuổi` : ""}
                  {profile.gender ? ` • ${profile.gender}` : ""}
                </div>
              </div>
            </button>
          ))
        )}

        <button
          type="button"
          onClick={() => setSelectedId(null)}
          className={cn(
            "flex items-center gap-3 rounded-xl border-2 p-3 text-left transition-colors",
            selectedId === null
              ? "border-sky-500 bg-sky-50/60 ring-2 ring-sky-500/20"
              : "border-slate-100 bg-background hover:bg-muted/80 hover:border-border",
          )}
        >
          <UserX
            className={cn("size-6 shrink-0", selectedId === null ? "text-sky-600" : "text-slate-400")}
            aria-hidden="true"
          />
          <div>
            <div className={cn("font-bold", selectedId === null ? "text-sky-900" : "text-slate-700 dark:text-slate-200")}>
              Ẩn danh / người mới
            </div>
            <div className="text-xs font-medium text-muted-foreground">Không gắn với hồ sơ nào</div>
          </div>
        </button>
      </div>

      <button
        type="button"
        onClick={() => canContinue && onProfileChosen(selectedId ?? null)}
        disabled={!canContinue}
        className="mt-4 flex min-h-11 w-full items-center justify-center rounded-xl bg-sky-600 px-6 text-sm font-bold text-white transition-colors hover:bg-sky-700 disabled:cursor-not-allowed disabled:bg-slate-300"
      >
        Tiếp tục
      </button>
    </div>
  );
}
