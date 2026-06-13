"use client";

import { relaunch } from "@tauri-apps/plugin-process";
import { check } from "@tauri-apps/plugin-updater";
import { useEffect } from "react";
import { toast } from "sonner";

const CHECK_INTERVAL_MS = 6 * 60 * 60 * 1000;

async function checkForUpdate() {
  try {
    const update = await check();
    if (!update?.available) return;

    toast(`Có bản cập nhật mới: v${update.version}`, {
      description: "Nhấn để tải và cài đặt. JARVIS sẽ khởi động lại sau khi cập nhật.",
      duration: Number.POSITIVE_INFINITY,
      action: {
        label: "Cập nhật ngay",
        onClick: async () => {
          try {
            await update.downloadAndInstall();
            await relaunch();
          } catch {
            // Download/install failed — user can retry on next periodic check
          }
        },
      },
    });
  } catch {
    // Updater plugin unavailable (e.g. browser dev mode) — ignore
  }
}

export function useUpdateAvailable() {
  useEffect(() => {
    checkForUpdate();
    const interval = setInterval(checkForUpdate, CHECK_INTERVAL_MS);
    return () => clearInterval(interval);
  }, []);
}
