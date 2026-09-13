"use client";

import { useEffect, useState, useCallback, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import { Event } from "@/types/event";
import EventCard from "@/components/EventCard";
import { useBrowserNotifications } from "@/hooks/useBrowserNotifications";

const INTEREST_OPTIONS = [
  "AI / ML",
  "Web Development",
  "Cloud",
  "Cybersecurity",
  "Data Science",
  "DevOps",
  "Open Source",
  "Mobile Development",
  "Blockchain",
  "IoT",
  "Robotics",
  "Game Development",
];

const EVENT_TYPE_OPTIONS = [
  "Hackathon",
  "Workshop",
  "Meetup",
  "Conference",
  "Webinar",
  "Talk",
];

const MODE_OPTIONS = ["Online", "Offline", "Hybrid"];

function ProfileContent() {
  const { user, token, isAuthenticated, isLoading: authLoading, refreshUser, updateUser } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialTab = (searchParams.get("tab") as "profile" | "saved" | "preferences") || "profile";
  const { permission: browserPerm, requestPermission: requestBrowserPerm } = useBrowserNotifications();

  const [activeTab, setActiveTab] = useState<"profile" | "saved" | "preferences">(initialTab);

  // Profile Form State
  const [usernameInput, setUsernameInput] = useState<string>("");
  const [savingProfile, setSavingProfile] = useState<boolean>(false);
  const [profileSuccess, setProfileSuccess] = useState<string | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);

  // Preferences Form State
  const [selectedInterests, setSelectedInterests] = useState<string[]>([]);
  const [selectedEventTypes, setSelectedEventTypes] = useState<string[]>([]);
  const [selectedModes, setSelectedModes] = useState<string[]>([]);
  const [skillsInput, setSkillsInput] = useState<string>("");
  const [skillsList, setSkillsList] = useState<string[]>([]);

  // Notification Preferences State
  const [dashboardEnabled, setDashboardEnabled] = useState(true);
  const [browserEnabled, setBrowserEnabled] = useState(true);
  const [emailEnabled, setEmailEnabled] = useState(true);

  const [savingPrefs, setSavingPrefs] = useState(false);
  const [prefsSuccess, setPrefsSuccess] = useState<string | null>(null);
  const [prefsError, setPrefsError] = useState<string | null>(null);

  // Saved Events State
  const [savedEvents, setSavedEvents] = useState<Event[]>([]);
  const [loadingSaved, setLoadingSaved] = useState(false);
  const [savedError, setSavedError] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Redirect if unauthenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login?redirect=/profile");
    }
  }, [authLoading, isAuthenticated, router]);

  // Load user data into form states
  useEffect(() => {
    if (user) {
      setUsernameInput(user.username || user.email?.split("@")[0] || "");
      setSelectedInterests(user.interests || []);
      setSelectedEventTypes(user.preferred_event_types || []);
      setSelectedModes(user.preferred_modes || []);
      setSkillsList(user.skills || []);

      if (user.notification_preferences) {
        setDashboardEnabled(user.notification_preferences.dashboard_enabled ?? true);
        setBrowserEnabled(user.notification_preferences.browser_enabled ?? true);
        setEmailEnabled(user.notification_preferences.email_enabled ?? true);
      }
    }
  }, [user]);

  // Fetch saved events
  const fetchSavedEvents = useCallback(async () => {
    if (!token) return;
    setLoadingSaved(true);
    setSavedError(null);
    try {
      if (!token.startsWith("demo-token-")) {
        const res = await fetch(`${apiUrl}/events/saved`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setSavedEvents(data);
          setLoadingSaved(false);
          return;
        }
      }

      // Fallback if backend offline or demo: fetch from local fallback_events.json using saved_event_ids
      const localIds = new Set(user?.saved_event_ids || []);
      const fallbackRes = await fetch("/fallback_events.json");
      if (fallbackRes.ok) {
        const allEvents: Event[] = await fallbackRes.json();
        const userSaved = allEvents.filter((e) => e.id && localIds.has(e.id));
        setSavedEvents(userSaved);
      }
    } catch (err: any) {
      console.warn("Failed to fetch saved events from API, using fallback:", err);
      const localIds = new Set(user?.saved_event_ids || []);
      try {
        const fallbackRes = await fetch("/fallback_events.json");
        if (fallbackRes.ok) {
          const allEvents: Event[] = await fallbackRes.json();
          setSavedEvents(allEvents.filter((e) => e.id && localIds.has(e.id)));
        }
      } catch {
        setSavedError("Unable to load saved events. Please try again.");
      }
    } finally {
      setLoadingSaved(false);
    }
  }, [apiUrl, token, user?.saved_event_ids]);

  // Load saved events when saved tab is chosen or on mount
  useEffect(() => {
    if (isAuthenticated && token) {
      fetchSavedEvents();
    }
  }, [isAuthenticated, token, fetchSavedEvents]);

  // Handle Save Profile (Username)
  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingProfile(true);
    setProfileSuccess(null);
    setProfileError(null);

    const trimmed = usernameInput.trim();
    if (!trimmed) {
      setProfileError("Username cannot be empty.");
      setSavingProfile(false);
      return;
    }

    try {
      if (!token?.startsWith("demo-token-")) {
        const res = await fetch(`${apiUrl}/me/profile`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ username: trimmed }),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || "Failed to update profile.");
        }
      }

      // Update local auth context
      updateUser({ username: trimmed });
      setProfileSuccess("Username updated successfully!");
      if (typeof window !== "undefined") {
        window.dispatchEvent(
          new CustomEvent("eventscout-toast", { detail: { message: "Profile Saved" } })
        );
      }
      setTimeout(() => setProfileSuccess(null), 4000);
    } catch (err: any) {
      setProfileError(err.message || "Failed to update username.");
    } finally {
      setSavingProfile(false);
    }
  };

  // Handle Save Preferences
  const handleSavePreferences = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingPrefs(true);
    setPrefsSuccess(null);
    setPrefsError(null);

    const payload = {
      interests: selectedInterests,
      skills: skillsList,
      preferred_event_types: selectedEventTypes,
      preferred_modes: selectedModes,
      notification_preferences: {
        dashboard_enabled: dashboardEnabled,
        browser_enabled: browserEnabled,
        email_enabled: emailEnabled,
      },
    };

    try {
      if (!token?.startsWith("demo-token-")) {
        const res = await fetch(`${apiUrl}/me/preferences`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || "Failed to update preferences.");
        }
      }

      updateUser(payload);
      setPrefsSuccess("Preferences saved successfully!");
      if (typeof window !== "undefined") {
        window.dispatchEvent(
          new CustomEvent("eventscout-toast", { detail: { message: "Preferences Saved" } })
        );
      }
      setTimeout(() => setPrefsSuccess(null), 4000);
    } catch (err: any) {
      setPrefsError(err.message || "Failed to save preferences.");
    } finally {
      setSavingPrefs(false);
    }
  };

  // Toggle interest
  const toggleInterest = (interest: string) => {
    setSelectedInterests((prev) =>
      prev.includes(interest) ? prev.filter((i) => i !== interest) : [...prev, interest]
    );
  };

  // Toggle event type
  const toggleEventType = (type: string) => {
    setSelectedEventTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  // Toggle mode
  const toggleMode = (mode: string) => {
    setSelectedModes((prev) =>
      prev.includes(mode) ? prev.filter((m) => m !== mode) : [...prev, mode]
    );
  };

  // Add skill tag
  const handleAddSkill = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      const val = skillsInput.trim().replace(/^,+|,+$/g, "");
      if (val && !skillsList.includes(val)) {
        setSkillsList((prev) => [...prev, val]);
        setSkillsInput("");
      }
    }
  };

  const removeSkill = (skillToRemove: string) => {
    setSkillsList((prev) => prev.filter((s) => s !== skillToRemove));
  };

  // Toggle Save on Saved Events tab
  const handleToggleSaveOnTab = async (eventId: string, currentlySaved: boolean) => {
    if (!token) return;

    // Optimistically update list
    if (currentlySaved) {
      setSavedEvents((prev) => prev.filter((ev) => ev.id !== eventId));
      const nextIds = (user?.saved_event_ids || []).filter((id) => id !== eventId);
      updateUser({ saved_event_ids: nextIds });
    }

    try {
      if (!token.startsWith("demo-token-")) {
        const endpoint = `${apiUrl}/events/${eventId}/save`;
        await fetch(endpoint, {
          method: currentlySaved ? "DELETE" : "POST",
          headers: { Authorization: `Bearer ${token}` },
        });
      }
      refreshUser();
    } catch (err) {
      console.error("Error updating saved event:", err);
      fetchSavedEvents();
    }
  };

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
            Loading your profile...
          </p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) return null;

  const savedCount = user?.saved_event_ids?.length || savedEvents.length;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
      {/* Profile Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white p-6 sm:p-8 rounded-2xl shadow-xl border border-indigo-900/50 mb-8 relative overflow-hidden">
        {/* Glow decoration */}
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-0 -ml-16 -mb-16 w-64 h-64 bg-purple-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-5">
          <div className="flex items-center gap-4 sm:gap-5">
            <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl bg-gradient-to-tr from-indigo-600 to-violet-500 text-white font-black text-2xl sm:text-3xl flex items-center justify-center shadow-lg uppercase border border-white/20">
              {(user?.username || user?.email || "U").slice(0, 2)}
            </div>
            <div>
              <div className="flex items-center gap-2.5 flex-wrap">
                <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
                  {user?.username || user?.email?.split("@")[0]}
                </h1>
                {user?.is_admin && (
                  <span className="text-xs uppercase font-extrabold tracking-wider px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-400/30 shadow-sm">
                    Admin
                  </span>
                )}
              </div>
              <p className="text-sm text-indigo-200/80 mt-1 font-mono">
                {user?.email}
              </p>
              <div className="flex items-center gap-3 mt-2 text-xs text-indigo-300/70">
                <span>Joined {user?.created_at ? new Date(user.created_at).toLocaleDateString("en-US", { month: "short", year: "numeric" }) : "Recently"}</span>
                <span>•</span>
                <span className="text-amber-300 font-semibold">{savedCount} Saved Opportunities</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {user?.is_admin && (
              <Link
                href="/admin/sources"
                className="px-3.5 py-2 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/30 text-xs font-bold transition-all flex items-center gap-1.5 shadow-sm"
              >
                <span>⚙️</span>
                <span>Admin Sources</span>
              </Link>
            )}
            <Link
              href="/"
              className="px-3.5 py-2 rounded-xl bg-white/10 hover:bg-white/15 text-white border border-white/10 text-xs font-semibold transition-all flex items-center gap-1.5"
            >
              <span>🧭</span>
              <span>Discover Events</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-gray-200 dark:border-gray-800 pb-px mb-8 overflow-x-auto no-scrollbar">
        <button
          id="profile-tab-details"
          onClick={() => setActiveTab("profile")}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-bold border-b-2 transition-all whitespace-nowrap ${
            activeTab === "profile"
              ? "border-indigo-600 text-indigo-600 dark:text-indigo-400 bg-indigo-50/50 dark:bg-indigo-950/20 rounded-t-lg"
              : "border-transparent text-gray-500 hover:text-gray-900 dark:hover:text-white"
          }`}
        >
          <span>👤</span>
          <span>Profile Details</span>
        </button>

        <button
          id="profile-tab-saved"
          onClick={() => {
            setActiveTab("saved");
            fetchSavedEvents();
          }}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-bold border-b-2 transition-all whitespace-nowrap ${
            activeTab === "saved"
              ? "border-indigo-600 text-indigo-600 dark:text-indigo-400 bg-indigo-50/50 dark:bg-indigo-950/20 rounded-t-lg"
              : "border-transparent text-gray-500 hover:text-gray-900 dark:hover:text-white"
          }`}
        >
          <span>🔖</span>
          <span>Saved Events</span>
          <span className="text-xs bg-indigo-100 text-indigo-700 dark:bg-indigo-900/60 dark:text-indigo-300 px-2 py-0.5 rounded-full font-bold">
            {savedCount}
          </span>
        </button>

        <button
          id="profile-tab-preferences"
          onClick={() => setActiveTab("preferences")}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-bold border-b-2 transition-all whitespace-nowrap ${
            activeTab === "preferences"
              ? "border-indigo-600 text-indigo-600 dark:text-indigo-400 bg-indigo-50/50 dark:bg-indigo-950/20 rounded-t-lg"
              : "border-transparent text-gray-500 hover:text-gray-900 dark:hover:text-white"
          }`}
        >
          <span>⚙️</span>
          <span>Discovery Preferences & Alerts</span>
        </button>
      </div>

      {/* Tab 1: Profile Details */}
      {activeTab === "profile" && (
        <div className="space-y-6">
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 sm:p-8">
            <div className="border-b border-gray-100 dark:border-gray-700 pb-4 mb-6">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <span>👤</span>
                <span>User Profile Details</span>
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                Manage your account credentials and personal display handle.
              </p>
            </div>

            {profileSuccess && (
              <div className="mb-6 p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 text-sm flex items-center gap-2">
                <span>✓</span>
                <span>{profileSuccess}</span>
              </div>
            )}

            {profileError && (
              <div className="mb-6 p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-sm flex items-center gap-2">
                <span>⚠️</span>
                <span>{profileError}</span>
              </div>
            )}

            <form onSubmit={handleSaveProfile} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Username Input */}
                <div>
                  <label
                    htmlFor="profile-username"
                    className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1.5"
                  >
                    Username / Handle
                  </label>
                  <input
                    id="profile-username"
                    type="text"
                    value={usernameInput}
                    onChange={(e) => setUsernameInput(e.target.value)}
                    required
                    placeholder="e.g. techgeek"
                    className="w-full px-4 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-medium text-sm transition-all"
                  />
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1.5">
                    Your unique username used on your profile and event notifications.
                  </p>
                </div>

                {/* Email (Display) */}
                <div>
                  <label
                    htmlFor="profile-email"
                    className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1.5"
                  >
                    Email Address
                  </label>
                  <input
                    id="profile-email"
                    type="email"
                    value={user?.email || ""}
                    disabled
                    className="w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 text-gray-500 dark:text-gray-400 cursor-not-allowed font-medium text-sm"
                  />
                  <p className="text-xs text-gray-400 mt-1.5">
                    Primary login identifier for EventScout.
                  </p>
                </div>
              </div>

              {/* Account Role & Statistics */}
              <div className="p-4 rounded-xl bg-gray-50 dark:bg-gray-900/60 border border-gray-100 dark:border-gray-700/60 grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider block">
                    Account Role
                  </span>
                  <span className="text-sm font-bold text-gray-900 dark:text-white mt-0.5 inline-block">
                    {user?.is_admin ? "🛡️ System Administrator" : "👤 Standard Member"}
                  </span>
                </div>
                <div>
                  <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider block">
                    Saved Opportunities
                  </span>
                  <span className="text-sm font-bold text-indigo-600 dark:text-indigo-400 mt-0.5 inline-block">
                    {savedCount} Events
                  </span>
                </div>
                <div>
                  <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider block">
                    Discovery Topics
                  </span>
                  <span className="text-sm font-bold text-gray-900 dark:text-white mt-0.5 inline-block">
                    {selectedInterests.length > 0 ? `${selectedInterests.length} Selected` : "None configured"}
                  </span>
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  id="save-profile-btn"
                  type="submit"
                  disabled={savingProfile}
                  className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-sm rounded-xl shadow-md hover:shadow-lg transition-all disabled:opacity-50 flex items-center gap-2"
                >
                  {savingProfile ? (
                    <>
                      <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>Saving Profile...</span>
                    </>
                  ) : (
                    <>
                      <span>Save Profile Changes</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Tab 2: Saved Events */}
      {activeTab === "saved" && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <span>🔖</span>
                <span>My Saved Technical Events</span>
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                All hackathons, workshops, and hiring challenges you bookmarked.
              </p>
            </div>
            <button
              onClick={fetchSavedEvents}
              disabled={loadingSaved}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300 transition-colors flex items-center gap-1.5"
            >
              <span>🔄</span>
              <span>Refresh</span>
            </button>
          </div>

          {loadingSaved ? (
            <div className="py-16 text-center">
              <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Loading saved events...
              </p>
            </div>
          ) : savedError ? (
            <div className="p-6 bg-rose-50 dark:bg-rose-950/30 rounded-2xl border border-rose-200 dark:border-rose-800 text-center">
              <p className="text-sm font-medium text-rose-700 dark:text-rose-300">{savedError}</p>
              <button
                onClick={fetchSavedEvents}
                className="mt-3 px-4 py-2 bg-rose-600 text-white rounded-lg text-xs font-bold"
              >
                Retry
              </button>
            </div>
          ) : savedEvents.length === 0 ? (
            <div className="py-16 text-center bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-8">
              <div className="w-16 h-16 rounded-full bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 flex items-center justify-center text-2xl mx-auto mb-4">
                🔖
              </div>
              <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">
                No saved events yet
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md mx-auto mb-6">
                When you discover hackathons, conferences, or workshops you like, click the bookmark icon on any event card to save it here.
              </p>
              <Link
                href="/"
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-sm rounded-xl shadow-md transition-all"
              >
                <span>🧭</span>
                <span>Discover Opportunities</span>
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {savedEvents.map((event) => (
                <EventCard
                  key={event.id || event.title}
                  event={event}
                  isSaved={true}
                  onToggleSave={handleToggleSaveOnTab}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Preferences */}
      {activeTab === "preferences" && (
        <form onSubmit={handleSavePreferences} className="space-y-8">
          {prefsSuccess && (
            <div className="p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 text-sm flex items-center gap-2">
              <span>✓</span>
              <span>{prefsSuccess}</span>
            </div>
          )}

          {prefsError && (
            <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-sm flex items-center gap-2">
              <span>⚠️</span>
              <span>{prefsError}</span>
            </div>
          )}

          {/* Technical Interests */}
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 sm:p-8 border border-gray-200 dark:border-gray-700 shadow-sm">
            <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2 mb-2">
              <span>💻</span>
              <span>Technical Interests</span>
            </h2>
            <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mb-5">
              Select topics you care about. EventScout ranks matching hackathons and conferences higher on your feed.
            </p>
            <div className="flex flex-wrap gap-2.5">
              {INTEREST_OPTIONS.map((interest) => {
                const isSelected = selectedInterests.includes(interest);
                return (
                  <button
                    key={interest}
                    type="button"
                    onClick={() => toggleInterest(interest)}
                    className={`px-3.5 py-1.5 rounded-full text-xs font-semibold border transition-all ${
                      isSelected
                        ? "bg-indigo-600 text-white border-indigo-600 shadow-sm ring-2 ring-indigo-500/20"
                        : "bg-gray-50 dark:bg-gray-900/50 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-700 hover:border-indigo-400"
                    }`}
                  >
                    {interest} {isSelected && "✓"}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Event Types & Preferred Modes */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Event Types */}
            <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 sm:p-8 border border-gray-200 dark:border-gray-700 shadow-sm">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2 mb-2">
                <span>⚡</span>
                <span>Preferred Event Types</span>
              </h2>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
                What formats do you prefer participating in?
              </p>
              <div className="flex flex-wrap gap-2">
                {EVENT_TYPE_OPTIONS.map((type) => {
                  const isSelected = selectedEventTypes.includes(type);
                  return (
                    <button
                      key={type}
                      type="button"
                      onClick={() => toggleEventType(type)}
                      className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition-all ${
                        isSelected
                          ? "bg-amber-600 text-white border-amber-600 shadow-sm"
                          : "bg-gray-50 dark:bg-gray-900/50 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-700 hover:border-amber-400"
                      }`}
                    >
                      {type} {isSelected && "✓"}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Preferred Modes */}
            <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 sm:p-8 border border-gray-200 dark:border-gray-700 shadow-sm">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2 mb-2">
                <span>📍</span>
                <span>Delivery Mode</span>
              </h2>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
                Filter by online virtual events or in-person venues.
              </p>
              <div className="flex flex-wrap gap-2">
                {MODE_OPTIONS.map((mode) => {
                  const isSelected = selectedModes.includes(mode);
                  return (
                    <button
                      key={mode}
                      type="button"
                      onClick={() => toggleMode(mode)}
                      className={`px-3.5 py-1.5 rounded-full text-xs font-semibold border transition-all ${
                        isSelected
                          ? "bg-emerald-600 text-white border-emerald-600 shadow-sm"
                          : "bg-gray-50 dark:bg-gray-900/50 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-700 hover:border-emerald-400"
                      }`}
                    >
                      {mode} {isSelected && "✓"}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Skills & Technologies Tag Input */}
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 sm:p-8 border border-gray-200 dark:border-gray-700 shadow-sm">
            <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2 mb-2">
              <span>🎯</span>
              <span>Skills & Tech Stack</span>
            </h2>
            <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mb-4">
              Add languages, frameworks, or tools (e.g. Python, Next.js, Docker). Press Enter to add.
            </p>
            <div className="space-y-3">
              <input
                type="text"
                value={skillsInput}
                onChange={(e) => setSkillsInput(e.target.value)}
                onKeyDown={handleAddSkill}
                placeholder="Type a skill and press Enter..."
                className="w-full px-4 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
              />
              {skillsList.length > 0 && (
                <div className="flex flex-wrap gap-2 pt-2">
                  {skillsList.map((skill) => (
                    <span
                      key={skill}
                      className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800"
                    >
                      {skill}
                      <button
                        type="button"
                        onClick={() => removeSkill(skill)}
                        className="hover:text-red-500 transition-colors"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Notification Channels */}
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 sm:p-8 border border-gray-200 dark:border-gray-700 shadow-sm space-y-5">
            <div>
              <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2 mb-1">
                <span>🔔</span>
                <span>Notification Preferences</span>
              </h2>
              <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">
                Choose how and when EventScout alerts you to matching opportunities.
              </p>
            </div>

            <div className="divide-y divide-gray-100 dark:divide-gray-700/60">
              {/* Dashboard */}
              <div className="py-3.5 flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                    Dashboard & In-App Notifications
                  </h4>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Badge and notification drawer in the top navigation bar.
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={dashboardEnabled}
                  onChange={(e) => setDashboardEnabled(e.target.checked)}
                  className="w-5 h-5 text-indigo-600 rounded focus:ring-indigo-500 cursor-pointer"
                />
              </div>

              {/* Browser Push */}
              <div className="py-3.5 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                      Instant Browser Push Alerts
                    </h4>
                    <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300">
                      {browserPerm === "granted" ? "Active" : "Permission Needed"}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Receive desktop notifications when top events matching your profile are crawled.
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  {browserPerm !== "granted" && (
                    <button
                      type="button"
                      onClick={requestBrowserPerm}
                      className="px-2.5 py-1 text-xs font-bold text-indigo-600 dark:text-indigo-400 border border-indigo-300 dark:border-indigo-700 rounded-lg hover:bg-indigo-50 dark:hover:bg-indigo-950/40"
                    >
                      Allow
                    </button>
                  )}
                  <input
                    type="checkbox"
                    checked={browserEnabled}
                    onChange={(e) => setBrowserEnabled(e.target.checked)}
                    className="w-5 h-5 text-indigo-600 rounded focus:ring-indigo-500 cursor-pointer"
                  />
                </div>
              </div>

              {/* Email */}
              <div className="py-3.5 flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                    Email Digest Alerts
                  </h4>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Receive morning summaries with upcoming deadlines directly to {user?.email}.
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={emailEnabled}
                  onChange={(e) => setEmailEnabled(e.target.checked)}
                  className="w-5 h-5 text-indigo-600 rounded focus:ring-indigo-500 cursor-pointer"
                />
              </div>
            </div>
          </div>

          <div className="flex justify-end pt-4">
            <button
              id="save-preferences-btn"
              type="submit"
              disabled={savingPrefs}
              className="px-8 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-sm rounded-xl shadow-lg hover:shadow-xl transition-all disabled:opacity-50 flex items-center gap-2"
            >
              {savingPrefs ? (
                <>
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Saving Preferences...</span>
                </>
              ) : (
                <span>Save Discovery Preferences</span>
              )}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

export default function ProfilePage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="flex flex-col items-center gap-3">
            <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
              Loading your profile...
            </p>
          </div>
        </div>
      }
    >
      <ProfileContent />
    </Suspense>
  );
}
