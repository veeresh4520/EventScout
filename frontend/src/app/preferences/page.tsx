"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function PreferencesPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/profile?tab=preferences");
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
          Loading your preferences & profile...
        </p>
      </div>
    </div>
  );
}
