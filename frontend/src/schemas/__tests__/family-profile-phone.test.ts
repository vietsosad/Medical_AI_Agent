import { describe, expect, it } from "vitest";

import { CreateFamilyProfileFormSchema } from "@/schemas/clinical-profile.schema";

const base = {
  fullName: "Nguyễn Văn A",
  relationship: "PARENT" as const,
  age: "68",
  gender: "Male" as const,
  bloodType: "O+" as const,
};

describe("family member phone number", () => {
  it("normalises a member's number the same way as the account owner's", () => {
    const parsed = CreateFamilyProfileFormSchema.parse({
      ...base,
      phoneNumber: "  +84 912 345 678  ",
    });
    expect(parsed.phoneNumber).toBe("0912345678");
  });

  it("treats an empty field as no number rather than a validation error", () => {
    expect(CreateFamilyProfileFormSchema.parse({ ...base, phoneNumber: "" }).phoneNumber).toBeNull();
    expect(CreateFamilyProfileFormSchema.parse({ ...base, phoneNumber: "   " }).phoneNumber).toBeNull();
  });

  it.each(["0112345678", "091234567", "09123456789", "+1 415 555 0100", "abcdefghij"])(
    "rejects %s",
    (phoneNumber) => {
      const result = CreateFamilyProfileFormSchema.safeParse({ ...base, phoneNumber });
      expect(result.success).toBe(false);
    },
  );

  it("reports the phone error against the phone field, not the whole form", () => {
    const result = CreateFamilyProfileFormSchema.safeParse({ ...base, phoneNumber: "0112345678" });
    expect(result.success).toBe(false);
    expect(result.success === false && result.error.issues[0].path).toContain("phoneNumber");
  });

  it("still validates the rest of the member form", () => {
    const result = CreateFamilyProfileFormSchema.safeParse({
      ...base,
      fullName: "A",
      phoneNumber: "0912345678",
    });
    expect(result.success).toBe(false);
  });
});
