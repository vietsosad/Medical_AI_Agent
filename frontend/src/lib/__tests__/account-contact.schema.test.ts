import { describe, expect, it } from "vitest";

import {
  formatVietnamPhoneForDisplay,
  normalizeVietnamPhone,
  optionalVietnamPhoneSchema,
  vietnamPhoneSchema,
} from "@/lib/validations/account-contact.schema";

describe("Vietnamese phone validation", () => {
  it.each([
    ["0912345678", "0912345678"],
    ["  0912345678  ", "0912345678"],
    ["0912 345 678", "0912345678"],
    ["0912-345-678", "0912345678"],
    ["+84912345678", "0912345678"],
    ["+84 912 345 678", "0912345678"],
    ["84912345678", "0912345678"],
    ["(024) 3936 1414", "02439361414"],
  ])("accepts %s and normalises it to %s", (raw, expected) => {
    const parsed = vietnamPhoneSchema.safeParse(raw);
    expect(parsed.success).toBe(true);
    expect(parsed.success && parsed.data).toBe(expected);
    expect(normalizeVietnamPhone(raw)).toBe(expected);
  });

  it.each([
    "091234567",
    "09123456789",
    "0112345678",
    "0243936141",
    "0912345abc",
    "+1 415 555 0100",
    "09123456780912345678091234",
  ])("rejects %s", (raw) => {
    expect(vietnamPhoneSchema.safeParse(raw).success).toBe(false);
  });

  it("returns a readable message instead of a raw regex error", () => {
    const parsed = vietnamPhoneSchema.safeParse("0112345678");
    expect(parsed.success).toBe(false);
    expect(parsed.success === false && parsed.error.issues[0].message).toContain(
      "định dạng Việt Nam",
    );
  });

  it("treats an empty field as clearing the stored number", () => {
    expect(optionalVietnamPhoneSchema.parse("")).toBeNull();
    expect(optionalVietnamPhoneSchema.parse("   ")).toBeNull();
  });

  it("still rejects an invalid number through the optional schema", () => {
    expect(optionalVietnamPhoneSchema.safeParse("0112345678").success).toBe(false);
  });

  it("groups digits for display without changing the stored value", () => {
    expect(formatVietnamPhoneForDisplay("0912345678")).toBe("0912 345 678");
    expect(formatVietnamPhoneForDisplay("02439361414")).toBe("024 3936 1414");
  });

  it("echoes an unrecognised value back rather than mangling it", () => {
    expect(formatVietnamPhoneForDisplay("not-a-number")).toBe("not-a-number");
  });
});
