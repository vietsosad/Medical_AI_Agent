/**
 * DTO cho tính năng "tìm cơ sở y tế gần nhất"
 * (`/api/v1/facilities/nearby`, xem `src/api/routes_facilities.py`).
 *
 * Ánh xạ một-một với `src/models/facility_schemas.py`. Đây là dữ liệu **địa
 * điểm hành chính**, không phải dữ liệu lâm sàng: không có trường nào ở đây
 * tham gia vào việc xác định mức ESI, và giao diện không được suy ra kết luận y
 * khoa nào từ chúng.
 */

/** Nguồn thực tế đã phục vụ một lần tra cứu. */
export type FacilityDataSource = "google_places" | "local_directory";

/**
 * `UNKNOWN` nghĩa là **chưa xác minh được**, không đồng nghĩa với "không có
 * khoa cấp cứu". Giao diện phải trình bày hai điều đó khác nhau; gộp chúng lại
 * là nói sai về một cơ sở y tế.
 */
export type FacilityEmergencyCapability = "EMERGENCY_DEPARTMENT" | "UNKNOWN";

export interface NearbyFacilityDTO {
  id: string;
  name: string;
  /** HOSPITAL | CLINIC | HEALTH_STATION | SPECIALIST_CENTER */
  facility_type: string;
  address: string;
  latitude: number;
  longitude: number;
  /** Khoảng cách đường chim bay, KHÔNG phải quãng đường đi thực tế. */
  distance_meters: number;
  /** `null` nghĩa là chưa xác minh được số -- giao diện ẩn nút gọi, không bịa số. */
  phone_number: string | null;
  emergency_capability: FacilityEmergencyCapability;
  /** Deep link Google Maps do server dựng sẵn; không chứa và không cần API key. */
  directions_url: string;
  source: string | null;
  source_url: string | null;
}

export interface NearbyFacilitiesResponseDTO {
  facilities: NearbyFacilityDTO[];
  data_source: FacilityDataSource;
  /**
   * True khi nguồn dữ liệu ưu tiên không phục vụ được và hệ thống đã rơi về
   * danh bạ nội bộ. Giao diện dùng cờ này để nói thật rằng danh sách có thể
   * chưa đầy đủ, thay vì lặng lẽ trình bày một kết quả hẹp như thể đó là tất cả.
   */
  degraded: boolean;
  search_radius_meters: number;
  accuracy_meters: number | null;
  disclaimer: string;
}

/** Thân request gửi lên `/facilities/nearby`. Chỉ chứa vị trí, không chứa danh tính. */
export interface NearbyFacilitiesRequestDTO {
  latitude: number;
  longitude: number;
  radius_meters?: number;
  accuracy_meters?: number;
}
