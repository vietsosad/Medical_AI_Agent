"use client";

import React from "react";
import {
  AlertTriangle,
  Building2,
  Loader2,
  LocateFixed,
  MapPin,
  Navigation,
  PhoneCall,
  RefreshCw,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { NEAREST_HOSPITAL_QUERY, buildMapsSearchUrl, formatDistance } from "@/lib/maps";
import { useGeolocation } from "@/hooks/useGeolocation";
import { useNearbyFacilities } from "@/queries/useFacilityQueries";
import type { EsiLevel } from "@/types/clinical-history";
import type { NearbyFacilityDTO } from "@/types/facilities";

/**
 * ============================================================================
 * [NEARBY FACILITIES CARD] TÌM CƠ SỞ Y TẾ GẦN NGƯỜI BỆNH (ESI 1 / 2 / 3)
 * ============================================================================
 *
 * Thẻ này chỉ **trình bày** dữ liệu địa điểm mà máy chủ đã trả về. Nó không
 * phát hiện, không suy luận và không thay đổi bất kỳ trạng thái lâm sàng nào;
 * `esiLevel` phải là mức mà backend đã chốt (xem `displayedEsiLevel` ở
 * `triage-pilot/page.tsx`), không bao giờ là mức do giao diện tự đoán.
 *
 * **Vì sao ba mức ESI lại có ba cách trình bày khác nhau.** Không phải để đổi
 * màu cho đẹp, mà vì hành động đúng ở mỗi mức là khác nhau:
 *
 * - **ESI 1**: hành động đúng là gọi 115, không phải tự tìm đường tới viện. Một
 *   người ở mức này tự lái xe đi là tình huống nguy hiểm. Bản đồ ở đây đóng vai
 *   phụ: để người bệnh hoặc người nhà đọc địa chỉ cho tổng đài.
 * - **ESI 2**: cần tới nơi càng sớm càng tốt, nhưng vẫn phải nói rõ là không
 *   nên tự lái xe.
 * - **ESI 3**: chỉ đường mới thực sự là hành động chính.
 *
 * **Vì sao không có bản đồ nhúng.** Nhúng bản đồ tương tác đòi hỏi một khoá API
 * nằm trong bundle trình duyệt, tức là lộ công khai. Deep link Google Maps làm
 * đúng việc cần làm mà không cần khoá nào -- xem `@/lib/maps`.
 *
 * Tuân thủ quy tắc 3.3 của `.agents/rules/frontend-rules.md`: 100% icon vector
 * Lucide, cấm emoji.
 */

interface UrgentGuidance {
  /** Câu mô tả hành động đúng ở mức này. */
  headline: string;
  body: string;
  /** True khi việc gọi 115 phải đứng trước danh sách cơ sở y tế. */
  callFirst: boolean;
  bandClass: string;
  accentClass: string;
}

/**
 * Chỉ ba mức khẩn có mặt ở đây. ESI 4/5 không phải tình huống cần tìm cơ sở cấp
 * cứu gấp, và dựng một lối đi "tìm bệnh viện ngay" cho chúng sẽ tạo ra cảm giác
 * khẩn cấp mà chính hệ thống vừa kết luận là không có.
 */
const URGENT_GUIDANCE: Record<1 | 2 | 3, UrgentGuidance> = {
  1: {
    headline: "Gọi 115 ngay lập tức",
    body:
      "Tình trạng này có thể đe dọa tính mạng. Hãy gọi 115 trước tiên. Danh sách bên dưới để bạn hoặc người nhà đọc địa chỉ cho tổng đài, không phải để tự di chuyển.",
    callFirst: true,
    bandClass: "bg-rose-50 text-rose-900",
    accentClass: "bg-rose-700 hover:bg-rose-800 focus-visible:ring-rose-600",
  },
  2: {
    headline: "Cần được thăm khám càng sớm càng tốt",
    body:
      "Hãy nhờ người khác chở đi hoặc gọi 115. Không tự lái xe, vì tình trạng có thể nặng lên trên đường.",
    callFirst: true,
    bandClass: "bg-amber-50 text-amber-950",
    accentClass: "bg-amber-700 hover:bg-amber-800 focus-visible:ring-amber-600",
  },
  3: {
    headline: "Nên đến cơ sở y tế sớm",
    body:
      "Bạn có thể chủ động di chuyển tới một trong các cơ sở bên dưới. Nếu triệu chứng nặng lên trên đường, hãy gọi 115.",
    callFirst: false,
    bandClass: "bg-sky-50 text-sky-950",
    accentClass: "bg-sky-600 hover:bg-sky-700 focus-visible:ring-sky-600",
  },
};

const FACILITY_TYPE_LABELS: Record<string, string> = {
  HOSPITAL: "Bệnh viện",
  CLINIC: "Phòng khám",
  HEALTH_STATION: "Trạm y tế",
  SPECIALIST_CENTER: "Cơ sở chuyên khoa",
};

function facilityTypeLabel(rawType: string): string {
  return FACILITY_TYPE_LABELS[rawType] ?? "Cơ sở y tế";
}

/** Nút gọi 115. Luôn hiển thị ở mọi nhánh hỏng -- đây là lối thoát không được phép mất. */
function EmergencyCallButton({ className }: { className?: string }) {
  return (
    <a
      href="tel:115"
      className={cn(
        "flex min-h-12 items-center justify-center gap-2 rounded-xl px-4 text-base font-black text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2",
        "bg-rose-700 hover:bg-rose-800 focus-visible:ring-rose-600",
        className,
      )}
      aria-label="Gọi Tổng đài Cấp cứu Quốc gia 115"
    >
      <PhoneCall className="size-5 shrink-0" aria-hidden="true" />
      Gọi 115
    </a>
  );
}

/** Lối đi khi không có toạ độ: để Google Maps tự dùng vị trí của chính nó. */
function ManualSearchLink() {
  return (
    <a
      href={buildMapsSearchUrl(NEAREST_HOSPITAL_QUERY)}
      target="_blank"
      rel="noopener noreferrer"
      className="flex min-h-12 items-center justify-center gap-2 rounded-xl border-2 border-slate-300 bg-card px-4 text-sm font-bold text-slate-800 transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-500 focus-visible:ring-offset-2 dark:text-slate-100 dark:border-slate-700"
    >
      <MapPin className="size-4 shrink-0" aria-hidden="true" />
      Tự tìm trên Google Maps
    </a>
  );
}

function FacilityRow({ facility }: { facility: NearbyFacilityDTO }) {
  return (
    <li className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <p className="flex items-center gap-2 text-base font-bold leading-6 text-slate-950 dark:text-slate-50">
          <Building2 className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
          <span className="truncate">{facility.name}</span>
        </p>
        <p className="mt-2 text-sm leading-6 text-slate-700 dark:text-slate-200">{facility.address}</p>
        <p className="mt-2 flex flex-wrap items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
          <span className="font-bold text-slate-800 dark:text-slate-100">
            Cách khoảng {formatDistance(facility.distance_meters)}
          </span>
          <span aria-hidden="true">·</span>
          <span>{facilityTypeLabel(facility.facility_type)}</span>
          {/* Chỉ nói "có khoa cấp cứu" khi dữ liệu nói rõ như vậy. Trạng thái
              UNKNOWN cố ý không hiển thị gì: viết "chưa rõ có cấp cứu hay
              không" lên từng dòng vừa gây nhiễu vừa dễ bị đọc thành "không
              có". Phần chú thích chung ở cuối thẻ đã nói đúng điều đó một lần. */}
          {facility.emergency_capability === "EMERGENCY_DEPARTMENT" && (
            <>
              <span aria-hidden="true">·</span>
              <span className="rounded-lg bg-emerald-50 px-2 py-1 text-sm font-semibold text-emerald-800">
                Có khoa cấp cứu
              </span>
            </>
          )}
        </p>
      </div>

      <div className="flex shrink-0 flex-col gap-2 sm:flex-row sm:items-center">
        {/* Số điện thoại chỉ hiện khi đã có thật. Không có số thì không có nút,
            tuyệt đối không dựng một số giữ chỗ. */}
        {facility.phone_number && (
          <a
            href={`tel:${facility.phone_number.replace(/\s/g, "")}`}
            className="flex min-h-12 items-center justify-center gap-2 rounded-xl border-2 border-slate-300 bg-card px-4 text-sm font-bold text-slate-800 transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-500 focus-visible:ring-offset-2 dark:text-slate-100 dark:border-slate-700"
          >
            <PhoneCall className="size-4 shrink-0" aria-hidden="true" />
            Gọi
          </a>
        )}
        <a
          href={facility.directions_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex min-h-12 items-center justify-center gap-2 rounded-xl bg-sky-600 px-4 text-sm font-bold text-white transition-colors hover:bg-sky-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2"
          aria-label={`Chỉ đường tới ${facility.name} trên Google Maps`}
        >
          <Navigation className="size-4 shrink-0" aria-hidden="true" />
          Chỉ đường
        </a>
      </div>
    </li>
  );
}

function FacilitySkeleton() {
  return (
    <ul className="divide-y divide-slate-200" aria-hidden="true">
      {[0, 1, 2].map((row) => (
        <li key={`facility-skeleton-${row}`} className="flex flex-col gap-2 p-4">
          <div className="h-4 w-1/2 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
          <div className="h-4 w-3/4 animate-pulse rounded bg-muted" />
          <div className="h-4 w-1/4 animate-pulse rounded bg-muted" />
        </li>
      ))}
    </ul>
  );
}

export function NearbyFacilitiesCard({ esiLevel }: { esiLevel: EsiLevel | null }) {
  const geolocation = useGeolocation();
  const facilitiesQuery = useNearbyFacilities(geolocation.fix);

  // Tầng chặn theo mức ESI. Đặt sau các hook để thứ tự hook không đổi giữa các
  // lần render (quy tắc của React), nhưng trước mọi thứ hiển thị: không có mức,
  // hoặc mức không khẩn, thì thẻ này không tồn tại trên màn hình.
  if (esiLevel === null || esiLevel > 3) return null;
  const guidance = URGENT_GUIDANCE[esiLevel as 1 | 2 | 3];

  const hasLocationProblem =
    geolocation.status === "denied" ||
    geolocation.status === "unavailable" ||
    geolocation.status === "timeout";
  const isBusy = geolocation.isLocating || (geolocation.fix !== null && facilitiesQuery.isLoading);
  const result = facilitiesQuery.data;

  return (
    <section
      aria-labelledby="nearby-facilities-heading"
      className="overflow-hidden rounded-2xl border-2 border-border bg-card shadow-sm"
    >
      {/* Dải hướng dẫn theo mức khẩn. Với ESI 1, đây là một chỉ dẫn cấp cứu
          xuất hiện động giữa dòng hội thoại nên phải được trình đọc màn hình
          đọc ngay (quy tắc 3.6 của frontend-rules). */}
      <div
        className={cn("p-4 sm:p-6", guidance.bandClass)}
        {...(esiLevel === 1 ? { role: "alert" as const, "aria-live": "assertive" as const } : {})}
      >
        <h3 id="nearby-facilities-heading" className="text-base font-black leading-6 sm:text-lg">
          {guidance.headline}
        </h3>
        <p className="mt-2 text-sm leading-6">{guidance.body}</p>

        {guidance.callFirst && (
          <div className="mt-4 flex flex-col gap-2 sm:flex-row">
            <EmergencyCallButton className="sm:min-w-40" />
          </div>
        )}
      </div>

      {/* Khối tra cứu vị trí */}
      <div className="border-t border-border p-4 sm:p-6">
        <p className="flex items-center gap-2 text-base font-bold text-slate-950 dark:text-slate-50">
          <MapPin className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
          Cơ sở y tế gần bạn
        </p>

        {geolocation.status === "idle" && (
          <div className="mt-4 flex flex-col gap-4">
            <p className="text-sm leading-6 text-slate-700 dark:text-slate-200">
              Bật định vị để hệ thống liệt kê các cơ sở y tế gần vị trí của bạn và mở đường chỉ dẫn
              trên Google Maps. Vị trí chỉ được dùng cho lần tra cứu này và không được lưu lại.
            </p>
            <div className="flex flex-col gap-2 sm:flex-row">
              <button
                type="button"
                onClick={geolocation.request}
                className={cn(
                  "flex min-h-12 items-center justify-center gap-2 rounded-xl px-4 text-sm font-bold text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2",
                  guidance.accentClass,
                )}
              >
                <LocateFixed className="size-4 shrink-0" aria-hidden="true" />
                Bật định vị để tìm cơ sở y tế gần nhất
              </button>
              <ManualSearchLink />
            </div>
          </div>
        )}

        {isBusy && (
          <div className="mt-4 flex items-center gap-2 text-sm font-semibold text-slate-600 dark:text-slate-300">
            <Loader2 className="size-4 animate-spin text-sky-600" aria-hidden="true" />
            {geolocation.isLocating ? "Đang xác định vị trí..." : "Đang tìm cơ sở y tế gần bạn..."}
          </div>
        )}

        {/* Quyền vị trí bị từ chối hoặc thiết bị không định vị được. Đây KHÔNG
            phải ngõ cụt: vẫn còn 115 và vẫn còn cách tự tìm trên Google Maps. */}
        {hasLocationProblem && (
          <div className="mt-4 flex flex-col gap-4">
            <p className="flex items-start gap-2 text-sm leading-6 text-slate-700 dark:text-slate-200">
              <AlertTriangle className="mt-1 size-4 shrink-0 text-amber-600" aria-hidden="true" />
              <span>{geolocation.errorMessage}</span>
            </p>
            <div className="flex flex-col gap-2 sm:flex-row">
              <ManualSearchLink />
              <button
                type="button"
                onClick={geolocation.request}
                className="flex min-h-12 items-center justify-center gap-2 rounded-xl border-2 border-slate-300 bg-card px-4 text-sm font-bold text-slate-800 transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-500 focus-visible:ring-offset-2 dark:text-slate-100 dark:border-slate-700"
              >
                <RefreshCw className="size-4 shrink-0" aria-hidden="true" />
                Thử định vị lại
              </button>
              {/* Trang này không có nút SOS nào khác, nên mọi nhánh hỏng đều
                  phải tự mang theo đường gọi 115. Mức 1 và 2 đã có nút ấy ở dải
                  hướng dẫn phía trên; chỉ mức 3 mới cần thêm ở đây. */}
              {!guidance.callFirst && <EmergencyCallButton />}
            </div>
          </div>
        )}

        {geolocation.fix !== null && facilitiesQuery.isLoading && <FacilitySkeleton />}

        {facilitiesQuery.isError && (
          <div className="mt-4 flex flex-col gap-4">
            <p className="flex items-start gap-2 text-sm leading-6 text-rose-900">
              <AlertTriangle className="mt-1 size-4 shrink-0" aria-hidden="true" />
              <span>
                {facilitiesQuery.error instanceof Error
                  ? facilitiesQuery.error.message
                  : "Không tra cứu được cơ sở y tế gần bạn."}
              </span>
            </p>
            <div className="flex flex-col gap-2 sm:flex-row">
              <ManualSearchLink />
              <button
                type="button"
                onClick={() => void facilitiesQuery.refetch()}
                className="flex min-h-12 items-center justify-center gap-2 rounded-xl border-2 border-slate-300 bg-card px-4 text-sm font-bold text-slate-800 transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-500 focus-visible:ring-offset-2 dark:text-slate-100 dark:border-slate-700"
              >
                <RefreshCw className="size-4 shrink-0" aria-hidden="true" />
                Thử lại
              </button>
              {!guidance.callFirst && <EmergencyCallButton />}
            </div>
          </div>
        )}

        {result && result.facilities.length === 0 && (
          <div className="mt-4 flex flex-col gap-4">
            <p className="text-sm leading-6 text-slate-700 dark:text-slate-200">
              Không tìm thấy cơ sở y tế nào trong bán kính{" "}
              {formatDistance(result.search_radius_meters)} quanh vị trí của bạn theo dữ liệu hiện
              có. Điều này không có nghĩa là quanh đây không có cơ sở nào -- hãy thử tìm trực tiếp
              trên Google Maps hoặc gọi 115 để được hướng dẫn.
            </p>
            <div className="flex flex-col gap-2 sm:flex-row">
              <ManualSearchLink />
              <EmergencyCallButton />
            </div>
          </div>
        )}
      </div>

      {/* Danh sách. Dùng đường kẻ ngăn cách thay vì thẻ lồng trong thẻ. */}
      {result && result.facilities.length > 0 && (
        <ul className="divide-y divide-slate-200 border-t border-border">
          {result.facilities.map((facility) => (
            <FacilityRow key={facility.id} facility={facility} />
          ))}
        </ul>
      )}

      {/* Chú thích. Nói đúng giới hạn của dữ liệu, không tô hồng. */}
      {result && (
        <div className="space-y-2 border-t border-border bg-background p-4 text-sm leading-6 text-slate-600 sm:p-6 dark:text-slate-300">
          <p>{result.disclaimer}</p>
          <p>
            Khoảng cách là đường chim bay, không phải quãng đường di chuyển thực tế.
            {result.accuracy_meters !== null && (
              <> Sai số định vị do thiết bị báo khoảng {formatDistance(result.accuracy_meters)}.</>
            )}
          </p>
          <p>
            Nguồn dữ liệu:{" "}
            {result.data_source === "google_places"
              ? "Google Maps"
              : "danh bạ nội bộ của hệ thống (bản nháp, chưa đối chiếu nguồn công bố chính thức)"}
            .
            {result.degraded && (
              <> Nguồn dữ liệu chính đang không phản hồi, nên danh sách có thể chưa đầy đủ.</>
            )}
          </p>
        </div>
      )}
    </section>
  );
}
