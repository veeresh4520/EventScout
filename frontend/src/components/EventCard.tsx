"use client";

import { useState } from "react";
import { Event } from "@/types/event";
import Image from "next/image";
import { getEventClassification } from "@/utils/eventUtils";

interface EventCardProps {
  event: Event;
  /** Whether the current user has saved this event. Undefined = not authenticated. */
  isSaved?: boolean;
  /** Called when the user clicks Save/Unsave. Undefined = not authenticated. */
  onToggleSave?: (eventId: string, currentlySaved: boolean) => Promise<void>;
}

export default function EventCard({ event, isSaved, onToggleSave }: EventCardProps) {
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [showWhyRecommended, setShowWhyRecommended] = useState(false);
  const [imageFailed, setImageFailed] = useState(false);

  const classification = getEventClassification(event);

  // Helper to detect if a scraped URL is a person's avatar/profile rather than an event poster
  const isAvatar = (url?: string | null) => {
    if (!url) return false;
    const lower = url.toLowerCase();
    return (
      lower.includes("avatar") ||
      lower.includes("/users/") ||
      lower.includes("/user/") ||
      lower.includes("profile") ||
      lower.includes("attendee") ||
      lower.includes("gravatar") ||
      lower.includes("author")
    );
  };

  const hasValidImage = Boolean(event.poster_image_url && !isAvatar(event.poster_image_url));

  const formattedDate = new Date(event.date_time).toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });

  const handleSaveClick = async () => {
    if (!onToggleSave || !event.id) return;
    setSaving(true);
    setSaveError(null);
    try {
      const willBeSaved = !isSaved;
      await onToggleSave(event.id, !!isSaved);
      if (typeof window !== "undefined") {
        window.dispatchEvent(
          new CustomEvent("eventscout-toast", {
            detail: { message: willBeSaved ? "Saved" : "Removed" },
          })
        );
      }
    } catch {
      setSaveError("Failed to update. Try again.");
      setTimeout(() => setSaveError(null), 3000);
    } finally {
      setSaving(false);
    }
  };

  const isTopPick = (event.ranking_score && event.ranking_score >= 0.81) || 
                    event.host_tier === "TIER_1_COMPANY" || 
                    event.host_tier === "TOP_UNIVERSITY";

  return (
    <div className="flex flex-col bg-white dark:bg-gray-800 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-all border border-gray-200 dark:border-gray-700 relative group">
      {/* Event Image & Badges */}
      <div className="relative h-48 w-full bg-slate-900 overflow-hidden">
        {hasValidImage && !imageFailed ? (
          <Image
            src={event.poster_image_url!}
            alt={event.title}
            fill
            unoptimized
            className="object-cover transition-transform duration-300 group-hover:scale-105"
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
            onError={() => setImageFailed(true)}
          />
        ) : (
          <div className="relative flex flex-col items-center justify-center h-full w-full bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 p-6 text-center select-none">
            {/* Subtle decorative glow effect */}
            <div className="absolute -top-12 -right-12 w-32 h-32 bg-indigo-500/20 rounded-full blur-2xl pointer-events-none" />
            <div className="absolute -bottom-12 -left-12 w-32 h-32 bg-purple-500/20 rounded-full blur-2xl pointer-events-none" />
            <div className="absolute inset-0 bg-[radial-gradient(#4f46e5_1px,transparent_1px)] [background-size:16px_16px] opacity-15 pointer-events-none" />

            <div className="relative z-10 flex flex-col items-center justify-center max-w-[85%]">
              <span className="text-[10px] uppercase font-extrabold tracking-widest text-indigo-400 mb-2 px-2 py-0.5 rounded-full bg-indigo-950/60 border border-indigo-800/50">
                {event.source ? `${event.source} • Opportunity` : "Tech Opportunity"}
              </span>
              <h4 className="text-base sm:text-lg font-black text-white line-clamp-3 leading-snug drop-shadow-md">
                {event.title}
              </h4>
            </div>
          </div>
        )}

        {/* Top Pick Highlight Tag */}
        {isTopPick && (
          <div className="absolute top-4 left-14 bg-gradient-to-r from-amber-500 to-orange-500 text-white text-[11px] font-bold px-2.5 py-1 rounded-full shadow-md flex items-center gap-1">
            <span>⭐</span>
            <span>TOP PICK</span>
          </div>
        )}

        {/* Price Badge */}
        <div className="absolute top-4 right-4 bg-white/90 dark:bg-gray-900/90 backdrop-blur-sm text-sm font-semibold px-3 py-1 rounded-full shadow-sm text-gray-900 dark:text-white">
          {event.is_free ? "Free" : `${event.price_currency || ""} ${event.price_amount || "Paid"}`}
        </div>

        {/* Source Platform & Classification Badges */}
        <div className="absolute bottom-3 left-3 flex items-center gap-1.5 flex-wrap max-w-[85%]">
          {event.source && (
            <div className="bg-gray-900/85 backdrop-blur-sm text-xs font-medium px-2.5 py-1 rounded-md shadow-sm text-white capitalize flex items-center gap-1.5 border border-white/20">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400"></span>
              <span>{event.source}</span>
            </div>
          )}

          {classification === "hackathon" && (
            <div className="bg-amber-600/90 backdrop-blur-sm text-[11px] font-semibold px-2 py-0.5 rounded-md shadow-sm text-white flex items-center gap-1 border border-amber-400/30">
              <span>⚡</span>
              <span>Hackathon</span>
            </div>
          )}

          {classification === "workshop" && (
            <div className="bg-emerald-600/90 backdrop-blur-sm text-[11px] font-semibold px-2 py-0.5 rounded-md shadow-sm text-white flex items-center gap-1 border border-emerald-400/30">
              <span>🛠️</span>
              <span>Workshop</span>
            </div>
          )}
        </div>

        {/* Save Button */}
        {onToggleSave && event.id && (
          <button
            id={`save-btn-${event.id}`}
            aria-label={isSaved ? "Unsave event" : "Save event"}
            onClick={handleSaveClick}
            disabled={saving}
            className={`absolute top-4 left-4 w-8 h-8 rounded-full flex items-center justify-center backdrop-blur-sm transition-all shadow-sm
              ${isSaved
                ? "bg-indigo-600 text-white hover:bg-indigo-700"
                : "bg-white/90 dark:bg-gray-900/90 text-gray-500 dark:text-gray-400 hover:text-indigo-600 dark:hover:text-indigo-400"
              }
              ${saving ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
            `}
          >
            {saving ? (
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : isSaved ? (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M5 4a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 20V4z" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 4a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 20V4z" />
              </svg>
            )}
          </button>
        )}
      </div>

      <div className="flex flex-col flex-grow p-5">
        {/* Date & Time */}
        <div className="text-sm font-medium text-indigo-600 dark:text-indigo-400 mb-1.5 uppercase tracking-wide">
          {formattedDate}
        </div>

        {/* Title */}
        <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2 line-clamp-2 leading-tight">
          {event.title}
        </h3>

        {/* Organizer & Host Badge */}
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <div className="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-1.5">
            <svg className="w-4 h-4 flex-shrink-0 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
            </svg>
            <span className="truncate max-w-[180px]">{event.organizer}</span>
          </div>

          {event.host_badge && (
            <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border
              ${event.host_tier === "TIER_1_COMPANY" 
                ? "bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300 border-purple-200 dark:border-purple-800" 
                : event.host_tier === "TOP_UNIVERSITY"
                ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800"
                : "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 border-blue-200 dark:border-blue-800"
              }`}
            >
              {event.host_badge}
            </span>
          )}
        </div>

        {/* Location / Mode */}
        <div className="text-sm text-gray-500 dark:text-gray-400 mb-3 flex items-center gap-1.5">
          <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.243-4.243a8 8 0 1111.314 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span className="truncate">{event.mode_location}</span>
        </div>

        {/* Categories / Tags */}
        <div className="flex flex-wrap gap-1.5 mb-3">
          {event.categories && event.categories.slice(0, 2).map((category) => (
            <span
              key={category}
              className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300 border border-indigo-100 dark:border-indigo-800/50"
            >
              {category}
            </span>
          ))}
          {event.categories && event.categories.length > 2 && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400">
              +{event.categories.length - 2} more
            </span>
          )}
        </div>

        {/* Why Recommended Toggle & Details */}
        {event.why_recommended && event.why_recommended.length > 0 && (
          <div className="mb-4">
            <button
              onClick={() => setShowWhyRecommended(!showWhyRecommended)}
              className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 flex items-center gap-1 py-1 focus:outline-none"
            >
              <span>✨</span>
              <span>Why recommended?</span>
              <svg 
                className={`w-3.5 h-3.5 transition-transform duration-200 ${showWhyRecommended ? "rotate-180" : ""}`} 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {showWhyRecommended && (
              <div className="mt-2 p-2.5 bg-slate-50 dark:bg-gray-900/80 rounded-lg border border-slate-200 dark:border-gray-700 text-xs text-slate-700 dark:text-slate-300 space-y-1.5 animate-fadeIn">
                <div className="font-semibold text-[11px] text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">
                  Recommendation Signals:
                </div>
                {event.why_recommended.map((reason, idx) => (
                  <div key={idx} className="flex items-start gap-1.5">
                    <span className="text-emerald-500 font-bold">✓</span>
                    <span>{reason}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Save error */}
        {saveError && (
          <p className="text-xs text-red-600 dark:text-red-400 mb-2">{saveError}</p>
        )}

        {/* Action Button */}
        <a
          href={event.registration_url || event.event_url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-auto flex justify-center items-center w-full px-4 py-2.5 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors focus:ring-4 focus:ring-indigo-200 dark:focus:ring-indigo-900 outline-none"
        >
          View Event
        </a>
      </div>
    </div>
  );
}
