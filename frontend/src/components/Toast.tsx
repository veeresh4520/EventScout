"use client";

import { useEffect, useState } from "react";

export default function Toast() {
  const [toast, setToast] = useState<{ message: string; visible: boolean }>({
    message: "",
    visible: false,
  });

  useEffect(() => {
    let timeoutId: NodeJS.Timeout;

    const handleToast = (e: Event) => {
      const customEvent = e as CustomEvent<{ message: string }>;
      const msg = customEvent.detail?.message || "Saved";
      setToast({ message: msg, visible: true });

      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => {
        setToast((prev) => ({ ...prev, visible: false }));
      }, 2500);
    };

    window.addEventListener("eventscout-toast", handleToast);
    return () => {
      window.removeEventListener("eventscout-toast", handleToast);
      clearTimeout(timeoutId);
    };
  }, []);

  if (!toast.visible) return null;

  return (
    <div
      id="bottom-left-toast"
      role="status"
      aria-live="polite"
      className="fixed bottom-6 left-6 z-50 flex items-center gap-2 bg-gray-900/95 dark:bg-gray-800/95 text-white text-xs font-semibold px-3 py-2 rounded-lg shadow-xl border border-gray-700/60 backdrop-blur-md transition-all duration-300 transform translate-y-0 opacity-100 animate-in fade-in slide-in-from-bottom-3"
    >
      <span className="flex h-2 w-2 relative">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
      </span>
      <span>{toast.message}</span>
    </div>
  );
}
