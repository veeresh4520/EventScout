"""
eventscout/services/ranking_service.py
======================================
Intelligent Event Ranking & Prioritization Service.

Decoupled from data collection/scrapers. Evaluates multiple weighted signals:
1. Organization / Host Reputation (via OrganizationRegistry)
2. Event Quality & Format (Hackathons, Workshops, Conferences, Hands-on)
3. User Personalization (Interests, Skills, Preferred Modes & Types)
4. Urgency (Registration Deadlines & Approaching Event Dates)

Generates transparent, human-readable explanations ("Why recommended?").
Ensures balanced distribution so community and individual events are discoverable.
"""

from datetime import datetime, timezone, timedelta
import logging
import math
import re
from typing import Any, Dict, List, Optional, Tuple

from eventscout.services.organization_registry import (
    HostType,
    OrganizationProfile,
    organization_registry,
    HOST_TYPE_WEIGHTS,
)

logger = logging.getLogger("EventScoutRanking")


# Weights for the composite score calculation
WEIGHT_ORGANIZATION = 0.35
WEIGHT_QUALITY = 0.25
WEIGHT_PERSONALIZATION = 0.25
WEIGHT_URGENCY = 0.15


class RankingService:
    """
    Evaluates events and produces composite scores with transparent explanations.
    """

    def __init__(self, registry=None):
        self.registry = registry or organization_registry

    def calculate_event_score(
        self,
        event: Dict[str, Any],
        user: Optional[Dict[str, Any]] = None,
        reference_time: Optional[datetime] = None,
    ) -> Tuple[float, List[str], Dict[str, float]]:
        """
        Calculate the multi-signal score for an event.
        Returns:
            (composite_score, why_recommended_list, breakdown_dict)
        """
        if reference_time is None:
            reference_time = datetime.now(timezone.utc)
        elif reference_time.tzinfo is None:
            reference_time = reference_time.replace(tzinfo=timezone.utc)

        why_recommended: List[str] = []
        breakdown: Dict[str, float] = {}

        # -------------------------------------------------------------
        # 1. Organization Reputation Signal
        # -------------------------------------------------------------
        org_name = event.get("organizer") or event.get("organization") or ""
        profile: OrganizationProfile = self.registry.classify_organization(org_name)
        org_score = profile.reputation_score

        if profile.organization_type == HostType.TIER_1_COMPANY:
            why_recommended.append(f"Hosted by premier tech leader {profile.canonical_name}")
        elif profile.organization_type == HostType.TOP_UNIVERSITY:
            why_recommended.append(f"Organized by premier institute {profile.canonical_name}")
        elif profile.organization_type == HostType.MAJOR_DEVELOPER_COMMUNITY:
            why_recommended.append(f"Organized by leading developer platform {profile.canonical_name}")
        elif profile.organization_type == HostType.TIER_2_COMPANY:
            why_recommended.append(f"Hosted by recognized tech company {profile.canonical_name}")
        elif profile.organization_type == HostType.ESTABLISHED_ORGANIZATION:
            why_recommended.append(f"Backed by established organization {profile.canonical_name}")

        breakdown["organization_score"] = round(org_score, 3)

        # -------------------------------------------------------------
        # 2. Event Quality & Format Signal
        # -------------------------------------------------------------
        title = (event.get("title") or "").lower()
        desc = (event.get("description") or "").lower()
        cats = [c.lower() for c in (event.get("categories") or [])]
        combined_text = f"{title} {desc} {' '.join(cats)}"

        quality_score = 0.50  # baseline quality

        # Event type bonuses
        if any(w in combined_text for w in ["hackathon", "buildathon", "codeathon"]):
            quality_score += 0.30
            if "Hackathon opportunity" not in why_recommended:
                why_recommended.append("High-impact hands-on hackathon")
        elif any(w in combined_text for w in ["conference", "summit", "symposium", "keynote"]):
            quality_score += 0.25
            why_recommended.append("Major technical conference / summit")
        elif any(w in combined_text for w in ["workshop", "bootcamp", "masterclass", "hands-on", "lab"]):
            quality_score += 0.20
            why_recommended.append("Interactive hands-on workshop")
        elif any(w in combined_text for w in ["open source", "gsoc", "contribution"]):
            quality_score += 0.20
            why_recommended.append("Open-source contribution opportunity")

        # Technical depth bonuses
        high_value_skills = [
            "ai", "artificial intelligence", "machine learning", "deep learning",
            "llm", "generative ai", "kubernetes", "cloud", "aws", "azure", "gcp",
            "rust", "golang", "distributed systems", "cybersecurity", "web3", "blockchain"
        ]
        matched_depth = [s for s in high_value_skills if re.search(r"\b" + re.escape(s) + r"\b", combined_text)]
        if matched_depth:
            quality_score += min(0.15, len(matched_depth) * 0.05)

        # Free tier appreciation
        is_free = event.get("is_free", True)
        if is_free:
            quality_score += 0.05
            why_recommended.append("Free registration")

        quality_score = min(1.0, quality_score)
        breakdown["quality_score"] = round(quality_score, 3)

        # -------------------------------------------------------------
        # 3. User Personalization Signal
        # -------------------------------------------------------------
        personalization_score = 0.50  # Default neutral for anonymous or non-matching users

        if user:
            user_interests = [i.lower() for i in (user.get("interests") or [])]
            user_skills = [s.lower() for s in (user.get("skills") or [])]
            user_event_types = [t.lower() for t in (user.get("preferred_event_types") or [])]
            user_modes = [m.lower() for m in (user.get("preferred_modes") or [])]

            matched_interests = []
            for interest in user_interests:
                if interest and re.search(r"\b" + re.escape(interest) + r"\b", combined_text):
                    matched_interests.append(interest)

            matched_skills = []
            for skill in user_skills:
                if skill and re.search(r"\b" + re.escape(skill) + r"\b", combined_text):
                    matched_skills.append(skill)

            total_matches = len(matched_interests) + len(matched_skills)
            if total_matches > 0:
                personalization_score = min(1.0, 0.50 + total_matches * 0.15)
                top_matched = (matched_interests + matched_skills)[:3]
                display_topics = ", ".join(m.capitalize() for m in top_matched)
                why_recommended.append(f"Matches your {display_topics} interests")

            # Preferred event types bonus
            for ptype in user_event_types:
                if ptype and ptype in combined_text:
                    personalization_score = min(1.0, personalization_score + 0.10)
                    break

            # Preferred mode bonus (Online vs In-person)
            event_mode = (event.get("mode_location") or event.get("location") or "Online").lower()
            for pmode in user_modes:
                if pmode in event_mode:
                    personalization_score = min(1.0, personalization_score + 0.05)
                    break

        breakdown["personalization_score"] = round(personalization_score, 3)

        # -------------------------------------------------------------
        # 4. Urgency & Registration Deadline Signal
        # -------------------------------------------------------------
        urgency_score = 0.40  # Default baseline

        # Parse date_time or registration_deadline
        deadline_raw = event.get("registration_deadline") or event.get("date_time")
        target_dt = None
        if deadline_raw:
            if isinstance(deadline_raw, datetime):
                target_dt = deadline_raw
            else:
                try:
                    s = str(deadline_raw).strip()
                    if s.endswith("Z"):
                        s = s[:-1] + "+00:00"
                    target_dt = datetime.fromisoformat(s)
                except Exception:
                    pass

        if target_dt:
            if target_dt.tzinfo is None:
                target_dt = target_dt.replace(tzinfo=timezone.utc)

            delta = target_dt - reference_time
            days_left = delta.total_seconds() / 86400.0

            if 0 <= days_left <= 2:
                urgency_score = 0.95
                why_recommended.append("Closing in less than 48 hours")
            elif 2 < days_left <= 7:
                urgency_score = 0.85
                why_recommended.append(f"Happening in {int(days_left)} days")
            elif 7 < days_left <= 21:
                urgency_score = 0.70
                why_recommended.append("Coming up this month")
            elif days_left > 21:
                urgency_score = 0.50
            else:
                # Past deadline or event
                urgency_score = 0.20

        breakdown["urgency_score"] = round(urgency_score, 3)

        # -------------------------------------------------------------
        # Composite Weighted Score Calculation
        # -------------------------------------------------------------
        composite_score = (
            (WEIGHT_ORGANIZATION * org_score) +
            (WEIGHT_QUALITY * quality_score) +
            (WEIGHT_PERSONALIZATION * personalization_score) +
            (WEIGHT_URGENCY * urgency_score)
        )

        # Deduplicate recommendations and limit to top 4 most impactful
        seen = set()
        clean_recs = []
        for r in why_recommended:
            if r not in seen:
                seen.add(r)
                clean_recs.append(r)

        return round(composite_score, 4), clean_recs[:4], breakdown

    def rank_events(
        self,
        events: List[Dict[str, Any]],
        user: Optional[Dict[str, Any]] = None,
        sort_by: str = "recommended",
    ) -> List[Dict[str, Any]]:
        """
        Ranks and enriches a list of event dictionaries.
        Supports sorting strategies:
        - 'recommended': Composite ranking score DESC
        - 'soonest': Date time ASC
        - 'deadline': Registration deadline ASC
        - 'newest': Scraped/discovered at DESC
        """
        now = datetime.now(timezone.utc)

        enriched = []
        for event in events:
            ev_copy = dict(event)
            score, why_list, breakdown = self.calculate_event_score(ev_copy, user=user, reference_time=now)
            ev_copy["ranking_score"] = score
            ev_copy["why_recommended"] = why_list
            ev_copy["score_breakdown"] = breakdown
            
            # Host tier label for UI badge
            org_name = ev_copy.get("organizer") or ev_copy.get("organization") or ""
            profile = self.registry.classify_organization(org_name)
            ev_copy["host_tier"] = profile.organization_type.value
            ev_copy["host_badge"] = profile.display_badge
            ev_copy["host_verified"] = profile.verified

            enriched.append(ev_copy)

        # Sorting strategies
        if sort_by == "soonest":
            enriched.sort(key=lambda x: x.get("date_time") or "9999-12-31")
        elif sort_by == "deadline":
            enriched.sort(key=lambda x: x.get("registration_deadline") or x.get("date_time") or "9999-12-31")
        elif sort_by == "newest":
            enriched.sort(key=lambda x: x.get("scraped_at") or x.get("created_at") or "", reverse=True)
        else:  # default 'recommended'
            enriched.sort(key=lambda x: x.get("ranking_score", 0.0), reverse=True)

        return enriched


# Global Singleton Instance
ranking_service = RankingService()
