import Image from "next/image";
import { HeartPulse } from "lucide-react";

import { BACKDROP_PHOTOS, type BackdropPhoto, type BackdropPhotoKey } from "@/components/landing/backdrop-photos";
import { cn } from "@/lib/utils";

/**
 * Bức tường ảnh phía sau đầu trang chủ: những nơi và vật dụng quen thuộc lúc
 * một người lo cho sức khỏe (trạm y tế xã, nhiệt kế, máy đo SpO2, điện thoại
 * trong tay), trôi chậm theo từng cột, xen vài màn hình theo dõi đang chạy.
 * Ảnh để đơn sắc và chìm dưới màu nền: bức tường tạo không khí, màu chỉ dành
 * cho phần thông tin phía trước (nút, mức ESI, phiên mẫu).
 *
 * Đây là phông nền, không phải nội dung: cả khối ẩn khỏi trình đọc màn hình, có
 * một lớp màu nền phủ lên để chữ và phiên mẫu luôn nổi phía trước, và chỉ hiện
 * từ màn hình rộng (lg), nơi hai bên còn khoảng trống; trên điện thoại không ảnh
 * nào được tải. Đứng yên khi người xem bấm dừng và với người đã tắt hiệu ứng
 * chuyển động (globals.css).
 *
 * Hai khối bên dưới cũng có nền động nhưng bố cục khác hẳn: lưới ô kẻ với vạch
 * quét (EvidenceBackdrop), vòng sóng và đường nối (CareLoopBackdrop).
 */

type WallTile = BackdropPhotoKey | "ecg" | "pleth";

/**
 * 10 cột x 7 ô, đủ phủ màn hình rộng tới 4K. Một ảnh không lặp trong cùng cột
 * và không đứng gần chính nó ở cột bên cạnh; ảnh bối cảnh Việt Nam và các màn
 * hình theo dõi nằm ở những cột không bị khối chữ che.
 */
const WALL: WallTile[][] = [
  ["benh-vien-ninh-thuan", "may-do-spo2", "nhiet-ke-dien-tu", "pho-nha-thuoc", "dien-thoai-toi", "tram-y-te-doi", "xe-cuu-thuong"],
  ["tram-y-te-doi", "pleth", "dien-thoai-sang", "ong-nghe-dien-tim", "hanh-lang", "dieu-duong", "nhiet-ke-tran"],
  ["dieu-duong", "nhiet-ke-tran", "xe-cuu-thuong", "phong-mo", "ecg", "ong-nghe", "may-theo-doi"],
  ["ong-nghe", "may-theo-doi", "pho-nha-thuoc", "dien-thoai-toi", "benh-vien-ninh-thuan", "tram-y-te-trang", "may-do-spo2"],
  ["xe-cuu-thuong", "hanh-lang", "nhiet-ke-dien-tu", "tram-y-te-doi", "ong-nghe-dien-tim", "phong-mo", "dien-thoai-sang"],
  ["pho-nha-thuoc", "tram-y-te-trang", "benh-vien-ninh-thuan", "nhiet-ke-tran", "may-do-spo2", "dien-thoai-toi", "dieu-duong"],
  ["may-theo-doi", "phong-mo", "xe-cuu-thuong", "hanh-lang", "ong-nghe", "nhiet-ke-dien-tu", "tram-y-te-doi"],
  ["ong-nghe-dien-tim", "dien-thoai-sang", "pho-nha-thuoc", "pleth", "benh-vien-ninh-thuan", "tram-y-te-trang", "nhiet-ke-tran"],
  ["may-do-spo2", "ecg", "dieu-duong", "nhiet-ke-dien-tu", "dien-thoai-toi", "may-theo-doi", "xe-cuu-thuong"],
  ["hanh-lang", "ong-nghe", "phong-mo", "tram-y-te-doi", "ong-nghe-dien-tim", "dien-thoai-sang", "pho-nha-thuoc"],
];

/** Mỗi cột lệch mép trên và trôi theo nhịp riêng, để bức tường không chuyển động như một khối. */
const COLUMN_RHYTHM = [
  { offset: "-2rem", seconds: 40 },
  { offset: "-4rem", seconds: 35 },
  { offset: "-1rem", seconds: 45 },
  { offset: "-3rem", seconds: 38 },
  { offset: "0rem", seconds: 44 },
  { offset: "-4rem", seconds: 36 },
  { offset: "-2rem", seconds: 42 },
  { offset: "0rem", seconds: 33 },
  { offset: "-3rem", seconds: 39 },
  { offset: "-1rem", seconds: 47 },
] as const;

const SHAPE_CLASS: Record<BackdropPhoto["shape"], string> = {
  wide: "aspect-[4/3]",
  square: "aspect-square",
  tall: "aspect-[4/5]",
};

/** Cột rộng max(12rem, 12vw): quá 1600px thì 12vw lớn hơn. */
const TILE_SIZES = "(min-width: 1600px) 12vw, 192px";

const TILE_CLASS = "relative w-full overflow-hidden rounded-3xl";

/** Một nhịp đặt lặp lại bốn lần trên khung 400 x 100; vệt chạy sang trái đúng hai nhịp nên vòng lặp liền mạch. */
function repeatBeats(start: string, beat: (x: number) => string): string {
  return `${start} ${[0, 100, 200, 300].map(beat).join(" ")}`;
}

const ECG_PATH = repeatBeats(
  "M 0 60",
  (x) =>
    `L ${x + 8} 60 C ${x + 11} 60 ${x + 12} 53 ${x + 15} 53 C ${x + 18} 53 ${x + 19} 60 ${x + 22} 60 ` +
    `L ${x + 27} 60 L ${x + 29} 66 L ${x + 32} 12 L ${x + 35} 76 L ${x + 38} 60 L ${x + 46} 60 ` +
    `C ${x + 50} 60 ${x + 52} 46 ${x + 57} 46 C ${x + 62} 46 ${x + 64} 60 ${x + 68} 60 L ${x + 100} 60`,
);

const PLETH_PATH = repeatBeats(
  "M 0 72",
  (x) =>
    `C ${x + 8} 72 ${x + 12} 24 ${x + 22} 24 C ${x + 32} 24 ${x + 38} 50 ${x + 44} 52 ` +
    `C ${x + 48} 53 ${x + 50} 46 ${x + 55} 47 C ${x + 64} 49 ${x + 80} 72 ${x + 100} 72`,
);

/** Màn hình theo dõi vẽ bằng SVG, nền sáng nét mảnh: điện tim hoặc sóng SpO2, chạy liên tục. */
function MonitorTile({ kind }: { kind: "ecg" | "pleth" }) {
  const ecg = kind === "ecg";
  return (
    <div className={cn(TILE_CLASS, "hero-monitor bg-card", ecg ? "aspect-[4/3]" : "aspect-square")}>
      <span className="live-dot live-teal absolute left-4 top-4 size-2 rounded-full bg-brand" />
      {ecg && <HeartPulse className="absolute right-4 top-4 size-5 text-brand/60" strokeWidth={2} />}
      <div className="absolute inset-x-0 inset-y-[22%] overflow-hidden [mask-image:linear-gradient(to_right,transparent,#000_30%,#000_86%,transparent)]">
        <svg viewBox="0 0 400 100" preserveAspectRatio="none" className="hero-monitor-trace h-full w-[200%]">
          <path
            d={ecg ? ECG_PATH : PLETH_PATH}
            fill="none"
            className={ecg ? "stroke-brand" : "stroke-brand/60"}
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            vectorEffect="non-scaling-stroke"
          />
        </svg>
      </div>
    </div>
  );
}

function PhotoTile({ id }: { id: BackdropPhotoKey }) {
  const photo: BackdropPhoto = BACKDROP_PHOTOS[id];
  return (
    <div className={cn(TILE_CLASS, "bg-brand-edge/40", SHAPE_CLASS[photo.shape])}>
      <Image
        src={photo.src}
        alt=""
        fill
        sizes={TILE_SIZES}
        className="object-cover grayscale"
        style={{ objectPosition: photo.focus }}
      />
    </div>
  );
}

export function HeroBackdrop({ paused }: { paused: boolean }) {
  return (
    <div
      aria-hidden="true"
      data-landing-backdrop="hero"
      data-paused={paused ? "" : undefined}
      className="landing-backdrop hero-wall pointer-events-none absolute inset-0 -z-10 hidden overflow-hidden lg:block"
    >
      <div className="absolute left-1/2 top-0 flex -translate-x-1/2 gap-4">
        {WALL.map((tiles, column) => {
          const { offset, seconds } = COLUMN_RHYTHM[column];
          return (
            <div
              key={column}
              className="hero-wall-column flex w-[max(12rem,12vw)] shrink-0 flex-col gap-4"
              style={{
                marginTop: offset,
                animationDuration: `${seconds}s`,
                // Cột chẵn trôi lên, cột lẻ trôi xuống.
                animationDirection: column % 2 === 0 ? "alternate" : "alternate-reverse",
              }}
            >
              {tiles.map((tile, row) =>
                tile === "ecg" || tile === "pleth" ? (
                  <MonitorTile key={row} kind={tile} />
                ) : (
                  <PhotoTile key={row} id={tile} />
                ),
              )}
            </div>
          );
        })}
      </div>
      <div className="hero-wall-veil absolute inset-0" />
    </div>
  );
}
