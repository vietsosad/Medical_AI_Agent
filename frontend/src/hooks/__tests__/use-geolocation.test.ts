import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useGeolocation } from "@/hooks/useGeolocation";

/**
 * Hook này đứng ngay trước một hộp thoại xin quyền của trình duyệt, với một
 * loại dữ liệu nhạy cảm. Hai điều phải đúng tuyệt đối:
 *
 * 1. **Không bao giờ tự xin vị trí.** Chỉ một hành động rõ ràng của người dùng
 *    mới được kích hoạt. Một lời xin quyền bật lên khi vừa mở trang thường bị
 *    bấm "Chặn" theo phản xạ, và trình duyệt ghi nhớ lựa chọn đó cho cả tên
 *    miền -- hỏng luôn cả những lần sau, đúng lúc cần nhất.
 * 2. **Mọi nhánh hỏng đều phải kết thúc ở một trạng thái đọc được.** Không có
 *    nhánh nào để hook treo mãi ở "đang định vị".
 */

const ERROR_CODES = { PERMISSION_DENIED: 1, POSITION_UNAVAILABLE: 2, TIMEOUT: 3 } as const;

type PositionCallback = (position: GeolocationPosition) => void;
type ErrorCallback = (error: GeolocationPositionError) => void;

const getCurrentPosition = vi.fn();

function installGeolocation(): void {
  Object.defineProperty(navigator, "geolocation", {
    configurable: true,
    writable: true,
    value: { getCurrentPosition, watchPosition: vi.fn(), clearWatch: vi.fn() },
  });
}

function removeGeolocation(): void {
  Object.defineProperty(navigator, "geolocation", {
    configurable: true,
    writable: true,
    value: undefined,
  });
}

function setSecureContext(value: boolean): void {
  Object.defineProperty(window, "isSecureContext", {
    configurable: true,
    writable: true,
    value,
  });
}

/** Trả về một bản định vị thành công cho lời gọi đang chờ. */
function resolveWith(latitude: number, longitude: number, accuracy: number | undefined): void {
  const [onSuccess] = getCurrentPosition.mock.calls.at(-1) as [PositionCallback, ErrorCallback];
  act(() => {
    onSuccess({
      coords: { latitude, longitude, accuracy },
      timestamp: Date.now(),
    } as unknown as GeolocationPosition);
  });
}

/** Trả về một lỗi cho lời gọi đang chờ, kèm đúng bộ hằng số của trình duyệt. */
function rejectWith(code: number): void {
  const [, onError] = getCurrentPosition.mock.calls.at(-1) as [PositionCallback, ErrorCallback];
  act(() => {
    onError({ code, message: "", ...ERROR_CODES } as unknown as GeolocationPositionError);
  });
}

beforeEach(() => {
  getCurrentPosition.mockReset();
  installGeolocation();
  setSecureContext(true);
});

afterEach(() => {
  installGeolocation();
  setSecureContext(true);
});

describe("không bao giờ tự xin vị trí", () => {
  it("không gọi trình duyệt khi vừa khởi tạo", () => {
    const { result } = renderHook(() => useGeolocation());

    expect(getCurrentPosition).not.toHaveBeenCalled();
    expect(result.current.status).toBe("idle");
    expect(result.current.fix).toBeNull();
  });

  it("không gọi lại ở lần render sau", () => {
    const { rerender } = renderHook(() => useGeolocation());
    rerender();
    rerender();
    expect(getCurrentPosition).not.toHaveBeenCalled();
  });
});

describe("nhánh thành công", () => {
  it("trả về toạ độ và sai số sau khi người dùng đồng ý", () => {
    const { result } = renderHook(() => useGeolocation());

    act(() => result.current.request());
    expect(result.current.status).toBe("locating");
    expect(result.current.isLocating).toBe(true);

    resolveWith(21.0278, 105.8342, 25);

    expect(result.current.status).toBe("granted");
    expect(result.current.fix).toEqual({
      latitude: 21.0278,
      longitude: 105.8342,
      accuracyMeters: 25,
    });
    expect(result.current.errorMessage).toBeNull();
  });

  it("chấp nhận bản định vị không kèm sai số", () => {
    const { result } = renderHook(() => useGeolocation());
    act(() => result.current.request());
    resolveWith(21.0278, 105.8342, undefined);

    expect(result.current.fix?.accuracyMeters).toBeNull();
  });

  it("xin vị trí với độ chính xác cao và có hạn giờ", () => {
    const { result } = renderHook(() => useGeolocation());
    act(() => result.current.request());

    const options = getCurrentPosition.mock.calls[0][2];
    expect(options.enableHighAccuracy).toBe(true);
    expect(options.timeout).toBeGreaterThan(0);
    expect(options.timeout).toBeLessThanOrEqual(15_000);
  });

  it("không ghi vị trí vào localStorage", () => {
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    const { result } = renderHook(() => useGeolocation());

    act(() => result.current.request());
    resolveWith(21.0278, 105.8342, 25);

    expect(setItem).not.toHaveBeenCalled();
  });
});

describe("nhánh hỏng", () => {
  it.each([
    [ERROR_CODES.PERMISSION_DENIED, "denied"],
    [ERROR_CODES.POSITION_UNAVAILABLE, "unavailable"],
    [ERROR_CODES.TIMEOUT, "timeout"],
  ])("mã lỗi %i cho trạng thái %s kèm lời giải thích", (code, expected) => {
    const { result } = renderHook(() => useGeolocation());

    act(() => result.current.request());
    rejectWith(code);

    expect(result.current.status).toBe(expected);
    expect(result.current.fix).toBeNull();
    expect(result.current.isLocating).toBe(false);
    expect(result.current.errorMessage).toBeTruthy();
  });

  it("trình duyệt không có API vị trí thì báo không dùng được, không văng lỗi", () => {
    removeGeolocation();
    const { result } = renderHook(() => useGeolocation());

    act(() => result.current.request());

    expect(result.current.status).toBe("unavailable");
  });

  it("trang chạy ngoài HTTPS thì không gọi API vị trí", () => {
    setSecureContext(false);
    const { result } = renderHook(() => useGeolocation());

    act(() => result.current.request());

    expect(getCurrentPosition).not.toHaveBeenCalled();
    expect(result.current.status).toBe("unavailable");
  });

  it("cho phép thử lại sau khi hỏng", () => {
    const { result } = renderHook(() => useGeolocation());

    act(() => result.current.request());
    rejectWith(ERROR_CODES.TIMEOUT);
    act(() => result.current.request());
    resolveWith(21.0, 105.8, 40);

    expect(getCurrentPosition).toHaveBeenCalledTimes(2);
    expect(result.current.status).toBe("granted");
  });
});

describe("chống bấm trùng", () => {
  it("hai lần bấm liên tiếp chỉ mở một lời gọi", () => {
    const { result } = renderHook(() => useGeolocation());

    act(() => {
      result.current.request();
      result.current.request();
    });

    expect(getCurrentPosition).toHaveBeenCalledTimes(1);
  });
});

describe("reset", () => {
  it("xoá sạch toạ độ đang giữ trong bộ nhớ", () => {
    const { result } = renderHook(() => useGeolocation());

    act(() => result.current.request());
    resolveWith(21.0, 105.8, 10);
    act(() => result.current.reset());

    expect(result.current.status).toBe("idle");
    expect(result.current.fix).toBeNull();
    expect(result.current.errorMessage).toBeNull();
  });
});
