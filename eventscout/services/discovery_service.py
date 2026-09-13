"""
Universal Source Discovery Service for EventScout.
Automates investigating unknown event websites, discovering extraction recipes via Gemini 1.5 Flash,
executing a test extraction run, validating samples, and preparing the source configuration for admin approval.
"""
import logging
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from eventscout.collectors.factory import get_collector_for_source
from eventscout.database.source_db import SourceDatabase, normalize_source_url
from eventscout.processors.normalizer import EventNormalizer
from eventscout.services.llm_service import GeminiDiscoveryLLM

logger = logging.getLogger("DiscoveryService")


class DiscoveryService:
    """
    Coordinates browser inspection, AI analysis with Gemini, and validation test runs.
    """

    def __init__(
        self,
        source_db: Optional[SourceDatabase] = None,
        llm_service: Optional[GeminiDiscoveryLLM] = None,
        normalizer: Optional[EventNormalizer] = None,
    ):
        self.source_db = source_db or SourceDatabase()
        self.llm = llm_service or GeminiDiscoveryLLM()
        self.normalizer = normalizer or EventNormalizer()

    def discover_source(self, url: str, existing_source_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes end-to-end discovery pipeline for a given website URL:
        1. Prepares/updates source document in DISCOVERING state.
        2. Inspects DOM & network activity.
        3. LLM determines strategy and configuration.
        4. Validates extraction on a sample run.
        5. Updates status to READY_FOR_REVIEW or FAILED.
        """
        parsed_url = urlparse(url)
        domain = parsed_url.netloc or url
        default_name = domain.replace("www.", "").split(".")[0].capitalize()

        if existing_source_id:
            source = self.source_db.get_source(existing_source_id)
            if not source:
                raise ValueError(f"Source with id {existing_source_id} not found.")
            source_id = existing_source_id
            self.source_db.update_source(source_id, {
                "status": "DISCOVERING",
                "discovery_status": "IN_PROGRESS",
                "last_error": None
            })
        else:
            # Check for existing duplicate by URL
            existing = self.source_db.find_duplicate_source(url)
            if existing:
                source_id = existing["id"]
                self.source_db.update_source(source_id, {
                    "status": "DISCOVERING",
                    "discovery_status": "IN_PROGRESS",
                    "last_error": None
                })
            else:
                new_doc = self.source_db.create_source(
                    url=url,
                    name=default_name,
                    status="DISCOVERING",
                    created_by="user",
                )
                source_id = new_doc["id"]

        logger.info("[SOURCE] Starting discovery: %s (ID: %s)", url, source_id)

        try:
            # Step 1: Open website in Playwright and capture DOM + network activity
            html_snippet, network_calls = self._inspect_page_and_network(url)

            # Step 2: AI analysis via Google Gemini
            logger.info("[SOURCE] Detecting extraction strategy via Gemini...")
            ai_result = self.llm.analyze_source_structure(
                url=url,
                html_snippet=html_snippet,
                network_requests=network_calls,
            )

            # Check if AI rejected the website
            if not ai_result.get("is_event_website", True):
                reason = ai_result.get("rejection_reason") or "Website does not appear to contain event or hackathon listings."
                logger.warning("[SOURCE] Rejection for %s: %s", url, reason)
                self.source_db.update_source(source_id, {
                    "status": "FAILED",
                    "discovery_status": "FAILED",
                    "last_error": f"INVALID_SOURCE: {reason}",
                })
                return self.source_db.get_source(source_id)

            discovered_name = ai_result.get("source_name") or default_name
            strategy = ai_result.get("collection_strategy") or ai_result.get("strategy", "PLAYWRIGHT")
            event_list_url = ai_result.get("event_list_url") or url
            configuration = ai_result.get("configuration", {})
            field_mapping = ai_result.get("field_mapping", {})
            notes = ai_result.get("notes", "")
            confidence = float(ai_result.get("confidence_score") or 0.8)
            source_type = ai_result.get("source_type") or "event_platform"

            logger.info("[SOURCE] Strategy detected: %s (Confidence: %.2f)", strategy, confidence)

            # Update status to TESTING
            self.source_db.update_source(source_id, {
                "name": discovered_name,
                "status": "TESTING",
                "collection_strategy": strategy,
                "strategy": strategy.lower(),
                "event_list_url": event_list_url,
                "source_type": source_type,
                "configuration": configuration,
                "field_mapping": field_mapping,
            })

            # Step 3: Test sample extraction using generic collector
            logger.info("[SOURCE] Extracting sample events...")
            test_config = {
                "id": source_id,
                "name": discovered_name,
                "base_url": url,
                "event_list_url": event_list_url,
                "collection_strategy": strategy,
                "strategy": strategy.lower(),
                "configuration": configuration,
            }

            collector = get_collector_for_source(test_config)
            raw_events = collector.test()
            normalized_events = self.normalizer.normalize_batch(raw_events, test_config)

            logger.info("[SOURCE] Found %d raw events, normalized %d valid events.",
                        len(raw_events), len(normalized_events))

            # Validate that extracted data is meaningful
            if not normalized_events:
                err_msg = "Extraction recipe generated by AI produced 0 valid events during validation test."
                logger.warning("[SOURCE] Validation failed for %s: %s", url, err_msg)
                self.source_db.update_source(source_id, {
                    "status": "FAILED",
                    "discovery_status": "FAILED",
                    "last_error": err_msg,
                    "notes": notes,
                })
                return self.source_db.get_source(source_id)

            # Step 4: Success! Save sample events and set status to READY_FOR_REVIEW
            sample_previews = [ev.to_dict() for ev in normalized_events[:5]]
            self.source_db.update_source(source_id, {
                "name": discovered_name,
                "status": "READY_FOR_REVIEW",
                "discovery_status": "READY",
                "confidence_score": confidence,
                "notes": notes,
                "sample_events": sample_previews,
                "last_error": None,
            })

            logger.info("[SOURCE] Validation successful. Found %d sample events. Awaiting admin approval.", len(sample_previews))
            return self.source_db.get_source(source_id)

        except Exception as e:
            logger.error("[SOURCE] Discovery failed for %s: %s", url, e, exc_info=True)
            self.source_db.update_source(source_id, {
                "status": "FAILED",
                "discovery_status": "FAILED",
                "last_error": str(e),
            })
            raise e

    def _inspect_page_and_network(self, url: str) -> tuple[str, list]:
        """Opens page in Playwright and captures intercepted API responses and DOM HTML."""
        intercepted_network = []
        html_content = ""

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                )
                page = context.new_page()

                def on_response(response):
                    try:
                        req_url = response.url
                        content_type = response.headers.get("content-type", "")
                        if "application/json" in content_type or "graphql" in req_url or "/api/" in req_url:
                            try:
                                body_text = response.text()
                                if body_text and len(body_text) > 10:
                                    intercepted_network.append({
                                        "url": req_url,
                                        "status": response.status,
                                        "method": response.request.method,
                                        "sample_body": body_text[:2000]
                                    })
                            except Exception:
                                pass
                    except Exception:
                        pass

                page.on("response", on_response)

                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    time.sleep(2)
                    page.evaluate("window.scrollTo(0, 500);")
                    time.sleep(1)
                    html_content = page.content()
                finally:
                    browser.close()
        except Exception as e:
            logger.warning("Browser inspection encountered error for %s: %s. Attempting HTTP GET fallback.", url, e)
            # Fallback to direct HTTP fetch if Playwright fails
            import httpx
            with httpx.Client(timeout=20.0, follow_redirects=True) as client:
                resp = client.get(url)
                html_content = resp.text

        return html_content, intercepted_network
