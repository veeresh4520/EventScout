# EventScout: Technical Architecture & System Walkthrough

> **Document Version:** 1.0.0  
> **Status:** Checkpoint Analysis & Documentation  
> **Scope:** Complete analysis of the actual implemented codebase (Meetup → Playwright → Extraction/Normalization → MongoDB Atlas → FastAPI → Next.js 16/React 19).

---

## 1. EventScout Overview

### What is EventScout?
**EventScout** is a specialized developer intelligence platform that automatically discovers, filters, organizes, and displays high-quality technical events, workshops, hackathons, and developer meetups. Instead of requiring developers and students to manually check multiple platforms every week, EventScout continuously aggregates technical events into a single, clean interface.

### What Problem Does It Solve?
1. **Information Fragmentation:** Tech events are scattered across Meetup, Devpost, Eventbrite, LinkedIn, Discord, and university portals. Finding relevant tech events requires visiting multiple websites repeatedly.
2. **Noise and Irrelevance:** Platforms like Meetup group together everything from salsa dancing and speed dating to Kubernetes deep dives and machine learning workshops. Manually sifting through non-technical events is time-consuming.
3. **Stale and Expired Information:** Many aggregators display outdated events whose dates have already passed, cluttering the user experience.
4. **Platform Lock-in and Siloed Formats:** Every website structures event data differently (different date formats, different price representations, different venue descriptions). EventScout unifies this into a single canonical event schema.

---

### Currently Implemented vs. Future / Planned Features

To maintain complete clarity about the project's current state, here is the exact breakdown:

| Capability | Currently Implemented in Codebase | Future / Planned Work |
| :--- | :--- | :--- |
| **Data Sources** | **Meetup.com** via headless browser network interception | Devpost, GitHub Events, Google Developers, Microsoft Reactor, Luma, Unstop |
| **Data Collection** | Playwright Chromium automation (`MeetupSource`), automated background scheduler (APScheduler) for periodic scraping | Webhook listeners |
| **Data Extraction** | Field-level extraction (`parse_meetup_node`) extracting title, URLs, dates, organizer, venue, pricing, images, and description | Full HTML page body parsing for rich agendas, speaker bios, and sponsor details |
| **Filtering** | Rule-based regex classification (`TechnicalEventFilter`) with 8 tech taxonomies + city/mode filters (Hyderabad & Online) | Machine Learning / LLM-based categorization, semantic relevance scoring |
| **Deduplication** | Exact ID (`source:source_event_id`), exact URL, and semantic composite keys (`norm_title::date::norm_organizer`) | Cross-platform fuzzy deduplication using embeddings/vector search |
| **Storage & Persistence** | **MongoDB Atlas** database (`eventscout.events`) with compound unique index and bulk upsert operations; local `data/events.json` snapshot | User profiles collection, saved events collection, user notification preferences |
| **Lifecycle Management** | Timezone-aware expiration check (`EventDatabase.is_expired`) that prunes past events from DB and query responses | Event status updates (cancelled, postponed, sold out) and change history tracking |
| **Backend API** | **FastAPI** (`api/main.py`) with CORS middleware, `/health`, and `/events` endpoints returning serialized JSON | Authentication (JWT), user bookmarking endpoints, search/filter query parameters |
| **Frontend UI** | **Next.js 16 (App Router)** + **React 19** + **Tailwind CSS 4**: responsive grid, search bar, category chips, loading skeletons, error handling, dark mode | User login/signup, "Save Event" bookmarking, calendar export (.ics), email/Telegram alerts, browser extension |

---

## 2. Current Architecture

The diagram below illustrates the actual end-to-end data pipeline currently running in EventScout:

```text
┌────────────────────────────────────────────────────────────────────────┐
│ 1. DATA ACQUISITION LAYER                                              │
│                                                                        │
│   Meetup.com Web Platform                                              │
│         │                                                              │
│         ▼ (Chromium headless browser navigates & scrolls)              │
│   Playwright Browser Automation (eventscout/sources/meetup.py)         │
│         │                                                              │
│         ▼ (Intercepts HTTP POST /gql2 responses with JSON payloads)    │
│   GraphQL Network Interceptor                                          │
└────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 2. EXTRACTION, NORMALIZATION & REFINEMENT                              │
│                                                                        │
│   Raw JSON Edge Nodes                                                  │
│         │                                                              │
│         ▼ parse_meetup_node() in eventscout/sources/meetup.py          │
│   Canonical Event Dataclass (eventscout/models/event.py)               │
│         │                                                              │
│         ▼ TechnicalEventFilter (eventscout/filters/technical_filter.py)│
│   Filter: Keeps Tech Events (Rejects speed dating, yoga, etc.)         │
│         │                                                              │
│         ▼ EventDeduplicator (eventscout/processors/deduplicator.py)    │
│   Deduplication: In-memory exact & composite signature checks          │
│         │                                                              │
│         ▼ EventDatabase.is_expired()                                   │
│   Expired Filter: Discards events whose date has passed                │
└────────────────────────────────────────────────────────────────────────┘
                                  │
                  ┌───────────────┴───────────────┐
                  ▼                               ▼
┌──────────────────────────────────┐ ┌──────────────────────────────────┐
│ Local Debug / Backup Snapshot    │ │ 3. PERSISTENT STORAGE LAYER      │
│                                  │ │                                  │
│ data/events.json                 │ │ MongoDB Atlas (Cloud Database)   │
│ (Readable JSON inspectable file) │ │   Database:   eventscout         │
│                                  │ │   Collection: events             │
│                                  │ │   Index: (source, source_event_id)
│                                  │ │   Operation: Idempotent Upsert   │
└──────────────────────────────────┘ └──────────────────────────────────┘
                                                  │
                                                  ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 4. BACKEND API SERVICE LAYER                                           │
│                                                                        │
│   FastAPI Application (api/main.py running on Uvicorn:8000)            │
│         │                                                              │
│         ├── GET /health  --> API Status Check                          │
│         └── GET /events  --> Queries MongoDB for future events,        │
│                              converts ObjectIds to strings,            │
│                              returns JSON array                        │
└────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼ (HTTP fetch with CORS enabled)
┌────────────────────────────────────────────────────────────────────────┐
│ 5. CLIENT APPLICATION LAYER                                            │
│                                                                        │
│   Next.js 16 + React 19 Frontend (frontend/src/app/page.tsx:3000)      │
│         │                                                              │
│         ├── State Management (events, loading, error, searchQuery)     │
│         ├── Category Filter Chips ("All", "AI/ML", "Cloud", etc.)      │
│         ├── Live Client-Side Text Search (title, organizer, keywords)  │
│         └── EventCard Component (frontend/src/components/EventCard.tsx)│
│               - Poster image with Next.js <Image> fallback             │
│               - Formatted date & time                                  │
│               - Price badge ("Free" vs currency amount)                │
│               - Organizer & venue / attendance mode                    │
│               - Direct registration link to original event             │
└────────────────────────────────────────────────────────────────────────┘
```

### Component Roles Explained in Plain English:
* **Playwright Scraper:** Acts like a silent, invisible user opening Chrome, going to Meetup's search page, scrolling down so more events load, and catching the raw data packets Meetup sends to its own web app.
* **Extractor & Normalizer:** Cleans up messy raw web data into clean, predictable Python objects where fields always have the same names and formats.
* **Technical Filter:** A smart gatekeeper with a rich dictionary of technology keywords that admits developer events and throws out unrelated social events.
* **Deduplicator:** Ensures that if the scraper runs twice or sees the same event across multiple pages, you never get two copies of the same meetup.
* **MongoDB Atlas:** A managed cloud database that permanently stores the clean events. It supports "upsert" (update if it exists, insert if it is new).
* **FastAPI:** A lightweight, high-speed Python web server that connects to MongoDB and serves event data as a clean JSON API endpoint (`/events`).
* **Next.js Frontend:** The web application that the user opens in their browser. It calls FastAPI, displays a responsive grid of event cards, and lets users search and filter by category.

---

## 3. Project Folder Structure

Below is the actual directory and file tree of the EventScout repository:

```text
EventScout/
├── .env                                # Local environment variables (DB credentials - gitignored)
├── .gitignore                          # Git ignore rules for virtual environments, secrets, caches
├── main.py                             # Root convenience runner for Meetup scraper pipeline
├── requirements.txt                    # Root Python dependencies list (playwright)
│
├── api/                                # Backend API service
│   └── main.py                         # FastAPI application defining /health and /events routes
│
├── data/                               # Workspace data directory
│   └── events.json                     # Root local JSON snapshot of active scraped events
│
├── docs/                               # System and technical documentation
│   └── EVENTSCOUT_TECHNICAL_WALKTHROUGH.md  # Comprehensive technical walkthrough (this file)
│
├── eventscout/                         # Core Python package for scraping, filtering, and storage
│   ├── __init__.py                     # Package initialization marker
│   ├── main.py                         # Package-level entry point to run scraper
│   │
│   ├── database/                       # Database repository layer
│   │   ├── __init__.py                 # Database module export
│   │   └── mongodb.py                  # EventDatabase class managing MongoDB Atlas connection,
│   │                                   # indexes, expiration checks, upsert, and JSON conversion
│   │
│   ├── filters/                        # Data filtering and classification
│   │   ├── __init__.py                 # Filter module export
│   │   └── technical_filter.py         # TechnicalEventFilter regex taxonomy classifier
│   │
│   ├── models/                         # Domain models
│   │   ├── __init__.py                 # Model exports
│   │   └── event.py                    # Event dataclass (canonical event schema & to_dict())
│   │
│   ├── processors/                     # Data processing and refinement
│   │   ├── __init__.py                 # Processors module export
│   │   └── deduplicator.py             # EventDeduplicator with exact ID & composite fuzzy keys
│   │
│   ├── scrapers/                       # Pipeline coordinators
│   │   ├── __init__.py                 # Scraper exports
│   │   └── meetup_scraper.py           # scrape_meetup_events() orchestrator: links browser,
│   │                                   # filter, deduplicator, JSON writer, and MongoDB upsert
│   │
│   ├── sources/                        # Platform-specific scraping adapters
│   │   ├── __init__.py                 # Source exports
│   │   ├── base.py                     # EventSource abstract base class contract
│   │   └── meetup.py                   # MeetupSource (Playwright browser automation & GraphQL parser)
│   │
│   ├── storage/                        # Alternative / utility storage handlers
│   │   ├── __init__.py                 # Storage module export
│   │   ├── mongo.py                    # MongoStorage utility class (legacy/direct storage helper)
│   │   └── sync_events.py              # CLI script to load events.json and sync into MongoDB
│   │
│   └── data/                           # Package-level data storage
│       └── events.json                 # Package copy of scraped events snapshot
│
├── frontend/                           # Next.js web application
│   ├── .env.local                      # Frontend environment variables (NEXT_PUBLIC_API_URL)
│   ├── package.json                    # Node dependencies (Next.js 16, React 19, Tailwind CSS 4)
│   ├── tsconfig.json                   # TypeScript configuration
│   ├── next.config.ts                  # Next.js configuration
│   └── src/
│       ├── app/
│       │   ├── globals.css             # Tailwind CSS imports and theme configuration
│       │   ├── layout.tsx              # Root HTML shell with header navigation, dark theme, footer
│       │   └── page.tsx                # Main Discover page (fetch, state, search bar, category filter, grid)
│       ├── components/
│       │   └── EventCard.tsx           # Reusable UI card displaying single event metadata
│       └── types/
│           └── event.ts                # TypeScript interface matching Event schema
│
└── Test & Validation Scripts:
    ├── test_api.py                     # Unit & integration tests for FastAPI /events endpoint
    ├── test_database.py                # Unit tests for MongoDB layer (upsert, idempotency, expiration)
    ├── test_scraper.py                 # Unit tests for parsing, tech classifier, and deduplicator
    ├── test_db_connection.py           # Diagnostic script to test live MongoDB Atlas ping
    └── test_insert_one.py              # Diagnostic script to test single document insertion to Atlas
```

### Detailed Breakdown of Key Files and Why They Exist:

| File / Folder | What It Does | Why It Exists | Who Uses It |
| :--- | :--- | :--- | :--- |
| `main.py` | Top-level entry point | Allows running `python main.py` directly from project root | Developers / CLI users; invokes `eventscout/scrapers/meetup_scraper.py` |
| `api/main.py` | FastAPI application | Exposes the HTTP REST API layer between MongoDB and frontend | Uvicorn server; consumed by Next.js frontend |
| `eventscout/sources/meetup.py` | Meetup browser automation & GraphQL extractor | Contains `MeetupSource` class and `parse_meetup_node` parsing function | Called by `meetup_scraper.py` |
| `eventscout/scrapers/meetup_scraper.py` | End-to-end pipeline coordinator | Connects browser scraping, filtering, deduplicating, JSON saving, and MongoDB upserting | Called by `main.py` and direct execution |
| `eventscout/database/mongodb.py` | Database repository class | Connects to MongoDB Atlas, builds indexes, performs bulk upserts, and filters expired records | Used by `meetup_scraper.py` and `api/main.py` |
| `eventscout/filters/technical_filter.py` | Rule-based classifier | Categorizes events into tech fields (AI/ML, Cloud, Web, etc.) and eliminates non-tech noise | Used by `meetup_scraper.py` |
| `eventscout/processors/deduplicator.py` | Deduplication engine | Eliminates identical events within a scrape run using exact IDs and composite fuzzy keys | Used by `meetup_scraper.py` |
| `eventscout/models/event.py` | Python dataclass model | Establishes the standard, canonical event format across all platforms | Used everywhere across the Python backend |
| `frontend/src/app/page.tsx` | Main web page | Renders header, search bar, filter buttons, loading skeleton, error message, and event grid | Opened by users in browser |
| `frontend/src/components/EventCard.tsx` | UI card component | Displays an individual event's poster, title, date, location, badges, and link | Rendered by `page.tsx` |
| `frontend/src/types/event.ts` | TypeScript interface | Ensures compile-time type safety when handling event data on the frontend | Imported by `page.tsx` and `EventCard.tsx` |

---

## 4. Meetup Scraper — Deep Explanation

### Browser Automation with Playwright

#### Why Playwright?
Meetup.com is a modern Single Page Application (SPA) built using React. When a web client visits `https://www.meetup.com/find/?categoryId=546&source=EVENTS`, the server does **not** return raw HTML filled with event cards. Instead, it returns an empty HTML skeleton and a bundle of JavaScript files. The client browser then executes the JavaScript, which dynamically makes GraphQL network requests to fetch the actual event listings.

If you used a traditional HTTP client like `requests.get()` or `httpx.get()`, you would only receive the empty HTML skeleton without any events. Furthermore, Meetup employs Cloudflare bot protection and anti-scraping defenses that block simple automated HTTP requests.

#### What Happens When Chromium Starts?
In [eventscout/sources/meetup.py](file:///c:/Keerthu/KL/NerdyGeeks/EventScout_project/EventScout/eventscout/sources/meetup.py#L172-L186):
```python
with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"],
    )
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 800},
    )
    page = context.new_page()
```
* Playwright launches a real Chromium binary in the background.
* **`headless=True`** means Chromium runs without opening a visible desktop window. It renders pages, executes JavaScript, and makes network calls completely in memory, consuming significantly less CPU and RAM.
* **Context & User Agent:** Meetup checks the HTTP `User-Agent` header. Playwright assigns a real modern Windows Chrome user-agent string and a 1280x800 viewport so Meetup treats the connection like an authentic desktop browser.

---

### GraphQL and the `gql2` Endpoint

#### What is GraphQL?
GraphQL is a query language for APIs. In traditional REST APIs, the backend defines what data is returned for each URL endpoint (e.g. `/api/events/123`). In GraphQL, the client sends a query specifying **precisely** which fields it needs:
```graphql
query getEvents {
  events {
    title
    dateTime
    group { name }
  }
}
```
Meetup uses GraphQL because it allows their frontend to fetch diverse relational data (event info, organizer info, venue, pricing, photos) in a single HTTP POST request rather than querying five separate REST endpoints.

#### What is the `gql2` Endpoint?
Meetup routes all internal frontend GraphQL requests to `https://www.meetup.com/gql2`. Every time you browse events, scroll down, or switch categories on Meetup, your browser sends an HTTP POST request to `/gql2`.

#### Why Intercept Network Responses?
Instead of attempting to scrape fragile CSS selectors or HTML elements (like `<div class="event-card">`), which change whenever Meetup updates its website styles, EventScout **intercepts the raw JSON data Meetup's backend sends to its own frontend**. 

By listening on the network layer:
1. We get clean, structured JSON with full detail.
2. We get fields that might not even be rendered visually in the DOM.
3. Our scraper is immune to CSS class name changes.

---

### Automatic Persisted Queries (APQ)

#### What is APQ?
GraphQL query strings can be huge (several kilobytes of nested text). To save bandwidth and speed up request handling, modern GraphQL servers use **Automatic Persisted Queries (APQ)**.

Instead of sending the entire 2,000-character query text over the wire on every scroll, the client sends a cryptographic **SHA-256 hash** of the query:
```json
{
  "operationName": "recommendedEventsWithSeriesQuery",
  "variables": { "first": 20, "lat": 17.385, "lon": 78.486 },
  "extensions": {
    "persistedQuery": {
      "version": 1,
      "sha256Hash": "4a73b9e4a8c9837a281897d8b5c9284..."
    }
  }
}
```
If the Meetup server already has that hash cached, it executes the query immediately.

#### Why We Let Meetup's Frontend Make the Request
Reverse-engineering Meetup's APQ query hashes and authentication cookies is difficult because Meetup frequently rotates these hashes across deployments.

EventScout uses a much more resilient approach:
1. We navigate a real headless Chromium browser to the Meetup page.
2. Meetup's own compiled JavaScript generates the exact APQ hash, session tokens, and variables.
3. Playwright simply stands by and intercepts the HTTP 200 response that comes back!

---

### Response Interception Walkthrough

In [eventscout/sources/meetup.py](file:///c:/Keerthu/KL/NerdyGeeks/EventScout_project/EventScout/eventscout/sources/meetup.py#L187-L209):

```text
1. Playwright opens Chromium and attaches response listener
         │
         ▼ page.on("response", handle_response)
2. page.goto("https://www.meetup.com/find/?categoryId=546&source=EVENTS")
         │
         ▼ Meetup frontend executes JS and sends POST to /gql2
3. Meetup backend sends back HTTP 200 with JSON payload
         │
         ▼ handle_response(response) fires
4. Check if "gql2" in response.url and response.status == 200
         │
         ▼ Check if body contains "edges" and "totalCount"
5. Parse JSON payload: data.result.edges -> array of { node: { ... } }
         │
         ▼ Deduplicate raw nodes by node["id"] into raw_nodes list
6. page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
         │
         ▼ Trigger next batch (infinite scroll pagination up to max_pages)
7. Browser closes -> raw_nodes passed to parse_meetup_node()
```

#### Actual Code in `MeetupSource.collect_events`:
```python
def handle_response(response: Response) -> None:
    nonlocal has_next_page
    if "gql2" in response.url and response.status == 200:
        try:
            body_text = response.text()
            if "edges" in body_text and "totalCount" in body_text:
                payload = json.loads(body_text)
                result = payload.get("data", {}).get("result", {})
                page_info = result.get("pageInfo", {})
                has_next_page = page_info.get("hasNextPage", False)

                edges = result.get("edges", [])
                for edge in edges:
                    node = edge.get("node") if isinstance(edge, dict) else None
                    if node and isinstance(node, dict):
                        node_id = node.get("id") or node.get("eventUrl") or len(raw_nodes)
                        if node_id not in seen_node_ids:
                            seen_node_ids.add(node_id)
                            raw_nodes.append(node)
        except Exception:
            pass

page.on("response", handle_response)
```

---

## 5. Event Data Extraction

In [eventscout/sources/meetup.py](file:///c:/Keerthu/KL/NerdyGeeks/EventScout_project/EventScout/eventscout/sources/meetup.py#L31-L146), the function `parse_meetup_node(node: Dict[str, Any], index: int = 0) -> Optional[Event]` transforms the raw GraphQL node dictionary into our standardized `Event` dataclass instance.

Here is the exact field-by-field trace:

### Field Extraction Traceability Table

| EventScout Field | Meetup GraphQL Source Path | Extraction Logic & Fallbacks | Example Result |
| :--- | :--- | :--- | :--- |
| `title` | `node["title"]` | Required string. Stripped of whitespace. If missing or blank, entire event is rejected as malformed. | `"From Embeddings to Search: Inside MongoDB Atlas Vector Search"` |
| `event_url` | `node["eventUrl"]` | Required string. Canonical URL to event page on Meetup. If missing, node rejected. | `"https://www.meetup.com/mongodb-usergroup-hyderabad/events/316348822/"` |
| `date_time` | `node["dateTime"]` | Required ISO 8601 string. Converted to Python `datetime` object (`fromisoformat`). Supports trailing `'Z'` or offset `+05:30`. | `datetime(2026, 9, 26, 10, 0, 0, tzinfo=...)` |
| `organizer` | `node["group"]["name"]` | Required string. The hosting community or meetup group name. | `"Hyderabad MongoDB User Group"` |
| `poster_image_url`| `node["featuredEventPhoto"]["highResUrl"]` | Checks `featuredEventPhoto.highResUrl` first. If `None`, falls back to `displayPhoto.highResUrl`. If both missing, returns `None`. | `"https://secure.meetupstatic.com/photos/event/d/9/5/highres_535923477.jpeg"` |
| `mode_location` | `node["eventType"]` and `node["venue"]` | If `eventType == "ONLINE"`, set to `"Online"`. Otherwise, reads `venue.city` or `venue.name` and formats as `"Offline - <city or name>"`. | `"Offline - Hyderabad"` |
| `city` | `node["venue"]["city"]` | Venue city name string or `None`. | `"Hyderabad"` |
| `country` | `node["venue"]["country"]` | Venue country code string or `None`. | `"in"` |
| `is_free` | `node["feeSettings"]` | If `node["feeSettings"] is None`, event is free (`is_free = True`). | `True` |
| `price_amount` | `node["feeSettings"]["amount"]` | Converted safely to `float(amount)` or `None`. | `None` (or `25.50` if paid) |
| `price_currency` | `node["feeSettings"]["currency"]` | Currency code string (e.g. `"USD"`, `"INR"`) or `None`. | `None` (or `"INR"`) |
| `source` | Hardcoded literal | Set to `"meetup"` by the scraper. | `"meetup"` |
| `source_event_id` | `node["id"]` | Unique identifier assigned by Meetup (e.g. `"316348822"`). | `"316348822"` |
| `registration_url`| `node["eventUrl"]` | Same as `event_url` for Meetup. | `"https://www.meetup.com/..."` |
| `description` | `node["description"]` | Full Markdown/plain text event details and speaker agenda. | `"### From Embeddings to Search..."` |
| `is_technical` | Assessed by `TechnicalEventFilter` | Boolean indicating whether title/description matched technical taxonomy keywords. | `True` |
| `categories` | Assessed by `TechnicalEventFilter` | Array of matched technical category labels. | `["Artificial Intelligence & Machine Learning", "Data & Databases"]` |
| `scraped_at` | Auto-generated timestamp | UTC ISO 8601 string of the exact moment the event was parsed. | `"2026-09-08T08:18:56.601713Z"` |

---

## 6. Normalization

### What Does "Normalization" Mean?
Different event platforms represent data in drastically different ways:
* Meetup calls the organizer `group.name`. Devpost calls it `hackathon.organization`. Eventbrite calls it `organizer.name`.
* Meetup represents event mode as an enum `eventType: "ONLINE"`. Other sites use a boolean `is_virtual: true`.
* Meetup stores pricing in a nested dictionary `feeSettings: { amount: "10.00", currency: "USD" }`. Other sites store a string `"Free"` or `ticket_types: [{ price: 1000 }]`.

If the frontend had to understand each platform's proprietary data structure, your React components would be flooded with messy `if/else` checks:
```javascript
// BAD PRACTICE: Fragile, un-normalized code
const organizer = event.group?.name || event.organization || event.host_name;
const isOnline = event.eventType === "ONLINE" || event.is_virtual === true;
```

**Normalization** is the process of converting all incoming external data structures into one single, standardized format called the **EventScout Canonical Event Model**.

```text
┌─────────────────────────┐
│ Meetup GraphQL Node     │
├─────────────────────────┤
│ node.group.name         │──┐
│ node.eventType          │  │
│ node.feeSettings        │  │
└─────────────────────────┘  │
                             ▼
┌─────────────────────────┐     ┌────────────────────────────────────┐
│ Devpost Hackathon Data  │     │ Canonical EventScout Event Model   │
├─────────────────────────┤────▶│ (eventscout/models/event.py)       │
│ hackathon.organization  │     ├────────────────────────────────────┤
│ hackathon.is_online     │     │ organizer:        str              │
└─────────────────────────┘  ▲  │ mode_location:    str              │
                             │  │ is_free:          bool             │
┌─────────────────────────┐  │  │ price_amount:     Optional[float]  │
│ Eventbrite Ticket API   │  │  │ price_currency:   Optional[str]    │
├─────────────────────────┤──┘  │ categories:       List[str]        │
│ ticket_classes.cost     │     └────────────────────────────────────┘
└─────────────────────────┘
```

### The Actual EventScout Schema
Below is a real document from [data/events.json](file:///c:/Keerthu/KL/NerdyGeeks/EventScout_project/EventScout/data/events.json#L2-L24) showing the normalized structure:

```json
{
  "title": "From Embeddings to Search: Inside MongoDB Atlas Vector Search",
  "event_url": "https://www.meetup.com/mongodb-usergroup-hyderabad/events/316348822/",
  "date_time": "2026-09-26T10:00:00+05:30",
  "organizer": "Hyderabad MongoDB User Group",
  "source": "meetup",
  "mode_location": "Offline - Hyderabad",
  "city": "Hyderabad",
  "country": "in",
  "poster_image_url": "https://secure.meetupstatic.com/photos/event/d/9/5/highres_535923477.jpeg",
  "description": "### From Embeddings to Search: Inside MongoDB Atlas Vector Search\n\nJoin MongoDB User Group Hyderabad...",
  "is_free": true,
  "price_amount": null,
  "price_currency": null,
  "source_event_id": "316348822",
  "registration_url": "https://www.meetup.com/mongodb-usergroup-hyderabad/events/316348822/",
  "is_technical": true,
  "categories": [
    "Artificial Intelligence & Machine Learning",
    "Data & Databases"
  ],
  "scraped_at": "2026-09-08T08:18:56.601713Z"
}
```

---

## 7. MongoDB

### MongoDB Fundamentals in EventScout

* **What is MongoDB?** A document-oriented NoSQL database that stores data in flexible, JSON-like records called BSON (Binary JSON).
* **What is MongoDB Atlas?** MongoDB's managed cloud service. Instead of running a database server on your local machine, Atlas hosts the database in the cloud (AWS/GCP/Azure) with automatic backups, high availability, and security.
* **Database Name:** `eventscout` (configured via `MONGODB_DATABASE` in `.env`).
* **Collection Name:** `events` (configured in [eventscout/database/mongodb.py](file:///c:/Keerthu/KL/NerdyGeeks/EventScout_project/EventScout/eventscout/database/mongodb.py#L37)).

### Core MongoDB Concepts Explained with EventScout:

| MongoDB Concept | Explanation | EventScout Concrete Example |
| :--- | :--- | :--- |
| **Database** | A top-level container holding collections of data. | `eventscout` database in MongoDB Atlas. |
| **Collection** | A grouping of related documents (equivalent to a table in SQL). | The `events` collection storing technical meetups. |
| **Document** | A single record stored in JSON/BSON format (equivalent to a row in SQL). | One specific event record (e.g. the OWASP Hyderabad Meetup). |
| **Field** | A key-value pair within a document (equivalent to a column in SQL). | `"organizer": "OWASP Hyderabad Chapter"`. |
| **`_id`** | A special 12-byte identifier automatically assigned by MongoDB as the primary key of every document. | `ObjectId("66dae67890abcdef12345678")`. |
| **Index** | A special data structure that allows the database to find matching documents instantly without scanning the entire collection. | `idx_date_time_asc` on `{"date_time": 1}` for fast chronological sorting. |
| **Unique Index** | An index that guarantees no two documents can have the exact same value for the indexed fields. | `idx_source_event_unique` on `[("source", 1), ("source_event_id", 1)]`. |

---

### How EventScout Connects and Queries MongoDB

The connection code lives in [eventscout/database/mongodb.py](file:///c:/Keerthu/KL/NerdyGeeks/EventScout_project/EventScout/eventscout/database/mongodb.py#L28-L76):

```python
class EventDatabase:
    def __init__(self, uri: Optional[str] = None, db_name: Optional[str] = None, collection_name: str = "events"):
        self.uri = uri or os.getenv("MONGODB_URI")
        self.db_name = db_name or os.getenv("MONGODB_DATABASE", "eventscout")
        self.collection_name = collection_name
        self._client: Optional[MongoClient] = None
        self._collection: Optional[Collection] = None

    def get_collection(self) -> Collection:
        if self._collection is None:
            # Connect to Atlas with 20 second timeout
            self._client = MongoClient(self.uri, serverSelectionTimeoutMS=20000)
            self._db = self._client[self.db_name]
            self._collection = self._db[self.collection_name]

            # Enforce compound unique identity index
            self._collection.create_index(
                [("source", 1), ("source_event_id", 1)],
                unique=True,
                name="idx_source_event_unique",
                background=True,
            )

            # Enforce date sorting index
            self._collection.create_index(
                [("date_time", 1)],
                name="idx_date_time_asc",
                background=True,
            )
        return self._collection
```

#### How Queries are Performed:
In `EventDatabase.get_upcoming_events()`:
```python
# Query all documents sorted chronologically by date_time ascending
raw_docs = list(col.find().sort("date_time", 1))
```
The database uses the `idx_date_time_asc` index to fetch and sort events in milliseconds.

---

## 8. Duplicate Prevention and Upsert

### The Problem of Repeated Scrapes
Web scrapers are designed to run repeatedly (e.g. every 6 hours or once a day). If a scraper simply ran `insert_one()` every time it found an event:
* Run 1 (Monday): Inserts 20 events.
* Run 2 (Tuesday): Inserts the same 20 events. Now you have 40 events with duplicates.
* Run 3 (Wednesday): Inserts the same 20 events. Now you have 60 events!

### How EventScout Solves This: The "Upsert" Pattern
"Upsert" is a combination of **UPDATE** and **INSERT**.
* If a document already exists matching our unique identity, MongoDB **updates** its fields (updating ticket prices, descriptions, or venue changes).
* If no matching document exists, MongoDB **inserts** it as a brand new document.

```text
Scraper Discovers Event:
source = "meetup", source_event_id = "316348822"
                          │
                          ▼
            MongoDB checks unique index
       (source = "meetup", source_event_id = "316348822")
                          │
             ┌────────────┴────────────┐
             ▼                         ▼
   Document DOES NOT exist    Document ALREADY exists
             │                         │
             ▼                         ▼
          INSERT                    UPDATE
   (Inserts fresh doc        (Updates fields like
   with "created_at")        title, venue, price)
```

### The Identity Key and Fallback
In [eventscout/database/mongodb.py](file:///c:/Keerthu/KL/NerdyGeeks/EventScout_project/EventScout/eventscout/database/mongodb.py#L145-L150):
```python
# Stable identity: source + source_event_id (fallback to event_url)
event_id = event.source_event_id or event.event_url
filter_query = {
    "source": event.source,
    "source_event_id": event_id,
}
```
* Every platform has an immutable ID. For Meetup, it is the numeric event ID (e.g. `"316348822"`).
* If a future platform does not provide a numeric ID, EventScout uses the normalized `event_url` as a rock-solid fallback.

### Bulk Write Upsert Implementation
Rather than sending 30 separate network requests to MongoDB Atlas, EventScout bundles all operations into a single **bulk write**:

```python
operations.append(
    UpdateOne(
        filter_query,
        {
            "$set": doc,  # Overwrites updated fields
            "$setOnInsert": {
                "created_at": datetime.now(timezone.utc).isoformat()  # Only written on first insertion!
            },
        },
        upsert=True,  # Tells MongoDB to insert if missing
    )
)
result = col.bulk_write(operations, ordered=False)
```
* **`$set`:** Updates all event fields to the latest scraped values.
* **`$setOnInsert`:** Sets the `created_at` timestamp **only** when the event is inserted for the first time. On subsequent updates, `created_at` remains untouched!

---

## 9. Expired Event Handling

### Why Expired Events Must Be Managed Carefully
Developers only want to discover **upcoming** events. Showing an event that took place yesterday is a poor user experience.

However, **an event should NEVER be deleted from the database simply because it was missing from a single scraper run**. 
* Meetup's search page might temporarily experience pagination errors or rate limits.
* If a scraper run only fetched 2 pages instead of 4, deleting everything not seen would wipe out valid future events!
* **Rule in EventScout:** An event is ONLY removed when its actual scheduled date and time has passed.

### How Event Time is Checked
In [eventscout/database/mongodb.py](file:///c:/Keerthu/KL/NerdyGeeks/EventScout_project/EventScout/eventscout/database/mongodb.py#L79-L104):
```python
@staticmethod
def is_expired(date_time_val: Any, reference_time: Optional[datetime] = None) -> bool:
    if reference_time is None:
        reference_time = datetime.now(timezone.utc)
    elif reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=timezone.utc)

    if isinstance(date_time_val, datetime):
        dt = date_time_val
    else:
        s = str(date_time_val).strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)

    # Ensure timezone awareness
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt <= reference_time
```

### Timezone Safety
Meetup events in India include a timezone offset (`+05:30`). Comparing a timezone-aware datetime with a timezone-naive datetime in Python causes a `TypeError`. EventScout normalizes all timestamps to UTC before comparing:
```python
if dt <= reference_time:
    # Event has already ended!
```

### Three-Layer Defense Against Expired Events:
1. **At Scraper Batch Level (`meetup_scraper.py:L184-L189`):** Expired events scraped from the web are filtered out before being saved to `events.json`.
2. **At Database Sync Level (`mongodb.py:L105-L123`):** Before upserting new events, `db.delete_expired_events()` scans the MongoDB collection and deletes documents whose `date_time` has elapsed.
3. **At API Query Level (`mongodb.py:L186-L189`):** When `/events` is called, `get_upcoming_events()` double-checks every document against the current system clock so no past event is ever returned to the frontend.

---

## 10. JSON vs MongoDB

In the current EventScout codebase, you will notice both a JSON file ([data/events.json](file:///c:/Keerthu/KL/NerdyGeeks/EventScout_project/EventScout/data/events.json)) and MongoDB Atlas storage.

```text
Meetup Scraper Pipeline (eventscout/scrapers/meetup_scraper.py)
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
┌──────────────────┐ ┌──────────────────┐
│ data/events.json │ │  MongoDB Atlas   │
│  (Debug Snapshot)│ │ (Source of Truth)│
└──────────────────┘ └──────────────────┘
         │                   │
         ▼                   ▼
Local Inspection      FastAPI Backend (/events)
  & Offline Dev              │
                             ▼
                      Next.js Frontend
```

### Clear Answers on Their Roles:

#### 1. Is JSON currently the source of truth?
**No.** `events.json` is not the source of truth for the active application.

#### 2. Is MongoDB currently the source of truth?
**Yes.** When the Next.js frontend calls the FastAPI backend (`GET /events`), FastAPI queries MongoDB Atlas directly ([api/main.py:L43-L45](file:///c:/Keerthu/KL/NerdyGeeks/EventScout_project/EventScout/api/main.py#L43-L45)). It does not read `events.json`.

#### 3. Why are we keeping JSON?
* **Instant Inspection:** Developers can open `data/events.json` in VS Code to immediately see what fields Meetup returned without logging into the MongoDB Atlas web console.
* **Offline Development & Fixtures:** Unit tests can load mock data directly from JSON without needing an active internet connection to Atlas.
* **Safety Net / Backup:** If MongoDB credentials fail or Atlas network access is blocked, scraped events are not lost—they remain saved on disk in `data/events.json`.

#### 4. Is JSON needed in the final production architecture?
**No.** In a production cloud deployment (e.g. running on AWS ECS, Docker, or Render with ephemeral filesystems), scrapers will write directly to MongoDB Atlas. `events.json` will only remain as an optional debug flag.

---

## 11. FastAPI

### What is FastAPI and Why Do We Use It?
FastAPI is a modern, high-performance web framework for building APIs with Python.
* It is based on standard Python type hints.
* It is asynchronous and extremely fast.
* It automatically produces interactive OpenAPI Swagger documentation at `http://localhost:8000/docs`.

### Where the FastAPI Application Starts
The API service lives in [api/main.py](file:///c:/Keerthu/KL/NerdyGeeks/EventScout_project/EventScout/api/main.py#L11-L25):

```python
app = FastAPI(
    title="EventScout API",
    description="API to serve technical events from MongoDB for the EventScout platform.",
    version="1.0.0",
)

# CORS configuration allowing the Next.js frontend to make requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)
```

### Current API Routes

#### 1. `GET /health`
* Returns: `{"status": "ok", "message": "EventScout API is running"}`
* Used by deployment platforms and developers to verify that the server is up and responsive.

#### 2. `GET /events`
* Retrieves all upcoming events from MongoDB Atlas.
* Filters out any expired events.
* Serializes MongoDB-specific data types (converting `ObjectId` to string and `datetime` to ISO strings).
* Returns an array of clean event objects.

### The Complete Request-Response Journey

```text
1. User loads http://localhost:3000 in Chrome
         │
         ▼
2. Next.js runs useEffect() in frontend/src/app/page.tsx
   fetch("http://localhost:8000/events")
         │
         ▼
3. FastAPI receives HTTP GET /events in api/main.py
         │
         ▼
4. api/main.py invokes db = EventDatabase()
   calls db.get_upcoming_events() in eventscout/database/mongodb.py
         │
         ▼
5. PyMongo queries MongoDB Atlas:
   col.find().sort("date_time", 1)
         │
         ▼
6. MongoDB Atlas returns list of BSON documents
         │
         ▼
7. db.get_upcoming_events() loops over documents:
   - Skips any event where is_expired(doc["date_time"]) == True
   - doc["id"] = str(doc["_id"]) (converts ObjectId to string)
   - doc["date_time"] = doc["date_time"].isoformat() (if datetime object)
         │
         ▼
8. FastAPI serializes the list into HTTP 200 JSON response
         │
         ▼
9. Next.js receives JSON, calls setEvents(data), renders <EventCard />
```

---

## 12. Next.js Frontend

### Current Frontend Architecture

The frontend is built using **Next.js 16 (App Router)**, **React 19**, and **Tailwind CSS 4**. It lives in the `frontend/` directory.

### Key Components and Files:

#### 1. `frontend/src/app/page.tsx` (The Discover Page)
This is the central client-side page (`"use client"`). It manages four key pieces of React state:
* `events`: Array of `Event` objects loaded from the FastAPI backend.
* `loading`: Boolean that is `true` while waiting for the API response.
* `error`: String containing an error message if the backend is unreachable.
* `searchQuery` & `selectedCategory`: User input state for live filtering.

#### 2. `frontend/src/components/EventCard.tsx` (The Event Card)
A component that receives a single `event: Event` prop and displays:
* **Event Poster Image:** Uses Next.js `<Image>` with `fill` and responsive `sizes`. If no image URL was provided by Meetup, it renders a subtle placeholder icon.
* **Price Badge:** An absolute-positioned pill in the top-right corner displaying `"Free"` or the formatted price (e.g. `USD 25.50`).
* **Formatted Date:** Formats the ISO date string into a user-friendly format (e.g. `"Sat, Sep 26, 10:00 AM"`).
* **Title & Organizer:** Two-line clamped title and host group name with icon.
* **Location Mode:** Shows `"Online"` or `"Offline - Hyderabad"` with pin icon.
* **Category Badges:** Tags like `"AI & Machine Learning"` and `"Cloud & DevOps"`.
* **Action Button:** A `"View Event"` button linking directly to the registration page in a new tab.

---

### The Three Content States

#### 1. Loading State (Skeleton Screen)
When `loading === true`, instead of an empty white screen or a basic spinner, Next.js displays an animated skeleton grid:
```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
  {[...Array(8)].map((_, i) => (
    <div key={i} className="bg-white dark:bg-gray-800 rounded-xl h-[420px] animate-pulse flex flex-col">
      <div className="h-48 bg-gray-200 dark:bg-gray-700 rounded-t-xl w-full"></div>
      ...
    </div>
  ))}
</div>
```
This gives users instant visual feedback that content is loading.

#### 2. Error State
If FastAPI is not running or MongoDB fails, `error` is populated and a helpful alert is displayed:
```text
┌─────────────────────────────────────────────────────────────┐
│ ⚠ Unable to load events.                                    │
│ Failed to fetch from backend.                               │
│ Make sure to start the backend with:                        │
│ uvicorn api.main:app --reload                               │
└─────────────────────────────────────────────────────────────┘
```

#### 3. Empty State
If the user searches for a term that doesn't exist (e.g. `"Quantum Fortran"`), an empty state appears with an icon and a `"Clear all filters"` button.

---

## 13. End-to-End Example: The Journey of One Event

Let's follow one real event currently in the database:  
**"From Embeddings to Search: Inside MongoDB Atlas Vector Search"**

```text
Step 1: Meetup Web Platform
An organizer in Hyderabad creates an event on Meetup.com.
Meetup's backend assigns ID "316348822".
                             │
                             ▼
Step 2: Playwright Chromium Browser
The scraper runs. Playwright launches Chromium headless and loads:
https://www.meetup.com/find/?categoryId=546&source=EVENTS
Meetup's JavaScript issues an APQ request to /gql2.
                             │
                             ▼
Step 3: Response Interception
Playwright's handle_response listener intercepts the HTTP 200 response.
It finds the edge node containing:
{
  "id": "316348822",
  "title": "From Embeddings to Search: Inside MongoDB Atlas Vector Search",
  "dateTime": "2026-09-26T10:00:00+05:30",
  "group": { "name": "Hyderabad MongoDB User Group" },
  "venue": { "city": "Hyderabad", "country": "in" },
  "feeSettings": null
}
                             │
                             ▼
Step 4: Extraction & Normalization
parse_meetup_node() extracts each field and validates:
- title: "From Embeddings to Search: Inside MongoDB Atlas Vector Search"
- organizer: "Hyderabad MongoDB User Group"
- is_free: True (feeSettings is None)
- mode_location: "Offline - Hyderabad"
Creates an Event dataclass instance.
                             │
                             ▼
Step 5: Filtering & Classification
TechnicalEventFilter analyzes title and description:
- Matches "embeddings", "vector search" -> "Artificial Intelligence & Machine Learning"
- Matches "mongodb", "search" -> "Data & Databases"
Event is approved as technical (is_technical = True).
                             │
                             ▼
Step 6: Deduplication & Expiration Check
EventDeduplicator checks seen IDs -> First time seen, approved.
EventDatabase.is_expired("2026-09-26...") -> Scheduled for future, approved.
                             │
                             ▼
Step 7: MongoDB Atlas Storage
EventDatabase.upsert_events() executes an UpdateOne bulk operation:
Filter: {"source": "meetup", "source_event_id": "316348822"}
Since it does not exist yet, MongoDB inserts the document and sets created_at.
                             │
                             ▼
Step 8: FastAPI Endpoint
FastAPI server receives GET /events.
db.get_upcoming_events() reads the document from MongoDB Atlas.
Converts ObjectId("...") to string "id", converts datetime to ISO string.
Returns the event in the JSON array.
                             │
                             ▼
Step 9: Next.js Frontend
DiscoverPage fetch("http://localhost:8000/events") completes.
setEvents([..., event, ...]) updates React state.
                             │
                             ▼
Step 10: Event Card on Screen
EventCard renders:
- Poster image: High-res Meetup banner
- Date: "Sat, Sep 26, 10:00 AM"
- Badge: "Free"
- Title: "From Embeddings to Search: Inside MongoDB Atlas Vector Search"
- Organizer: "Hyderabad MongoDB User Group"
- Mode: "Offline - Hyderabad"
- Tags: ["Artificial Intelligence & Machine Learning", "Data & Databases"]
- Button: "View Event" linking to meetup.com/.../316348822/
```

---

## 14. Important Programming Concepts Used in EventScout

| Concept | What It Means Generally | Where It Appears in EventScout | Why We Need It |
| :--- | :--- | :--- | :--- |
| **Python** | High-level interpreted programming language known for readable syntax. | Powers the entire scraping pipeline, filtering, models, and FastAPI backend. | Rapid development and vast ecosystem for web automation and data processing. |
| **Playwright** | Modern browser automation framework developed by Microsoft. | `eventscout/sources/meetup.py` | Navigates SPAs, executes JavaScript, and captures dynamic network calls. |
| **async / await** | Language feature allowing non-blocking asynchronous execution. | `api/main.py` (`async def get_events()`) and Next.js React components. | Allows web servers to handle hundreds of concurrent requests without blocking threads. |
| **HTTP Requests** | Standard protocol for transferring web data (GET, POST). | Frontend `fetch()` to FastAPI; Playwright intercepting POST calls to `/gql2`. | Standard communication across frontend, backend, and external platforms. |
| **GraphQL** | Query language for APIs that lets clients request exact data shapes. | Meetup's internal `gql2` API. | Allows Meetup to bundle group, event, venue, and ticket data in single responses. |
| **JSON** | JavaScript Object Notation: lightweight human-readable data format. | `data/events.json`, API payloads, and MongoDB storage format. | Universal data interchange format between Python, MongoDB, and TypeScript. |
| **MongoDB** | Document-oriented NoSQL database storing JSON-like BSON records. | MongoDB Atlas cloud cluster storing the `eventscout.events` collection. | Schema flexibility allows storing diverse event metadata without rigid SQL migrations. |
| **CRUD** | Create, Read, Update, Delete: basic persistent storage operations. | `upsert_events` (Create/Update), `get_upcoming_events` (Read), `delete_expired_events` (Delete). | Complete lifecycle management of event records. |
| **Upsert** | Atomic database operation that updates an existing record or inserts a new one. | `UpdateOne(..., upsert=True)` in `mongodb.py`. | Prevents duplicate records across repeated scraper executions. |
| **Indexes** | B-tree database structures enabling rapid query lookup. | `idx_source_event_unique` and `idx_date_time_asc` in `mongodb.py`. | Guarantees uniqueness and ensures milliseconds-fast date sorting. |
| **FastAPI** | High-performance Python web framework for building REST APIs. | `api/main.py`. | Exposes clean, typed endpoints connecting MongoDB to our web frontend. |
| **REST API** | Architectural style using standard HTTP verbs for web services. | `GET /events` and `GET /health`. | Clear, predictable interface for the frontend to consume. |
| **HTTP GET** | Safe, idempotent HTTP method used to request data from a server. | `fetch('http://localhost:8000/events')`. | Standard web protocol for retrieving listings without mutating server state. |
| **JSON Serialization** | Converting in-memory objects (Python classes, ObjectIds) into JSON text. | `doc["id"] = str(doc["_id"])` and `event.to_dict()`. | Native BSON types like `ObjectId` cannot be transferred over HTTP without string conversion. |
| **React** | Component-based UI library for building interactive interfaces. | `frontend/src/app/page.tsx` and `EventCard.tsx`. | Reusable UI components and declarative state updates. |
| **Next.js** | Production React framework offering App Router, SSR, and bundling. | `frontend/` directory (Next.js 16). | Industry standard full-stack React framework with optimized routing and asset handling. |
| **TypeScript** | Statically typed superset of JavaScript. | `frontend/src/types/event.ts`. | Prevents runtime bugs by verifying property names (`event.title`) at compile time. |
| **API Calls** | Programmatic network requests between frontend and backend. | `fetch(`${apiUrl}/events`)` in `page.tsx`. | Decouples frontend rendering from backend database logic. |
| **Environment Variables**| Key-value configuration pairs kept outside source code. | `.env` (`MONGODB_URI`) and `.env.local` (`NEXT_PUBLIC_API_URL`). | Protects database passwords and allows changing environments without editing code. |
| **Error Handling** | Catching exceptions gracefully to prevent crashes. | `try...except` blocks in scraper, database, and API; error UI in React. | Ensures a database glitch or malformed event doesn't crash the user's screen. |
| **Logging** | Recording operational messages during software execution. | Python `logging` module throughout `eventscout`. | Provides clear terminal diagnostics during scraping and API requests. |
| **Testing** | Automated verification that code behaves according to specification. | `test_scraper.py`, `test_database.py`, `test_api.py`. | Guarantees that changes don't break parsing, deduplication, or API contracts. |

---

## 15. Testing

EventScout has a comprehensive automated test suite located in the project root:

```text
Test Suite Overview:
├── test_scraper.py      (9 unit tests: parsing, regex classification, deduplication)
├── test_database.py     (6 unit tests: upsert logic, idempotency, expiration)
├── test_api.py          (5 unit tests: FastAPI routes, serialization, error states)
├── test_db_connection.py(Integration check: live Atlas cluster ping)
└── test_insert_one.py   (Integration check: single document live insert)
```

### What Each Test Suite Covers:

#### 1. `test_scraper.py`
* **`test_valid_online_event`:** Confirms that online events correctly extract title, URL, date, and set `mode_location = "Online"`.
* **`test_valid_offline_event_with_paid_fee_and_city_fallback`:** Confirms venue name fallback when city is blank, and parses paid fees (`price_amount: 25.50`).
* **`test_missing_optional_fields_resilience`:** Confirms nodes without photos or descriptions still parse cleanly without raising exceptions.
* **`test_malformed_events_skipped`:** Confirms nodes missing critical fields (no title, no URL, invalid date) return `None`.
* **`test_technical_event_detection`:** Tests 7 realistic technical titles (Docker, LLMs, LeetCode, AWS) to confirm they match taxonomy.
* **`test_non_technical_event_rejection`:** Tests non-tech titles (Speed Dating, Yoga, Salsa) to confirm they are rejected.
* **`test_word_boundary_safety`:** Tests tricky edge cases (e.g. `"chair"` containing `"ai"`, `"email"` containing `"ml"`) to confirm regex word boundaries (`\b`) prevent false positives.
* **`test_deduplication_exact_and_composite`:** Verifies that both exact IDs and fuzzy composite signatures (`norm_title::date::norm_organizer`) flag duplicates.
* **`test_multi_batch_aggregation`:** Tests accumulating nodes across multiple simulated scroll batches.

#### 2. `test_database.py`
* **`test_6_stable_identity`:** Verifies that title updates to the same event produce identical identity keys (`meetup:99999`).
* **`test_4_expired_event_detection`:** Verifies that past datetimes return `is_expired() == True`.
* **`test_5_future_event_retention`:** Verifies that future datetimes return `is_expired() == False`.
* **`test_1_new_event_inserted`:** Mocks PyMongo `bulk_write` to confirm new events trigger `upserted_count = 1`.
* **`test_2_existing_event_idempotency`:** Confirms running the same event twice matches without re-inserting.
* **`test_3_existing_event_changed`:** Confirms modified details trigger `modified_count = 1`.
* **`test_4_delete_expired_events_query`:** Confirms `delete_expired_events()` issues `delete_many` targeting only expired IDs.

#### 3. `test_api.py`
* **`test_health_endpoint`:** Confirms `/health` returns HTTP 200 with `status: ok`.
* **`test_get_events_returns_events_and_valid_json`:** Uses FastAPI's `TestClient` to verify `/events` returns a 200 array.
* **`test_serialization_of_mongodb_types`:** Confirms BSON `ObjectId` is converted to a string and `datetime` to ISO format.
* **`test_expired_events_not_returned`:** Confirms past events in the database are filtered out from API responses.
* **`test_empty_database_returns_empty_list`:** Confirms an empty collection returns `[]` without error.

### How to Run the Tests
```powershell
# Run scraper parsing & classification unit tests
.venv\Scripts\python test_scraper.py

# Run database repository unit tests
.venv\Scripts\python -m unittest test_database.py

# Run FastAPI API unit tests
.venv\Scripts\python -m unittest test_api.py
```

### What a Successful Test Means
* All parsing logic handles edge cases without throwing unhandled exceptions.
* The classifier accurately identifies tech topics while rejecting social events.
* Deduplication and upserts are completely idempotent.
* MongoDB types are guaranteed to be serialized safely for frontend consumption.

### Current Limitations of the Tests:
* The tests use **mocking** (`unittest.mock.patch`) for network requests and database interactions. They do not test live Meetup network connections in CI. If Meetup alters its internal GraphQL schema, the mocks will still pass, but the live scraper will need an update.

---

## 16. Running the Project

### Prerequisites
* Windows 10/11 or macOS/Linux
* Python 3.10+ (virtual environment located in `.venv/`)
* Node.js 18+ and npm
* MongoDB Atlas account and cluster

---

### Step 1: MongoDB Atlas Configuration
1. Log into [MongoDB Atlas](https://cloud.mongodb.com).
2. Create a free M0 cluster (e.g. `EventScoutCluster`).
3. Under **Database Access**, create a user (e.g. `eventscout_user`) with read/write permissions.
4. Under **Network Access**, click **Add IP Address** and add your current IP address (or `0.0.0.0/0` for development).
5. In your project root, create a `.env` file (see Section 17 for format).

---

### Step 2: Running the Meetup Scraper & Pipeline
To scrape fresh events from Meetup, classify them, write `data/events.json`, and upsert into MongoDB Atlas:

```powershell
# Activate virtual environment
.venv\Scripts\Activate.ps1

# Run the scraper
python main.py
```

You will see the pipeline progress:
```text
[1/8] Starting Meetup scraper pipeline...
[2/8] Launching headless browser via Playwright...
[3/8] Intercepting GraphQL responses from Meetup (gql2)...
[4/8] Collecting event batches via scroll pagination (max 4 pages)...
[5/8] Raw events discovered: 48 (valid parsed: 46)
[6/8] Filtering technical events...
      Retained 38 technical events (8 non-technical rejected).
[7/9] Deduplicating and validating events...
[8/9] Filtering expired events from current batch...
[9/9] Writing to events.json and synchronizing with MongoDB Atlas...
[SUCCESS] Saved 38 technical events to data/events.json
```

---

### Step 3: Starting the FastAPI Backend
In a terminal, start the Uvicorn server:

```powershell
# Activate virtual environment
.venv\Scripts\Activate.ps1

# Start FastAPI on port 8000 with auto-reload
uvicorn api.main:app --reload --port 8000
```
* **API URL:** `http://localhost:8000/events`
* **Swagger Documentation:** `http://localhost:8000/docs`

---

### Step 4: Starting the Next.js Frontend
In a second terminal, start the Next.js development server:

```powershell
# Change directory to frontend
cd frontend

# Start Next.js development server
npm run dev
```
* **Frontend Web App:** `http://localhost:3000`

Open your browser to `http://localhost:3000` to view the live EventScout Discover page.

---

## 17. Environment Variables

The project uses two environment configuration files. **Never commit secrets, passwords, or actual connection strings to public git repositories.**

### 1. Root Backend `.env` (Project Root)
Read by `python-dotenv` in [eventscout/database/mongodb.py](file:///c:/Keerthu/KL/NerdyGeeks/EventScout_project/EventScout/eventscout/database/mongodb.py#L23):

| Variable Name | Purpose | Example / Format |
| :--- | :--- | :--- |
| `MONGODB_URI` | Standard MongoDB connection string with credentials and cluster hostname. | `mongodb+srv://<username>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority` |
| `MONGODB_DATABASE` | Name of the target MongoDB database. | `eventscout` |

### 2. Frontend `.env.local` (`frontend/.env.local`)
Read by Next.js in [frontend/src/app/page.tsx](file:///c:/Keerthu/KL/NerdyGeeks/EventScout_project/EventScout/frontend/src/app/page.tsx#L20):

| Variable Name | Purpose | Example / Format |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | Base URL of the running FastAPI backend. | `http://localhost:8000` |

---

## 18. Current Limitations

Being completely honest about current limitations is critical before building new features:

1. **Single Data Source:** Only Meetup.com is currently implemented. Major student hackathon platforms (Devpost, Unstop, MLH) and corporate platforms (Microsoft Reactor, Google Developers) are not yet integrated.
2. **Website Structure Fragility:** The scraper relies on Meetup sending GraphQL responses to `/gql2`. If Meetup changes its internal API routes or locks down query interception, the scraper will need maintenance.
3. **Hardcoded Geographic & Mode Filter:** In [eventscout/scrapers/meetup_scraper.py:L155-L160](file:///c:/Keerthu/KL/NerdyGeeks/EventScout_project/EventScout/eventscout/scrapers/meetup_scraper.py#L155-L160), events are currently restricted to `"Online"` or cities containing `"hyderabad"`. Users from other cities cannot yet customize this without editing code.
4. **Manual Scraper Execution:** The scraper runs via CLI command (`python main.py`). There is currently no automated scheduler (e.g. Celery, APScheduler, or GitHub Actions cron) running it periodically.
5. **No Authentication or User Accounts:** The frontend does not have user logins. All visitors see the same global list of events.
6. **No "Save Event" / Bookmarking Persistence:** While the header has a "Saved" navigation link, bookmarks are not yet saved to a database or local storage.
7. **No Notifications:** There is no automated system to alert users via email, Telegram, or Discord when a new hackathon matching their skills is discovered.
8. **Rule-Based vs. AI Classification:** The `TechnicalEventFilter` uses deterministic regex patterns. While very fast and reliable, it lacks semantic awareness (e.g. an event titled "Building a Future-Proof Tech Career" might be missed if it lacks specific tech keywords).

---

## 19. Future Architecture

EventScout was deliberately architected with modular abstractions (like `EventSource` in `eventscout/sources/base.py`) so it can cleanly scale into a multi-platform developer intelligence platform.

### Target Future Architecture:

```text
┌────────────────────────────────────────────────────────────────────────┐
│ MULTI-PLATFORM SOURCE COLLECTORS                                       │
│                                                                        │
│   [EXISTING]      [FUTURE]        [FUTURE]      [FUTURE]    [FUTURE]   │
│   MeetupSource    DevpostSource   GoogleDevs    LumaSource  Unstop     │
│   (Playwright)    (REST/HTML)     (RSS/API)     (API)       (HTML)     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ NORMALIZATION & INGESTION PIPELINE                                     │
│                                                                        │
│   Canonical Event Dataclass (eventscout/models/event.py)  [EXISTING]   │
│         │                                                              │
│         ▼                                                              │
│   Deduplication Engine (Multi-Source Fuzzy Matching)      [EXISTING]   │
│         │                                                              │
│         ▼                                                              │
│   AI Classification & Skill Tagging (LLM / Embeddings)    [FUTURE]     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ PERSISTENT DATA & USER STORAGE (MongoDB Atlas)                         │
│                                                                        │
│   ├── events collection (all normalized active events)     [EXISTING]  │
│   ├── users collection (accounts, skills, interests)       [FUTURE]    │
│   ├── saved_events collection (user bookmarks)             [FUTURE]    │
│   └── notification_rules collection (alert criteria)       [FUTURE]    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ BACKEND & PERSONALIZATION ENGINE (FastAPI)                             │
│                                                                        │
│   ├── GET /events (filter by city, tags, price, date)      [EXISTING]  │
│   ├── POST /auth (JWT user login / signup)                 [FUTURE]    │
│   ├── POST /events/save (bookmark events)                  [FUTURE]    │
│   ├── GET /recommendations (tailored to user skills)       [FUTURE]    │
│   └── Background Notification Worker (Email / Telegram)    [FUTURE]    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                  ┌─────────────────┴─────────────────┐
                  ▼                                   ▼
┌──────────────────────────────────┐ ┌──────────────────────────────────┐
│ CLIENT WEB INTERFACE             │ │ BROWSER EXTENSION & ALERTS       │
│                                  │ │                                  │
│ Next.js 16 Web Application       │ │ Chrome/Brave Browser Extension   │
│ - Discover & Category Filtering  │ │ - One-click "Scout Event"        │
│ - User Profile & Bookmarks       │ │ - Push notifications on new      │
│ - Calendar Sync (.ics export)    │ │   hackathons                     │
└──────────────────────────────────┘ └──────────────────────────────────┘
```

---

## 20. What I Should Understand Before Continuing

Review this checklist to ensure you have complete mastery over the current system before writing any new features:

- [x] **Playwright Automation:** I understand how Playwright launches a headless Chromium instance, uses an authentic User-Agent, and simulates user scrolling.
- [x] **GraphQL Interception:** I understand why Meetup uses `/gql2` with APQ hashes, and why listening to network responses is far more reliable than parsing HTML classes.
- [x] **Data Extraction:** I can trace how raw fields in Meetup's GraphQL node (e.g. `group.name`, `feeSettings`, `venue`) map directly to fields in our `Event` dataclass.
- [x] **Normalization:** I understand why converting all platform-specific formats into a standard `Event` model prevents frontend bugs.
- [x] **MongoDB Collections & Documents:** I understand the role of the `eventscout` database, the `events` collection, and BSON documents.
- [x] **Idempotent Upsert:** I understand how `UpdateOne(..., upsert=True)` updates existing records and inserts new ones using `(source, source_event_id)` as the unique key.
- [x] **Duplicate Prevention:** I understand how exact IDs and composite fuzzy keys (`title::date::organizer`) prevent duplicate cards.
- [x] **Expired Event Handling:** I understand why an event is only deleted when its scheduled time has passed, rather than when it's missing from a single scrape.
- [x] **FastAPI Request Flow:** I understand how `/events` queries MongoDB, serializes BSON types, and returns JSON.
- [x] **Next.js Rendering:** I understand how `page.tsx` fetches from FastAPI, manages loading/error states, and renders responsive `<EventCard />` components.
- [x] **The Complete Data Flow:** I can trace an event from a Meetup POST response all the way to a DOM element on the user's screen.
- [x] **Currently Implemented vs. Planned:** I know exactly what is built today versus what is scheduled for future milestones.

---

## 21. Recommended Next Steps

Here is a prioritized, logical roadmap of what to build next, along with the technical reasoning for each step:

### Step 1: Add City & Attendance Filters to the Frontend & Backend (Priority: High)
* **What:** Add query parameters to FastAPI (`GET /events?city=hyderabad&mode=online`) and dropdown filters on the Next.js Discover page.
* **Why:** Currently, the city filter is hardcoded in the Python scraper. Moving filtering to the API and UI allows users to easily toggle between Online events and in-person events in any city.

### Step 2: Add a Second Source Collector (e.g. Devpost or Luma) (Priority: High)
* **What:** Implement `DevpostSource` inheriting from `EventSource` in `eventscout/sources/base.py`.
* **Why:** EventScout's core value proposition is **multi-source aggregation**. Adding Devpost will immediately introduce high-value student hackathons into the platform and validate that our normalization layer handles non-Meetup schemas seamlessly.

### Step 3: Implement Automated Scheduled Scraping (Priority: Medium)
* **What:** Add an automated background runner (such as GitHub Actions scheduled workflows or APScheduler).
* **Why:** Running `python main.py` manually in a terminal is acceptable for testing, but in production, data must refresh automatically without human intervention.

### Step 4: User Bookmarking & Local Storage / Database Persistence (Priority: Medium)
* **What:** Make the "Saved" tab functional by allowing users to click a bookmark icon on an `EventCard` to save events to `localStorage` (or user accounts in MongoDB).
* **Why:** Users need a place to track events they are interested in attending before the event date arrives.

### Step 5: Calendar Export (.ics / Google Calendar) (Priority: Low)
* **What:** Add an "Add to Calendar" button on `EventCard`.
* **Why:** Frictionless conversion—enables developers to place events directly onto their personal Google or Outlook calendars with one click.
