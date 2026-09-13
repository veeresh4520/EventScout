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
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const pathname = usePathname();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    setIsMobileMenuOpen(false);
    router.push("/");
  };

  const isActive = (href: string) =>
    pathname === href
      ? "text-indigo-600 dark:text-indigo-400 font-semibold"
      : "text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200 font-medium transition-colors";

  return (
    <header className="sticky top-0 z-50 bg-white/90 dark:bg-gray-900/90 backdrop-blur-md border-b border-gray-200 dark:border-gray-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <Link
            href="/"
            onClick={() => setIsMobileMenuOpen(false)}
            className="flex items-center gap-2.5 group"
          >
            <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center text-white font-black text-xl group-hover:bg-indigo-500 transition-colors shadow-md shadow-indigo-500/20">
              E
            </div>
            <span className="font-extrabold text-xl tracking-tight text-gray-900 dark:text-white">
              EventScout
            </span>
          </Link>
        </div>

        {/* Desktop Navigation Links */}
        <nav className="hidden md:flex items-center gap-5 lg:gap-6">
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
              <div className="flex items-center gap-2.5 ml-1">
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
                className="text-sm px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-semibold shadow-sm"
              >
                Sign up
              </Link>
            </>
          )}
        </nav>

        {/* Mobile Right Controls: Notification Bell + Hamburger Toggle */}
        <div className="flex md:hidden items-center gap-2">
          {isAuthenticated && <NotificationBell />}

          <button
            id="mobile-menu-toggle"
            type="button"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="p-2 rounded-xl text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            aria-label="Toggle mobile menu"
          >
            {isMobileMenuOpen ? (
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {isMobileMenuOpen && (
        <div className="md:hidden border-t border-gray-200 dark:border-gray-800 bg-white/95 dark:bg-gray-900/95 backdrop-blur-lg px-4 py-4 space-y-3 shadow-xl animate-in slide-in-from-top duration-200">
          {isAuthenticated && (
            <div className="p-3 bg-gray-50 dark:bg-gray-800/70 rounded-xl border border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-indigo-600 text-white font-bold text-sm flex items-center justify-center uppercase shadow-sm">
                  {(user?.username || user?.email || "U").slice(0, 2)}
                </div>
                <div className="flex flex-col">
                  <span className="text-sm font-semibold text-gray-900 dark:text-white">
                    {user?.username || user?.email?.split("@")[0]}
                  </span>
                  <span className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-[200px]">
                    {user?.email}
                  </span>
                </div>
              </div>
              {user?.is_admin && (
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-500/30">
                  Admin
                </span>
              )}
            </div>
          )}

          <div className="flex flex-col space-y-1">
            <Link
              href="/"
              onClick={() => setIsMobileMenuOpen(false)}
              className={`px-3 py-2.5 rounded-lg text-sm font-medium flex items-center gap-2 ${
                pathname === "/"
                  ? "bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 font-bold"
                  : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
              }`}
            >
              <span>🧭</span>
              <span>Discover Events</span>
            </Link>

            {isAuthenticated ? (
              <>
                <Link
                  href="/preferences"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className={`px-3 py-2.5 rounded-lg text-sm font-medium flex items-center gap-2 ${
                    pathname === "/preferences"
                      ? "bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 font-bold"
                      : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
                  }`}
                >
                  <span>⚙️</span>
                  <span>My Preferences & Saved</span>
                </Link>

                <button
                  onClick={() => {
                    setIsMobileMenuOpen(false);
                    setIsSuggestModalOpen(true);
                  }}
                  className="w-full text-left px-3 py-2.5 rounded-lg text-sm font-medium text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 flex items-center gap-2"
                >
                  <span>➕</span>
                  <span>Suggest Event URL</span>
                </button>

                {user?.is_admin && (
                  <Link
                    href="/admin/sources"
                    onClick={() => setIsMobileMenuOpen(false)}
                    className="px-3 py-2.5 rounded-lg text-sm font-medium text-amber-700 dark:text-amber-300 hover:bg-amber-50 dark:hover:bg-amber-950/30 flex items-center gap-2"
                  >
                    <span>🛡️</span>
                    <span>Admin Dashboard</span>
                  </Link>
                )}

                <div className="pt-2 border-t border-gray-200 dark:border-gray-800">
                  <button
                    onClick={handleLogout}
                    className="w-full px-3 py-2.5 rounded-lg text-sm font-semibold text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30 flex items-center gap-2"
                  >
                    <span>🚪</span>
                    <span>Log Out</span>
                  </button>
                </div>
              </>
            ) : (
              <div className="pt-2 flex flex-col gap-2">
                <Link
                  href="/login"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className="w-full text-center py-2.5 px-4 rounded-xl border border-gray-300 dark:border-gray-700 text-sm font-semibold text-gray-800 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
                >
                  Log In
                </Link>
                <Link
                  href="/signup"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className="w-full text-center py-2.5 px-4 rounded-xl bg-indigo-600 text-sm font-semibold text-white hover:bg-indigo-700 shadow-md shadow-indigo-500/20"
                >
                  Create Free Account
                </Link>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Suggest Source Modal */}
      <SuggestSourceModal
        isOpen={isSuggestModalOpen}
        onClose={() => setIsSuggestModalOpen(false)}
      />
    </header>
  );
}
