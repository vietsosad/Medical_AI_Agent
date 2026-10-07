"use client";

import { useMutation, useQuery, useQueryClient, UseQueryResult } from "@tanstack/react-query";
import { profileService, ProfileResponseDTO, CreateProfileRequestDTO, UpdateProfileRequestDTO } from "@/services/profile.service";

// ============================================================================
// 1. QUERY KEYS REGISTRY
// ============================================================================
export const PROFILE_QUERY_KEYS = {
  all: ["family-profiles"] as const,
  detail: (id: string) => ["family-profiles", id] as const,
};

// ============================================================================
// 2. TANSTACK QUERY V5 CUSTOM HOOKS (SINGLE SOURCE OF TRUTH FOR REMOTE DATA)
// ============================================================================

/**
 * Hook tải danh sách toàn bộ hồ sơ trong gia đình (Multi-Profile Care)
 */
export function useGetProfiles(): UseQueryResult<ProfileResponseDTO[], Error> {
  return useQuery({
    queryKey: PROFILE_QUERY_KEYS.all,
    queryFn: async () => {
      return await profileService.getProfiles();
    },
    staleTime: 5 * 60 * 1000, // Cache giữ độ tươi lâm sàng trong 5 phút
    retry: 1,
  });
}

/**
 * Hook truy vấn chi tiết của 1 hồ sơ
 */
export function useGetProfileById(profileId: string | null | undefined): UseQueryResult<ProfileResponseDTO | undefined, Error> {
  const { data: profiles } = useGetProfiles();
  
  return useQuery({
    queryKey: profileId ? PROFILE_QUERY_KEYS.detail(profileId) : ["family-profiles", "null-detail"],
    queryFn: async () => {
      if (!profileId) return undefined;
      // Ưu tiên tìm trong mảng cache tổng trước
      const cached = profiles?.find((p) => p.id === profileId);
      if (cached) return cached;
      return await profileService.getProfileById(profileId);
    },
    enabled: !!profileId,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Hook Mutation khởi tạo hồ sơ thân nhân nhanh (<15s)
 */
export function useCreateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateProfileRequestDTO) => profileService.createProfile(payload),
    onSuccess: (newProfile) => {
      // Optimistic cache upgrade hoặc invalidate query mảng hồ sơ
      queryClient.setQueryData<ProfileResponseDTO[]>(PROFILE_QUERY_KEYS.all, (oldData) => {
        if (!oldData) return [newProfile];
        return [newProfile, ...oldData].sort((a, b) => (b.is_primary ? 1 : 0) - (a.is_primary ? 1 : 0));
      });
      queryClient.invalidateQueries({ queryKey: PROFILE_QUERY_KEYS.all });
    },
  });
}

/**
 * Hook Mutation cập nhật hồ sơ thân nhân
 */
export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: UpdateProfileRequestDTO }) =>
      profileService.updateProfile(id, payload),
    onSuccess: (updated, variables) => {
      queryClient.invalidateQueries({ queryKey: PROFILE_QUERY_KEYS.all });
      queryClient.invalidateQueries({ queryKey: PROFILE_QUERY_KEYS.detail(variables.id) });
    },
  });
}

/**
 * Hook Mutation xóa hồ sơ phụ thuộc (Không được xóa SELF)
 */
export function useDeleteProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => profileService.deleteProfile(id),
    onSuccess: (_, deletedId) => {
      queryClient.setQueryData<ProfileResponseDTO[]>(PROFILE_QUERY_KEYS.all, (oldData) =>
        oldData ? oldData.filter((p) => p.id !== deletedId) : []
      );
      queryClient.invalidateQueries({ queryKey: PROFILE_QUERY_KEYS.all });
    },
  });
}
