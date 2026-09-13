"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import NotificationBell from "@/components/NotificationBell";
import SuggestSourceModal from "@/components/SuggestSourceModal";

export default function NavBar() {
  const { user, isAuthenticated, logout } = useAuth();
  const [isSuggestModalOpen, setIsSuggestModalOpen] = useState(false);
  const pathname = usePathname();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push("/");
  };

  const isActive = (href: string) =>
    pathname === href
      ? "text-indigo-600 dark:text-indigo-400 font-semibold"
      : "text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200 font-medium transition-colors";

  return (
    <header className="sticky top-0 z-50 bg-white/80 dark:bg-gray-900/80 backdrop-blur-md border-b border-gray-200 dark:border-gray-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <Link href="/" className="flex items-center gap-2 group">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-bold text-xl group-hover:bg-indigo-500 transition-colors">
              E
            </div>
            <span className="font-bold text-xl tracking-tight hidden sm:block">
              EventScout
            </span>
          </Link>
        </div>

        {/* Navigation Links */}
        <nav className="flex items-center gap-6">
          <Link href="/" className={`text-sm ${isActive("/")}`}>
            Discover
          </Link>

          {isAuthenticated ? (
            <>
              <Link
                href="/preferences"
                className={`text-sm ${isActive("/preferences")}`}
              >
                Preferences
              </Link>

              <button
                id="suggest-source-btn"
                onClick={() => setIsSuggestModalOpen(true)}
                className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800 hover:bg-indigo-100 dark:hover:bg-indigo-900/50 transition-all flex items-center gap-1.5"
                title="Add or suggest a new event website URL for EventScout"
              >
                <span>➕</span>
                <span>Add URL</span>
              </button>

              {user?.is_admin && (
                <Link
                  id="admin-dashboard-link"
                  href="/admin/sources"
                  className={`text-sm font-semibold px-3 py-1.5 rounded-lg bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-500/30 hover:bg-amber-500/20 transition-all flex items-center gap-1.5 ${
                    pathname === "/admin/sources" ? "ring-2 ring-amber-500 shadow-sm" : ""
                  }`}
                  title="Admin Dashboard & Source Discovery"
                >
                  <span>⚙️</span>
                  <span>Admin Dashboard</span>
                </Link>
              )}

              {/* Notification Bell */}
              <NotificationBell />

              {/* User menu / Profile area */}
              <div className="flex items-center gap-3 ml-1">
                <div
                  id="user-profile-badge"
                  className="flex items-center gap-2 bg-gray-100 dark:bg-gray-800 py-1 px-2.5 rounded-full border border-gray-200 dark:border-gray-700"
                  title={user?.email}
                >
                  <div className="w-6 h-6 rounded-full bg-indigo-600 text-white font-bold text-xs flex items-center justify-center uppercase">
                    {(user?.username || user?.email || "U").slice(0, 2)}
                  </div>
                  <span className="text-sm font-medium text-gray-800 dark:text-gray-200 max-w-[120px] truncate">
                    {user?.username || user?.email?.split("@")[0]}
                  </span>
                  {user?.is_admin && (
                    <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-500/30">
                      Admin
                    </span>
                  )}
                </div>
                <button
                  id="logout-button"
                  onClick={handleLogout}
                  className="text-sm px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                >
                  Log out
                </button>
              </div>
            </>
          ) : (
            <>
              <Link
                href="/login"
                className={`text-sm ${isActive("/login")}`}
              >
                Log in
              </Link>
              <Link
                href="/signup"
                className="text-sm px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium shadow-sm"
              >
                Sign up
              </Link>
            </>
          )}
        </nav>
      </div>

      {/* Suggest Source Modal */}
      <SuggestSourceModal
        isOpen={isSuggestModalOpen}
        onClose={() => setIsSuggestModalOpen(false)}
      />
    </header>
  );
}
