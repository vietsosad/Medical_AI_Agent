"use client";

import { useMutation, useQueryClient, UseMutationResult } from "@tanstack/react-query";
import { axiosClient } from "@/lib/api/axios.client";
import { CLINICAL_QUERY_KEYS } from "@/hooks/queries/use-clinical-profile";
import { PROFILE_QUERY_KEYS } from "@/queries/useProfileQueries";
import { EhrLiteSchema, EmergencyContactSchema } from "@/schemas/clinical-profile.schema";
import type { EhrLiteDTO, EmergencyContactDTO } from "@/types/clinical-profile";
import { toast } from "sonner";
import * as z from "zod";
import { useActiveProfileStore } from "@/store/useActiveProfileStore";

// ============================================================================
// MUTATION HOOKS FOR CLINICAL PROFILE WITH OPTIMISTIC UPDATES & TOASTS
// ============================================================================

/**
 * Hook cập nhật Hồ sơ Lâm sàng Rút gọn (EHR Lite) kèm Optimistic UI Update.
 */
export const useUpdateEhrLite = (customProfileId?: string | null): UseMutationResult<
  EhrLiteDTO,
  Error,
  Partial<EhrLiteDTO>,
  { previousEhr?: EhrLiteDTO }
> => {
  const queryClient = useQueryClient();
  const storeProfileId = useActiveProfileStore((s) => s.activeProfileId);
  const profileId = customProfileId !== undefined ? customProfileId : storeProfileId;

  return useMutation<EhrLiteDTO, Error, Partial<EhrLiteDTO>, { previousEhr?: EhrLiteDTO }>({
    mutationFn: async (updatedFields: Partial<EhrLiteDTO>): Promise<EhrLiteDTO> => {
      if (!profileId) throw new Error("Chưa chọn hồ sơ y khoa.");
      
      const currentData = queryClient.getQueryData<EhrLiteDTO>(CLINICAL_QUERY_KEYS.ehrLite(profileId));
      const fullPayload = { ...currentData, ...updatedFields };
      
      const response = await axiosClient.put<unknown>(`/api/v1/profiles/${profileId}/ehr-lite`, fullPayload);
      return EhrLiteSchema.parse(response.data);
    },
    onMutate: async (updatedFields) => {
      if (!profileId) return {};
      await queryClient.cancelQueries({ queryKey: CLINICAL_QUERY_KEYS.ehrLite(profileId) });

      const previousEhr = queryClient.getQueryData<EhrLiteDTO>(CLINICAL_QUERY_KEYS.ehrLite(profileId));

      if (previousEhr) {
        queryClient.setQueryData<EhrLiteDTO>(CLINICAL_QUERY_KEYS.ehrLite(profileId), {
          ...previousEhr,
          ...updatedFields,
          last_updated: new Date().toISOString(),
        });
      }

      return { previousEhr };
    },
    onError: (error, _variables, context) => {
      if (profileId && context?.previousEhr) {
        queryClient.setQueryData(CLINICAL_QUERY_KEYS.ehrLite(profileId), context.previousEhr);
      }
      toast.error("Cập nhật hồ sơ lâm sàng thất bại. Đã khôi phục dữ liệu gốc.", {
        description: error.message,
      });
    },
    onSuccess: (data) => {
      if (profileId) {
        queryClient.setQueryData(CLINICAL_QUERY_KEYS.ehrLite(profileId), data);
      }
      toast.success("Cập nhật Hồ Sơ Y Khoa (EHR Lite) thành công!", {
        description: `Dữ liệu sinh hiệu và bệnh nền đã được đồng bộ trực tiếp lên cơ sở dữ liệu.`,
      });
    },
    onSettled: () => {
      if (profileId) {
        queryClient.invalidateQueries({ queryKey: CLINICAL_QUERY_KEYS.ehrLite(profileId) });
      }
      // Bệnh nền, dị ứng và nhóm máu cũng hiện trên thẻ hồ sơ gia đình.
      queryClient.invalidateQueries({ queryKey: PROFILE_QUERY_KEYS.all });
    },
  });
};

/**
 * Hook cập nhật Danh sách Liên hệ Khẩn cấp (Emergency SOS Contacts) kèm Optimistic UI Update.
 */
export const useUpdateEmergencyContacts = (customProfileId?: string | null): UseMutationResult<
  EmergencyContactDTO[],
  Error,
  EmergencyContactDTO[],
  { previousContacts?: EmergencyContactDTO[] }
> => {
  const queryClient = useQueryClient();
  const storeProfileId = useActiveProfileStore((s) => s.activeProfileId);
  const profileId = customProfileId !== undefined ? customProfileId : storeProfileId;

  return useMutation<
    EmergencyContactDTO[],
    Error,
    EmergencyContactDTO[],
    { previousContacts?: EmergencyContactDTO[] }
  >({
    mutationFn: async (updatedContacts: EmergencyContactDTO[]): Promise<EmergencyContactDTO[]> => {
      if (!profileId) throw new Error("Chưa chọn hồ sơ y khoa.");
      const response = await axiosClient.put<unknown>(
        `/api/v1/profiles/${profileId}/emergency-contacts`,
        updatedContacts
      );
      const contactsSchema = z.array(EmergencyContactSchema);
      return contactsSchema.parse(response.data);
    },
    onMutate: async (newContacts) => {
      if (!profileId) return {};
      await queryClient.cancelQueries({ queryKey: CLINICAL_QUERY_KEYS.emergencyContacts(profileId) });
      const previousContacts = queryClient.getQueryData<EmergencyContactDTO[]>(
        CLINICAL_QUERY_KEYS.emergencyContacts(profileId)
      );

      if (previousContacts) {
        queryClient.setQueryData<EmergencyContactDTO[]>(
          CLINICAL_QUERY_KEYS.emergencyContacts(profileId),
          newContacts
        );
      }

      return { previousContacts };
    },
    onError: (error, _variables, context) => {
      if (profileId && context?.previousContacts) {
        queryClient.setQueryData(
          CLINICAL_QUERY_KEYS.emergencyContacts(profileId),
          context.previousContacts
        );
      }
      toast.error("Lưu danh sách liên hệ SOS thất bại. Đã khôi phục dữ liệu cũ.", {
        description: error.message,
      });
    },
    onSuccess: (data) => {
      if (profileId) {
        queryClient.setQueryData(CLINICAL_QUERY_KEYS.emergencyContacts(profileId), data);
      }
      toast.success("Đã cập nhật Danh sách Người Liên Hệ Khẩn Cấp (SOS)!", {
        description: `Hệ thống đã ghi nhận thay đổi vào hồ sơ của bạn.`,
      });
    },
    onSettled: () => {
      if (profileId) {
        queryClient.invalidateQueries({ queryKey: CLINICAL_QUERY_KEYS.emergencyContacts(profileId) });
      }
      // Người liên hệ khẩn cấp cũng hiện trên thẻ hồ sơ gia đình.
      queryClient.invalidateQueries({ queryKey: PROFILE_QUERY_KEYS.all });
    },
  });
};
