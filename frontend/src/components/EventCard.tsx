import { Event } from "@/types/event";
import Image from "next/image";

interface EventCardProps {
  event: Event;
}

export default function EventCard({ event }: EventCardProps) {
  const formattedDate = new Date(event.date_time).toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });

  return (
    <div className="flex flex-col bg-white dark:bg-gray-800 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-shadow border border-gray-200 dark:border-gray-700">
      {/* Event Image */}
      <div className="relative h-48 w-full bg-gray-200 dark:bg-gray-700">
        {event.poster_image_url ? (
          <Image
            src={event.poster_image_url}
            alt={event.title}
            fill
            className="object-cover"
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
          />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400 dark:text-gray-500">
            <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
        )}
        
        {/* Price Badge */}
        <div className="absolute top-4 right-4 bg-white/90 dark:bg-gray-900/90 backdrop-blur-sm text-sm font-semibold px-3 py-1 rounded-full shadow-sm text-gray-900 dark:text-white">
          {event.is_free ? "Free" : `${event.price_currency || ""} ${event.price_amount || "Paid"}`}
        </div>
      </div>

      <div className="flex flex-col flex-grow p-5">
        {/* Date & Time */}
        <div className="text-sm font-medium text-indigo-600 dark:text-indigo-400 mb-2 uppercase tracking-wide">
          {formattedDate}
        </div>

        {/* Title */}
        <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2 line-clamp-2 leading-tight">
          {event.title}
        </h3>

        {/* Organizer */}
        <div className="text-sm text-gray-600 dark:text-gray-300 mb-4 flex items-center gap-1.5">
          <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
          <span className="truncate">{event.organizer}</span>
        </div>

        {/* Location / Mode */}
        <div className="text-sm text-gray-500 dark:text-gray-400 mb-4 flex items-center gap-1.5">
          <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.243-4.243a8 8 0 1111.314 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span className="truncate">{event.mode_location}</span>
        </div>

        {/* Categories / Tags */}
        <div className="flex flex-wrap gap-2 mt-auto mb-5">
          {event.categories && event.categories.slice(0, 2).map((category) => (
            <span 
              key={category} 
              className="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300 border border-indigo-100 dark:border-indigo-800/50"
            >
              {category}
            </span>
          ))}
          {event.categories && event.categories.length > 2 && (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400">
              +{event.categories.length - 2} more
            </span>
          )}
        </div>

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
