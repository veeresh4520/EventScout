import { Event } from "@/types/event";

export type EventSectionType = "all" | "hackathons" | "workshops";

export type EventClassification = "hackathon" | "workshop" | "meetup";

const HACKATHON_PLATFORMS = new Set(["devpost", "devfolio", "mlh", "unstop"]);

const HACKATHON_REGEX =
  /\b(hackathon|hackathons|hack|hacks|buildathon|codeathon|datathon|game\s*jam|ideathon|challenge|bounty)\b/i;

const WORKSHOP_REGEX =
  /\b(workshop|workshops|bootcamp|bootcamps|masterclass|masterclasses|hands-on|hands on|training|tutorial|tutorials|webinar|webinars|deep dive|lab|labs|coding camp|study jam|tech talk|lecture|course)\b/i;

/**
 * Checks if an event is classified as a hackathon.
 */
export function isHackathon(event: Event): boolean {
  const src = (event.source || "").toLowerCase().trim();
  if (HACKATHON_PLATFORMS.has(src)) return true;

  const title = (event.title || "").toLowerCase();
  const desc = (event.description || "").toLowerCase();
  const cats = (event.categories || []).map((c) => c.toLowerCase()).join(" ");

  return (
    HACKATHON_REGEX.test(title) ||
    HACKATHON_REGEX.test(cats) ||
    HACKATHON_REGEX.test(desc)
  );
}

/**
 * Checks if an event is classified as a workshop / masterclass / webinar.
 */
export function isWorkshop(event: Event): boolean {
  if (isHackathon(event)) return false;

  const title = (event.title || "").toLowerCase();
  const desc = (event.description || "").toLowerCase();
  const cats = (event.categories || []).map((c) => c.toLowerCase()).join(" ");

  return (
    WORKSHOP_REGEX.test(title) ||
    WORKSHOP_REGEX.test(cats) ||
    WORKSHOP_REGEX.test(desc)
  );
}

/**
 * Returns the primary classification for display badges.
 */
export function getEventClassification(event: Event): EventClassification {
  if (isHackathon(event)) return "hackathon";
  if (isWorkshop(event)) return "workshop";
  return "meetup";
}
