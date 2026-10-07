import { useQuery } from "@tanstack/react-query";

import { FACILITY_QUERY_KEYS } from "@/queries/facility-query-keys";
import { facilitiesService } from "@/services/facilities.service";
import type { GeolocationFix } from "@/hooks/useGeolocation";

export { FACILITY_QUERY_KEYS } from "@/queries/facility-query-keys";

/**
 * Khớp với `facility_cache_ttl_seconds` mặc định của backend (300 giây). Giữ hai
 * con số bằng nhau để một lần bấm lại trong vài phút không đi ra tận Google
 * Places thêm lần nữa -- danh sách bệnh viện quanh một điểm không đổi theo phút.
 */
const FACILITY_STALE_TIME_MS = 5 * 60_000;

/**
 * Cơ sở y tế quanh một vị trí đã được người bệnh **chủ động cho phép** chia sẻ.
 *
 * Truy vấn chỉ chạy khi `fix` khác null, tức là chỉ sau khi người dùng bấm nút
 * và trình duyệt trả về toạ độ. Không có đường nào để hook này tự xin vị trí.
 *
 * Cố ý không `retry`: backend đã tự rơi về danh bạ nội bộ khi nguồn ngoài hỏng,
 * nên một lỗi tới được đây là lỗi mạng hoặc lỗi phiên -- thử lại ngầm chỉ kéo
 * dài thời gian người bệnh nhìn vào ô trống mà không đổi được kết quả.
 */
export function useNearbyFacilities(fix: GeolocationFix | null) {
  return useQuery({
    queryKey: fix
      ? FACILITY_QUERY_KEYS.nearby(fix.latitude, fix.longitude)
      : [...FACILITY_QUERY_KEYS.all, "nearby", "inactive"],
    queryFn: () =>
      facilitiesService.searchNearby({
        latitude: (fix as GeolocationFix).latitude,
        longitude: (fix as GeolocationFix).longitude,
        ...((fix as GeolocationFix).accuracyMeters !== null
          ? { accuracy_meters: (fix as GeolocationFix).accuracyMeters as number }
          : {}),
      }),
    enabled: fix !== null,
    staleTime: FACILITY_STALE_TIME_MS,
    retry: false,
  });
}
