"use client";

import type { ReactNode } from "react";
import { AnimatePresence } from "framer-motion";

import type { SimpleNurseQueueItemDTO } from "@/types/simple-nurse";

import { useArrivals } from "./queue-hooks";
import type { QueueView } from "./queue-model";
import { QueueRow } from "./QueueRow";

/**
 * Danh sách ca của một góc nhìn (nhóm + bộ lọc + trang).
 *
 * Nơi gọi đặt `key` theo góc nhìn: đổi tab, lọc hay sang trang thì danh sách
 * cũ biến mất ngay và danh sách mới nổi lên lần lượt, thay vì từng hàng cũ
 * diễn hoạt rời đi. Trong cùng một góc nhìn, component sống qua các lần tự làm
 * mới -- kể cả lúc trống -- nên ca đầu tiên tới một hàng đợi rỗng vẫn được
 * nhận ra là "vừa tới".
 */
export function QueueList({
  items,
  view,
  empty,
}: {
  items: SimpleNurseQueueItemDTO[];
  view: QueueView;
  empty: ReactNode;
}) {
  const arrivals = useArrivals(items.map((item) => item.session_id));

  if (items.length === 0) return <>{empty}</>;

  return (
    <ol aria-label="Danh sách ca" className="flex flex-col gap-2">
      <AnimatePresence>
        {items.map((item, index) => (
          <QueueRow
            key={item.session_id}
            item={item}
            view={view}
            index={index}
            arrived={arrivals.has(item.session_id)}
          />
        ))}
      </AnimatePresence>
    </ol>
  );
}
