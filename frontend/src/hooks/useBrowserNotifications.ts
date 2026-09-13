"use client";

import { useEffect, useState, useCallback } from "react";

export type NotificationPermissionState = "default" | "granted" | "denied" | "unsupported";

export function useBrowserNotifications() {
  const [permission, setPermission] = useState<NotificationPermissionState>("default");

  useEffect(() => {
    if (typeof window !== "undefined" && "Notification" in window) {
      setPermission(Notification.permission);
    } else {
      setPermission("unsupported");
    }
  }, []);

  const requestPermission = useCallback(async () => {
    if (typeof window === "undefined" || !("Notification" in window)) {
      setPermission("unsupported");
      return "unsupported";
    }

    try {
      const res = await Notification.requestPermission();
      setPermission(res);
      return res;
    } catch {
      return "denied";
    }
  }, []);

  const showNotification = useCallback(
    (title: string, options?: NotificationOptions) => {
      if (typeof window === "undefined" || !("Notification" in window)) return;
      if (Notification.permission !== "granted") return;

      try {
        const notif = new Notification(title, {
          icon: "/favicon.ico",
          badge: "/favicon.ico",
          ...options,
        });

        notif.onclick = () => {
          window.focus();
          notif.close();
        };
      } catch (err) {
        console.warn("Failed to trigger browser notification:", err);
      }
    },
    []
  );

  return {
    permission,
    requestPermission,
    showNotification,
    isSupported: permission !== "unsupported",
  };
}
