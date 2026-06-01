import { api } from "@/lib/api";
import { ApiException } from "@/lib/types/api";
import { useCallback, useEffect, useState } from "react";

export type PushPermission = "default" | "granted" | "denied" | "unsupported";

export interface UsePushNotificationReturn {
  permission: PushPermission;
  isSubscribed: boolean;
  isLoading: boolean;
  error: string | null;
  subscribe: () => Promise<void>;
  unsubscribe: () => Promise<void>;
}

function urlBase64ToUint8Array(base64String: string): ArrayBuffer {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = atob(base64);
  const arr = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; i++) arr[i] = rawData.charCodeAt(i);
  return arr.buffer as ArrayBuffer;
}

export function usePushNotification(): UsePushNotificationReturn {
  const [permission, setPermission] = useState<PushPermission>("default");
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Read initial state from browser
  useEffect(() => {
    if (
      typeof window === "undefined" ||
      !("Notification" in window) ||
      !("serviceWorker" in navigator)
    ) {
      setPermission("unsupported");
      return;
    }
    setPermission(Notification.permission as PushPermission);

    // Check if already subscribed
    navigator.serviceWorker.ready
      .then((reg) => reg.pushManager.getSubscription())
      .then((sub) => setIsSubscribed(!!sub))
      .catch(() => {});
  }, []);

  const subscribe = useCallback(async () => {
    setError(null);
    setIsLoading(true);
    try {
      if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
        throw new Error("Trình duyệt không hỗ trợ thông báo đẩy");
      }

      const perm = await Notification.requestPermission();
      setPermission(perm as PushPermission);
      if (perm !== "granted") {
        throw new Error("Quyền thông báo bị từ chối");
      }

      const reg = await navigator.serviceWorker.register("/sw.js");
      await navigator.serviceWorker.ready;

      const vapidKey = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY;
      if (!vapidKey) throw new Error("VAPID public key chưa được cấu hình");

      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidKey),
      });

      try {
        const json = sub.toJSON();
        await api.subscribePush({
          endpoint: sub.endpoint,
          p256dh: json.keys?.p256dh ?? "",
          auth: json.keys?.auth ?? "",
        });
      } catch (apiErr) {
        // Backend failed — clean up the browser subscription to avoid orphan state
        await sub.unsubscribe().catch(() => {});
        throw apiErr;
      }

      setIsSubscribed(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không bật được thông báo");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const unsubscribe = useCallback(async () => {
    setError(null);
    setIsLoading(true);
    try {
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.getSubscription();
      if (sub) await sub.unsubscribe();
      try {
        await api.unsubscribePush();
      } catch (apiErr) {
        // 404 means server already has no active subscription — treat as success
        if (!(apiErr instanceof ApiException && apiErr.statusCode === 404)) throw apiErr;
      }
      setIsSubscribed(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tắt được thông báo");
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { permission, isSubscribed, isLoading, error, subscribe, unsubscribe };
}
