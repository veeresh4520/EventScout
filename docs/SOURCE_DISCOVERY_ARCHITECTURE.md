# Universal Source Discovery + Scraping Agent Architecture

## Overview
EventScout features an autonomous **Universal Source Discovery & Scraping Agent**. Instead of manually developing and maintaining bespoke scrapers for dozens or hundreds of event platforms (e.g. Meetup, Devpost, Unstop, Devfolio, MLH, HackerEarth), administrators can provide any target website URL. The system autonomously investigates the site, determines the optimal extraction strategy, formulates extraction recipes, executes validation test runs, and registers dynamic sources into MongoDB.

---

## High-Level Architecture Flow

```
                                 [ Administrator ]
                                         │
                         Enters Target URL (e.g. devpost.com)
                                         ▼
                     ┌────────────────────────────────────────┐
                     │       FastAPI /api/sources/discover    │
                     └───────────────────┬────────────────────┘
                                         │
                       Step 1: Headless DOM & Network Probe
                                         ▼
                     ┌────────────────────────────────────────┐
                     │          Playwright Inspector          │
                     │  - Captures DOM / rendered HTML        │
                     │  - Intercepts XHR / Fetch JSON APIs    │
                     └───────────────────┬────────────────────┘
                                         │
                       Step 2: AI Recipe Formulation (FREE)
                                         ▼
                     ┌────────────────────────────────────────┐
                     │    Google Gemini 1.5 Flash (Free API)  │
                     │  - Analyzes 1M token context           │
                     │  - Returns structured JSON strategy:   │
                     │    * "api_json" OR "playwright_html"   │
                     │    * Field selectors & pagination      │
                     └───────────────────┬────────────────────┘
                                         │
                       Step 3: Validation Test Run & Normalization
                                         ▼
                     ┌────────────────────────────────────────┐
                     │    Generic Collectors & Normalizer     │
                     │  - ApiCollector / PlaywrightCollector  │
                     │  - Validates extraction of >= 1 events │
                     └───────────────────┬────────────────────┘
                                         │
                     ┌───────────────────┴────────────────────┐
                     │                                        │
           [ Validation Passed ]                    [ Validation Failed ]
                     │                                        │
                     ▼                                        ▼
         Status: READY_FOR_REVIEW                       Status: FAILED
   Saved to MongoDB `sources` Collection            Error details logged
                     │
                     ▼
          [ Human Review & Approval ]
            - Inspect sample events
            - Edit configuration if needed
            - Click "Approve & Enable"
                     │
                     ▼
              Status: ENABLED
                     │
                     ▼
     ┌────────────────────────────────────────────────────────┐
     │              Automated Scheduler Pipeline              │
     │  - Runs Meetup Scraper (Custom Adapter)                │
     │  - Runs All ENABLED Dynamic Sources in Registry        │
     │  - Failure Isolation: Isolated try/except per source   │
     │  - Idempotent MongoDB Atlas Upsert                     │
     │  - User Notification & Daily Digest Dispatch           │
     └────────────────────────────────────────────────────────┘
```

---

## Key Principles & Architectural Guarantees

### 1. Zero Ongoing AI Costs (Cost Efficiency)
* **AI is only used once during initial discovery** or when an admin requests a re-discovery.
* Daily automated scraping executes deterministic Playwright CSS selectors or direct REST/GraphQL HTTP requests (`httpx`).
* Powered by **Google Gemini 1.5 Flash Free Tier**, meaning developers never need a paid credit card.

### 2. Human-in-the-Loop Approval
* Newly discovered sources transition to `READY_FOR_REVIEW`.
* The admin panel at `/admin/sources` provides:
  * Discovered source name, confidence score, and AI notes.
  * Preview of extracted sample events.
  * Live test scrape trigger.
  * Interactive JSON configuration editor.
* Sources are only scraped by the automated scheduler once an admin explicitly clicks **Approve & Enable**.

### 3. Failure Isolation
* Each dynamic collector run is wrapped in an independent fault-tolerant boundary:
  ```python
  try:
      raw_items = collector.collect(max_pages=max_pages)
      ...
      source_db.update_source_health(source_id, success=True)
  except Exception as source_err:
      source_db.update_source_health(source_id, success=False, error_msg=str(source_err))
  ```
* If a third-party website changes its HTML or goes down, only that single source's health status is marked with an error. All other scrapers and the daemon scheduler continue running uninterrupted.

### 4. Backward Compatibility
* The existing Meetup scraper pipeline is retained as a custom adapter and runs seamlessly alongside dynamically registered sources.

---

## Setup & Configuration

1. **Obtain Free Gemini API Key**:
   * Visit [Google AI Studio](https://aistudio.google.com).
   * Click **Get API key** and copy your key.
2. **Add to `.env`**:
   ```env
   GEMINI_API_KEY=AIzaSy...your_key_here
   ```
3. **Promote an Admin User**:
   ```bash
   python -m eventscout.database.make_admin <your_email_or_username>
   ```
4. **Access the Admin Portal**:
   * Navigate to `http://localhost:3000/admin/sources`.
