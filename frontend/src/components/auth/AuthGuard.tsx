"use client";

import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

const PUBLIC_PATHS = ["/auth/login", "/auth/register"];

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading, setLoading } = useAuthStore();

  const isPublicPath = PUBLIC_PATHS.some((p) => pathname.startsWith(p));

  useEffect(() => {
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
  }, [isAuthenticated, isPublicPath, router, setLoading]);

  // Public paths: render immediately without waiting
  if (isPublicPath) return <>{children}</>;

  if (isLoading) {
    return (
      <div
        className="flex h-full items-center justify-center"
        style={{ backgroundColor: "#030712" }}
      >
        <div
          className="h-8 w-8 animate-spin rounded-full border-2"
          style={{ borderColor: "rgba(0,180,216,0.6)", borderTopColor: "transparent" }}
        />
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return <>{children}</>;
}
