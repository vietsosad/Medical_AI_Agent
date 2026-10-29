/**
 * Nền sau sơ đồ "không đoán": lưới ô kẻ như giấy điện tim, một vạch quét chậm
 * chạy ngang, vài ô sáng lên đúng lúc vạch đi qua -- tiêu chí được đối chiếu
 * từng ô một. Chỉ một sắc xanh ngọc rất nhạt trên nền trắng: nền lùi lại để
 * sơ đồ và chữ là thứ nổi bật nhất.
 *
 * Khác hai nền còn lại: bức tường ảnh đầu trang là các ô ảnh trôi theo cột,
 * nền "hai màn hình" là vòng sóng và đường nối; ở đây là lưới tĩnh và một vạch.
 */

/** Ô sáng: cột k tính từ giữa khối, hàng m tính từ mép trên, mỗi ô 40 px. Né tiêu đề và sơ đồ. */
const CELLS = [
  { k: 3, m: 1 },
  { k: 6, m: 4 },
  { k: 9, m: 2 },
  { k: 12, m: 5 },
  { k: 15, m: 1 },
  { k: 18, m: 7 },
  { k: -19, m: 3 },
  { k: -17, m: 12 },
  { k: -9, m: 17 },
  { k: 4, m: 18 },
  { k: 11, m: 17 },
  { k: 17, m: 13 },
] as const;

/**
 * Vạch quét đi 2400 px quanh giữa khối trong 8.4 giây (70% của nhịp 12 giây,
 * globals.css), nên lúc nó qua mỗi ô không phụ thuộc bề rộng màn hình.
 */
const SWEEP_SECONDS = 8.4;
const SWEEP_HALF_PX = 1200;

function cellDelay(k: number): string {
  return `${((SWEEP_SECONDS * (SWEEP_HALF_PX + 40 * k)) / (2 * SWEEP_HALF_PX)).toFixed(2)}s`;
}

export function EvidenceBackdrop({ paused }: { paused: boolean }) {
  return (
    <div
      aria-hidden="true"
      data-landing-backdrop="evidence"
      data-paused={paused ? "" : undefined}
      className="landing-backdrop pointer-events-none absolute inset-0 -z-10 hidden overflow-hidden lg:block"
    >
      <div className="evidence-grid absolute inset-0" />
      {CELLS.map(({ k, m }) => (
        <span
          key={`${k}-${m}`}
          className="evidence-cell absolute size-[39px]"
          style={{ left: `calc(50% + ${40 * k + 1}px)`, top: `${40 * m + 1}px`, animationDelay: cellDelay(k) }}
        />
      ))}
      <div className="evidence-scan absolute inset-y-0 w-60" />
    </div>
  );
}
