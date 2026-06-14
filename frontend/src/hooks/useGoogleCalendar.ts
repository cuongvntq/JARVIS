import { api } from "@/lib/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

const STATUS_KEY = ["google-calendar", "status"];

/**
 * Open a URL in the system browser. Uses the Tauri shell plugin when running in
 * the desktop app; falls back to window.open in a plain browser / dev.
 */
async function openInBrowser(url: string): Promise<void> {
  try {
    const { open } = await import("@tauri-apps/plugin-shell");
    await open(url);
  } catch {
    window.open(url, "_blank", "noopener");
  }
}

export function useGoogleStatus() {
  return useQuery({
    queryKey: STATUS_KEY,
    queryFn: () => api.googleStatus(),
    staleTime: 30_000,
  });
}

/**
 * Start the OAuth flow: fetch the authorize URL, open the system browser, then
 * poll the status until the backend reports connected (or a timeout elapses).
 */
export function useConnectGoogle() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const { authorize_url } = await api.googleConnect();
      await openInBrowser(authorize_url);

      // Poll status: the backend completes the flow via the loopback callback.
      const deadline = Date.now() + 3 * 60 * 1000; // 3 min, matches backend timeout
      while (Date.now() < deadline) {
        await new Promise((r) => setTimeout(r, 2000));
        const status = await api.googleStatus();
        if (status.connected) return status;
      }
      throw new Error("Hết thời gian chờ xác thực Google. Vui lòng thử lại.");
    },
    onSuccess: (status) => {
      if (status) queryClient.setQueryData(STATUS_KEY, status);
      queryClient.invalidateQueries({ queryKey: STATUS_KEY });
    },
  });
}

export function useDisconnectGoogle() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.googleDisconnect(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: STATUS_KEY });
    },
  });
}
