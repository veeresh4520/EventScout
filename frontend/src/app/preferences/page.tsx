"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
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

export default function PreferencesPage() {
  const { user, token, isAuthenticated, isLoading: authLoading, refreshUser, updateUser } = useAuth();
  const router = useRouter();
  const { permission: browserPerm, requestPermission: requestBrowserPerm } = useBrowserNotifications();

  const [activeTab, setActiveTab] = useState<"preferences" | "saved">("preferences");

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
      router.push("/login?redirect=/preferences");
    }
  }, [authLoading, isAuthenticated, router]);

  // Load preferences from user context or backend
  useEffect(() => {
    if (user) {
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
          return;
        }
      }
      throw new Error("Loading from local fallback");
    } catch {
      try {
        const fbRes = await fetch("/fallback_events.json");
        if (fbRes.ok) {
          const allEvents = await fbRes.json();
          const savedSet = new Set(user?.saved_event_ids || []);
          const matched = allEvents.filter((ev: any) => savedSet.has(ev.id) || savedSet.has(ev._id));
          setSavedEvents(matched);
          return;
        }
      } catch (fallbackErr) {
        console.error("Fallback error:", fallbackErr);
      }
      setSavedError("Unable to load saved events.");
    } finally {
      setLoadingSaved(false);
    }
  }, [apiUrl, token, user?.saved_event_ids]);

  useEffect(() => {
    if (activeTab === "saved" && token) {
      fetchSavedEvents();
    }
  }, [activeTab, token, fetchSavedEvents]);

  // Toggle helpers
  const toggleItem = (list: string[], setList: (v: string[]) => void, item: string) => {
    if (list.includes(item)) {
      setList(list.filter((x) => x !== item));
    } else {
      setList([...list, item]);
    }
  };

  const handleAddSkill = () => {
    const trimmed = skillsInput.trim();
    if (trimmed && !skillsList.includes(trimmed)) {
      setSkillsList([...skillsList, trimmed]);
      setSkillsInput("");
    }
  };

  const handleRemoveSkill = (skillToRemove: string) => {
    setSkillsList(skillsList.filter((s) => s !== skillToRemove));
  };

  // Save Preferences
  const handleSavePreferences = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;

    setSavingPrefs(true);
    setPrefsSuccess(null);
    setPrefsError(null);

    const updatedPrefs = {
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
      if (!token.startsWith("demo-token-")) {
        const res = await fetch(`${apiUrl}/me/preferences`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(updatedPrefs),
        });

        if (!res.ok) {
          const errorData = await res.json().catch(() => ({}));
          throw new Error(errorData.detail || "Failed to update preferences");
        }
      }

      updateUser(updatedPrefs);
      setPrefsSuccess("Preferences saved successfully!");
      await refreshUser();
      setTimeout(() => setPrefsSuccess(null), 4000);
    } catch (err: any) {
      if (
        !err.message ||
        err.message === "Failed to fetch" ||
        err.message.includes("NetworkError") ||
        err.name === "TypeError"
      ) {
        updateUser(updatedPrefs);
        setPrefsSuccess("Preferences saved successfully!");
        setTimeout(() => setPrefsSuccess(null), 4000);
      } else {
        setPrefsError(err.message || "An error occurred while saving preferences.");
      }
    } finally {
      setSavingPrefs(false);
    }
  };

  // Toggle Save on Saved Events Tab
  const handleToggleSaveOnTab = async (eventId: string, currentlySaved: boolean) => {
    if (!token) return;

    const method = currentlySaved ? "DELETE" : "POST";
    const endpoint = `${apiUrl}/events/${eventId}/save`;

    // Optimistically update list
    if (currentlySaved) {
      setSavedEvents((prev) => prev.filter((e) => (e.id || e._id) !== eventId));
    }
    const newSavedList = currentlySaved
      ? (user?.saved_event_ids || []).filter((id) => id !== eventId)
      : [...(user?.saved_event_ids || []), eventId];
    updateUser({ saved_event_ids: newSavedList });

    try {
      if (!token.startsWith("demo-token-")) {
        const res = await fetch(endpoint, {
          method,
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) {
          throw new Error("Failed to update saved event");
        }
      }
      refreshUser();
    } catch (err: any) {
      if (
        !err.message ||
        err.message === "Failed to fetch" ||
        err.message.includes("NetworkError") ||
        err.name === "TypeError"
      ) {
        return;
      }
      console.error(err);
      fetchSavedEvents(); // Revert by refetching
    }
  };

  if (authLoading || (!isAuthenticated && typeof window !== "undefined")) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 flex justify-center items-center">
        <div className="flex items-center gap-3 text-indigo-600 dark:text-indigo-400">
          <svg className="animate-spin h-6 w-6" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <span className="text-lg font-medium">Loading preferences...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Page Header */}
      <div className="mb-8">
        <h1 className="text-3xl sm:text-4xl font-extrabold text-gray-900 dark:text-white tracking-tight">
          Personalize Your Experience
        </h1>
        <p className="text-gray-600 dark:text-gray-300 mt-2">
          Manage your tech interests, preferences, and saved events.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 dark:border-gray-800 mb-8">
        <button
          onClick={() => setActiveTab("preferences")}
          className={`pb-4 px-4 text-base font-semibold transition-colors relative ${
            activeTab === "preferences"
              ? "text-indigo-600 dark:text-indigo-400 border-b-2 border-indigo-600 dark:border-indigo-400"
              : "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          }`}
        >
          My Preferences
        </button>
        <button
          onClick={() => setActiveTab("saved")}
          className={`pb-4 px-4 text-base font-semibold transition-colors relative flex items-center gap-2 ${
            activeTab === "saved"
              ? "text-indigo-600 dark:text-indigo-400 border-b-2 border-indigo-600 dark:border-indigo-400"
              : "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          }`}
        >
          <span>Saved Events</span>
          {user?.saved_event_ids && user.saved_event_ids.length > 0 && (
            <span className="px-2 py-0.5 text-xs rounded-full bg-indigo-100 text-indigo-800 dark:bg-indigo-900/60 dark:text-indigo-300 font-medium">
              {user.saved_event_ids.length}
            </span>
          )}
        </button>
      </div>

      {/* Tab 1: Preferences Form */}
      {activeTab === "preferences" && (
        <form onSubmit={handleSavePreferences} className="space-y-8 max-w-4xl">
          {prefsSuccess && (
            <div className="p-4 rounded-xl bg-green-50 dark:bg-green-950/40 border border-green-200 dark:border-green-800 text-green-800 dark:text-green-300 text-sm flex items-center gap-2">
              <svg className="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <span>{prefsSuccess}</span>
            </div>
          )}

          {prefsError && (
            <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-300 text-sm flex items-center gap-2">
              <svg className="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              <span>{prefsError}</span>
            </div>
          )}

          {/* Technical Interests */}
          <div className="bg-white dark:bg-gray-800/80 p-6 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-sm">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-1">
              Technical Interests
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Select topics you are passionate about.
            </p>
            <div className="flex flex-wrap gap-2.5">
              {INTEREST_OPTIONS.map((interest) => {
                const selected = selectedInterests.includes(interest);
                return (
                  <button
                    type="button"
                    key={interest}
                    onClick={() => toggleItem(selectedInterests, setSelectedInterests, interest)}
                    className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                      selected
                        ? "bg-indigo-600 text-white shadow-sm ring-2 ring-indigo-600 ring-offset-1 dark:ring-offset-gray-900"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700/60 dark:text-gray-300 dark:hover:bg-gray-700"
                    }`}
                  >
                    {interest}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Skills */}
          <div className="bg-white dark:bg-gray-800/80 p-6 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-sm">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-1">
              Skills & Technologies
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Add technical skills you know or want to learn (e.g. Python, React, Docker).
            </p>
            <div className="flex gap-2 max-w-md mb-4">
              <input
                type="text"
                value={skillsInput}
                onChange={(e) => setSkillsInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleAddSkill();
                  }
                }}
                placeholder="Add a skill and press Enter"
                className="flex-1 px-3.5 py-2.5 text-sm rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <button
                type="button"
                onClick={handleAddSkill}
                className="px-4 py-2.5 bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900 rounded-xl text-sm font-medium hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors"
              >
                Add
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {skillsList.map((skill) => (
                <span
                  key={skill}
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800/60 text-sm font-medium"
                >
                  {skill}
                  <button
                    type="button"
                    onClick={() => handleRemoveSkill(skill)}
                    className="text-indigo-400 hover:text-indigo-600 dark:hover:text-indigo-200 font-bold"
                  >
                    ×
                  </button>
                </span>
              ))}
              {skillsList.length === 0 && (
                <span className="text-sm text-gray-400 italic">No custom skills added yet.</span>
              )}
            </div>
          </div>

          {/* Preferred Event Types */}
          <div className="bg-white dark:bg-gray-800/80 p-6 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-sm">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-1">
              Preferred Event Types
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Select formats you enjoy attending.
            </p>
            <div className="flex flex-wrap gap-2.5">
              {EVENT_TYPE_OPTIONS.map((type) => {
                const selected = selectedEventTypes.includes(type);
                return (
                  <button
                    type="button"
                    key={type}
                    onClick={() => toggleItem(selectedEventTypes, setSelectedEventTypes, type)}
                    className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                      selected
                        ? "bg-indigo-600 text-white shadow-sm ring-2 ring-indigo-600 ring-offset-1 dark:ring-offset-gray-900"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700/60 dark:text-gray-300 dark:hover:bg-gray-700"
                    }`}
                  >
                    {type}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Preferred Modes */}
          <div className="bg-white dark:bg-gray-800/80 p-6 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-sm">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-1">
              Event Attendance Mode
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Do you prefer virtual, in-person, or hybrid events?
            </p>
            <div className="flex flex-wrap gap-2.5">
              {MODE_OPTIONS.map((mode) => {
                const selected = selectedModes.includes(mode);
                return (
                  <button
                    type="button"
                    key={mode}
                    onClick={() => toggleItem(selectedModes, setSelectedModes, mode)}
                    className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                      selected
                        ? "bg-indigo-600 text-white shadow-sm ring-2 ring-indigo-600 ring-offset-1 dark:ring-offset-gray-900"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700/60 dark:text-gray-300 dark:hover:bg-gray-700"
                    }`}
                  >
                    {mode}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Section 5: Notification Preferences */}
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 sm:p-8 shadow-sm border border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-1">
              5. Notification Preferences
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
              Choose how you want to be notified about newly discovered tech events matching your profile.
            </p>

            <div className="space-y-4">
              {/* Dashboard Notifications Toggle */}
              <div className="flex items-center justify-between p-4 rounded-xl border border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/30">
                <div>
                  <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                    Dashboard In-App Notifications
                  </h4>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    Show notification badge 🔔 and alerts on your dashboard when new events are discovered.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setDashboardEnabled(!dashboardEnabled)}
                  className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                    dashboardEnabled ? "bg-indigo-600" : "bg-gray-300 dark:bg-gray-600"
                  }`}
                  role="switch"
                  aria-checked={dashboardEnabled}
                >
                  <span
                    className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                      dashboardEnabled ? "translate-x-5" : "translate-x-0"
                    }`}
                  />
                </button>
              </div>

              {/* Browser / Device Notifications Toggle */}
              <div className="flex items-center justify-between p-4 rounded-xl border border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/30">
                <div className="mr-4">
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                      Browser & Device Notifications
                    </h4>
                    <span
                      className={`text-[11px] px-2 py-0.5 rounded-full font-semibold ${
                        browserPerm === "granted"
                          ? "bg-green-100 text-green-700 dark:bg-green-950/40 dark:text-green-300"
                          : "bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300"
                      }`}
                    >
                      {browserPerm === "granted" ? "Permission Allowed" : "Needs Permission"}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    Receive desktop alerts on this device while EventScout is open.
                  </p>
                  {browserPerm !== "granted" && (
                    <button
                      type="button"
                      onClick={requestBrowserPerm}
                      className="mt-2 text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:underline"
                    >
                      Request Browser Permission →
                    </button>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => setBrowserEnabled(!browserEnabled)}
                  className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                    browserEnabled ? "bg-indigo-600" : "bg-gray-300 dark:bg-gray-600"
                  }`}
                  role="switch"
                  aria-checked={browserEnabled}
                >
                  <span
                    className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                      browserEnabled ? "translate-x-5" : "translate-x-0"
                    }`}
                  />
                </button>
              </div>

              {/* Daily Email Digest Toggle */}
              <div className="flex items-center justify-between p-4 rounded-xl border border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/30">
                <div>
                  <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                    Daily Email Digest
                  </h4>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    Receive a clean daily summary of upcoming events sent directly to your email.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setEmailEnabled(!emailEnabled)}
                  className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                    emailEnabled ? "bg-indigo-600" : "bg-gray-300 dark:bg-gray-600"
                  }`}
                  role="switch"
                  aria-checked={emailEnabled}
                >
                  <span
                    className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                      emailEnabled ? "translate-x-5" : "translate-x-0"
                    }`}
                  />
                </button>
              </div>
            </div>
          </div>

          {/* Submit Button */}
          <div className="flex justify-end pt-4">
            <button
              type="submit"
              disabled={savingPrefs}
              className="px-6 py-3 bg-indigo-600 text-white font-medium rounded-xl hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {savingPrefs ? (
                <>
                  <svg className="animate-spin h-5 w-5 text-white" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <span>Saving...</span>
                </>
              ) : (
                "Save Preferences"
              )}
            </button>
          </div>
        </form>
      )}

      {/* Tab 2: Saved Events */}
      {activeTab === "saved" && (
        <div>
          {loadingSaved ? (
            <div className="py-16 text-center text-indigo-600 dark:text-indigo-400 flex items-center justify-center gap-2">
              <svg className="animate-spin h-6 w-6" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span>Loading your saved events...</span>
            </div>
          ) : savedError ? (
            <div className="p-8 rounded-2xl bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 text-center max-w-xl mx-auto">
              <p className="text-red-700 dark:text-red-400 font-medium">{savedError}</p>
              <button
                onClick={fetchSavedEvents}
                className="mt-4 px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                Retry
              </button>
            </div>
          ) : savedEvents.length === 0 ? (
            <div className="text-center py-16 px-4 bg-gray-50 dark:bg-gray-800/40 border border-dashed border-gray-300 dark:border-gray-700 rounded-2xl max-w-2xl mx-auto">
              <svg
                className="w-16 h-16 text-gray-400 mx-auto mb-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"
                />
              </svg>
              <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
                No saved events yet
              </h3>
              <p className="text-gray-500 dark:text-gray-400 mb-6">
                When you discover tech events you're interested in, click the bookmark icon on their card to save them here for quick access.
              </p>
              <Link
                href="/"
                className="inline-flex items-center px-5 py-2.5 bg-indigo-600 text-white font-medium rounded-xl hover:bg-indigo-700 transition-colors shadow-sm"
              >
                Discover Events
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {savedEvents.map((event) => {
                const eventId = event.id || event._id || "";
                return (
                  <EventCard
                    key={eventId || event.source_event_id || event.title}
                    event={event}
                    isSaved={true}
                    onToggleSave={handleToggleSaveOnTab}
                  />
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
