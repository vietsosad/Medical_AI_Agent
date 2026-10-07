/**
 * Đường dẫn Google Maps dùng được mà không cần API key.
 *
 * Toàn bộ tính năng tìm cơ sở y tế cố ý **không nhúng SDK bản đồ nào** vào
 * trình duyệt. Nhúng bản đồ tương tác sẽ kéo theo một khoá API nằm trong
 * bundle, mà mọi biến `NEXT_PUBLIC_*` đều lộ công khai cho bất kỳ ai mở trình
 * duyệt. Google Maps URLs giải quyết trọn nhu cầu chỉ đường mà không cần khoá,
 * và trên điện thoại còn mở thẳng ứng dụng Maps đã cài.
 *
 * Deep link chỉ đường tới từng cơ sở do **backend** dựng (`directions_url`), để
 * định dạng chỉ nằm ở một nơi. File này chỉ giữ đường dẫn dự phòng: thứ giao
 * diện cần khi chưa có toạ độ nào để mà chỉ đường.
 */

/**
 * Mở Google Maps với một câu tìm kiếm, không kèm toạ độ.
 *
 * Đây là lối đi khi người bệnh từ chối quyền vị trí hoặc thiết bị không định vị
 * được: Google Maps sẽ tự dùng vị trí của chính nó (thường đã được cấp quyền từ
 * trước) để tìm. Nhờ vậy, việc từ chối chia sẻ vị trí với ứng dụng này không
 * đồng nghĩa với việc mất luôn đường tới bệnh viện.
 */
export function buildMapsSearchUrl(query: string): string {
  const params = new URLSearchParams({ api: "1", query });
  return `https://www.google.com/maps/search/?${params.toString()}`;
}

/** Câu tìm kiếm dự phòng mặc định cho các mức ESI khẩn. */
export const NEAREST_HOSPITAL_QUERY = "bệnh viện gần đây";

/**
 * Khoảng cách dạng người đọc được.
 *
 * Luôn là đường chim bay, nên nơi gọi phải nói rõ điều đó ở ngay cạnh con số.
 * Dưới 1km hiển thị theo mét (làm tròn tới 10m, vì sai số định vị thường còn
 * lớn hơn thế), từ 1km trở lên hiển thị một chữ số thập phân.
 */
export function formatDistance(meters: number): string {
  if (!Number.isFinite(meters) || meters < 0) return "";
  if (meters < 1000) {
    return `${Math.max(0, Math.round(meters / 10) * 10)} m`;
  }
  return `${(meters / 1000).toFixed(1)} km`;
}
