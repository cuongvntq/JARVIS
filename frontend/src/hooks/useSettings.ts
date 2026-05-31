import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";
import type { UserUpdateRequest } from "@/lib/types/api";

export function useUpdateProfile() {
  const setAuth = useAuthStore((s) => s.setAuth);
  const accessToken = useAuthStore((s) => s.accessToken);

  return useMutation({
    mutationFn: (data: UserUpdateRequest) => api.updateProfile(data),
    onSuccess: (user) => {
      if (accessToken) setAuth(user, accessToken);
    },
  });
}
