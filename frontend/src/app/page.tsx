"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { Event } from "@/types/event";
import EventCard from "@/components/EventCard";
import { useAuth } from "@/contexts/AuthContext";
import { isHackathon, isWorkshop, EventSectionType } from "@/utils/eventUtils";

export default function DiscoverPage() {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Authentication & Saved state
  const { user, token, isAuthenticated, refreshUser } = useAuth();
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set());

  // Sync saved event IDs with the authenticated user
  useEffect(() => {
    if (user?.saved_event_ids) {
      setSavedIds(new Set(user.saved_event_ids));
    } else {
      setSavedIds(new Set());
    }
  }, [user?.saved_event_ids]);

  // Section Tab, Search & Multi-Facet Filters
  const [activeSection, setActiveSection] = useState<EventSectionType>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("All");
  const [selectedMode, setSelectedMode] = useState<string>("All");
  const [selectedPrice, setSelectedPrice] = useState<string>("All");
  const [selectedSource, setSelectedSource] = useState<string>("All");
  const [sortBy, setSortBy] = useState<string>("recommended");

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Fetch events from FastAPI backend with query params and optional token for personalization
  useEffect(() => {
    async function fetchEvents() {
      setLoading(true);
      try {
        const params = new URLSearchParams();
        if (sortBy) params.append("sort_by", sortBy);
        
        const headers: Record<string, string> = {};
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }

        const url = `${apiUrl}/events?${params.toString()}`;
        const response = await fetch(url, { headers });

        if (!response.ok) {
          throw new Error("Failed to fetch events");
        }

        const data = await response.json();
        setEvents(data);
        setError(null);
      } catch (err) {
        console.error("Error fetching events:", err);
        setError("Unable to load events. Make sure the EventScout API is running.");
      } finally {
        setLoading(false);
      }
    }

    fetchEvents();
  }, [apiUrl, sortBy, token]);

  // Handle Save / Unsave toggle
  const handleToggleSave = useCallback(
    async (eventId: string, currentlySaved: boolean) => {
      if (!token) return;

      const method = currentlySaved ? "DELETE" : "POST";
      const endpoint = `${apiUrl}/events/${eventId}/save`;

      // Optimistic update
      setSavedIds((prev) => {
        const next = new Set(prev);
        if (currentlySaved) {
          next.delete(eventId);
        } else {
          next.add(eventId);
        }
        return next;
      });

      try {
        const res = await fetch(endpoint, {
          method,
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (!res.ok) {
          throw new Error(`Failed to ${currentlySaved ? "unsave" : "save"} event`);
        }

        refreshUser();
      } catch (err) {
        console.error("Error toggling save:", err);
        setSavedIds((prev) => {
          const reverted = new Set(prev);
          if (currentlySaved) {
            reverted.add(eventId);
          } else {
            reverted.delete(eventId);
          }
          return reverted;
        });
        throw err;
      }
    },
    [apiUrl, token, refreshUser]
  );

  // Compute total counts per primary tab
  const sectionCounts = useMemo(() => {
    let hackathons = 0;
    let workshops = 0;
    events.forEach((ev) => {
      if (isHackathon(ev)) hackathons++;
      else if (isWorkshop(ev)) workshops++;
    });
    return {
      all: events.length,
      hackathons,
      workshops,
    };
  }, [events]);

  // Compute available categories and sources
  const availableCategories = useMemo(() => {
    const cats = new Set<string>();
    events.forEach((event) => {
      event.categories?.forEach((c) => cats.add(c));
    });
    return ["All", ...Array.from(cats).sort()];
  }, [events]);

  const availableSources = useMemo(() => {
    const sources = new Set<string>();
    events.forEach((event) => {
      if (event.source) sources.add(event.source);
    });
    return ["All", ...Array.from(sources).sort()];
  }, [events]);

  // Multi-Filter combination logic
  const filteredEvents = useMemo(() => {
    return events.filter((event) => {
      // 1. Primary Section Tab Filter
      if (activeSection === "hackathons" && !isHackathon(event)) return false;
      if (activeSection === "workshops" && !isWorkshop(event)) return false;

      // 2. Category Filter
      if (selectedCategory !== "All") {
        const hasCat = event.categories && event.categories.some(c => c.toLowerCase() === selectedCategory.toLowerCase());
        if (!hasCat) return false;
      }

      // 3. Mode Filter (Online vs In-Person)
      if (selectedMode !== "All") {
        const modeText = (event.mode_location || "").toLowerCase();
        if (selectedMode === "Online" && !modeText.includes("online")) return false;
        if (selectedMode === "In-Person" && modeText.includes("online")) return false;
      }

      // 4. Price Filter
      if (selectedPrice === "Free" && !event.is_free) return false;
      if (selectedPrice === "Paid" && event.is_free) return false;

      // 5. Source Platform Filter
      if (selectedSource !== "All") {
        if (event.source?.toLowerCase() !== selectedSource.toLowerCase()) return false;
      }

      // 6. Text Search (title, organizer, description, skills, categories, source)
      const query = searchQuery.toLowerCase().trim();
      if (!query) return true;

      const titleMatch = event.title?.toLowerCase().includes(query) || false;
      const orgMatch = event.organizer?.toLowerCase().includes(query) || false;
      const descMatch = event.description?.toLowerCase().includes(query) || false;
      const sourceMatch = event.source?.toLowerCase().includes(query) || false;
      const catMatch = event.categories?.some(c => c.toLowerCase().includes(query)) || false;

      return titleMatch || orgMatch || descMatch || sourceMatch || catMatch;
    });
  }, [events, activeSection, selectedCategory, selectedMode, selectedPrice, selectedSource, searchQuery]);

  // Top Picks: Highest ranked opportunities
  const topPicks = useMemo(() => {
    return filteredEvents
      .filter((ev) => (ev.ranking_score && ev.ranking_score >= 0.81) || ev.host_tier === "TIER_1_COMPANY" || ev.host_tier === "TOP_UNIVERSITY")
      .slice(0, 3);
  }, [filteredEvents]);

  // Closing Soon: Events happening or registration closing within 4 days
  const closingSoon = useMemo(() => {
    const now = new Date();
    return filteredEvents
      .filter((ev) => {
        try {
          const dt = new Date(ev.date_time);
          const diffDays = (dt.getTime() - now.getTime()) / (1000 * 3600 * 24);
          return diffDays >= 0 && diffDays <= 4;
        } catch {
          return false;
        }
      })
      .slice(0, 3);
  }, [filteredEvents]);

  const hasActiveFilters = searchQuery !== "" || 
                           selectedCategory !== "All" || 
                           selectedMode !== "All" || 
                           selectedPrice !== "All" || 
                           selectedSource !== "All" ||
                           sortBy !== "recommended";

  const clearFilters = () => {
    setSearchQuery("");
    setSelectedCategory("All");
    setSelectedMode("All");
    setSelectedPrice("All");
    setSelectedSource("All");
    setSortBy("recommended");
    setActiveSection("all");
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Hero Header */}
      <div className="mb-10">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-4">
          <div>
            <h1 className="text-4xl md:text-5xl font-extrabold text-gray-900 dark:text-white tracking-tight mb-3">
              Discover what's happening in tech.
            </h1>
            <p className="text-lg text-gray-600 dark:text-gray-300 max-w-2xl">
              Intelligently ranked technical hackathons, workshops, and conferences from premier tech leaders and institutes.
            </p>
          </div>

          {!loading && !error && (
            <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 font-semibold text-sm border border-indigo-200 dark:border-indigo-800 self-start md:self-auto shadow-sm">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-indigo-500"></span>
              </span>
              <span>{filteredEvents.length} opportunities available</span>
            </div>
          )}
        </div>
      </div>

      {/* Primary Section Tabs */}
      <div className="mb-6 border-b border-gray-200 dark:border-gray-800">
        <div className="flex items-center gap-2 sm:gap-3 overflow-x-auto pb-px">
          {/* Tab 1: All Events */}
          <button
            id="tab-all-events"
            type="button"
            onClick={() => setActiveSection("all")}
            className={`flex items-center gap-2 px-5 py-3 text-sm sm:text-base font-bold rounded-t-xl transition-all border-b-2 whitespace-nowrap ${
              activeSection === "all"
                ? "text-indigo-600 dark:text-indigo-400 border-indigo-600 dark:border-indigo-400 bg-indigo-50/60 dark:bg-indigo-950/30"
                : "text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white border-transparent hover:border-gray-300 dark:hover:border-gray-700"
            }`}
          >
            <span>✨</span>
            <span>All Events</span>
            <span
              className={`px-2 py-0.5 text-xs rounded-full font-semibold transition-colors ${
                activeSection === "all"
                  ? "bg-indigo-600 text-white"
                  : "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300"
              }`}
            >
              {sectionCounts.all}
            </span>
          </button>

          {/* Tab 2: Hackathons */}
          <button
            id="tab-hackathons"
            type="button"
            onClick={() => setActiveSection("hackathons")}
            className={`flex items-center gap-2 px-5 py-3 text-sm sm:text-base font-bold rounded-t-xl transition-all border-b-2 whitespace-nowrap ${
              activeSection === "hackathons"
                ? "text-indigo-600 dark:text-indigo-400 border-indigo-600 dark:border-indigo-400 bg-indigo-50/60 dark:bg-indigo-950/30"
                : "text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white border-transparent hover:border-gray-300 dark:hover:border-gray-700"
            }`}
          >
            <span>⚡</span>
            <span>Hackathons</span>
            <span
              className={`px-2 py-0.5 text-xs rounded-full font-semibold transition-colors ${
                activeSection === "hackathons"
                  ? "bg-amber-600 text-white"
                  : "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300"
              }`}
            >
              {sectionCounts.hackathons}
            </span>
          </button>

          {/* Tab 3: Workshops */}
          <button
            id="tab-workshops"
            type="button"
            onClick={() => setActiveSection("workshops")}
            className={`flex items-center gap-2 px-5 py-3 text-sm sm:text-base font-bold rounded-t-xl transition-all border-b-2 whitespace-nowrap ${
              activeSection === "workshops"
                ? "text-indigo-600 dark:text-indigo-400 border-indigo-600 dark:border-indigo-400 bg-indigo-50/60 dark:bg-indigo-950/30"
                : "text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white border-transparent hover:border-gray-300 dark:hover:border-gray-700"
            }`}
          >
            <span>🛠️</span>
            <span>Workshops</span>
            <span
              className={`px-2 py-0.5 text-xs rounded-full font-semibold transition-colors ${
                activeSection === "workshops"
                  ? "bg-emerald-600 text-white"
                  : "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300"
              }`}
            >
              {sectionCounts.workshops}
            </span>
          </button>
        </div>
      </div>

      {/* Advanced Search & Filter Bar */}
      <div className="bg-white dark:bg-gray-800/80 backdrop-blur-md rounded-2xl p-4 sm:p-5 border border-gray-200 dark:border-gray-700 shadow-sm mb-10">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3 mb-3">
          {/* Search Input */}
          <div className="md:col-span-6 relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-gray-400">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <input
              type="text"
              id="search-input"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by title, company, university, skill (e.g. AI, Python, AWS)..."
              className="w-full pl-10 pr-4 py-2.5 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white placeholder-gray-500 focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
              >
                ✕
              </button>
            )}
          </div>

          {/* Sort By Dropdown */}
          <div className="md:col-span-3">
            <select
              id="sort-select"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="w-full py-2.5 px-3 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-xl text-sm font-medium text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="recommended">🌟 Recommended (Intelligent)</option>
              <option value="soonest">📅 Soonest Event</option>
              <option value="deadline">⏳ Registration Deadline</option>
              <option value="newest">🆕 Newly Discovered</option>
            </select>
          </div>

          {/* Mode Dropdown */}
          <div className="md:col-span-3">
            <select
              id="mode-select"
              value={selectedMode}
              onChange={(e) => setSelectedMode(e.target.value)}
              className="w-full py-2.5 px-3 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-xl text-sm font-medium text-gray-900 dark:text-white outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="All">🌐 All Modes</option>
              <option value="Online">💻 Online Only</option>
              <option value="In-Person">🏢 In-Person / Campus</option>
            </select>
          </div>
        </div>

        {/* Secondary Filter Row: Price, Source, Category & Reset */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-gray-100 dark:border-gray-700/60">
          <div className="flex flex-wrap items-center gap-2 text-xs">
            {/* Price Pill Buttons */}
            <div className="flex rounded-lg bg-gray-100 dark:bg-gray-900 p-0.5 border border-gray-200 dark:border-gray-700">
              {["All", "Free", "Paid"].map((p) => (
                <button
                  key={p}
                  onClick={() => setSelectedPrice(p)}
                  className={`px-3 py-1 rounded-md font-medium transition-colors ${
                    selectedPrice === p
                      ? "bg-white dark:bg-gray-800 text-indigo-600 dark:text-indigo-400 shadow-sm"
                      : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
                  }`}
                >
                  {p === "All" ? "All Prices" : p}
                </button>
              ))}
            </div>

            {/* Source Filter Select */}
            <select
              value={selectedSource}
              onChange={(e) => setSelectedSource(e.target.value)}
              className="py-1 px-2.5 bg-gray-100 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg text-xs text-gray-700 dark:text-gray-300 outline-none capitalize"
            >
              <option value="All">All Sources</option>
              {availableSources.filter(s => s !== "All").map((src) => (
                <option key={src} value={src}>{src}</option>
              ))}
            </select>

            {/* Category Select */}
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="py-1 px-2.5 bg-gray-100 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg text-xs text-gray-700 dark:text-gray-300 outline-none"
            >
              <option value="All">All Categories</option>
              {availableCategories.filter(c => c !== "All").slice(0, 15).map((cat) => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
          </div>

          {/* Clear Filters Button */}
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="text-xs font-semibold text-rose-600 dark:text-rose-400 hover:underline flex items-center gap-1"
            >
              <span>✕</span>
              <span>Reset Filters</span>
            </button>
          )}
        </div>
      </div>

      {/* Loading Skeleton State */}
      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="flex flex-col bg-white dark:bg-gray-800 rounded-xl overflow-hidden border border-gray-200 dark:border-gray-700 animate-pulse h-96">
              <div className="h-48 bg-gray-200 dark:bg-gray-700" />
              <div className="p-5 flex-grow flex flex-col gap-3">
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4" />
                <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
                <div className="mt-auto h-10 bg-gray-200 dark:bg-gray-700 rounded" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-6 text-center text-red-700 dark:text-red-400">
          <p className="font-semibold mb-2">Error</p>
          <p>{error}</p>
        </div>
      )}

      {/* Non-Loading Results Sections */}
      {!loading && !error && (
        <>
          {/* Section 1: Top Picks & Highlights (Shown if no narrow text search) */}
          {topPicks.length > 0 && !searchQuery && (
            <div className="mb-12">
              <div className="flex items-center justify-between mb-5">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                    <span>🌟</span>
                    <span>Top Picks & High-Value Opportunities</span>
                  </h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    Selected by EventScout ranking engine from tier 1 tech companies and premier universities.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {topPicks.map((event) => (
                  <EventCard
                    key={event.id || event.title}
                    event={event}
                    isSaved={event.id ? savedIds.has(event.id) : false}
                    onToggleSave={isAuthenticated ? handleToggleSave : undefined}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Section 2: Closing Soon (Urgent Opportunities) */}
          {closingSoon.length > 0 && !searchQuery && activeSection === "all" && (
            <div className="mb-12">
              <div className="flex items-center justify-between mb-5">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                    <span>⏳</span>
                    <span>Closing Soon / Happening This Week</span>
                  </h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    Upcoming deadlines within the next 4 days.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {closingSoon.map((event) => (
                  <EventCard
                    key={`urgent-${event.id || event.title}`}
                    event={event}
                    isSaved={event.id ? savedIds.has(event.id) : false}
                    onToggleSave={isAuthenticated ? handleToggleSave : undefined}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Section 3: All Filtered Events */}
          <div>
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <span>📚</span>
                <span>All Opportunities</span>
                <span className="text-sm font-medium text-gray-500 dark:text-gray-400">
                  ({filteredEvents.length})
                </span>
              </h2>
            </div>

            {filteredEvents.length === 0 ? (
              <div className="text-center py-16 bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700">
                <span className="text-4xl block mb-3">🔍</span>
                <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-1">
                  No matching opportunities found
                </h3>
                <p className="text-gray-500 dark:text-gray-400 text-sm max-w-md mx-auto mb-5">
                  Try adjusting your search terms, switching event modes, or resetting your filters.
                </p>
                <button
                  onClick={clearFilters}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-semibold transition-colors"
                >
                  Reset All Filters
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredEvents.map((event) => (
                  <EventCard
                    key={event.id || event.title}
                    event={event}
                    isSaved={event.id ? savedIds.has(event.id) : false}
                    onToggleSave={isAuthenticated ? handleToggleSave : undefined}
                  />
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
