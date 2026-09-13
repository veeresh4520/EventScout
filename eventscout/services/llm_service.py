"""
LLM Service for EventScout Dynamic AI Source Discovery.
Powered by Google Gemini 1.5 Flash for fast, structured JSON analysis.
"""
import json
import logging
import os
import re
from typing import Any, Dict, Optional

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("LLMService")


class GeminiDiscoveryLLM:
    """
    Analyzes website DOM and intercepted network calls to generate
    a structured source configuration recipe (REST API, GraphQL, Static HTML, or Playwright).
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key or "your_gemini_api_key_here" in self.api_key:
            logger.warning("GEMINI_API_KEY is not set or using placeholder.")
        else:
            try:
                genai.configure(api_key=self.api_key)
            except Exception as e:
                logger.error("Failed to configure Google Generative AI: %s", e)

    def is_configured(self) -> bool:
        return bool(self.api_key and "your_gemini_api_key_here" not in self.api_key)

    def analyze_source_structure(
        self,
        url: str,
        html_snippet: str,
        network_requests: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Uses Gemini 1.5 Flash to inspect page DOM and network activity,
        determining whether it is an event platform and generating a structured extraction recipe.
        """
        if not self.is_configured():
            logger.info("GEMINI_API_KEY not configured. Generating heuristic extraction recipe for %s", url)
            return self._heuristic_fallback(url, html_snippet, network_requests)

        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={"response_mime_type": "application/json"}
        )

        network_summary = json.dumps(network_requests or [], indent=2)[:4000]
        trimmed_html = html_snippet[:60000]

        prompt = f"""
You are an expert web scraping and data extraction architect for EventScout.
Analyze the target website DOM snapshot and intercepted network traffic to determine if it is an event/hackathon/meetup site and produce a reusable, structured configuration.

Target URL: {url}

Network Requests Intercepted During Page Load:
{network_summary}

Page HTML / DOM Snapshot:
{trimmed_html}

INSTRUCTIONS:
1. Verify if this website provides event, hackathon, conference, or meetup listings.
   If NO, set "is_event_website": false and provide "rejection_reason".
2. If YES, determine:
   - "source_name": Clean display name (e.g. "Devpost", "Unstop", "GDG")
   - "source_type": "hackathon_platform" | "event_platform" | "community" | "university"
   - "event_list_url": Specific URL where events are listed (e.g., https://devpost.com/hackathons if root was provided)
   - "collection_strategy": Simplest reliable strategy:
       * "REST_API" if a public/internal REST endpoint returning event JSON was found in network requests.
       * "GRAPHQL" if a GraphQL endpoint with event queries was found in network requests.
       * "HTML" if static HTML / Schema.org JSON-LD contains events without dynamic JavaScript requirement.
       * "PLAYWRIGHT" if DOM requires browser execution, JavaScript rendering, or dynamic scrolling.
   - "confidence_score": 0.0 to 1.0 (float)
   - "notes": Concise summary of findings and how data was identified.
   - "configuration":
       * For "REST_API":
           "endpoint": "https://...",
           "method": "GET" or "POST",
           "items_path": "path.to.items" (dot-separated or "" if root list),
           "fields": {{ "title": "jsonKey", "event_url": "linkKey", "date_time": "dateKey", ... }},
           "pagination": {{ "page_param": "page", "size_param": "size" }}
       * For "GRAPHQL":
           "endpoint": "https://...",
           "query": "query ...",
           "variables": {{}},
           "items_path": "data.events",
           "fields": {{ "title": "name", "event_url": "url", "date_time": "startDate" }}
       * For "HTML" or "PLAYWRIGHT":
           "container_selector": "CSS selector for repeating event cards",
           "fields": {{
               "title": {{ "selector": "...", "type": "text" }},
               "event_url": {{ "selector": "...", "type": "attribute", "attribute": "href" }},
               "date_time": {{ "selector": "...", "type": "text" }},
               "organizer": {{ "selector": "...", "type": "text" }},
               "mode_location": {{ "selector": "...", "type": "text" }},
               "poster_image_url": {{ "selector": "...", "type": "attribute", "attribute": "src" }},
               "description": {{ "selector": "...", "type": "text" }},
               "deadline": {{ "selector": "...", "type": "text" }}
           }},
           "pagination": {{ "type": "scroll" }} or {{ "type": "next_button", "selector": "..." }}

Output JSON matching this exact structure:
{{
  "is_event_website": true,
  "source_name": "...",
  "source_type": "...",
  "event_list_url": "...",
  "collection_strategy": "PLAYWRIGHT" | "REST_API" | "GRAPHQL" | "HTML",
  "confidence_score": 0.90,
  "notes": "...",
  "configuration": {{ ... }},
  "field_mapping": {{ ... }}
}}
"""

        try:
            logger.info("Sending DOM and network payload to Gemini 1.5 Flash...")
            response = model.generate_content(prompt)
            text = response.text.strip()
            parsed = json.loads(text)
            # Normalize strategy naming
            strat = parsed.get("collection_strategy") or parsed.get("strategy") or "PLAYWRIGHT"
            parsed["collection_strategy"] = strat.upper()
            parsed["strategy"] = strat.lower()
            return parsed
        except Exception as e:
            logger.warning("Gemini analysis error: %s. Falling back to heuristic extractor.", e)
            return self._heuristic_fallback(url, html_snippet, network_requests)

    def _heuristic_fallback(
        self,
        url: str,
        html_snippet: str,
        network_requests: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Deterministic fallback that extracts reasonable selectors from DOM cues
        when Gemini API is unconfigured or unreachable.
        """
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.replace("www.", "")
        name = domain.split(".")[0].capitalize()

        # Check for REST API in intercepted requests
        if network_requests:
            for req in network_requests:
                req_url = req.get("url", "")
                if any(term in req_url.lower() for term in ("/api/events", "/api/v1/events", "/hackathons/api", "graphql")):
                    return {
                        "is_event_website": True,
                        "source_name": name,
                        "source_type": "event_platform",
                        "event_list_url": url,
                        "collection_strategy": "REST_API",
                        "strategy": "api_json",
                        "confidence_score": 0.85,
                        "notes": f"Detected active JSON API endpoint {req_url}",
                        "configuration": {
                            "endpoint": req_url,
                            "method": req.get("method", "GET"),
                            "items_path": "events",
                            "fields": {
                                "title": "title",
                                "event_url": "url",
                                "date_time": "date_time",
                            }
                        }
                    }

        # Check for JSON-LD in HTML
        if 'application/ld+json' in html_snippet and ('"Event"' in html_snippet or '"schema.org"' in html_snippet):
            return {
                "is_event_website": True,
                "source_name": name,
                "source_type": "event_platform",
                "event_list_url": url,
                "collection_strategy": "HTML",
                "strategy": "html",
                "confidence_score": 0.90,
                "notes": "Detected Schema.org Event JSON-LD structured data in page header.",
                "configuration": {
                    "target_url": url,
                }
            }

        # Default DOM Playwright configuration
        container_candidates = [
            "article",
            "[data-testid*='event']",
            "[class*='event-card']",
            "[class*='event_card']",
            "[class*='hackathon-card']",
            "[class*='challenge-card']",
            "[class*='card']",
        ]
        chosen_container = "div[class*='card'], article"
        for cand in container_candidates:
            if cand in html_snippet:
                chosen_container = cand
                break

        return {
            "is_event_website": True,
            "source_name": name,
            "source_type": "event_platform",
            "event_list_url": url,
            "collection_strategy": "PLAYWRIGHT",
            "strategy": "playwright_html",
            "confidence_score": 0.75,
            "notes": f"DOM-based extraction with selector '{chosen_container}'",
            "configuration": {
                "target_url": url,
                "container_selector": chosen_container,
                "fields": {
                    "title": {"selector": "h2, h3, h4, [class*='title']", "type": "text"},
                    "event_url": {"selector": "a", "type": "attribute", "attribute": "href"},
                    "date_time": {"selector": "time, [class*='date'], [class*='time']", "type": "text"},
                    "description": {"selector": "p, [class*='desc']", "type": "text"},
                    "poster_image_url": {"selector": "img", "type": "attribute", "attribute": "src"},
                },
                "pagination": {"type": "scroll"},
            }
        }
