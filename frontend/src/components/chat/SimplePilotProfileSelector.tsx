"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { Check, UserRound, UserX } from "lucide-react";

import { DURATION, EASE_OUT, staggerDelay } from "@/lib/motion";
import { genderLabel, relationLabel } from "@/lib/profile-labels";
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
  /** Hồ sơ người dùng vừa chọn ở trang hồ sơ ("Sàng lọc cho <tên>"). Chỉ được
   * chọn sẵn khi nó thật sự có trong danh sách -- vẫn phải bấm "Tiếp tục". */
  preselectedId?: string | null;
}

function initialOf(name: string): string {
  return name.trim().split(/\s+/).at(-1)?.charAt(0).toUpperCase() ?? "?";
}

export function SimplePilotProfileSelector({ onProfileChosen, preselectedId = null }: Props) {
  const { data: profiles, isLoading } = useGetProfiles();
  const [pickedId, setPickedId] = useState<string | null | undefined>(undefined);
  const preselected =
    preselectedId && profiles?.some((profile) => profile.id === preselectedId) ? preselectedId : undefined;
  const selectedId = pickedId !== undefined ? pickedId : preselected;

  const canContinue = selectedId !== undefined;

  const options = [
    ...(profiles ?? []).map((profile) => ({
      id: profile.id as string | null,
      title: profile.full_name,
      detail: [
        relationLabel(profile.relationship_type, profile.is_primary),
        profile.age != null ? `${profile.age} tuổi` : null,
        genderLabel(profile.gender),
      ]
        .filter(Boolean)
        .join(" · "),
      initial: initialOf(profile.full_name),
    })),
    { id: null, title: "Ẩn danh / người mới", detail: "Không gắn với hồ sơ nào", initial: null },
  ];

  return (
    <section aria-labelledby="who-title" className="w-full">
      <h2 id="who-title" className="text-lg font-bold text-foreground">
        Đang khám cho ai?
      </h2>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">
        Chọn một hồ sơ để trợ lý hỏi đúng theo tuổi và giới tính, hoặc chọn ẩn danh nếu không muốn gắn với hồ sơ
        nào.
      </p>

      <div role="radiogroup" aria-labelledby="who-title" className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
        {isLoading
          ? [0, 1].map((key) => (
              <div key={key} className="skeleton-sweep relative h-16 overflow-hidden rounded-2xl bg-muted" />
            ))
          : options.map((option, index) => {
              const selected = selectedId === option.id;
              return (
                <motion.button
                  key={option.id ?? "anonymous"}
                  type="button"
                  role="radio"
                  aria-checked={selected}
                  onClick={() => setPickedId(option.id)}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: DURATION.base, ease: EASE_OUT, delay: staggerDelay(index) }}
                  whileTap={{ scale: 0.98 }}
                  className={cn(
                    "flex min-h-16 items-center gap-4 rounded-2xl border px-4 py-2 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2",
                    selected
                      ? "border-brand bg-brand-soft shadow-[0_0_0_1px_var(--brand)]"
                      : "border-border bg-card hover:bg-muted",
                  )}
                >
                  <span
                    aria-hidden="true"
                    className={cn(
                      "flex size-10 shrink-0 items-center justify-center rounded-full text-base font-bold transition-colors",
                      selected ? "bg-brand text-brand-foreground" : "bg-muted text-muted-foreground",
                    )}
                  >
                    {selected ? (
                      <Check className="size-5" strokeWidth={3} />
                    ) : option.initial ? (
                      option.initial
                    ) : option.id === null ? (
                      <UserX className="size-5" />
                    ) : (
                      <UserRound className="size-5" />
                    )}
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate text-base font-bold text-foreground">{option.title}</span>
                    {option.detail && (
                      <span className="block truncate text-sm text-muted-foreground">{option.detail}</span>
                    )}
                  </span>
                </motion.button>
              );
            })}
      </div>

      <motion.button
        type="button"
        onClick={() => canContinue && onProfileChosen(selectedId ?? null)}
        disabled={!canContinue}
        whileTap={canContinue ? { scale: 0.97 } : undefined}
        className="mt-6 flex min-h-12 w-full items-center justify-center rounded-xl bg-brand px-6 text-base font-bold text-brand-foreground transition-colors hover:bg-brand-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground"
      >
        Tiếp tục
      </motion.button>
    </section>
  );
}
