import { esiTheme } from "@/components/clinical/nurse-simple/esi-theme";
import { cn } from "@/lib/utils";

/** Cùng màu chip với mọi màn khác (bản sáng và tối nằm sẵn trong `esiTheme`). */
export function esiTileClass(level: number): string {
  return esiTheme(level).chip;
}

/**
 * Ô vuông mức ESI ở đầu mỗi phiên. Màu luôn đi kèm chữ: số mức hiện rõ, tên
 * mức ("Cấp cứu") đọc được cho trình đọc màn hình. Null là chưa có mức nào,
 * hiển thị "?" với viền đứt, không tô màu khẩn cấp nào.
 */
export function EsiTile({ level, className }: { level: number | null; className?: string }) {
  if (level === null) {
    return (
      <span
        className={cn(
          "flex size-12 shrink-0 items-center justify-center rounded-2xl border border-dashed border-slate-400 bg-muted text-xl font-extrabold text-slate-600 dark:border-slate-500 dark:text-slate-300",
          className,
        )}
      >
        <span aria-hidden="true">?</span>
        <span className="sr-only">Chưa có mức ESI</span>
      </span>
    );
  }

  return (
    <span
      className={cn(
        "flex size-12 shrink-0 flex-col items-center justify-center rounded-2xl border leading-none",
        esiTileClass(level),
        className,
      )}
      title={`ESI ${level} · ${esiTheme(level).label}`}
    >
      <span className="text-xs font-bold">ESI</span>
      <span className="text-xl font-extrabold">{level}</span>
      <span className="sr-only">· {esiTheme(level).label}</span>
    </span>
  );
}
