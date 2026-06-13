"use client";

import { useUpdateAvailable } from "@/hooks/useUpdateAvailable";

export function UpdatePrompt() {
  useUpdateAvailable();
  return null;
}
