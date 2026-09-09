"use client";

import { useEffect, useState, useMemo } from "react";
import { Event } from "@/types/event";
import EventCard from "@/components/EventCard";

export default function DiscoverPage() {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Search & Filter State
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("All");

  // Fetch events from FastAPI backend
  useEffect(() => {
    async function fetchEvents() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const response = await fetch(`${apiUrl}/events`);
        
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
  }, []);

  // Compute unique categories from available events
  const availableCategories = useMemo(() => {
    const cats = new Set<string>();
    events.forEach(event => {
      event.categories?.forEach(c => cats.add(c));
    });
    return ["All", ...Array.from(cats).sort()];
  }, [events]);

  // Filter and search logic
  const filteredEvents = useMemo(() => {
    return events.filter(event => {
      // 1. Category Filter
      const matchesCategory = selectedCategory === "All" || (event.categories && event.categories.includes(selectedCategory));
      if (!matchesCategory) return false;

      // 2. Text Search (title, organizer, description)
      const query = searchQuery.toLowerCase().trim();
      if (!query) return true;

      const titleMatch = event.title?.toLowerCase().includes(query) || false;
      const orgMatch = event.organizer?.toLowerCase().includes(query) || false;
      const descMatch = event.description?.toLowerCase().includes(query) || false;

      return titleMatch || orgMatch || descMatch;
    });
  }, [events, searchQuery, selectedCategory]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      
      {/* Hero Section */}
      <div className="mb-12">
        <h1 className="text-4xl md:text-5xl font-extrabold text-gray-900 dark:text-white tracking-tight mb-4">
          Discover what's happening in tech.
        </h1>
        <p className="text-xl text-gray-600 dark:text-gray-300 max-w-3xl mb-6">
          EventScout collects technical events, hackathons, and workshops from top sources so you never miss an opportunity to learn and connect.
        </p>
        
        {!loading && !error && (
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-100 text-indigo-800 dark:bg-indigo-900/50 dark:text-indigo-300 font-medium text-sm border border-indigo-200 dark:border-indigo-800">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
            </span>
            {filteredEvents.length} events found
          </div>
        )}
      </div>

      {/* Search and Filters */}
      <div className="mb-10 space-y-6">
        {/* Search Bar */}
        <div className="relative max-w-2xl">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <input
            type="text"
            className="block w-full pl-10 pr-3 py-3 border border-gray-300 dark:border-gray-700 rounded-xl leading-5 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors shadow-sm"
            placeholder="Search events by title, organizer, or keywords..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        {/* Category Filter Chips */}
        {availableCategories.length > 1 && (
          <div className="flex flex-wrap gap-2">
            {availableCategories.map(category => (
              <button
                key={category}
                onClick={() => setSelectedCategory(category)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  selectedCategory === category
                    ? "bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900 shadow-md"
                    : "bg-white text-gray-700 border border-gray-200 hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-700 dark:hover:bg-gray-700"
                }`}
              >
                {category}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Content States */}
      {loading ? (
        <div>
          <div className="flex items-center gap-2 mb-6 text-indigo-600 dark:text-indigo-400 font-medium">
            <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>Loading events...</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="bg-white dark:bg-gray-800 rounded-xl h-[420px] shadow-sm border border-gray-100 dark:border-gray-700 animate-pulse flex flex-col">
                <div className="h-48 bg-gray-200 dark:bg-gray-700 rounded-t-xl w-full"></div>
                <div className="p-5 flex-grow flex flex-col gap-4">
                  <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/3"></div>
                  <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-full"></div>
                  <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-5/6"></div>
                  <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mt-auto"></div>
                  <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded w-full mt-2"></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : error ? (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center max-w-2xl mx-auto mt-12">
          <svg className="w-12 h-12 text-red-500 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <h3 className="text-lg font-bold text-red-800 dark:text-red-400 mb-2">Unable to load events.</h3>
          <p className="text-red-600 dark:text-red-300">{error}</p>
          <p className="text-red-600 dark:text-red-300 mt-4 text-sm font-medium">Make sure to start the backend with: <code className="bg-red-100 dark:bg-red-900/40 px-2 py-1 rounded">uvicorn api.main:app --reload</code></p>
        </div>
      ) : filteredEvents.length === 0 ? (
        <div className="bg-gray-50 dark:bg-gray-800/50 border border-dashed border-gray-300 dark:border-gray-700 rounded-xl p-16 text-center mt-8">
          <svg className="w-16 h-16 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z M10 14v-4m-2 2h4" />
          </svg>
          <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">No upcoming events found.</h3>
          <p className="text-gray-500 dark:text-gray-400 max-w-md mx-auto">
            We couldn't find any events matching your current search or filter criteria. Try adjusting your search term or selecting "All" categories.
          </p>
          {(searchQuery || selectedCategory !== "All") && (
            <button 
              onClick={() => { setSearchQuery(""); setSelectedCategory("All"); }}
              className="mt-6 px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              Clear all filters
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filteredEvents.map(event => (
            <EventCard key={event.source_event_id || event.title} event={event} />
          ))}
        </div>
      )}
    </div>
  );
}
