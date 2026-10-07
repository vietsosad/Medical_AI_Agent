/**
 * Khoá cache cho tính năng tìm cơ sở y tế.
 *
 * Toạ độ trong khoá được làm tròn tới 3 chữ số thập phân (~110m), đúng bằng độ
 * mịn cache của backend. Hai lợi ích, cả hai đều quan trọng: người bệnh nhích
 * vài mét rồi bấm lại sẽ dùng lại kết quả cũ thay vì gọi thêm một lần API tính
 * tiền, và bản thân khoá cache trong bộ nhớ trình duyệt không giữ vị trí chính
 * xác của ai.
 */

export const FACILITY_COORDINATE_PRECISION = 3;

/** Làm tròn một toạ độ về đúng độ mịn dùng làm khoá cache. */
export const roundCoordinate = (value: number): number =>
  Number(value.toFixed(FACILITY_COORDINATE_PRECISION));

export const FACILITY_QUERY_KEYS = {
  all: ["facilities"] as const,
  nearby: (latitude: number, longitude: number) =>
    [
      ...FACILITY_QUERY_KEYS.all,
      "nearby",
      roundCoordinate(latitude),
      roundCoordinate(longitude),
    ] as const,
};
