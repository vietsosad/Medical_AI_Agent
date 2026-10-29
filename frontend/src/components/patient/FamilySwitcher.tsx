"use client";

import { useRef, type KeyboardEvent } from "react";
import { motion } from "framer-motion";
import { Plus } from "lucide-react";

import { avatarInitial, avatarToneClass, relationTitle, switcherLabel } from "@/components/patient/family-identity";
import { DURATION, EASE_IN_OUT } from "@/lib/motion";
import { cn } from "@/lib/utils";
import type { ProfileResponseDTO } from "@/services/profile.service";

interface FamilySwitcherProps {
  profiles: ProfileResponseDTO[];
  selectedId: string | null;
  onSelect: (profileId: string) => void;
  onAdd: () => void;
  /** id của vùng hiển thị hồ sơ đang chọn (tabpanel). */
  panelId: string;
  /** Duy nhất trên trang: vòng sáng trượt giữa các người nhờ layoutId này. */
  layoutId: string;
  idPrefix?: string;
  className?: string;
}

const RING_TRANSITION = { duration: DURATION.base, ease: EASE_IN_OUT };

export function familyTabId(idPrefix: string, profileId: string): string {
  return `${idPrefix}-${profileId}`;
}

/**
 * Hàng vòng tròn chữ cái để chọn người trong gia đình ("Tôi", người thân,
 * "Thêm"). Vòng viền thương hiệu trượt từ người cũ sang người mới, nên mắt
 * thấy ngay hồ sơ bên dưới vừa đổi sang ai. Tablist chuẩn WAI-ARIA: phím mũi
 * tên, Home, End chuyển người; nút "Thêm" nằm ngoài tablist.
 */
export function FamilySwitcher({
  profiles,
  selectedId,
  onSelect,
  onAdd,
  panelId,
  layoutId,
  idPrefix = "family-member",
  className,
}: FamilySwitcherProps) {
  const tabsRef = useRef<Array<HTMLButtonElement | null>>([]);
  // Không ai được chọn (chưa đồng bộ xong) thì người đầu tiên nhận tiêu điểm Tab.
  const focusableId = profiles.some((profile) => profile.id === selectedId) ? selectedId : profiles[0]?.id;

  const moveTo = (index: number) => {
    const profile = profiles[index];
    if (!profile) return;
    onSelect(profile.id);
    tabsRef.current[index]?.focus();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const last = profiles.length - 1;
    if (event.key === "ArrowRight") {
      event.preventDefault();
      moveTo(index === last ? 0 : index + 1);
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      moveTo(index === 0 ? last : index - 1);
    } else if (event.key === "Home") {
      event.preventDefault();
      moveTo(0);
    } else if (event.key === "End") {
      event.preventDefault();
      moveTo(last);
    }
  };

  return (
    <div className={cn("flow-rail flex items-start gap-4 overflow-x-auto py-2", className)}>
      <div role="tablist" aria-label="Chọn người trong gia đình" className="flex items-start gap-4">
        {profiles.map((profile, index) => {
          const selected = profile.id === selectedId;
          return (
            <button
              key={profile.id}
              ref={(node) => {
                tabsRef.current[index] = node;
              }}
              id={familyTabId(idPrefix, profile.id)}
              type="button"
              role="tab"
              aria-selected={selected}
              aria-controls={panelId}
              tabIndex={profile.id === focusableId ? 0 : -1}
              onClick={() => onSelect(profile.id)}
              onKeyDown={(event) => handleKeyDown(event, index)}
              className="group flex w-16 shrink-0 flex-col items-center gap-2 rounded-2xl text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            >
              <span className="relative flex size-16 items-center justify-center">
                {selected && (
                  <motion.span
                    layoutId={layoutId}
                    transition={RING_TRANSITION}
                    aria-hidden="true"
                    className="absolute inset-0 rounded-full border-2 border-brand"
                  />
                )}
                <span
                  aria-hidden="true"
                  className={cn(
                    "flex size-14 items-center justify-center rounded-full text-lg font-extrabold transition duration-[180ms] group-hover:-translate-y-0.5 group-active:scale-[0.97] motion-reduce:transition-none motion-reduce:group-hover:translate-y-0",
                    selected ? "bg-brand text-brand-foreground" : avatarToneClass(profile.avatar_color),
                  )}
                >
                  {avatarInitial(profile.full_name)}
                </span>
              </span>
              <span
                className={cn(
                  "max-w-16 truncate leading-5",
                  selected ? "font-extrabold text-foreground" : "font-semibold text-muted-foreground",
                )}
              >
                {switcherLabel(profile)}
              </span>
              <span className="sr-only">
                , {profile.full_name}, {relationTitle(profile)}
              </span>
            </button>
          );
        })}
      </div>

      <button
        type="button"
        onClick={onAdd}
        className="group flex w-16 shrink-0 flex-col items-center gap-2 rounded-2xl text-sm font-semibold text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-background"
      >
        <span className="flex size-16 items-center justify-center">
          <span className="flex size-14 items-center justify-center rounded-full border border-dashed border-slate-400 transition duration-[180ms] group-hover:border-brand group-hover:text-brand group-active:scale-[0.97] motion-reduce:transition-none dark:border-slate-500">
            <Plus className="size-6" aria-hidden="true" />
          </span>
        </span>
        <span className="leading-5">
          Thêm<span className="sr-only"> người trong gia đình</span>
        </span>
      </button>
    </div>
  );
}
