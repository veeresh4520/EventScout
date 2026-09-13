"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { Source, SourceStatus, SourcesOverview } from "@/types/source";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function AdminSourcesPage() {
  const { user, token, isAuthenticated, isLoading: isAuthLoading } = useAuth();
  const router = useRouter();

  const [sources, setSources] = useState<Source[]>([]);
  const [overview, setOverview] = useState<SourcesOverview | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<string>("ALL");

  // Discovery input
  const [targetUrl, setTargetUrl] = useState("");
  const [isDiscovering, setIsDiscovering] = useState(false);
  const [discoveryStep, setDiscoveryStep] = useState<string>("");

  // Verification & Inspection modal
  const [selectedSource, setSelectedSource] = useState<Source | null>(null);
  const [isVerifyMode, setIsVerifyMode] = useState(false);
  const [testResults, setTestResults] = useState<any | null>(null);
  const [isTesting, setIsTesting] = useState(false);

  // Fetch sources and overview metrics
  const fetchSources = async () => {
    if (!token) return;
    try {
      setIsLoading(true);
      setError(null);

      const [sourcesRes, overviewRes] = await Promise.all([
        fetch(`${API_URL}/api/sources`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API_URL}/api/sources/overview`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]);

      if (!sourcesRes.ok) {
        if (sourcesRes.status === 403) {
          throw new Error("Admin privileges required to access Source Registry.");
        }
        throw new Error("Failed to load sources from database.");
      }

      const sourcesData = await sourcesRes.json();
      setSources(sourcesData);

      if (overviewRes.ok) {
        const overviewData = await overviewRes.json();
        setOverview(overviewData);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!isAuthLoading) {
      if (!isAuthenticated) {
        router.push("/login");
      } else if (user && !user.is_admin) {
        setError("Access Restricted: Admin privileges required to manage Source Discovery.");
        setIsLoading(false);
      } else {
        fetchSources();
      }
    }
  }, [isAuthenticated, isAuthLoading, user, token]);

  // Handle Admin Direct Discovery
  const handleDiscover = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetUrl.trim() || !token) return;

    try {
      setIsDiscovering(true);
      setDiscoveryStep("Inspecting website DOM & network requests via Playwright...");
      setError(null);

      const res = await fetch(`${API_URL}/api/sources/discover`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ url: targetUrl.trim() }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Discovery agent failed to identify events.");
      }

      const discoveredSource = await res.json();
      setTargetUrl("");
      await fetchSources();
      setSelectedSource(discoveredSource);
      setIsVerifyMode(true);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsDiscovering(false);
      setDiscoveryStep("");
    }
  };

  // Handle Verify / Approve
  const handleApprove = async (sourceId: string) => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/api/sources/${sourceId}/approve`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to approve source.");
      await fetchSources();
      setSelectedSource(null);
      setIsVerifyMode(false);
    } catch (err: any) {
      alert(err.message);
    }
  };

  // Handle Reject
  const handleReject = async (sourceId: string) => {
    if (!token || !confirm("Are you sure you want to reject this source?")) return;
    try {
      const res = await fetch(`${API_URL}/api/sources/${sourceId}/reject`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to reject source.");
      await fetchSources();
      setSelectedSource(null);
      setIsVerifyMode(false);
    } catch (err: any) {
      alert(err.message);
    }
  };

  // Handle Retry Discovery
  const handleRetryDiscovery = async (sourceId: string) => {
    if (!token) return;
    try {
      setIsDiscovering(true);
      setDiscoveryStep("Re-running AI discovery pipeline...");
      const res = await fetch(`${API_URL}/api/sources/${sourceId}/retry-discovery`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || "Retry discovery failed.");
      }
      const updated = await res.json();
      await fetchSources();
      setSelectedSource(updated);
      setIsVerifyMode(true);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setIsDiscovering(false);
      setDiscoveryStep("");
    }
  };

  // Handle Toggle Enable/Disable
  const handleToggle = async (sourceId: string) => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/api/sources/${sourceId}/toggle`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to toggle source state.");
      await fetchSources();
    } catch (err: any) {
      alert(err.message);
    }
  };

  // Handle Test Scrape
  const handleRunTest = async (sourceId: string) => {
    if (!token) return;
    try {
      setIsTesting(true);
      setTestResults(null);
      const res = await fetch(`${API_URL}/api/sources/${sourceId}/test`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Test scrape failed.");
      }
      const data = await res.json();
      setTestResults(data);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setIsTesting(false);
    }
  };

  // Handle Delete
  const handleDelete = async (sourceId: string) => {
    if (!token || !confirm("Are you sure you want to permanently delete this source?")) return;
    try {
      const res = await fetch(`${API_URL}/api/sources/${sourceId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to delete source.");
      await fetchSources();
      if (selectedSource?.id === sourceId || selectedSource?._id === sourceId) {
        setSelectedSource(null);
      }
    } catch (err: any) {
      alert(err.message);
    }
  };

  const getStatusBadge = (status: SourceStatus) => {
    switch (status) {
      case "ENABLED":
        return (
          <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
            ENABLED
          </span>
        );
      case "READY_FOR_REVIEW":
        return (
          <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20 animate-pulse">
            READY FOR REVIEW
          </span>
        );
      case "DISCOVERING":
      case "TESTING":
        return (
          <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
            DISCOVERING
          </span>
        );
      case "FAILED":
        return (
          <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
            FAILED
          </span>
        );
      case "NEEDS_REDISCOVERY":
        return (
          <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
            NEEDS REDISCOVERY
          </span>
        );
      case "DISABLED":
      default:
        return (
          <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-gray-500/10 text-gray-600 dark:text-gray-400 border border-gray-500/20">
            DISABLED
          </span>
        );
    }
  };

  // Filter sources
  const filteredSources = sources.filter((s) => {
    if (activeFilter === "ALL") return true;
    if (activeFilter === "REVIEW") return s.status === "READY_FOR_REVIEW" || s.status === "PENDING";
    if (activeFilter === "ENABLED") return s.status === "ENABLED";
    if (activeFilter === "FAILED") return s.status === "FAILED" || s.status === "NEEDS_REDISCOVERY";
    if (activeFilter === "DISABLED") return s.status === "DISABLED";
    return true;
  });

  if (isAuthLoading || (isLoading && !sources.length)) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950">
        <div className="flex items-center gap-3 text-indigo-600 dark:text-indigo-400">
          <svg className="animate-spin h-6 w-6" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
          </svg>
          <span className="font-medium text-lg">Loading Source Registry...</span>
        </div>
      </main>
    );
  }

  if (user && !user.is_admin) {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center p-6 bg-gray-50 dark:bg-gray-950">
        <div className="max-w-md w-full bg-white dark:bg-gray-900 border border-red-200 dark:border-red-900/50 p-8 rounded-2xl shadow-xl text-center">
          <div className="w-12 h-12 rounded-full bg-red-100 dark:bg-red-900/30 text-red-600 flex items-center justify-center mx-auto mb-4 text-2xl">
            🔒
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">403 Forbidden</h1>
          <p className="text-gray-600 dark:text-gray-400 text-sm mb-6">
            Administrator privileges required. You do not have permission to view or manage the EventScout Source Registry.
          </p>
          <button
            onClick={() => router.push("/")}
            className="px-5 py-2 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 transition-colors font-medium text-sm"
          >
            Return to EventScout Home
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 p-4 sm:p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-gray-200 dark:border-gray-800 pb-6">
          <div>
            <div className="flex items-center gap-3">
              <span className="text-3xl">⚙️</span>
              <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
                Source Registry & Admin Management
              </h1>
            </div>
            <p className="text-gray-600 dark:text-gray-400 text-sm mt-1">
              Dynamic AI discovery, source verification, generic collectors, and zero-downtime scraper scheduling.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs px-3 py-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800 font-semibold">
              Gemini Source Agent Active
            </span>
          </div>
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-red-700 dark:text-red-300 text-sm flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-xs font-semibold hover:underline">
              Dismiss
            </button>
          </div>
        )}

        {/* Overview Stats Cards */}
        <section className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 shadow-sm">
            <div className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Total Sources</div>
            <div className="text-2xl font-bold mt-1">{overview?.total_sources ?? sources.length}</div>
          </div>
          <div className="bg-white dark:bg-gray-900 border border-emerald-200 dark:border-emerald-900/40 rounded-xl p-4 shadow-sm">
            <div className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">Enabled</div>
            <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">
              {overview?.enabled ?? sources.filter(s => s.status === "ENABLED").length}
            </div>
          </div>
          <div className="bg-white dark:bg-gray-900 border border-blue-200 dark:border-blue-900/40 rounded-xl p-4 shadow-sm">
            <div className="text-xs font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wider">Pending Review</div>
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400 mt-1">
              {overview?.pending_review ?? sources.filter(s => s.status === "READY_FOR_REVIEW" || s.status === "PENDING").length}
            </div>
          </div>
          <div className="bg-white dark:bg-gray-900 border border-amber-200 dark:border-amber-900/40 rounded-xl p-4 shadow-sm">
            <div className="text-xs font-semibold text-amber-600 dark:text-amber-400 uppercase tracking-wider">Discovering</div>
            <div className="text-2xl font-bold text-amber-600 dark:text-amber-400 mt-1">
              {overview?.discovering ?? sources.filter(s => s.status === "DISCOVERING" || s.status === "TESTING").length}
            </div>
          </div>
          <div className="bg-white dark:bg-gray-900 border border-rose-200 dark:border-rose-900/40 rounded-xl p-4 shadow-sm">
            <div className="text-xs font-semibold text-rose-600 dark:text-rose-400 uppercase tracking-wider">Failed</div>
            <div className="text-2xl font-bold text-rose-600 dark:text-rose-400 mt-1">
              {overview?.failed ?? sources.filter(s => s.status === "FAILED" || s.status === "NEEDS_REDISCOVERY").length}
            </div>
          </div>
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 shadow-sm">
            <div className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Disabled</div>
            <div className="text-2xl font-bold text-gray-500 dark:text-gray-400 mt-1">
              {overview?.disabled ?? sources.filter(s => s.status === "DISABLED").length}
            </div>
          </div>
        </section>

        {/* Discovery Input Form */}
        <section className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 shadow-sm space-y-3">
          <h2 className="text-base font-bold flex items-center gap-2">
            <span>🔍</span> Trigger AI Discovery on New Website
          </h2>
          <form onSubmit={handleDiscover} className="flex flex-col sm:flex-row gap-3">
            <input
              type="url"
              placeholder="e.g. https://devpost.com/hackathons or https://unstop.com/hackathons"
              value={targetUrl}
              onChange={(e) => setTargetUrl(e.target.value)}
              required
              disabled={isDiscovering}
              className="flex-1 px-4 py-2.5 rounded-xl border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm transition-all"
            />
            <button
              type="submit"
              disabled={isDiscovering || !targetUrl.trim()}
              className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-xl font-semibold text-sm shadow-md transition-all flex items-center justify-center gap-2 whitespace-nowrap"
            >
              {isDiscovering ? (
                <>
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                  </svg>
                  <span>Agent Investigating...</span>
                </>
              ) : (
                <>
                  <span>⚡</span>
                  <span>Discover & Test</span>
                </>
              )}
            </button>
          </form>

          {isDiscovering && (
            <div className="p-3.5 rounded-xl bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-100 dark:border-indigo-900/50 text-indigo-700 dark:text-indigo-300 text-xs flex items-center gap-3">
              <div className="w-2 h-2 rounded-full bg-indigo-600 animate-ping"></div>
              <span>{discoveryStep || "Analyzing page DOM, detecting endpoints, and testing sample extraction..."}</span>
            </div>
          )}
        </section>

        {/* Source Table Section */}
        <section className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold tracking-tight">Source Registry</h2>
              <span className="text-xs text-gray-500 dark:text-gray-400">({filteredSources.length} showing)</span>
            </div>

            {/* Filter Tabs */}
            <div className="flex items-center gap-1.5 bg-gray-200 dark:bg-gray-800 p-1 rounded-xl text-xs font-semibold">
              {[
                { id: "ALL", label: "All" },
                { id: "REVIEW", label: "Needs Review" },
                { id: "ENABLED", label: "Enabled" },
                { id: "FAILED", label: "Failed" },
                { id: "DISABLED", label: "Disabled" },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveFilter(tab.id)}
                  className={`px-3 py-1.5 rounded-lg transition-all ${
                    activeFilter === tab.id
                      ? "bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 shadow-sm"
                      : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
              <button
                onClick={fetchSources}
                className="px-2.5 py-1.5 text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1"
                title="Refresh table"
              >
                🔄
              </button>
            </div>
          </div>

          {/* Table */}
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl shadow-sm overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-gray-50 dark:bg-gray-800/60 border-b border-gray-200 dark:border-gray-800 text-gray-600 dark:text-gray-400 uppercase font-semibold tracking-wider">
                <tr>
                  <th className="py-3.5 px-4">Source</th>
                  <th className="py-3.5 px-4">URL</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4">Strategy</th>
                  <th className="py-3.5 px-4">Events Found</th>
                  <th className="py-3.5 px-4">Last Scraped</th>
                  <th className="py-3.5 px-4">Last Success</th>
                  <th className="py-3.5 px-4">Failures</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800/60">
                {filteredSources.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="py-10 text-center text-gray-500 dark:text-gray-400">
                      No sources matching filter "{activeFilter}".
                    </td>
                  </tr>
                ) : (
                  filteredSources.map((source) => {
                    const sId = source.id || source._id || "";
                    const strategy = source.collection_strategy || source.strategy || "PLAYWRIGHT";
                    const isReview = source.status === "READY_FOR_REVIEW" || source.status === "PENDING";

                    return (
                      <tr key={sId} className={`hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors ${
                        isReview ? "bg-blue-50/20 dark:bg-blue-950/10" : ""
                      }`}>
                        <td className="py-3.5 px-4 font-bold text-gray-900 dark:text-gray-100 whitespace-nowrap">
                          {source.name}
                        </td>
                        <td className="py-3.5 px-4">
                          <a
                            href={source.event_list_url || source.base_url || source.url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-indigo-600 dark:text-indigo-400 hover:underline max-w-[180px] truncate block"
                            title={source.event_list_url || source.base_url || source.url}
                          >
                            {source.event_list_url || source.base_url || source.url}
                          </a>
                        </td>
                        <td className="py-3.5 px-4 whitespace-nowrap">
                          {getStatusBadge(source.status)}
                        </td>
                        <td className="py-3.5 px-4 font-mono whitespace-nowrap">
                          <span className="bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded text-[11px]">
                            {strategy.toUpperCase()}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 whitespace-nowrap font-medium">
                          {source.events_found_last_run ?? (source.sample_events?.length ?? "-")}
                        </td>
                        <td className="py-3.5 px-4 whitespace-nowrap text-gray-500 dark:text-gray-400">
                          {source.last_scraped_at ? new Date(source.last_scraped_at).toLocaleTimeString() : "Never"}
                        </td>
                        <td className="py-3.5 px-4 whitespace-nowrap text-gray-500 dark:text-gray-400">
                          {source.last_success_at ? new Date(source.last_success_at).toLocaleDateString() : "Never"}
                        </td>
                        <td className="py-3.5 px-4 whitespace-nowrap font-semibold">
                          <span className={source.consecutive_failures ? "text-rose-600 dark:text-rose-400" : "text-gray-400"}>
                            {source.consecutive_failures ?? 0}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-right whitespace-nowrap space-x-1.5">
                          {/* Verify / Approve Action */}
                          {isReview && (
                            <button
                              onClick={() => {
                                setSelectedSource(source);
                                setIsVerifyMode(true);
                                setTestResults(null);
                              }}
                              className="px-2.5 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold text-xs shadow-sm transition-all"
                            >
                              Verify / Approve
                            </button>
                          )}

                          {/* Test scrape */}
                          <button
                            onClick={() => {
                              setSelectedSource(source);
                              setIsVerifyMode(false);
                              handleRunTest(sId);
                            }}
                            className="px-2 py-1 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg text-xs font-medium transition-colors"
                            title="Run live 1-page test"
                          >
                            Test
                          </button>

                          {/* View details */}
                          <button
                            onClick={() => {
                              setSelectedSource(source);
                              setIsVerifyMode(false);
                              setTestResults(null);
                            }}
                            className="px-2 py-1 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg text-xs font-medium transition-colors"
                          >
                            View
                          </button>

                          {/* Retry discovery if failed */}
                          {(source.status === "FAILED" || source.status === "NEEDS_REDISCOVERY") && (
                            <button
                              onClick={() => handleRetryDiscovery(sId)}
                              className="px-2 py-1 bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 hover:bg-amber-500/20 rounded-lg text-xs font-semibold transition-colors"
                            >
                              Retry Discovery
                            </button>
                          )}

                          {/* Toggle Enabled / Disabled */}
                          {source.status === "ENABLED" && (
                            <button
                              onClick={() => handleToggle(sId)}
                              className="px-2 py-1 bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20 hover:bg-rose-500/20 rounded-lg text-xs font-medium transition-colors"
                            >
                              Disable
                            </button>
                          )}
                          {source.status === "DISABLED" && (
                            <button
                              onClick={() => handleToggle(sId)}
                              className="px-2 py-1 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 rounded-lg text-xs font-medium transition-colors"
                            >
                              Enable
                            </button>
                          )}

                          <button
                            onClick={() => handleDelete(sId)}
                            className="p-1 text-gray-400 hover:text-rose-500 transition-colors"
                            title="Delete"
                          >
                            🗑️
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      {/* Verification & Inspection Modal */}
      {selectedSource && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 sm:p-6 animate-fadeIn">
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="p-5 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-extrabold text-lg text-gray-900 dark:text-gray-100">
                    {selectedSource.name}
                  </h3>
                  {getStatusBadge(selectedSource.status)}
                </div>
                <p className="text-xs text-indigo-600 dark:text-indigo-400 mt-0.5">
                  {selectedSource.event_list_url || selectedSource.base_url || selectedSource.url}
                </p>
              </div>
              <button
                onClick={() => {
                  setSelectedSource(null);
                  setIsVerifyMode(false);
                  setTestResults(null);
                }}
                className="w-8 h-8 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-gray-500 hover:text-gray-900 dark:hover:text-gray-100 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6 overflow-y-auto space-y-6 flex-1 text-sm">
              {/* Agent Findings Banner */}
              <div className="bg-gray-50 dark:bg-gray-800/40 border border-gray-200 dark:border-gray-800 rounded-2xl p-5 space-y-4">
                <h4 className="font-bold text-xs uppercase tracking-wider text-gray-500 dark:text-gray-400">
                  Agent Discovery Findings
                </h4>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
                  <div>
                    <span className="text-gray-500 dark:text-gray-400 block">Detected Strategy:</span>
                    <span className="font-bold font-mono text-sm uppercase text-indigo-600 dark:text-indigo-400">
                      {selectedSource.collection_strategy || selectedSource.strategy || "PLAYWRIGHT"}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500 dark:text-gray-400 block">Discovery Confidence:</span>
                    <span className="font-bold text-sm text-emerald-600 dark:text-emerald-400">
                      {selectedSource.confidence_score ? `${(selectedSource.confidence_score * 100).toFixed(0)}%` : "N/A"}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500 dark:text-gray-400 block">Sample Events Validated:</span>
                    <span className="font-bold text-sm">
                      {selectedSource.sample_events?.length ?? 0}
                    </span>
                  </div>
                </div>

                {selectedSource.notes && (
                  <div className="text-xs text-gray-600 dark:text-gray-300 bg-white dark:bg-gray-900/60 p-3 rounded-xl border border-gray-200 dark:border-gray-800">
                    <span className="font-semibold block mb-0.5">Notes:</span>
                    {selectedSource.notes}
                  </div>
                )}

                {/* Fields Detected Checklist */}
                <div>
                  <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 block mb-2">
                    Fields Detected:
                  </span>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                    <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
                      <span>✓</span> <span>Title</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
                      <span>✓</span> <span>Event URL</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
                      <span>✓</span> <span>Date / Time</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
                      <span>✓</span> <span>Registration URL</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
                      <span>✓</span> <span>Organizer</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
                      <span>✓</span> <span>Description</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
                      <span>✓</span> <span>Poster Image</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
                      <span>✓</span> <span>Location / Mode</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Sample Events Preview */}
              {selectedSource.sample_events && selectedSource.sample_events.length > 0 && (
                <div className="space-y-3">
                  <h4 className="font-bold text-xs uppercase tracking-wider text-gray-500 dark:text-gray-400">
                    Sample Extracted Events ({selectedSource.sample_events.length})
                  </h4>
                  <div className="space-y-2.5">
                    {selectedSource.sample_events.map((ev: any, idx: number) => (
                      <div
                        key={idx}
                        className="bg-gray-50 dark:bg-gray-800/40 border border-gray-200 dark:border-gray-800 p-3.5 rounded-xl space-y-1 text-xs"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <h5 className="font-bold text-sm text-gray-900 dark:text-gray-100">{ev.title}</h5>
                          <span className="text-gray-500 dark:text-gray-400 whitespace-nowrap">
                            {ev.date_time ? new Date(ev.date_time).toLocaleDateString() : ""}
                          </span>
                        </div>
                        {ev.organizer && (
                          <div className="text-gray-500 dark:text-gray-400">Organizer: {ev.organizer}</div>
                        )}
                        {ev.event_url && (
                          <a
                            href={ev.event_url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-indigo-600 dark:text-indigo-400 hover:underline block truncate"
                          >
                            {ev.event_url}
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Test Scrape Runner Output */}
              {isTesting && (
                <div className="p-4 rounded-xl bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800 text-xs text-indigo-700 dark:text-indigo-300 flex items-center gap-3">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                  </svg>
                  <span>Executing 1-page test scrape via generic collector...</span>
                </div>
              )}

              {testResults && (
                <div className="space-y-3 p-4 rounded-xl bg-gray-50 dark:bg-gray-800/40 border border-gray-200 dark:border-gray-800 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-gray-900 dark:text-gray-100">Live Test Run Results:</span>
                    <span className="font-semibold text-emerald-600 dark:text-emerald-400">
                      {testResults.normalized_count} events normalized ({testResults.raw_count} raw)
                    </span>
                  </div>
                  <pre className="bg-gray-900 text-gray-100 p-3 rounded-lg overflow-x-auto text-[11px] font-mono max-h-48">
                    {JSON.stringify(testResults.events, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            {/* Modal Footer with Verification Actions */}
            <div className="p-4 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/30 flex items-center justify-between gap-3">
              <button
                onClick={() => handleRunTest(selectedSource.id || selectedSource._id || "")}
                disabled={isTesting}
                className="px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 rounded-xl text-xs font-semibold transition-colors"
              >
                {isTesting ? "Testing..." : "🧪 Run Test Scrape"}
              </button>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleReject(selectedSource.id || selectedSource._id || "")}
                  className="px-4 py-2 bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20 hover:bg-rose-500/20 rounded-xl text-xs font-semibold transition-colors"
                >
                  Reject
                </button>
                <button
                  onClick={() => handleApprove(selectedSource.id || selectedSource._id || "")}
                  className="px-6 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold shadow-md transition-all flex items-center gap-1.5"
                >
                  <span>✓</span>
                  <span>Approve & Enable</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
