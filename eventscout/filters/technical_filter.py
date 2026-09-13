"""
Technical Event Classifier for EventScout.
Uses deterministic rule-based pattern matching with word boundaries
to accurately identify technical events and reject non-technical events.
"""

import re
from typing import Dict, List, Optional, Set, Tuple


# Technical categories and associated regex patterns (compiled with word boundaries)
TECHNICAL_TAXONOMY: Dict[str, List[str]] = {
    "Artificial Intelligence & Machine Learning": [
        r"\bai\b",
        r"\bartificial intelligence\b",
        r"\bmachine learning\b",
        r"\bml\b",
        r"\bdeep learning\b",
        r"\bllm\b",
        r"\bllms\b",
        r"\bgenerative ai\b",
        r"\bgenai\b",
        r"\bagentic ai\b",
        r"\bai agents?\b",
        r"\bnlp\b",
        r"\bcomputer vision\b",
        r"\bneural networks?\b",
        r"\btransformers?\b",
        r"\bhugging face\b",
        r"\blangchain\b",
        r"\bllama\b",
        r"\bopenai\b",
        r"\brag\b",
        r"\bvector search\b",
        r"\bembeddings?\b",
    ],
    "Cloud & DevOps": [
        r"\baws\b",
        r"\bazure\b",
        r"\bgcp\b",
        r"\bgoogle cloud\b",
        r"\bcloud computing\b",
        r"\bdevops\b",
        r"\bdocker\b",
        r"\bkubernetes\b",
        r"\bk8s\b",
        r"\bterraform\b",
        r"\bci/cd\b",
        r"\bmicroservices\b",
        r"\bserverless\b",
        r"\blinux\b",
        r"\bansible\b",
        r"\bobservability\b",
    ],
    "Software & Web Development": [
        r"\bpython\b",
        r"\bjavascript\b",
        r"\btypescript\b",
        r"\bgolang\b",
        r"\brust\b",
        r"\bjava\b",
        r"\bc\+\+\b",
        r"\bc#\b",
        r"\breact\b",
        r"\bnext\.?js\b",
        r"\bnode\.?js\b",
        r"\bvue\b",
        r"\bangular\b",
        r"\bflutter\b",
        r"\bswift\b",
        r"\bkotlin\b",
        r"\bandroid dev\b",
        r"\bios dev\b",
        r"\bapi\b",
        r"\bapis\b",
        r"\brest\b",
        r"\bgraphql\b",
        r"\bweb development\b",
        r"\bfrontend\b",
        r"\bbackend\b",
        r"\bfullstack\b",
        r"\bwordpress\b",
    ],
    "Data & Databases": [
        r"\bdata science\b",
        r"\bdata engineering\b",
        r"\bdata analytics\b",
        r"\bbig data\b",
        r"\bsql\b",
        r"\bnosql\b",
        r"\bpostgresql\b",
        r"\bmongodb\b",
        r"\bkafka\b",
        r"\bspark\b",
        r"\bdata warehouse\b",
        r"\bdatabase\b",
        r"\bdatabases\b",
    ],
    "Cybersecurity": [
        r"\bcybersecurity\b",
        r"\binfosec\b",
        r"\bethical hacking\b",
        r"\bpenetration testing\b",
        r"\bpen testing\b",
        r"\bnetwork security\b",
        r"\bcryptography\b",
        r"\bzero trust\b",
        r"\bvulnerability\b",
    ],
    "DSA & Competitive Programming": [
        r"\bdsa\b",
        r"\bdata structures\b",
        r"\balgorithms\b",
        r"\bleetcode\b",
        r"\bcompetitive programming\b",
        r"\bsystem design\b",
        r"\bhackerrank\b",
        r"\bcodeforces\b",
    ],
    "Open Source & Hackathons": [
        r"\bopen source\b",
        r"\bgithub\b",
        r"\bgit\b",
        r"\bhackathon\b",
        r"\bhackathons\b",
        r"\bdevfest\b",
        r"\btech conference\b",
        r"\bdeveloper community\b",
        r"\btech meetup\b",
    ],
    "Emerging Tech & Hardware": [
        r"\brobotics\b",
        r"\brobotica\b",
        r"\biot\b",
        r"\binternet of things\b",
        r"\bembedded systems?\b",
        r"\barduino\b",
        r"\braspberry pi\b",
        r"\bblockchain\b",
        r"\bweb3\b",
        r"\bsmart contracts?\b",
        r"\bar/vr\b",
        r"\baugmented reality\b",
        r"\bvirtual reality\b",
    ],
}

# Explicit non-technical patterns that should cause rejection unless overwhelming technical terms exist
NON_TECHNICAL_EXCLUSIONS: List[str] = [
    r"\bspeed dating\b",
    r"\bsingles mixer\b",
    r"\byoga\b",
    r"\bmeditation\b",
    r"\bboard games?\b",
    r"\bsalsa\b",
    r"\bdance class\b",
    r"\bbook club\b",
    r"\bwine tasting\b",
    r"\bhiking trip\b",
    r"\bfashion show\b",
    r"\breal estate investing\b",
]

# Pre-compile regular expressions for performance
COMPILED_TAXONOMY = {
    category: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    for category, patterns in TECHNICAL_TAXONOMY.items()
}
COMPILED_EXCLUSIONS = [re.compile(pattern, re.IGNORECASE) for pattern in NON_TECHNICAL_EXCLUSIONS]


class TechnicalEventFilter:
    """
    Evaluates whether an event is technical using deterministic rule-based matching.
    """

    def __init__(self, min_match_score: int = 1):
        self.min_match_score = min_match_score

    def classify(
        self,
        title: str,
        description: Optional[str] = None,
        organizer: Optional[str] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Classifies whether an event is technical and returns matched categories.
        
        Returns:
            Tuple of (is_technical: bool, matched_categories: List[str])
        """
        title = title or ""
        description = description or ""
        organizer = organizer or ""

        # Title carries the highest weight (score weight = 2)
        # Description and organizer provide supporting context (score weight = 1)
        search_blob_high_weight = title.lower()
        search_blob_context = f"{organizer} {description}".lower()

        # Check for explicit non-technical disqualifications in title
        for exc_regex in COMPILED_EXCLUSIONS:
            if exc_regex.search(title):
                # If the title explicitly mentions a non-tech activity (e.g. "Speed Dating"), reject
                return False, []

        matched_categories: Set[str] = set()
        total_score = 0

        for category, regex_list in COMPILED_TAXONOMY.items():
            for regex in regex_list:
                # Check in title first
                if regex.search(search_blob_high_weight):
                    matched_categories.add(category)
                    total_score += 2
                    break  # Found match for this category, move to next category
                # Check in organizer or description
                elif regex.search(search_blob_context):
                    matched_categories.add(category)
                    total_score += 1
                    break

        is_technical = total_score >= self.min_match_score
        return is_technical, sorted(list(matched_categories))

    def is_technical_event(
        self,
        title: str,
        description: Optional[str] = None,
        organizer: Optional[str] = None,
    ) -> bool:
        """Convenience method returning boolean is_technical flag."""
        is_tech, _ = self.classify(title, description, organizer)
        return is_tech
