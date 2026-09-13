# EventScout — Technical Interview Demo Guide

This document contains step-by-step walkthrough scripts for demonstrating EventScout's capabilities in a live engineering interview or portfolio review.

---

## 🎬 Demo 1: Multi-Source Discovery at Scale

**Goal**: Show that EventScout aggregates opportunities from 15 distinct platforms rather than a single website.

1. Open `http://localhost:3000` in your browser.
2. Note the count pill: `116 opportunities available`.
3. Switch primary tabs:
   - Click **All Events** (`116` total)
   - Click **⚡ Hackathons** (`59` hackathons from Devfolio, Devpost, MLH, HackerEarth, Unstop)
   - Click **🛠️ Workshops** (`20` workshops from GDG, Meetup, AWS, Microsoft Reactor)
4. Use the **Source** dropdown in the secondary filter row to filter by:
   - `devfolio`, `meetup`, `mlh`, `unstop`, `gdg`, `fossunited`, `iithyderabad`
5. Show that all cards render uniformly with source badges, dates, mode tags, and prices.

---

## 🎬 Demo 2: Autonomous Source Discovery (Gemini Agent)

**Goal**: Demonstrate how the system dynamically discovers how to scrape an unfamiliar event site without writing custom code.

1. Navigate to `http://localhost:3000/admin/sources` (or click **Admin Sources** in navigation).
2. Click **+ Add Source**.
3. Enter a new public event URL (e.g. `https://devpost.com/hackathons` or any community meetup link) and submit.
4. Explain the Gemini AI workflow:
   - Fetches the live HTML and checks for hidden REST / GraphQL endpoints.
   - Synthesizes an extraction recipe (CSS selectors, regexes, JSON paths).
   - Generates sample extracted event documents.
   - Puts the source in `PENDING` state.
5. Click **Test Scrape** to verify the extracted fields in the modal.
6. Click **Approve** to transition the source to `ENABLED` for automated scheduler runs.

---

## 🎬 Demo 3: Intelligent Event Ranking & "Why Recommended?"

**Goal**: Prove that ranking is not based on scrape recency, but rather host tier and technical value.

1. On the home page `http://localhost:3000`, observe the **🌟 Top Picks & High-Value Opportunities** section.
2. Highlight that premier tech leaders (AWS, Google, Microsoft) and premier institutes (IIT Hyderabad, IIIT Hyderabad) automatically appear at the top.
3. Point out the host badges: `Tier 1 Tech Leader` (purple), `Premier Institute` (green).
4. Click the **✨ Why recommended?** toggle on any top pick:
   - Show the generated explanation bullets:
     - `✓ Hosted by premier tech leader Amazon Web Services`
     - `✓ High-impact hands-on hackathon`
     - `✓ Free registration`
     - `✓ Happening in 4 days`
5. Emphasize that community events are still preserved in the **All Opportunities** feed.

---

## 🎬 Demo 4: User Personalization

**Goal**: Demonstrate that updating user profile interests reshuffles event rankings.

1. Log in with a user account (or use `sk` / `dev@eventscout.local`).
2. Navigate to your Profile (`/profile`).
3. Set your interests to `AI, Machine Learning, Python`.
4. Return to the home discovery feed:
   - Events involving AI, LLMs, and Python will be elevated to the top with explanations reading `✓ Matches your AI & Python interests`.
5. Return to profile, change interests to `Cloud, Kubernetes, DevOps`:
   - Refresh the home feed and watch AWS, Kubernetes, and Cloud workshops move to the top!

---

## 🎬 Demo 5: Chrome Browser Extension (Manifest V3)

**Goal**: Show seamless opportunity capture while browsing external websites.

1. Open a new tab and visit any hackathon or event page (e.g., `https://devpost.com/hackathons`).
2. Click the **EventScout Clipper** icon in the Chrome toolbar.
3. Show the extension popup:
   - Automatically extracted Title, Organizer, Mode, Date, and Description.
4. Click **Save to EventScout**:
   - Status updates to `✓ Saved to your EventScout dashboard!`.
5. Click **Open EventScout**:
   - Jump to `http://localhost:3000/saved` and show the newly saved event in the user's personal bookmarks.

---

## 🎬 Demo 6: Production Health, Resilience & Monitoring

**Goal**: Show observability, failure isolation, and scheduler health.

1. Open `http://localhost:3000/admin/sources`.
2. Inspect the **Source Health** table:
   - Shows Last Success, Status (`ENABLED`), Consecutive Failures (`0`), and Health metrics for all 15 sources.
3. Open backend terminal or test logs:
   - Show structured telemetry logs (`[SCRAPE_STARTED]`, `[SCRAPE_COMPLETED]`, `[ADMIN_SOURCE_APPROVED]`).
   - Point out that passwords and tokens are redacted (`***REDACTED***`).
4. Run automated test suite:
   ```bash
   .venv\Scripts\pytest tests/ -v
   ```
   - Show 8/8 passing tests covering ranking, filter combinations, and failure isolation.
