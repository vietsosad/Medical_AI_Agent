/**
 * Nền sau khối "Một phiên, hai màn hình": vòng sóng nhạt tỏa ra từ điện thoại
 * người bệnh, hai vùng sáng rất nhẹ sau hai màn hình, và những đường nối có
 * chấm nhỏ chạy từ trái sang phải -- đúng chiều một ca đi từ điện thoại tới
 * hàng đợi của điều dưỡng. Chỉ một sắc xanh ngọc nhạt, không ảnh: nền lùi lại
 * để hai màn hình là thứ nổi bật.
 *
 * Khác hai nền còn lại: không có ô ảnh trôi như đầu trang, không có lưới và
 * vạch quét như khối "không đoán".
 */

/** Ba đường nối trên khung 1600 x 1000, kéo giãn theo khối; chấm của mỗi đường lệch nhịp nhau. */
const SIGNALS = [
  { d: "M -40 300 C 260 240, 420 470, 700 420 S 1180 300, 1640 360", delay: "0s" },
  { d: "M -40 560 C 300 640, 520 470, 820 540 S 1300 690, 1640 600", delay: "-2.2s" },
  { d: "M -40 790 C 340 720, 640 860, 900 770 S 1360 650, 1640 760", delay: "-4.4s" },
] as const;

/** Ba vòng sóng, mỗi vòng lệch một phần ba nhịp 7.8 giây (globals.css). */
const RINGS = ["0s", "-2.6s", "-5.2s"] as const;

export function CareLoopBackdrop({ paused }: { paused: boolean }) {
  return (
    <div
      aria-hidden="true"
      data-landing-backdrop="care"
      data-paused={paused ? "" : undefined}
      className="landing-backdrop pointer-events-none absolute inset-0 -z-10 hidden overflow-hidden lg:block"
    >
      <div className="care-zones absolute inset-0" />
      {RINGS.map((delay) => (
        <span
          key={delay}
          className="care-ring absolute size-[52rem] -translate-x-1/2 -translate-y-1/2 rounded-full"
          style={{ animationDelay: delay }}
        />
      ))}
      <svg viewBox="0 0 1600 1000" preserveAspectRatio="none" fill="none" className="absolute inset-0 size-full">
        {SIGNALS.map(({ d, delay }) => (
          <g key={d}>
            <path d={d} pathLength={1000} className="care-signal-track" />
            <path d={d} pathLength={1000} className="care-signal-pulse" style={{ animationDelay: delay }} />
          </g>
        ))}
      </svg>
    </div>
  );
}
