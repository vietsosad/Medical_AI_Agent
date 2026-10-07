"use client";

import { useQuery, UseQueryResult } from "@tanstack/react-query";
import { axiosClient } from "@/lib/api/axios.client";
import { EhrLiteSchema, EmergencyContactSchema } from "@/schemas/clinical-profile.schema";
import type { EhrLiteDTO, EmergencyContactDTO } from "@/types/clinical-profile";
import * as z from "zod";
import { useActiveProfileStore } from "@/store/useActiveProfileStore";

// ============================================================================
// 1. EMPTY DEFAULTS FOR FORM INITIALIZATION (NO MOCK DATA — REAL API DRIVEN)
// ============================================================================
export const EMPTY_EHR_LITE: EhrLiteDTO = {
  patient_id: "",
  age: null,
  gender: null,
  height_cm: null,
  weight_kg: null,
  blood_type: null,
  chronic_conditions: [],
  allergies: [],
  current_medications: [],
  last_updated: null,
};

export const EMPTY_EMERGENCY_CONTACTS: EmergencyContactDTO[] = [];

// ============================================================================
// 2. QUERY KEYS CONSTANTS FOR TANSTACK QUERY V5
// ============================================================================
export const CLINICAL_QUERY_KEYS = {
  all: ["clinical-profile"] as const,
  ehrLite: (profileId: string) => [...CLINICAL_QUERY_KEYS.all, "ehr-lite", profileId] as const,
  emergencyContacts: (profileId: string) => [...CLINICAL_QUERY_KEYS.all, "emergency-contacts", profileId] as const,
};

// ============================================================================
// 3. TANSTACK QUERY V5 HOOKS — SERVER STATE ONLY (NO MOCK)
// ============================================================================

/**
 * Hook fetch Hồ sơ Lâm sàng Rút gọn (EHR Lite).
 * Cam kết: CHỈ TanStack Query nắm giữ server state. Dữ liệu thực từ API backend.
 * Gender được normalize UPPERCASE qua backend EhrLiteDTO validator.
 */
export const useEhrLite = (customProfileId?: string | null): UseQueryResult<EhrLiteDTO, Error> => {
  const storeProfileId = useActiveProfileStore((s) => s.activeProfileId);
  const profileId = customProfileId !== undefined ? customProfileId : storeProfileId;

  return useQuery<EhrLiteDTO, Error>({
    queryKey: profileId ? CLINICAL_QUERY_KEYS.ehrLite(profileId) : ["clinical-profile", "null-ehr-lite"],
    queryFn: async (): Promise<EhrLiteDTO> => {
      if (!profileId) throw new Error("Chưa chọn hồ sơ");
      const response = await axiosClient.get<unknown>(`/api/v1/profiles/${profileId}/ehr-lite`);

      // Runtime strict validation với Zod schema — đảm bảo backend response khớp Frontend types
      const parsed = EhrLiteSchema.parse(response.data);
      return parsed;
    },
    enabled: !!profileId,
    staleTime: 5 * 60 * 1000, // 5 phút chuẩn lâm sàng
    gcTime: 15 * 60 * 1000,   // Cache sống 15 phút
    retry: 1,
    refetchOnWindowFocus: false,
  });
};

/**
 * Hook fetch Danh sách Người liên hệ Khẩn cấp (Emergency SOS Contacts).
 * Hỗ trợ tối đa 3 thẻ SOS theo kiến trúc Multi-SOS Architecture.
 */
export const useEmergencyContacts = (customProfileId?: string | null): UseQueryResult<EmergencyContactDTO[], Error> => {
  const storeProfileId = useActiveProfileStore((s) => s.activeProfileId);
  const profileId = customProfileId !== undefined ? customProfileId : storeProfileId;

  return useQuery<EmergencyContactDTO[], Error>({
    queryKey: profileId ? CLINICAL_QUERY_KEYS.emergencyContacts(profileId) : ["clinical-profile", "null-emergency"],
    queryFn: async (): Promise<EmergencyContactDTO[]> => {
      if (!profileId) throw new Error("Chưa chọn hồ sơ");
      const response = await axiosClient.get<unknown>(`/api/v1/profiles/${profileId}/emergency-contacts`);

      const contactsSchema = z.array(EmergencyContactSchema);
      return contactsSchema.parse(response.data);
    },
    enabled: !!profileId,
    staleTime: 10 * 60 * 1000, // 10 phút cho danh sách liên hệ SOS
    gcTime: 30 * 60 * 1000,
    retry: 1,
    refetchOnWindowFocus: false,
  });
};
