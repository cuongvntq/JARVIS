"use client";

import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

const PUBLIC_PATHS = ["/auth/login", "/auth/register"];

// Desktop sidecar (PyInstaller jarvis-server.exe) takes ~20-25s to cold-start.
// Poll /health every 1s, give up after 90s (well past the typical window).
const HEALTH_POLL_INTERVAL_MS = 1000;
const HEALTH_MAX_ATTEMPTS = 90;

function LoadingScreen({ message }: { message: string }) {
  return (
    <div
      className="flex h-full flex-col items-center justify-center gap-4"
      style={{ backgroundColor: "#030712" }}
    >
      <div
        className="h-8 w-8 animate-spin rounded-full border-2"
        style={{ borderColor: "rgba(0,180,216,0.6)", borderTopColor: "transparent" }}
      />
      <p className="text-sm" style={{ color: "#5e8a9e" }}>
        {message}
      </p>
    </div>
  );
}

function BackendUnavailableScreen({ onRetry }: { onRetry: () => void }) {
  return (
    <div
      className="flex h-full flex-col items-center justify-center gap-4 px-6 text-center"
      style={{ backgroundColor: "#030712" }}
    >
      <p className="text-sm" style={{ color: "#5e8a9e" }}>
        Không thể kết nối đến J.A.R.V.I.S backend. Vui lòng khởi động lại ứng dụng.
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="rounded-md border px-4 py-2 text-sm transition-colors"
        style={{ borderColor: "rgba(0,180,216,0.4)", color: "#dff3fd" }}
      >
        Thử lại
      </button>
    </div>
  );
}

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading, setLoading } = useAuthStore();
  const [backendStatus, setBackendStatus] = useState<"checking" | "ready" | "unavailable">(
    "checking",
  );
  const [pollKey, setPollKey] = useState(0);

  const isPublicPath = PUBLIC_PATHS.some((p) => pathname.startsWith(p));

  // Wait for the backend (sidecar) to come up before doing anything auth-related.
  // biome-ignore lint/correctness/useExhaustiveDependencies: pollKey only triggers a re-run (retry button), not read in body
  useEffect(() => {
    let cancelled = false;
    setBackendStatus("checking");

    async function poll() {
      for (let attempt = 0; attempt < HEALTH_MAX_ATTEMPTS; attempt++) {
        if (cancelled) return;
        if (await api.health()) {
          if (!cancelled) setBackendStatus("ready");
          return;
        }
        await new Promise((resolve) => setTimeout(resolve, HEALTH_POLL_INTERVAL_MS));
      }
      if (!cancelled) setBackendStatus("unavailable");
    }

    poll();
    return () => {
      cancelled = true;
    };
  }, [pollKey]);

  useEffect(() => {
    if (backendStatus !== "ready") return;

    if (isPublicPath || isAuthenticated) {
      setLoading(false);
      return;
    }

    api.silentRefresh().then((ok) => {
      if (!ok) {
        router.replace("/auth/login");
      }
      setLoading(false);
    });
  }, [backendStatus, isAuthenticated, isPublicPath, router, setLoading]);

  if (backendStatus === "checking") {
    return <LoadingScreen message="Đang khởi động J.A.R.V.I.S..." />;
  }

  if (backendStatus === "unavailable") {
    return <BackendUnavailableScreen onRetry={() => setPollKey((k) => k + 1)} />;
  }

  // Public paths: render immediately without waiting
  if (isPublicPath) return <>{children}</>;

  if (isLoading) {
    return <LoadingScreen message="Đang xác thực..." />;
  }

  if (!isAuthenticated) return null;

  return <>{children}</>;
}
