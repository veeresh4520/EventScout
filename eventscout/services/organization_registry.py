"""
eventscout/services/organization_registry.py
============================================
Organization Reputation Registry and Organizer Classification Engine.

Maintains normalized profiles, reputation tiers, and alias mappings for
companies, universities, developer communities, and institutes.
Provides robust alias matching and host classification without brittle string equality.
"""

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Dict, List, Optional, Tuple


class HostType(str, Enum):
    TIER_1_COMPANY = "TIER_1_COMPANY"
    TIER_2_COMPANY = "TIER_2_COMPANY"
    TOP_UNIVERSITY = "TOP_UNIVERSITY"
    COLLEGE = "COLLEGE"
    MAJOR_DEVELOPER_COMMUNITY = "MAJOR_DEVELOPER_COMMUNITY"
    ESTABLISHED_ORGANIZATION = "ESTABLISHED_ORGANIZATION"
    COMMUNITY = "COMMUNITY"
    INDIVIDUAL = "INDIVIDUAL"
    UNKNOWN = "UNKNOWN"


# Base reputation scores by host type (normalized 0.0 to 1.0)
HOST_TYPE_WEIGHTS: Dict[HostType, float] = {
    HostType.TIER_1_COMPANY: 0.95,
    HostType.TOP_UNIVERSITY: 0.92,
    HostType.MAJOR_DEVELOPER_COMMUNITY: 0.88,
    HostType.TIER_2_COMPANY: 0.82,
    HostType.ESTABLISHED_ORGANIZATION: 0.78,
    HostType.COLLEGE: 0.70,
    HostType.COMMUNITY: 0.60,
    HostType.INDIVIDUAL: 0.45,
    HostType.UNKNOWN: 0.40,
}


@dataclass
class OrganizationProfile:
    canonical_name: str
    aliases: List[str]
    organization_type: HostType
    reputation_score: float
    verified: bool = True
    display_badge: str = ""
    domain_hints: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.display_badge:
            badge_map = {
                HostType.TIER_1_COMPANY: "Tier 1 Tech Leader",
                HostType.TOP_UNIVERSITY: "Premier Institute",
                HostType.MAJOR_DEVELOPER_COMMUNITY: "Developer Community",
                HostType.TIER_2_COMPANY: "Recognized Tech Company",
                HostType.ESTABLISHED_ORGANIZATION: "Established Organization",
                HostType.COLLEGE: "Academic Institution",
                HostType.COMMUNITY: "Community Group",
                HostType.INDIVIDUAL: "Independent Organizer",
                HostType.UNKNOWN: "Community",
            }
            self.display_badge = badge_map.get(self.organization_type, "Community")


class OrganizationRegistry:
    """
    Registry for organization profiles, aliases, and reputation scoring.
    Supports dynamic registration and extensible alias resolution.
    """

    def __init__(self):
        self._profiles: Dict[str, OrganizationProfile] = {}
        self._alias_map: Dict[str, str] = {}  # normalized_alias -> canonical_name
        self._seed_default_profiles()

    def _normalize(self, text: str) -> str:
        """Strip punctuation, excessive whitespaces, and lowercase text."""
        if not text:
            return ""
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
        return " ".join(cleaned.split())

    def register_profile(self, profile: OrganizationProfile):
        """Register an organization profile and index all its aliases."""
        self._profiles[profile.canonical_name] = profile
        
        # Index canonical name
        norm_canonical = self._normalize(profile.canonical_name)
        self._alias_map[norm_canonical] = profile.canonical_name

        # Index all aliases
        for alias in profile.aliases:
            norm_alias = self._normalize(alias)
            if norm_alias:
                self._alias_map[norm_alias] = profile.canonical_name

    def get_profile(self, canonical_name: str) -> Optional[OrganizationProfile]:
        return self._profiles.get(canonical_name)

    def classify_organization(self, raw_name: Optional[str]) -> OrganizationProfile:
        """
        Classify an organizer name into an OrganizationProfile.
        Performs exact alias matching, token containment, and heuristic classification.
        """
        if not raw_name or not raw_name.strip():
            return OrganizationProfile(
                canonical_name="Unknown Organizer",
                aliases=[],
                organization_type=HostType.UNKNOWN,
                reputation_score=HOST_TYPE_WEIGHTS[HostType.UNKNOWN],
                verified=False,
            )

        norm_input = self._normalize(raw_name)

        # 1. Exact alias match
        if norm_input in self._alias_map:
            return self._profiles[self._alias_map[norm_input]]

        # 2. Key phrase / containment matching against known aliases (longest match first)
        sorted_aliases = sorted(self._alias_map.keys(), key=len, reverse=True)
        for alias in sorted_aliases:
            # Check word boundary matching
            pattern = r"\b" + re.escape(alias) + r"\b"
            if re.search(pattern, norm_input):
                return self._profiles[self._alias_map[alias]]

        # 3. Dynamic heuristic classification based on domain keywords
        college_keywords = ["university", "institute", "college", "campus", "polytechnic", "school of", "academy"]
        if any(kw in norm_input for kw in college_keywords):
            if any(top in norm_input for top in ["iit", "iiit", "nit", "bits", "iisc", "national institute"]):
                return OrganizationProfile(
                    canonical_name=raw_name.strip(),
                    aliases=[raw_name.strip()],
                    organization_type=HostType.TOP_UNIVERSITY,
                    reputation_score=HOST_TYPE_WEIGHTS[HostType.TOP_UNIVERSITY],
                    verified=True,
                )
            return OrganizationProfile(
                canonical_name=raw_name.strip(),
                aliases=[raw_name.strip()],
                organization_type=HostType.COLLEGE,
                reputation_score=HOST_TYPE_WEIGHTS[HostType.COLLEGE],
                verified=False,
            )

        community_keywords = ["community", "meetup", "group", "club", "devs", "developers", "chapter", "network"]
        if any(kw in norm_input for kw in community_keywords):
            return OrganizationProfile(
                canonical_name=raw_name.strip(),
                aliases=[raw_name.strip()],
                organization_type=HostType.COMMUNITY,
                reputation_score=HOST_TYPE_WEIGHTS[HostType.COMMUNITY],
                verified=False,
            )

        # 4. Fallback profile
        return OrganizationProfile(
            canonical_name=raw_name.strip(),
            aliases=[raw_name.strip()],
            organization_type=HostType.INDIVIDUAL,
            reputation_score=HOST_TYPE_WEIGHTS[HostType.INDIVIDUAL],
            verified=False,
        )

    def _seed_default_profiles(self):
        """Seed the registry with high-reputation companies, universities, and communities."""
        
        # --- TIER 1 TECH COMPANIES ---
        tier_1_orgs = [
            ("Google", ["Google Developers", "Google Cloud", "GDG", "Google Developer Groups", "Google DeepMind", "GDSC", "Google for Developers"], HostType.TIER_1_COMPANY, 0.98),
            ("Microsoft", ["Microsoft Reactor", "Microsoft Developer", "Microsoft Foundry", "Microsoft Azure", "Microsoft Learn", "MS Reactor"], HostType.TIER_1_COMPANY, 0.98),
            ("Amazon Web Services", ["AWS", "Amazon", "AWS User Group", "AWS Community", "Amazon Cloud"], HostType.TIER_1_COMPANY, 0.97),
            ("Meta", ["Facebook", "Meta Open Source", "Meta Developer", "PyTorch"], HostType.TIER_1_COMPANY, 0.96),
            ("Apple", ["Apple Developer", "Swift Community", "Apple Worldwide Developer"], HostType.TIER_1_COMPANY, 0.96),
            ("NVIDIA", ["NVIDIA Developer", "NVIDIA Deep Learning Institute", "NVIDIA Inception", "NVIDIA AI"], HostType.TIER_1_COMPANY, 0.98),
            ("OpenAI", ["OpenAI Developers", "OpenAI Forum"], HostType.TIER_1_COMPANY, 0.99),
            ("GitHub", ["GitHub Education", "GitHub Campus", "GitHub Community"], HostType.TIER_1_COMPANY, 0.96),
            ("IBM", ["IBM Developer", "IBM Cloud", "IBM Research", "Red Hat"], HostType.TIER_1_COMPANY, 0.92),
            ("Oracle", ["Oracle Cloud", "Oracle Developer", "Java Community"], HostType.TIER_1_COMPANY, 0.91),
            ("Intel", ["Intel Developer Zone", "Intel AI"], HostType.TIER_1_COMPANY, 0.92),
            ("Cisco", ["Cisco DevNet"], HostType.TIER_1_COMPANY, 0.90),
            ("Salesforce", ["Salesforce Developers", "Trailhead"], HostType.TIER_1_COMPANY, 0.91),
            ("Adobe", ["Adobe Developer", "Adobe Tech"], HostType.TIER_1_COMPANY, 0.91),
        ]

        for name, aliases, host_type, score in tier_1_orgs:
            self.register_profile(OrganizationProfile(name, aliases, host_type, score, verified=True))

        # --- TIER 2 TECH & FAST-GROWING TECH COMPANIES ---
        tier_2_orgs = [
            ("Uber", ["Uber Engineering"], HostType.TIER_2_COMPANY, 0.86),
            ("Spotify", ["Spotify Engineering"], HostType.TIER_2_COMPANY, 0.85),
            ("Netflix", ["Netflix Tech Blog", "Netflix Open Source"], HostType.TIER_2_COMPANY, 0.88),
            ("Stripe", ["Stripe Developer"], HostType.TIER_2_COMPANY, 0.88),
            ("Atlassian", ["Atlassian Developer"], HostType.TIER_2_COMPANY, 0.84),
            ("Databricks", ["Databricks Community", "Spark Community"], HostType.TIER_2_COMPANY, 0.89),
            ("Snowflake", ["Snowflake Developer"], HostType.TIER_2_COMPANY, 0.86),
            ("MongoDB", ["MongoDB User Group", "MUG", "MongoDB Developer"], HostType.TIER_2_COMPANY, 0.87),
            ("Postman", ["Postman Galaxy", "Postman Community"], HostType.TIER_2_COMPANY, 0.85),
            ("Docker", ["Docker Community"], HostType.TIER_2_COMPANY, 0.85),
        ]

        for name, aliases, host_type, score in tier_2_orgs:
            self.register_profile(OrganizationProfile(name, aliases, host_type, score, verified=True))

        # --- PREMIER UNIVERSITIES & INSTITUTES ---
        top_universities = [
            ("IIT Hyderabad", ["Indian Institute of Technology Hyderabad", "IITH", "IIT-H"], HostType.TOP_UNIVERSITY, 0.94),
            ("IIT Bombay", ["Indian Institute of Technology Bombay", "IITB", "Techfest IIT Bombay"], HostType.TOP_UNIVERSITY, 0.95),
            ("IIT Delhi", ["Indian Institute of Technology Delhi", "IITD"], HostType.TOP_UNIVERSITY, 0.95),
            ("IIT Madras", ["Indian Institute of Technology Madras", "IITM", "Shaastra IIT Madras"], HostType.TOP_UNIVERSITY, 0.95),
            ("IIT Kharagpur", ["Indian Institute of Technology Kharagpur", "IITKGP", "Kshitij IIT KGP"], HostType.TOP_UNIVERSITY, 0.94),
            ("IIT Kanpur", ["Indian Institute of Technology Kanpur", "IITK"], HostType.TOP_UNIVERSITY, 0.94),
            ("IIIT Hyderabad", ["International Institute of Information Technology Hyderabad", "IIITH", "Felicity IIITH"], HostType.TOP_UNIVERSITY, 0.94),
            ("IIIT Bangalore", ["International Institute of Information Technology Bangalore", "IIITB"], HostType.TOP_UNIVERSITY, 0.91),
            ("BITS Pilani", ["Birla Institute of Technology and Science", "BITS Hyderabad", "BITS Goa", "ATMOS BITS"], HostType.TOP_UNIVERSITY, 0.93),
            ("IISc Bangalore", ["Indian Institute of Science", "IISc", "Pravega IISc"], HostType.TOP_UNIVERSITY, 0.96),
            ("NIT Trichy", ["National Institute of Technology Tiruchirappalli", "NITT"], HostType.TOP_UNIVERSITY, 0.90),
            ("NIT Warangal", ["National Institute of Technology Warangal", "NITW"], HostType.TOP_UNIVERSITY, 0.90),
            ("NIT Surathkal", ["National Institute of Technology Karnataka", "NITK"], HostType.TOP_UNIVERSITY, 0.90),
            ("Stanford University", ["Stanford", "Stanford AI Lab"], HostType.TOP_UNIVERSITY, 0.98),
            ("MIT", ["Massachusetts Institute of Technology", "MIT CSAIL"], HostType.TOP_UNIVERSITY, 0.99),
            ("Carnegie Mellon University", ["CMU"], HostType.TOP_UNIVERSITY, 0.97),
            ("Harvard University", ["Harvard"], HostType.TOP_UNIVERSITY, 0.97),
        ]

        for name, aliases, host_type, score in top_universities:
            self.register_profile(OrganizationProfile(name, aliases, host_type, score, verified=True))

        # --- MAJOR DEVELOPER COMMUNITIES & PLATFORMS ---
        communities = [
            ("Major League Hacking", ["MLH", "Major League Hacking (MLH)"], HostType.MAJOR_DEVELOPER_COMMUNITY, 0.93),
            ("Devfolio", ["Devfolio Community", "ETHIndia", "Hackathons on Devfolio"], HostType.MAJOR_DEVELOPER_COMMUNITY, 0.92),
            ("Devpost", ["Devpost Hackathons", "Devpost Inc."], HostType.MAJOR_DEVELOPER_COMMUNITY, 0.91),
            ("Unstop", ["Unstop Hackathons", "Dare2Compete", "Unstop Quizzes"], HostType.MAJOR_DEVELOPER_COMMUNITY, 0.90),
            ("FOSS United", ["FOSS United Foundation", "FOSS Meetup", "IndiaFOSS", "Hyderabad FOSS"], HostType.MAJOR_DEVELOPER_COMMUNITY, 0.89),
            ("HackerEarth", ["HackerEarth Competitions", "HackerEarth Hackathons"], HostType.MAJOR_DEVELOPER_COMMUNITY, 0.88),
            ("Hack2Skill", ["Hack2Skill Innovation", "H2S"], HostType.MAJOR_DEVELOPER_COMMUNITY, 0.87),
            ("CNCF", ["Cloud Native Computing Foundation", "Kubernetes Community"], HostType.MAJOR_DEVELOPER_COMMUNITY, 0.92),
            ("Linux Foundation", ["LF", "The Linux Foundation"], HostType.MAJOR_DEVELOPER_COMMUNITY, 0.93),
            ("Python Software Foundation", ["PSF", "PyCon", "PyData", "Hyderabad Python Users Group", "HydPy"], HostType.MAJOR_DEVELOPER_COMMUNITY, 0.90),
            ("T-Hub", ["T-Hub Innovation Hub", "THub", "T-Hub Hyderabad"], HostType.ESTABLISHED_ORGANIZATION, 0.89),
            ("Telangana AI Mission", ["T-AIM", "T-AIM Hyderabad"], HostType.ESTABLISHED_ORGANIZATION, 0.88),
            ("NASSCOM", ["NASSCOM DeepTech", "10,000 Startups"], HostType.ESTABLISHED_ORGANIZATION, 0.88),
        ]

        for name, aliases, host_type, score in communities:
            self.register_profile(OrganizationProfile(name, aliases, host_type, score, verified=True))


# Global Singleton Instance
organization_registry = OrganizationRegistry()
