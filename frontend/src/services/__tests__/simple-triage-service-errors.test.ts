import { AxiosError, AxiosHeaders, type AxiosResponse } from "axios";
import { afterEach, describe, expect, it, vi } from "vitest";

const client = vi.hoisted(() => ({ post: vi.fn(), get: vi.fn() }));

vi.mock("@/lib/api/axios.client", () => ({ axiosClient: client }));

const { SimpleTriageApiError, isPilotUnavailableError, simpleTriageService } = await import(
  "@/services/simple-triage.service"
);

/**
 * Câu lỗi đi thẳng lên màn hình người bệnh, nên nó phải là tiếng Việt cố định:
 * không bao giờ là tên biến môi trường, tên framework, chuỗi gốc của axios,
 * hay mảng `detail` 422 hiện thành "[object Object]".
 */

const DEVELOPER_TEXT = /SIMPLE_AGENT_ENABLED|FastAPI|Backend|Request failed|status code|\[object Object\]/;

function httpError(status: number, data: unknown): AxiosError {
  const config = { headers: new AxiosHeaders() };
  const response: AxiosResponse = { status, statusText: "", headers: {}, config, data };
  return new AxiosError(`Request failed with status code ${status}`, "ERR_BAD_RESPONSE", config, {}, response);
}

async function failureOf(error: unknown): Promise<InstanceType<typeof SimpleTriageApiError>> {
  client.post.mockRejectedValueOnce(error);
  try {
    await simpleTriageService.chat("session-1", "tôi bị đau ngực");
  } catch (caught) {
    expect(caught).toBeInstanceOf(SimpleTriageApiError);
    return caught as InstanceType<typeof SimpleTriageApiError>;
  }
  throw new Error("expected the turn to fail");
}

describe("lỗi của dịch vụ sàng lọc", () => {
  afterEach(() => client.post.mockReset());

  it("503 được nhận diện theo loại lỗi, không phải theo tên cờ cấu hình", async () => {
    const error = await failureOf(httpError(503, { detail: "simple_agent pilot is disabled (set SIMPLE_AGENT_ENABLED=true)" }));

    expect(isPilotUnavailableError(error)).toBe(true);
    expect(error.message).not.toMatch(DEVELOPER_TEXT);
  });

  it("hết thời gian chờ khác với mất kết nối", async () => {
    const timeout = await failureOf(new AxiosError("timeout of 90000ms exceeded", AxiosError.ECONNABORTED));
    const offline = await failureOf(new AxiosError("Network Error", AxiosError.ERR_NETWORK));

    expect(timeout.kind).toBe("TIMEOUT");
    expect(offline.kind).toBe("NETWORK");
    expect(timeout.message).not.toBe(offline.message);
    expect(`${timeout.message} ${offline.message}`).not.toMatch(DEVELOPER_TEXT);
  });

  it("mảng detail của lỗi 422 không bao giờ hiện thành [object Object]", async () => {
    const error = await failureOf(httpError(422, { detail: [{ loc: ["body", "message"], msg: "field required" }] }));

    expect(error.kind).toBe("INVALID_INPUT");
    expect(error.message).not.toMatch(DEVELOPER_TEXT);
  });

  it("lỗi máy chủ dùng câu cố định thay vì chuỗi gốc", async () => {
    const error = await failureOf(httpError(500, "Internal Server Error"));

    expect(error.kind).toBe("SERVER");
    expect(error.message).not.toMatch(DEVELOPER_TEXT);
  });

  it("câu tiếng Việt do route viết cho lỗi 4xx vẫn được giữ", async () => {
    const detail = "Phiên này đã kết thúc. Vui lòng bắt đầu phiên mới nếu cần hỏi thêm.";
    const error = await failureOf(httpError(409, { detail }));

    expect(error.message).toBe(detail);
  });
});
