"use client";

import { motion } from "framer-motion";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { DURATION } from "@/lib/motion";
import type { SimpleNurseQueuePaginationDTO } from "@/types/simple-nurse";

const pageButton =
  "flex size-11 items-center justify-center rounded-xl border border-border bg-card text-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-background";

export function QueuePagination({
  pagination,
  onPageChange,
}: {
  pagination: SimpleNurseQueuePaginationDTO;
  onPageChange: (page: number) => void;
}) {
  const { page, page_size: pageSize, total_items: total, total_pages: totalPages } = pagination;
  const from = (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);

  return (
    <nav aria-label="Phân trang hàng đợi" className="flex flex-wrap items-center justify-between gap-4 pt-4">
      <p className="text-sm text-muted-foreground">
        Hiển thị{" "}
        <span className="font-semibold tabular-nums text-foreground">
          {from}–{to}
        </span>{" "}
        trên <span className="font-semibold tabular-nums text-foreground">{total}</span> ca
      </p>
      <div className="flex items-center gap-2">
        <motion.button
          type="button"
          whileTap={{ scale: 0.97 }}
          transition={{ duration: DURATION.press }}
          disabled={page <= 1}
          onClick={() => onPageChange(Math.max(1, page - 1))}
          aria-label="Trang trước"
          className={pageButton}
        >
          <ChevronLeft className="size-4" aria-hidden="true" />
        </motion.button>
        <span className="min-w-24 text-center text-sm font-semibold tabular-nums text-foreground">
          Trang {page} / {totalPages}
        </span>
        <motion.button
          type="button"
          whileTap={{ scale: 0.97 }}
          transition={{ duration: DURATION.press }}
          disabled={page >= totalPages}
          onClick={() => onPageChange(Math.min(totalPages, page + 1))}
          aria-label="Trang sau"
          className={pageButton}
        >
          <ChevronRight className="size-4" aria-hidden="true" />
        </motion.button>
      </div>
    </nav>
  );
}
