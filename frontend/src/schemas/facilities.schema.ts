import { z } from "zod";

/**
 * Zod schema kiểm định phản hồi của `/api/v1/facilities/nearby` tại ranh giới
 * mạng, cùng mục đích với `simple-triage.schema.ts`.
 *
 * Kiểm định ở đây cố ý chặt với hai trường toạ độ: một giá trị ngoài dải hợp lệ
 * lọt qua được sẽ thành một đường chỉ đường dẫn người bệnh đi sai chỗ, và lỗi
 * đó không có cách nào nhận ra trên giao diện. Thà hỏng ồn ào ở đây.
 */

export const nearbyFacilitySchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  facility_type: z.string(),
  address: z.string(),
  latitude: z.number().min(-90).max(90),
  longitude: z.number().min(-180).max(180),
  distance_meters: z.number().min(0),
  phone_number: z.string().nullable(),
  emergency_capability: z.enum(["EMERGENCY_DEPARTMENT", "UNKNOWN"]),
  // Chỉ nhận đúng deep link công khai của Google Maps. Chặn luôn khả năng một
  // phản hồi bị can thiệp đẩy được người bệnh sang một địa chỉ khác.
  directions_url: z.string().url().startsWith("https://www.google.com/maps/"),
  source: z.string().nullable(),
  source_url: z.string().nullable(),
});

export const nearbyFacilitiesResponseSchema = z.object({
  facilities: z.array(nearbyFacilitySchema),
  data_source: z.enum(["google_places", "local_directory"]),
  degraded: z.boolean(),
  search_radius_meters: z.number().min(0),
  accuracy_meters: z.number().nullable(),
  disclaimer: z.string().min(1),
});
