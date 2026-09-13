"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { NotificationItem, NotificationsResponse } from "@/types/notification";
import { useBrowserNotifications } from "@/hooks/useBrowserNotifications";

export default function NotificationBell() {
  const { token, isAuthenticated } = useAuth();
  const { showNotification } = useBrowserNotifications();

  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);

  const prevUnreadRef = useRef<number>(0);
  const panelRef = useRef<HTMLDivElement>(null);
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Fetch notifications from FastAPI backend
  const fetchNotifications = useCallback(async () => {
    if (!token || !isAuthenticated) return;
    try {
      const res = await fetch(`${apiUrl}/notifications?limit=25`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return;

      const data: NotificationsResponse = await res.json();
      setNotifications(data.notifications);
      setUnreadCount(data.unread_count);

      // Trigger browser notification if a brand new unread notification arrived
      if (data.unread_count > prevUnreadRef.current && prevUnreadRef.current !== 0) {
        const newest = data.notifications[0];
        if (newest && !newest.read) {
          showNotification(newest.title, {
            body: newest.message,
          });
        }
      }
      prevUnreadRef.current = data.unread_count;
    } catch (err) {
      console.warn("API notifications unreachable, using fallback notifications:", err);
      setNotifications((prev) => {
        if (prev.length > 0) return prev;
        return [
          {
            id: "notif-welcome",
            user_id: "demo-user",
            type: "welcome",
            title: "Welcome to EventScout! 🚀",
            message: "Explore hackathons and tech events matched directly to your profile.",
            read: false,
            created_at: new Date().toISOString(),
            event_id: "devfolio-1",
          },
          {
            id: "notif-match",
            user_id: "demo-user",
            type: "recommendation",
            title: "Top Match: AI Genesis Hackathon 🔥",
            message: "A new high-match opportunity in AI/ML is open for registration.",
            read: false,
            created_at: new Date(Date.now() - 3600000).toISOString(),
            event_id: "mlh-1",
          },
        ];
      });
      setUnreadCount((prev) => (prev > 0 ? prev : 2));
    }
  }, [apiUrl, token, isAuthenticated, showNotification]);

  // Initial load and periodic polling every 30 seconds
  useEffect(() => {
    if (isAuthenticated && token) {
      fetchNotifications();
      const interval = setInterval(fetchNotifications, 30000);
      return () => clearInterval(interval);
    } else {
      setNotifications([]);
      setUnreadCount(0);
    }
  }, [isAuthenticated, token, fetchNotifications]);

  // Click outside to close dropdown
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  // Mark single notification as read
  const handleMarkAsRead = async (id: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (!token) return;

    // Optimistic UI update
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
    setUnreadCount((c) => Math.max(0, c - 1));

    try {
      await fetch(`${apiUrl}/notifications/${id}/read`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch (err) {
      console.error("Failed to mark notification as read:", err);
    }
  };

  // Handle clicking anywhere on notification card: marks read & navigates to event
  const handleNotificationClick = (notif: NotificationItem) => {
    handleMarkAsRead(notif.id);
    setIsOpen(false);

    const targetUrl =
      notif.event_url ||
      (notif.event_id ? `/?q=${encodeURIComponent(notif.title)}` : undefined);

    if (targetUrl) {
      if (targetUrl.startsWith("http://") || targetUrl.startsWith("https://")) {
        window.open(targetUrl, "_blank", "noopener,noreferrer");
      } else {
        window.location.href = targetUrl;
      }
    }
  };

  // Mark all as read
  const handleMarkAllRead = async () => {
    if (!token) return;
    setLoading(true);

    // Optimistic UI update
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    setUnreadCount(0);

    try {
      await fetch(`${apiUrl}/notifications/read-all`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch (err) {
      console.error("Failed to mark all as read:", err);
    } finally {
      setLoading(false);
    }
  };

  if (!isAuthenticated) return null;

  return (
    <div className="relative" ref={panelRef}>
      {/* Bell Button */}
      <button
        id="notification-bell-btn"
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors focus:outline-none"
        aria-label="View notifications"
        title="Notifications"
      >
        <svg
          className="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
          />
        </svg>

        {/* Unread badge */}
        {unreadCount > 0 && (
          <span
            id="notification-badge"
            className="absolute top-1 right-1 flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[11px] font-bold text-white bg-indigo-600 rounded-full shadow-sm animate-pulse"
          >
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown Panel */}
      {isOpen && (
        <div
          id="notification-dropdown"
          className="absolute right-0 mt-2 w-80 sm:w-96 bg-white dark:bg-gray-800 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 py-3 z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-150"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 pb-3 border-b border-gray-100 dark:border-gray-700">
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-gray-900 dark:text-white text-base">
                Notifications
              </h3>
              {unreadCount > 0 && (
                <span className="text-xs bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300 px-2 py-0.5 rounded-full font-semibold">
                  {unreadCount} new
                </span>
              )}
            </div>

            {unreadCount > 0 && (
              <button
                id="mark-all-read-btn"
                onClick={handleMarkAllRead}
                disabled={loading}
                className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:underline disabled:opacity-50"
              >
                Mark all read
              </button>
            )}
          </div>

          {/* List */}
          <div className="max-h-[390px] overflow-y-auto divide-y divide-gray-100 dark:divide-gray-700/50">
            {notifications.length === 0 ? (
              <div className="py-10 text-center px-4">
                <div className="w-10 h-10 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center text-gray-400 mx-auto mb-2">
                  🔔
                </div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-300">
                  No notifications yet
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  We'll notify you when new events matching your interests are discovered.
                </p>
              </div>
            ) : (
              notifications.map((notif) => {
                const hasUrl = Boolean(notif.event_url || notif.event_id);
                return (
                  <div
                    key={notif.id}
                    onClick={() => handleNotificationClick(notif)}
                    className={`group relative p-3.5 transition-all flex items-start gap-3 cursor-pointer hover:bg-indigo-50/70 dark:hover:bg-indigo-950/40 border-l-[3px] ${
                      !notif.read
                        ? "bg-indigo-50/40 dark:bg-indigo-950/20 border-indigo-600"
                        : "border-transparent hover:border-indigo-400"
                    }`}
                    title={hasUrl ? "Click to view event opportunity" : "Click to view"}
                  >
                    {/* Status Indicator Icon / Dot */}
                    <div className="mt-1 flex-shrink-0">
                      {!notif.read ? (
                        <span className="w-2.5 h-2.5 rounded-full bg-indigo-600 block shadow-sm animate-pulse" />
                      ) : (
                        <span className="w-2 h-2 rounded-full bg-gray-300 dark:bg-gray-600 block opacity-40" />
                      )}
                    </div>

                    {/* Content */}
                    <div className="flex-grow min-w-0">
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-indigo-100 dark:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300">
                          {notif.type === "recommendation"
                            ? "🔥 Top Match"
                            : notif.type === "welcome"
                            ? "🚀 Update"
                            : "⚡ Event"}
                        </span>
                        <span className="text-[11px] text-gray-400">
                          {new Date(notif.created_at).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                      </div>

                      <p
                        className={`text-sm leading-snug line-clamp-2 transition-colors ${
                          !notif.read
                            ? "font-bold text-gray-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400"
                            : "font-medium text-gray-700 dark:text-gray-300 group-hover:text-indigo-600 dark:group-hover:text-indigo-400"
                        }`}
                      >
                        {notif.title}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-2 leading-relaxed">
                        {notif.message}
                      </p>

                      <div className="flex items-center justify-between mt-2.5 pt-1.5 border-t border-gray-100 dark:border-gray-700/50">
                        <span className="text-[11px] font-semibold text-indigo-600 dark:text-indigo-400 flex items-center gap-1 group-hover:translate-x-0.5 transition-transform">
                          <span>Open Opportunity</span>
                          <span>↗</span>
                        </span>
                        <span className="text-[10px] text-gray-400 dark:text-gray-500">
                          {!notif.read ? "Unread" : "Viewed"}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
