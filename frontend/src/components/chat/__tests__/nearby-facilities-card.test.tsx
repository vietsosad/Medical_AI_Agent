import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { GeolocationFix, GeolocationStatus } from "@/hooks/useGeolocation";
import type { EsiLevel } from "@/types/clinical-history";
import type { NearbyFacilitiesResponseDTO, NearbyFacilityDTO } from "@/types/facilities";

/**
 * Điều được kiểm tra gắt nhất ở đây không phải "thẻ có hiển thị danh sách
 * không", mà là ba ràng buộc an toàn:
 *
 * 1. **Thẻ chỉ tồn tại ở mức ESI khẩn (1/2/3).** Không có đường nào để nó dựng
 *    ra cảm giác cấp cứu cho một ca mà hệ thống vừa kết luận là không khẩn.
 * 2. **Không nhánh nào đóng lối gọi 115.** Trang `/triage-pilot` không có nút SOS
 *    nào khác, nên thẻ này là lối thoát duy nhất ở đó.
 * 3. **Không tự nâng cấp thông tin.** Không bịa số điện thoại, không gắn nhãn
 *    "có khoa cấp cứu" cho một cơ sở chưa xác minh, không giấu chuyện dữ liệu
 *    đang chạy ở chế độ dự phòng.
 */

const hooks = vi.hoisted(() => ({
  useGeolocation: vi.fn(),
  useNearbyFacilities: vi.fn(),
}));

vi.mock("@/hooks/useGeolocation", () => ({ useGeolocation: hooks.useGeolocation }));
vi.mock("@/queries/useFacilityQueries", () => ({ useNearbyFacilities: hooks.useNearbyFacilities }));

const { NearbyFacilitiesCard } = await import("@/components/chat/NearbyFacilitiesCard");

const FIX = { latitude: 21.0, longitude: 105.8, accuracyMeters: 30 };

function facility(overrides: Partial<NearbyFacilityDTO> = {}): NearbyFacilityDTO {
  return {
    id: "facility-1",
    name: "Bệnh viện Bạch Mai",
    facility_type: "HOSPITAL",
    address: "78 Giải Phóng, Đống Đa, Hà Nội",
    latitude: 21.0005,
    longitude: 105.841,
    distance_meters: 1200,
    phone_number: null,
    emergency_capability: "UNKNOWN",
    directions_url: "https://www.google.com/maps/dir/?api=1&destination=21.0005,105.841",
    source: "Danh bạ nội bộ (bản nháp)",
    source_url: "https://moh.gov.vn",
    ...overrides,
  };
}

function response(overrides: Partial<NearbyFacilitiesResponseDTO> = {}): NearbyFacilitiesResponseDTO {
  return {
    facilities: [facility()],
    data_source: "local_directory",
    degraded: false,
    search_radius_meters: 10_000,
    accuracy_meters: 30,
    disclaimer: "Trường hợp nguy kịch, hãy gọi 115 trước.",
    ...overrides,
  };
}

interface SetupOptions {
  esiLevel?: EsiLevel | null;
  geo?: Partial<ReturnType<typeof baseGeo>>;
  query?: Record<string, unknown>;
}

function baseGeo() {
  return {
    // Chú thích kiểu rộng (không dùng `as const`) để từng test đặt được mọi
    // trạng thái của hook mà không phải ép kiểu ở chỗ gọi.
    status: "idle" as GeolocationStatus,
    fix: null as GeolocationFix | null,
    errorMessage: null as string | null,
    isLocating: false,
    request: vi.fn(),
    reset: vi.fn(),
  };
}

function setup({ esiLevel = 2, geo = {}, query = {} }: SetupOptions = {}) {
  const geolocation = { ...baseGeo(), ...geo };
  const facilitiesQuery = {
    data: undefined as NearbyFacilitiesResponseDTO | undefined,
    isLoading: false,
    isError: false,
    error: null as Error | null,
    refetch: vi.fn(),
    ...query,
  };
  hooks.useGeolocation.mockReturnValue(geolocation);
  hooks.useNearbyFacilities.mockReturnValue(facilitiesQuery);

  const utils = render(<NearbyFacilitiesCard esiLevel={esiLevel} />);
  return { ...utils, geolocation, facilitiesQuery };
}

const emergencyLinks = () =>
  screen.queryAllByRole("link", { name: /Gọi Tổng đài Cấp cứu Quốc gia 115/i });

// ---------------------------------------------------------------------------
// Cổng chặn theo mức ESI
// ---------------------------------------------------------------------------

describe("cổng chặn theo mức ESI", () => {
  it.each([4, 5] as EsiLevel[])("không hiển thị gì ở mức ESI %s", (esiLevel) => {
    const { container } = setup({ esiLevel });
    expect(container).toBeEmptyDOMElement();
  });

  it("không hiển thị gì khi chưa có mức ESI nào", () => {
    const { container } = setup({ esiLevel: null });
    expect(container).toBeEmptyDOMElement();
  });

  it.each([1, 2, 3] as EsiLevel[])("hiển thị ở mức ESI %s", (esiLevel) => {
    setup({ esiLevel });
    expect(screen.getByRole("heading", { level: 3 })).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Hướng dẫn theo mức: hành động đúng ở mỗi mức là khác nhau
// ---------------------------------------------------------------------------

describe("hướng dẫn theo mức khẩn", () => {
  it("ESI 1 đặt việc gọi 115 lên trước danh sách và báo động cho trình đọc màn hình", () => {
    setup({ esiLevel: 1, query: { data: response() } });

    const alert = screen.getByRole("alert");
    expect(within(alert).getByText(/Gọi 115 ngay lập tức/i)).toBeInTheDocument();
    expect(alert).toHaveAttribute("aria-live", "assertive");
    // Nút 115 phải nằm trong chính dải cảnh báo, không nằm lẫn dưới danh sách.
    expect(within(alert).getByRole("link", { name: /115/i })).toBeInTheDocument();
  });

  it("ESI 1 nói rõ danh sách là để đọc địa chỉ cho tổng đài, không phải để tự di chuyển", () => {
    setup({ esiLevel: 1 });
    expect(screen.getByText(/không phải để tự di chuyển/i)).toBeInTheDocument();
  });

  it("ESI 2 cảnh báo không tự lái xe", () => {
    setup({ esiLevel: 2 });
    expect(screen.getByText(/Không tự lái xe/i)).toBeInTheDocument();
    expect(emergencyLinks().length).toBeGreaterThan(0);
  });

  it("ESI 3 không dựng nút 115 như hành động chính", () => {
    setup({ esiLevel: 3, query: { data: response() } });
    expect(screen.getByText(/Nên đến cơ sở y tế sớm/i)).toBeInTheDocument();
    expect(emergencyLinks()).toHaveLength(0);
  });

  it("ESI 1 và 2 không bị lặp hai nút 115 khi định vị hỏng", () => {
    setup({ esiLevel: 2, geo: { status: "denied", errorMessage: "Trình duyệt đang chặn quyền vị trí." } });
    expect(emergencyLinks()).toHaveLength(1);
  });
});

// ---------------------------------------------------------------------------
// Xin quyền vị trí
// ---------------------------------------------------------------------------

describe("xin quyền vị trí", () => {
  it("không tự xin vị trí khi vừa hiển thị", () => {
    const { geolocation } = setup({ esiLevel: 2 });
    expect(geolocation.request).not.toHaveBeenCalled();
  });

  it("chỉ xin vị trí sau khi người dùng bấm nút", async () => {
    const user = userEvent.setup();
    const { geolocation } = setup({ esiLevel: 2 });

    await user.click(screen.getByRole("button", { name: /Bật định vị/i }));

    expect(geolocation.request).toHaveBeenCalledTimes(1);
  });

  it("nói rõ vị trí không được lưu lại", () => {
    setup({ esiLevel: 2 });
    expect(screen.getByText(/không được lưu lại/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Nhánh hỏng: không lối nào được đóng lại
// ---------------------------------------------------------------------------

describe("nhánh hỏng vẫn giữ đủ lối đi", () => {
  it.each(["denied", "unavailable", "timeout"] as const)(
    "trạng thái %s vẫn còn cách tự tìm trên Google Maps và thử lại",
    (status) => {
      setup({
        esiLevel: 3,
        geo: { status, errorMessage: "Không lấy được vị trí." },
      });

      expect(screen.getByText("Không lấy được vị trí.")).toBeInTheDocument();
      const manual = screen.getByRole("link", { name: /Tự tìm trên Google Maps/i });
      expect(manual).toHaveAttribute(
        "href",
        expect.stringContaining("https://www.google.com/maps/search/?api=1&query="),
      );
      expect(screen.getByRole("button", { name: /Thử định vị lại/i })).toBeInTheDocument();
      // Mức 3 chưa có nút 115 ở dải trên, nên nhánh hỏng phải tự mang theo.
      expect(emergencyLinks()).toHaveLength(1);
    },
  );

  it("lỗi tra cứu hiện đúng thông điệp và vẫn cho thử lại", async () => {
    const user = userEvent.setup();
    const { facilitiesQuery } = setup({
      esiLevel: 3,
      geo: { status: "granted", fix: FIX },
      query: { isError: true, error: new Error("Không kết nối được tới máy chủ.") },
    });

    expect(screen.getByText("Không kết nối được tới máy chủ.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /^Thử lại$/i }));
    expect(facilitiesQuery.refetch).toHaveBeenCalledTimes(1);
    expect(emergencyLinks()).toHaveLength(1);
  });

  it("danh sách rỗng không được đọc thành quanh đây không có bệnh viện nào", () => {
    setup({
      esiLevel: 3,
      geo: { status: "granted", fix: FIX },
      query: { data: response({ facilities: [] }) },
    });

    expect(screen.getByText(/không có nghĩa là quanh đây không có cơ sở nào/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Tự tìm trên Google Maps/i })).toBeInTheDocument();
    expect(emergencyLinks()).toHaveLength(1);
  });

  it("hiện khung chờ khi đang tải thay vì để trống", () => {
    const { container } = setup({
      esiLevel: 2,
      geo: { status: "granted", fix: FIX },
      query: { isLoading: true },
    });

    expect(screen.getByText(/Đang tìm cơ sở y tế gần bạn/i)).toBeInTheDocument();
    expect(container.querySelectorAll(".animate-pulse").length).toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------------
// Danh sách cơ sở
// ---------------------------------------------------------------------------

describe("danh sách cơ sở", () => {
  it("hiện tên, địa chỉ, khoảng cách và đường chỉ dẫn không cần khoá API", () => {
    setup({
      esiLevel: 2,
      geo: { status: "granted", fix: FIX },
      query: { data: response() },
    });

    expect(screen.getByText("Bệnh viện Bạch Mai")).toBeInTheDocument();
    expect(screen.getByText("78 Giải Phóng, Đống Đa, Hà Nội")).toBeInTheDocument();
    expect(screen.getByText(/Cách khoảng 1\.2 km/)).toBeInTheDocument();

    const directions = screen.getByRole("link", { name: /Chỉ đường tới Bệnh viện Bạch Mai/i });
    expect(directions).toHaveAttribute(
      "href",
      "https://www.google.com/maps/dir/?api=1&destination=21.0005,105.841",
    );
    expect(directions.getAttribute("href")).not.toContain("key=");
    expect(directions).toHaveAttribute("rel", expect.stringContaining("noopener"));
  });

  it("không dựng nút gọi khi cơ sở chưa có số điện thoại xác minh", () => {
    setup({
      esiLevel: 2,
      geo: { status: "granted", fix: FIX },
      query: { data: response({ facilities: [facility({ phone_number: null })] }) },
    });

    expect(screen.queryByRole("link", { name: /^Gọi$/ })).not.toBeInTheDocument();
  });

  it("hiện nút gọi khi đã có số", () => {
    setup({
      esiLevel: 2,
      geo: { status: "granted", fix: FIX },
      query: { data: response({ facilities: [facility({ phone_number: "024 3869 3731" })] }) },
    });

    expect(screen.getByRole("link", { name: /^Gọi$/ })).toHaveAttribute("href", "tel:02438693731");
  });

  it("chỉ gắn nhãn có khoa cấp cứu khi dữ liệu khẳng định điều đó", () => {
    setup({
      esiLevel: 2,
      geo: { status: "granted", fix: FIX },
      query: {
        data: response({
          facilities: [
            facility({ id: "a", name: "Đã xác minh", emergency_capability: "EMERGENCY_DEPARTMENT" }),
            facility({ id: "b", name: "Chưa xác minh", emergency_capability: "UNKNOWN" }),
          ],
        }),
      },
    });

    // Đúng một nhãn, không phải hai -- UNKNOWN không được nâng thành có.
    expect(screen.getAllByText("Có khoa cấp cứu")).toHaveLength(1);
    // Và cũng không được hạ thành "không có khoa cấp cứu".
    expect(screen.queryByText(/không có khoa cấp cứu/i)).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Nói thật về dữ liệu
// ---------------------------------------------------------------------------

describe("ghi nguồn và giới hạn dữ liệu", () => {
  it("luôn nói khoảng cách là đường chim bay", () => {
    setup({ esiLevel: 2, geo: { status: "granted", fix: FIX }, query: { data: response() } });
    expect(screen.getByText(/đường chim bay/i)).toBeInTheDocument();
  });

  it("ghi đúng nguồn Google Maps", () => {
    setup({
      esiLevel: 2,
      geo: { status: "granted", fix: FIX },
      query: { data: response({ data_source: "google_places" }) },
    });
    expect(screen.getByText(/Nguồn dữ liệu:\s*Google Maps/i)).toBeInTheDocument();
  });

  it("ghi rõ danh bạ nội bộ là bản nháp chưa đối chiếu", () => {
    setup({ esiLevel: 2, geo: { status: "granted", fix: FIX }, query: { data: response() } });
    expect(screen.getByText(/danh bạ nội bộ.*bản nháp/i)).toBeInTheDocument();
  });

  it("không giấu chuyện đang chạy ở chế độ dự phòng", () => {
    setup({
      esiLevel: 2,
      geo: { status: "granted", fix: FIX },
      query: { data: response({ degraded: true }) },
    });
    expect(screen.getByText(/có thể chưa đầy đủ/i)).toBeInTheDocument();
  });

  it("phát lại nguyên văn lời nhắc của máy chủ thay vì tự chế", () => {
    setup({
      esiLevel: 2,
      geo: { status: "granted", fix: FIX },
      query: { data: response({ disclaimer: "Lời nhắc do máy chủ phát." }) },
    });
    expect(screen.getByText("Lời nhắc do máy chủ phát.")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Quy ước giao diện của repo
// ---------------------------------------------------------------------------

it("không dùng emoji trong giao diện", () => {
  const { container } = setup({
    esiLevel: 1,
    geo: { status: "granted", fix: FIX },
    query: { data: response({ facilities: [facility({ phone_number: "0243869 3731" })] }) },
  });

  expect(container.textContent ?? "").not.toMatch(/\p{Extended_Pictographic}/u);
});
