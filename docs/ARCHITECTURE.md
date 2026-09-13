# EventScout — System Architecture & Engineering Design

EventScout is a personalized technical event and opportunity discovery platform. It continuously discovers events from multiple public sources, normalizes and deduplicates them, ranks them based on host reputation, event quality, and user relevance, and surfaces them through a responsive Next.js frontend, Chrome extension, and automated notifications.

---

## 1. High-Level Architecture Flow

```text
               ┌────────────────────────────────────────────────────────┐
               │                     Public Web                         │
               │   (Meetup, Devfolio, MLH, Unstop, Devpost, GDG, etc)   │
               └───────────────────────────┬────────────────────────────┘
                                           ↓
               ┌────────────────────────────────────────────────────────┐
               │              Gemini AI Source Agent                    │
               │  - Analyzes raw HTML / Network traffic                 │
               │  - Synthesizes dynamic extraction recipes              │
               │  - Submits to Source Registry as PENDING               │
               └───────────────────────────┬────────────────────────────┘
                                           ↓
               ┌────────────────────────────────────────────────────────┐
               │           Admin Source Management & Approval           │
               │  - Live test scraping in isolated sandbox              │
               │  - Admin approval transitions source to ENABLED        │
               └───────────────────────────┬────────────────────────────┘
                                           ↓
               ┌────────────────────────────────────────────────────────┐
               │              Generic Multi-Source Collectors           │
               │  - Playwright Headless Browser                         │
               │  - Static HTML / BeautifulSoup                         │
               │  - REST API & GraphQL Collectors                       │
               │  - Per-source failure isolation & timeout protection   │
               └───────────────────────────┬────────────────────────────┘
                                           ↓
               ┌────────────────────────────────────────────────────────┐
               │          Normalization & Deduplication Pipeline        │
               │  - Date parsing & UTC timezone alignment               │
               │  - Compound key deduplication (source + source_id)     │
               │  - Technical categorization & quality filtering        │
               └───────────────────────────┬────────────────────────────┘
                                           ↓
               ┌────────────────────────────────────────────────────────┐
               │              Intelligent Ranking Engine                │
               │  - Organization Reputation Registry (Tiers & Aliases)  │
               │  - Technical Quality & Format Scoring                  │
               │  - User Interest & Skill Personalization               │
               │  - Urgency & Approaching Deadline Multipliers          │
               │  - "Why Recommended?" Explainability Generator         │
               └───────────────────────────┬────────────────────────────┘
                                           ↓
               ┌────────────────────────────────────────────────────────┐
               │                  MongoDB Atlas Cluster                 │
               │  Collections: events, users, sources, notifications    │
               └───────────────────────────┬────────────────────────────┘
                                           ↓
               ┌────────────────────────────────────────────────────────┐
               │              FastAPI High-Performance API              │
               │  - Parameterized Multi-Criteria Search & Filtering     │
               │  - JWT Bearer Authentication & Admin Guards            │
               │  - Chrome Extension Save & Clipper Endpoints           │
               └───────────────┬────────────────────────┬───────────────┘
                               ↓                        ↓
                 ┌───────────────────────────┐    ┌───────────────────────────┐
                 │       Next.js 15 UI       │    │     Chrome Extension      │
                 │ - Multi-facet filter bar  │    │  (Manifest V3 Clipper)    │
                 │ - Top Picks & Urgent grid │    │ - Schema.org & DOM scan   │
                 │ - Why recommended tooltips│    │ - 1-Click Save to Scout   │
                 └───────────────────────────┘    └───────────────────────────┘
```

---

## 2. Separation of Concerns

A core engineering principle of EventScout is the strict separation between:

1. **Scrapers ≠ Ranking**:
   - Collectors extract raw data from websites. They know nothing about scoring formulas or user profiles.
   - Ranking is handled by a standalone `RankingService` that scores normalized event documents across multiple independent signals.
2. **Scrapers ≠ Personalization**:
   - Scraping runs on an automated schedule for all users.
   - Personalization happens at query time or during notification dispatch, matching user preference vectors (`interests`, `skills`, `preferred_modes`) against event classification vectors.
3. **Scrapers ≠ Notifications**:
   - Scrapers write to the database and identify *newly discovered* IDs.
   - The notification service evaluates user match thresholds and delivers multi-channel alerts (in-app, browser notifications, email digests).

---

## 3. Data Integrity & Idempotency

- **Compound Unique Index**: `(source, source_event_id)` ensures duplicate runs never create duplicate documents.
- **Timezone-Aware Expiration**: Events whose `date_time` has elapsed are automatically filtered out and cleaned up.
- **Audit Logging**: Every scrape run records duration, events found, events inserted, and errors into the structured logger with strict secret sanitization.
