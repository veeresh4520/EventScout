# ⚡ EventScout — Autonomous Technical Opportunity Discovery & Ranking Platform

> **A production-ready, personalized technical event and opportunity discovery platform.** EventScout continuously aggregates hackathons, workshops, and developer conferences across multiple public platforms, normalizes and deduplicates them, ranks them using an intelligent multi-signal scoring engine, and surfaces them through a responsive Next.js web application, Chrome browser extension, and automated notification digests.

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-2.0-009688.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15_App_Router-black.svg)](https://nextjs.org)
[![MongoDB Atlas](https://img.shields.io/badge/Database-MongoDB_Atlas-green.svg)](https://mongodb.com)
[![Chrome Extension](https://img.shields.io/badge/Extension-Manifest_V3-yellow.svg)](https://developer.chrome.com/docs/extensions/mv3/)
[![Tests](https://img.shields.io/badge/Tests-Pytest_Passing-brightgreen.svg)](https://pytest.org)

---

## 🎯 The Problem

Developers, engineering students, and researchers miss high-value hackathons, exclusive workshops, and premier conferences because technical opportunities are scattered across dozens of disjoint platforms (Meetup, Devfolio, Devpost, Unstop, MLH, University portals, and company developer blogs). By the time an opportunity is discovered on social media, registration deadlines have often closed.

## 💡 The Solution

EventScout automates the entire discovery and curation pipeline:
1. **Autonomous Multi-Source Extraction**: Continuously collects opportunities from 15+ verified platforms using generic Playwright, REST, and HTML collectors.
2. **Gemini AI Source Discovery Agent**: Enables users to submit arbitrary event websites. Gemini analyzes the page DOM and network requests to automatically synthesize extraction recipes without custom scraper code.
3. **Multi-Signal Intelligent Ranking Engine**: High-value opportunities from premier technology leaders (Google, AWS, Microsoft, NVIDIA) and top universities (IITs, IIITs, BITS, IISc) are elevated to the top with transparent "Why recommended?" explanations.
4. **User Personalization**: Learns developer interests, skills, and mode preferences to compute individualized opportunity relevance.
5. **Chrome Extension (Manifest V3)**: 1-click bookmarks and extracts structured event metadata from any webpage directly into your dashboard.
6. **Multi-Channel Alerts**: Delivers in-app bell notifications, browser desktop alerts, and scheduled HTML email digests.

---

## 🏗️ System Architecture

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

## ⚡ Intelligent Ranking Engine

Unlike naive scrapers that order events purely by scrape recency, EventScout ranks opportunities using a multi-signal composite formula:

$$\text{Final Score} = 0.35 \cdot S_{\text{org}} + 0.25 \cdot S_{\text{quality}} + 0.25 \cdot S_{\text{user}} + 0.15 \cdot S_{\text{urgency}}$$

- **Organization Reputation ($S_{\text{org}}$)**: Normalized aliases categorized into tiers (`TIER_1_COMPANY`, `TOP_UNIVERSITY`, `MAJOR_DEVELOPER_COMMUNITY`, `TIER_2_COMPANY`, `ESTABLISHED_ORGANIZATION`, `COLLEGE`, `COMMUNITY`).
- **Event Quality ($S_{\text{quality}}$)**: Format bonuses for hackathons, workshops, conferences, and technical depth.
- **User Relevance ($S_{\text{user}}$)**: Cosine/token matching against user profile interests and declared skills.
- **Urgency ($S_{\text{urgency}}$)**: Boosts events with registration closing within 48 hours without overwhelming baseline quality.
- **Explainability**: Cards feature an interactive `✨ Why recommended?` drawer disclosing exact decision signals (e.g., `✓ Hosted by premier tech leader Amazon Web Services`, `✓ Matches your AI and Python interests`).

---

## 💻 Tech Stack

- **Backend**: Python 3.12, FastAPI, Pydantic v2, PyMongo, Playwright, BeautifulSoup4.
- **Frontend**: Next.js 15 (App Router), React 19, TypeScript, Vanilla CSS + Tailwind CSS utilities.
- **Database**: MongoDB Atlas (with compound unique indexes and TTL cleanup).
- **AI / LLM**: Google Gemini 1.5 Flash via official Google Generative AI SDK.
- **Browser Extension**: Google Chrome Manifest V3 (Service Worker + Content Script + Popup).
- **Authentication**: JWT Bearer authentication with bcrypt password hashing and server-enforced admin roles.
- **Deployment**: Multi-stage Dockerfiles, Docker Compose, systemd / background workers.

---

## 🚀 Quickstart & Setup

### 1. Prerequisites
- Python 3.10+ (Recommended: 3.12)
- Node.js 18+ (Recommended: Node 20)
- MongoDB Atlas cluster URI
- Free Google Gemini API Key from [Google AI Studio](https://aistudio.google.com)

### 2. Backend Setup
```bash
# Clone repository
git clone https://github.com/your-username/eventscout.git
cd eventscout

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser binaries
playwright install chromium

# Setup environment variables
cp .env.example .env
# Open .env and add your MONGODB_URI and GEMINI_API_KEY
```

### 3. Run FastAPI Backend
```bash
uvicorn api.main:app --reload --port 8000
```
API documentation is accessible at `http://localhost:8000/docs`.

### 4. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` to view the EventScout interface.

### 5. Automated Background Worker
To run the automated scraper and daily email digest worker:
```bash
python -m eventscout.scheduler
```

---

## 🧩 Chrome Browser Extension (Manifest V3)

1. Open Google Chrome and navigate to `chrome://extensions/`.
2. Toggle **Developer mode** in the top right to **ON**.
3. Click **Load unpacked** in the top-left corner.
4. Select the `extension/` folder inside this repository.
5. Navigate to any hackathon or event page (e.g. `https://devpost.com/hackathons`), click the EventScout icon in your toolbar, and click **Save to EventScout**!

---

## 🧪 Running Automated Tests

EventScout includes an automated test suite verifying ranking formulas, multi-criteria filters, and scraper failure isolation:

```bash
# Run complete test suite
.venv\Scripts\pytest tests/ -v
```

---

## 📁 Repository Structure

```text
eventscout/
├── api/                      # FastAPI REST API
│   ├── auth.py               # JWT Bearer tokens & role dependencies
│   ├── main.py               # App entrypoint, /events query & extension endpoints
│   └── routers/              # auth, users, saved_events, sources, notifications
├── eventscout/               # Core Pipeline & Domain Logic
│   ├── collectors/           # Factory, Playwright, REST, HTML, GraphQL collectors
│   ├── database/             # MongoDB repositories (mongodb.py, source_db.py, user_db.py)
│   ├── models/               # Canonical Event, User, and Source domain models
│   ├── processors/           # Normalizer, Deduplicator
│   ├── services/
│   │   ├── organization_registry.py  # Host tiers, aliases & reputation registry
│   │   ├── ranking_service.py        # Multi-signal ranking & explainability engine
│   │   ├── scraper_service.py        # Dynamic scraper orchestrator with failure isolation
│   │   ├── discovery_service.py      # Gemini AI Source Discovery Agent
│   │   └── notification_service.py   # In-app, browser, and email notifications
│   ├── utils/
│   │   └── logging_config.py         # Structured JSON telemetry & secret sanitization
│   └── scheduler.py          # Background worker process for periodic scraping
├── extension/                # Chrome Extension (Manifest V3)
│   ├── manifest.json         # Extension manifest
│   ├── content.js            # Microdata & DOM scanner
│   ├── background.js         # Service worker & API bridge
│   ├── popup.html/css/js     # Interactive clipper popup
│   └── README.md             # Extension installation guide
├── frontend/                 # Next.js 15 Web Application
│   ├── src/app/              # App router pages (discover, profile, saved, admin/sources)
│   ├── src/components/       # EventCard, Navbar, NotificationDropdown, TestScrapeModal
│   └── src/types/            # TypeScript interfaces
├── docs/                     # Comprehensive Architecture & Demo Documentation
│   ├── ARCHITECTURE.md       # Detailed system design & component boundaries
│   ├── RANKING_ARCHITECTURE.md # Scoring formula, signals & explainability
│   ├── DEMO_GUIDE.md         # 6 interview walkthrough demo scripts
│   └── DEPLOYMENT.md         # Production deployment guide (Docker, PaaS)
├── tests/                    # Pytest test suite
├── Dockerfile                # Backend production Dockerfile
├── docker-compose.yml        # Multi-service compose orchestration
└── README.md                 # Primary project overview
```

---

## 📖 Architecture & Interview Guides

- **[System Architecture](docs/ARCHITECTURE.md)**: Deep dive into the data collection, normalization, and indexing pipeline.
- **[Ranking Architecture](docs/RANKING_ARCHITECTURE.md)**: Mathematical scoring formulas, tier definitions, and explainability mechanisms.
- **[Interview Demo Guide](docs/DEMO_GUIDE.md)**: Step-by-step scripts to demonstrate multi-source collection, autonomous discovery, ranking, extension clipping, and admin monitoring.
- **[Production Deployment](docs/DEPLOYMENT.md)**: Docker Compose and PaaS deployment instructions.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.